#include "../defines.h"
#include "../defines_battle.h"
#include "../../include/constants/battle_move_effects.h"
#include "../../include/constants/trainers.h"

#include "../../include/new/ai_master.h"
#include "../../include/new/ai_standard.h"
#include "../../include/new/ai_standard_policy.h"
#include "../../include/new/ai_standard_mechanics.h"
#include "../../include/new/battle_util.h"
#include "../../include/new/frontier.h"
#include "../../include/new/switching.h"
#include "../../include/new/util.h"

/*
 * This file is the only CFRU-facing Standard adapter.  Its inputs are either
 * own-trainer state, public active-battler state, or public engine results.
 * It never calls the legacy prediction/damage helpers: those helpers accept
 * bank IDs and may transitively inspect unrevealed player moves, items,
 * abilities, or stats.
 */

#define STANDARD_AI_PENDING_NONE 0xFF
#define STANDARD_AI_SWITCH_ID_BASE 4
#define STANDARD_AI_DEFAULT_SEED 0x51A1F512
#define STANDARD_AI_INT32_MAX 2147483647

void StandardAI_LoadMemory(u8 bank, struct StandardPolicyMemory* memory);
static void StandardAI_SaveMemory(u8 bank, const struct StandardPolicyMemory* memory);
static void StandardAI_FinalizeLastAction(u8 bank);
void StandardAI_StageLastAction(u8 bank, const struct StandardPolicyCandidate* candidate);
void StandardAI_BuildObservation(u8 bank, bool8 includeSwitches,
	struct StandardPolicyObservation* observation);

/* Only the displayed HP ratio crosses this boundary, never max HP or exact
 * current HP. Floor to the 48-pixel public bar; the builder restores an interval.
 * Both values are deliberately read ONLY here, not in mechanics/scoring. */
static u8 StandardAI_PublicHpPixels(u8 foe)
{
	u32 maximum = gBattleMons[foe].maxHP;
	u32 current = gBattleMons[foe].hp;
	if (!maximum) return 255;
	return current ? MathMax(1, MathMin(48, current * 48 / maximum)) : 0;
}

/* The history is populated by public ability messages. Do not infer an ability
 * from the actual species/hidden slot, or inspect the current hidden ability. */
static ability_t StandardAI_RevealedAbility(u8 bank)
{
	if (gStatuses3[bank] & STATUS3_ABILITY_SUPPRESS) return ABILITY_NONE;
	return BATTLE_HISTORY->abilities[bank];
}

u8 StandardAI_PublicTypeMultiplier(u8 attackType, u8 defenseType)
{
	u8 value;
	if (attackType >= NUMBER_OF_MON_TYPES || defenseType >= NUMBER_OF_MON_TYPES)
		return 10;
	value = gTypeEffectiveness[attackType][defenseType];
	/* CFRU encodes neutral as NO_DATA=0 and immunity as NO_EFFECT=1. */
	return value == TYPE_MUL_NO_DATA ? 10 : value == TYPE_MUL_NO_EFFECT ? 0 : value;
}

/* Baseline types belong to the PUBLIC appearance, not the hidden battler.
 * A publicly observed type-changing move/ability invalidates this baseline.
 * Until an explicit public dynamic-type model is supported, keep it UNKNOWN
 * (including failed applications: over-widening is safe). History contains
 * resolved/revealed moves, never queued choices. No current foe type is read. */
void StandardAI_ObservePublicMove(u16 move)
{
	u8 bank;
	switch (move)
	{
	case MOVE_CONVERSION: case MOVE_CONVERSION2: case MOVE_CAMOUFLAGE:
	case MOVE_REFLECTTYPE: case MOVE_SOAK: case MOVE_TRICKORTREAT:
	case MOVE_FORESTSCURSE: case MOVE_MAGICPOWDER: case MOVE_TRANSFORM:
	case MOVE_BURNUP: case MOVE_DOUBLESHOCK: case MOVE_ROOST:
		/* Deliberately over-wide: retain uncertainty after history eviction,
		 * switches, or ability replacement. Never recover by reading real types. */
		if (gNewBS != NULL)
			for (bank = 0; bank < MAX_BATTLERS_COUNT; ++bank)
				gNewBS->ai.standardTypeUncertain[bank] = TRUE;
	}
}

void StandardAI_ObservePublicAbility(u8 bank, u8 ability)
{
	if (gNewBS != NULL && bank < MAX_BATTLERS_COUNT
		&& (ability == ABILITY_COLORCHANGE || ability == ABILITY_PROTEAN))
		gNewBS->ai.standardTypeUncertain[bank] = TRUE;
}

bool8 StandardAI_GetPublicTypes(u8 foe, u8 types[3])
{
	u16 species = gNewBS->ai.standardDisplayedSpecies[foe];
	u8 bank, slot;
	ability_t ability = BATTLE_HISTORY->abilities[foe];
	if (species == SPECIES_NONE || species >= NUM_SPECIES
		|| gNewBS->ai.standardTypeUncertain[foe]
		|| ability == ABILITY_COLORCHANGE || ability == ABILITY_PROTEAN
		|| (gBattleMons[foe].status2 & STATUS2_TRANSFORMED)
		|| gNewBS->teraData.done[SIDE(foe)][gBattlerPartyIndexes[foe]]) return FALSE;
	for (bank = 0; bank < 2; ++bank)
		for (slot = 0; slot < MAX_MON_MOVES; ++slot)
			switch (BATTLE_HISTORY->usedMoves[bank][slot])
			{
			case MOVE_CONVERSION: case MOVE_CONVERSION2: case MOVE_CAMOUFLAGE:
			case MOVE_REFLECTTYPE: case MOVE_SOAK: case MOVE_TRICKORTREAT:
			case MOVE_FORESTSCURSE: case MOVE_MAGICPOWDER: case MOVE_TRANSFORM:
			case MOVE_BURNUP: case MOVE_DOUBLESHOCK: case MOVE_ROOST:
				return FALSE;
			}
	types[0] = gBaseStats[species].type1;
	types[1] = gBaseStats[species].type2;
	types[2] = NUMBER_OF_MON_TYPES;
	return TRUE;
}

static u8 StandardAI_KnownTypeImmunity(u16 move, u8 bankDef)
{
	ability_t knownAbility;
	u8 type;
	u8 types[3];

	if (move == MOVE_NONE || SPLIT(move) == SPLIT_STATUS)
		return FALSE;
	type = gBattleMoves[move].type;
	if (type >= NUMBER_OF_MON_TYPES)
		return FALSE;
	knownAbility = StandardAI_RevealedAbility(bankDef);
	if ((knownAbility == ABILITY_LEVITATE || knownAbility == ABILITY_EARTHEATER) && type == TYPE_GROUND)
		return TRUE;
	if (knownAbility == ABILITY_FLASHFIRE && type == TYPE_FIRE)
		return TRUE;
	if ((knownAbility == ABILITY_WATERABSORB
		|| knownAbility == ABILITY_DRYSKIN
		|| knownAbility == ABILITY_STORMDRAIN) && type == TYPE_WATER)
		return TRUE;
	if ((knownAbility == ABILITY_VOLTABSORB
		|| knownAbility == ABILITY_LIGHTNINGROD
		|| knownAbility == ABILITY_MOTORDRIVE) && type == TYPE_ELECTRIC)
		return TRUE;
	if (knownAbility == ABILITY_SAPSIPPER && type == TYPE_GRASS)
		return TRUE;
	if (!StandardAI_GetPublicTypes(bankDef, types)) return FALSE;
	return StandardAI_PublicTypeMultiplier(type, types[0]) == 0
		|| StandardAI_PublicTypeMultiplier(type, types[1]) == 0;
}

static u8 StandardAI_StageForFamily(u8 family)
{
	switch (family)
	{
	case STANDARD_EFFECT_ATTACK_UP:
	case STANDARD_EFFECT_ATTACK_DOWN:
		return STAT_STAGE_ATK;
	case STANDARD_EFFECT_DEFENSE_UP:
	case STANDARD_EFFECT_DEFENSE_DOWN:
		return STAT_STAGE_DEF;
	case STANDARD_EFFECT_SPEED_UP:
	case STANDARD_EFFECT_SPEED_DOWN:
		return STAT_STAGE_SPEED;
	case STANDARD_EFFECT_SPECIAL_ATTACK_UP:
	case STANDARD_EFFECT_SPECIAL_ATTACK_DOWN:
		return STAT_STAGE_SPATK;
	case STANDARD_EFFECT_SPECIAL_DEFENSE_UP:
	case STANDARD_EFFECT_SPECIAL_DEFENSE_DOWN:
		return STAT_STAGE_SPDEF;
	case STANDARD_EFFECT_ACCURACY_DOWN:
	case STANDARD_EFFECT_ACCURACY_UP:
		return STAT_STAGE_ACC;
	case STANDARD_EFFECT_EVASION_DOWN:
	case STANDARD_EFFECT_EVASION_UP:
		return STAT_STAGE_EVASION;
	default:
		return 0;
	}
}

static u8 StandardAI_IsMajorStatusEffect(u8 effect)
{
	switch (effect)
	{
	case EFFECT_SLEEP:
	case EFFECT_TOXIC:
	case EFFECT_POISON:
	case EFFECT_PARALYZE:
	case EFFECT_WILL_O_WISP:
		return TRUE;
	default:
		return FALSE;
	}
}

static u8 StandardAI_FamilyForEffect(u8 effect)
{
	switch (effect)
	{
	case EFFECT_ACCURACY_DOWN:
	case EFFECT_ACCURACY_DOWN_2:
		return STANDARD_EFFECT_ACCURACY_DOWN;
	case EFFECT_SPEED_DOWN:
	case EFFECT_SPEED_DOWN_2:
		return STANDARD_EFFECT_SPEED_DOWN;
	case EFFECT_ATTACK_UP:
	case EFFECT_ATTACK_UP_2:
		return STANDARD_EFFECT_ATTACK_UP;
	case EFFECT_DEFENSE_UP:
	case EFFECT_DEFENSE_UP_2:
		return STANDARD_EFFECT_DEFENSE_UP;
	case EFFECT_SPEED_UP:
	case EFFECT_SPEED_UP_2:
		return STANDARD_EFFECT_SPEED_UP;
	case EFFECT_SPECIAL_ATTACK_UP:
	case EFFECT_SPECIAL_ATTACK_UP_2:
		return STANDARD_EFFECT_SPECIAL_ATTACK_UP;
	case EFFECT_SPECIAL_DEFENSE_UP:
	case EFFECT_SPECIAL_DEFENSE_UP_2:
		return STANDARD_EFFECT_SPECIAL_DEFENSE_UP;
	case EFFECT_EVASION_UP:
	case EFFECT_EVASION_UP_2:
		return STANDARD_EFFECT_EVASION_UP;
	case EFFECT_ATTACK_DOWN:
	case EFFECT_ATTACK_DOWN_2:
		return STANDARD_EFFECT_ATTACK_DOWN;
	case EFFECT_DEFENSE_DOWN:
	case EFFECT_DEFENSE_DOWN_2:
		return STANDARD_EFFECT_DEFENSE_DOWN;
	case EFFECT_SPECIAL_ATTACK_DOWN:
	case EFFECT_SPECIAL_ATTACK_DOWN_2:
		return STANDARD_EFFECT_SPECIAL_ATTACK_DOWN;
	case EFFECT_SPECIAL_DEFENSE_DOWN:
	case EFFECT_SPECIAL_DEFENSE_DOWN_2:
		return STANDARD_EFFECT_SPECIAL_DEFENSE_DOWN;
	case EFFECT_EVASION_DOWN:
	case EFFECT_EVASION_DOWN_2:
		return STANDARD_EFFECT_EVASION_DOWN;
	default:
		return STANDARD_EFFECT_NONE;
	}
}

static u8 StandardAI_EffectDelta(u8 effect)
{
	switch (effect)
	{
	case EFFECT_ACCURACY_DOWN_2:
	case EFFECT_SPEED_DOWN_2:
	case EFFECT_ATTACK_UP_2:
	case EFFECT_DEFENSE_UP_2:
	case EFFECT_SPEED_UP_2:
	case EFFECT_SPECIAL_ATTACK_UP_2:
	case EFFECT_SPECIAL_DEFENSE_UP_2:
	case EFFECT_EVASION_UP_2:
	case EFFECT_ATTACK_DOWN_2:
	case EFFECT_DEFENSE_DOWN_2:
	case EFFECT_SPECIAL_ATTACK_DOWN_2:
	case EFFECT_SPECIAL_DEFENSE_DOWN_2:
	case EFFECT_EVASION_DOWN_2:
		return 2;
	default:
		return 1;
	}
}

static u8 StandardAI_IsSelfStageEffect(u8 effect)
{
	return effect == EFFECT_ATTACK_UP || effect == EFFECT_ATTACK_UP_2
		|| effect == EFFECT_DEFENSE_UP || effect == EFFECT_DEFENSE_UP_2
		|| effect == EFFECT_SPEED_UP || effect == EFFECT_SPEED_UP_2
		|| effect == EFFECT_SPECIAL_ATTACK_UP || effect == EFFECT_SPECIAL_ATTACK_UP_2
		|| effect == EFFECT_SPECIAL_DEFENSE_UP || effect == EFFECT_SPECIAL_DEFENSE_UP_2
		|| effect == EFFECT_EVASION_UP || effect == EFFECT_EVASION_UP_2;
}

static u8 StandardAI_IsSelfStageFamily(u8 family)
{
	return family == STANDARD_EFFECT_ATTACK_UP
		|| family == STANDARD_EFFECT_DEFENSE_UP
		|| family == STANDARD_EFFECT_SPEED_UP
		|| family == STANDARD_EFFECT_SPECIAL_ATTACK_UP
		|| family == STANDARD_EFFECT_SPECIAL_DEFENSE_UP
		|| family == STANDARD_EFFECT_EVASION_UP;
}

static u8 StandardAI_IsForcedMove(u8 bank, u16 move)
{
	if (gBattleMons[bank].status2 & (STATUS2_RECHARGE | STATUS2_MULTIPLETURNS))
		return gLockedMoves[bank] != MOVE_NONE && gLockedMoves[bank] == move;
	if (gDisableStructs[bank].encoreTimer && gDisableStructs[bank].encoredMove == move)
		return TRUE;
	return FALSE;
}

/* Explicit constant-power, single-hit subset: no recoil, self-KO, variable
 * power, charging, contact-dependent power, or item removal. Secondary effects
 * receive no speculative positive utility; the direct damage is supported. */
bool8 StandardAI_IsSupportedDamage(u16 move)
{
	switch (move)
	{
	case MOVE_TACKLE: case MOVE_POUND: case MOVE_SCRATCH: case MOVE_QUICKATTACK:
	case MOVE_VINEWHIP: case MOVE_WATERGUN: case MOVE_HORNATTACK: case MOVE_PECK:
	case MOVE_WINGATTACK: case MOVE_SWIFT: case MOVE_AERIALACE:
	case MOVE_DRAGONCLAW: case MOVE_DRAGONPULSE: case MOVE_STRENGTH:
	case MOVE_EMBER: case MOVE_FLAMETHROWER: case MOVE_ICEBEAM:
	case MOVE_THUNDERSHOCK: case MOVE_THUNDERBOLT: case MOVE_BUBBLE:
	case MOVE_CONFUSION: case MOVE_PSYCHIC: case MOVE_BITE: case MOVE_CRUNCH:
	case MOVE_METALCLAW: case MOVE_ROCKTHROW: case MOVE_ROCKSLIDE:
	case MOVE_SURF: case MOVE_RAZORLEAF: case MOVE_LEAFBLADE:
	case MOVE_ENERGYBALL: case MOVE_SHADOWBALL: case MOVE_FLASHCANNON:
		return TRUE;
	default: return FALSE;
	}
}

static void StandardAI_ProjectDamage(u8 bank, u8 foe, u16 move,
	const struct StandardPolicyCandidate* candidate, struct StandardMechanicsInput* out)
{
	struct StandardMechanicsInput input;
	u16 species = gNewBS->ai.standardDisplayedSpecies[foe];
	u8 split = SPLIT(move);
	u8 type = gBattleMoves[move].type;
	u8 types[3] = {NUMBER_OF_MON_TYPES, NUMBER_OF_MON_TYPES, NUMBER_OF_MON_TYPES};
	bool8 publicTypes = StandardAI_GetPublicTypes(foe, types);
	u8 i;
	if (species >= NUM_SPECIES) species = SPECIES_NONE;
	Memset(&input, 0, sizeof(input));
	input.power = gBattleMoves[move].power;
	input.attack = split == SPLIT_PHYSICAL ? gBattleMons[bank].attack : gBattleMons[bank].spAttack;
	input.attack_stage = gBattleMons[bank].statStages[(split == SPLIT_PHYSICAL ? STAT_STAGE_ATK : STAT_STAGE_SPATK) - 1];
	input.defense_stage = gBattleMons[foe].statStages[(split == SPLIT_PHYSICAL ? STAT_STAGE_DEF : STAT_STAGE_SPDEF) - 1];
	input.level = gBattleMons[bank].level;
	input.target_level = gBattleMons[foe].level;
	input.base_defense = split == SPLIT_PHYSICAL ? gBaseStats[species].baseDefense : gBaseStats[species].baseSpDefense;
	input.base_hp = gBaseStats[species].baseHP;
	input.shedinja = species == SPECIES_SHEDINJA;
	input.hp_pixels = StandardAI_PublicHpPixels(foe);
	input.accuracy = gBattleMoves[move].accuracy;
	input.accuracy_stage = gBattleMons[bank].statStages[STAT_STAGE_ACC - 1];
	input.evasion_stage = gBattleMons[foe].statStages[STAT_STAGE_EVASION - 1];
	input.stab = type == gBattleMons[bank].type1 || type == gBattleMons[bank].type2 || type == gBattleMons[bank].type3;
	input.own_burn = split == SPLIT_PHYSICAL && (gBattleMons[bank].status1 & STATUS_BURN);
	input.known_immunity = candidate->known_no_effect;
	input.supported_damage = species != SPECIES_NONE && species < NUM_SPECIES
		&& publicTypes && StandardAI_IsSupportedDamage(move);
	for (i = 0; i < 3; ++i)
		input.effectiveness[i] = types[i] >= NUMBER_OF_MON_TYPES
			|| (i > 0 && types[i] == types[0]) || (i > 1 && types[i] == types[1])
			? 10 : StandardAI_PublicTypeMultiplier(type, types[i]);
	/* The initial CERTIFIED envelope deliberately requires public suppression
	 * of both abilities and held items. Hidden Sash/Band/Sturdy/absorbers are
	 * never assumed absent. Other contexts still receive a nominal estimate
	 * but a [0,65535] complete envelope and cannot claim a robust KO. */
	input.certified_modifiers = (gStatuses3[bank] == STATUS3_ABILITY_SUPPRESS)
		&& (gStatuses3[foe] == STATUS3_ABILITY_SUPPRESS)
		&& gNewBS->MagicRoomTimer > 1 && !gBattleWeather && !gNewBS->TerrainTimer
		&& !gNewBS->WonderRoomTimer && !gNewBS->TrickRoomTimer
		&& !gNewBS->IonDelugeTimer && !gNewBS->ElectrifyTimers[bank]
		&& !gNewBS->MudSportTimer && !gNewBS->WaterSportTimer
		&& !gNewBS->AuroraVeilTimers[SIDE(foe)]
		&& !gSideStatuses[SIDE(bank)] && !gSideStatuses[SIDE(foe)]
		&& !gBattleMons[bank].status2 && gBattleMons[foe].status2 == STATUS2_RECHARGE
		&& !gNewBS->teraData.done[SIDE(bank)][gBattlerPartyIndexes[bank]]
		&& !gNewBS->teraData.done[SIDE(foe)][gBattlerPartyIndexes[foe]];
	/* The selected engine has a species-based Tera Shell modifier even with
	 * ability suppression. Do not certify that known special-case species. */
	if (species == SPECIES_TERAPAGOS
	#ifdef SPECIES_TERAPAGOS_TERA
		|| species == SPECIES_TERAPAGOS_TERA
	#endif
	)
		input.certified_modifiers = FALSE;
	/* Public recharge precludes every unrevealed opponent move this turn.
	 * No speed guess, submitted choice, or future damage roll certifies survival. */
	input.can_act_safely = input.certified_modifiers && gBattleMons[bank].hp != 0
		&& !(gBattleMons[bank].status1 & (STATUS_SLEEP | STATUS_FREEZE | STATUS_PARALYSIS));
	*out = input;
}

static void StandardAI_DeriveDamage(u8 bank, u8 foe, u16 move,
	struct StandardPolicyCandidate* candidate, struct StandardDamageEnvelope* report)
{
	struct StandardMechanicsInput input;
	struct StandardDamageEnvelope envelope;
	StandardAI_ProjectDamage(bank, foe, move, candidate, &input);
	StandardMechanicsDamage(&input, candidate, &envelope);
	if (report != NULL) *report = envelope;
}

void StandardAI_DeriveDamageWithCertificate(u8 bank, u8 foe, u16 move,
	struct StandardPolicyCandidate* candidate, bool8 certified)
{
	struct StandardMechanicsInput input;
	struct StandardDamageEnvelope envelope;
	StandardAI_ProjectDamage(bank, foe, move, candidate, &input);
	/* Ironmon supplies an independently narrow public modifier certificate.
	 * Reuse the exact Standard projection/mechanics arithmetic, changing only
	 * the certificate bit that controls complete-envelope and robust-KO claims. */
	input.certified_modifiers = certified;
	input.can_act_safely = certified && gBattleMons[bank].hp != 0
		&& !(gBattleMons[bank].status1 & (STATUS_SLEEP | STATUS_FREEZE | STATUS_PARALYSIS));
	StandardMechanicsDamage(&input, candidate, &envelope);
}

static u8 StandardAI_MoveLegal(u8 bank, u8 movePos, u16 move, u8 forcedMove)
{
	if (move == MOVE_NONE || gBattleMons[bank].pp[movePos] == 0)
		return FALSE;
	if (forcedMove && !StandardAI_IsForcedMove(bank, move))
		return FALSE;
	if (!forcedMove && StandardAI_IsForcedMove(bank, move))
		return FALSE;
	if (gDisableStructs[bank].disabledMove == move)
		return FALSE;
	if ((gBattleMons[bank].status2 & STATUS2_TORMENT) && gLastUsedMoves[bank] == move)
		return FALSE;
	if (gDisableStructs[bank].tauntTimer && SPLIT(move) == SPLIT_STATUS)
		return FALSE;
	if (gDisableStructs[bank].encoreTimer && gDisableStructs[bank].encoredMove != move)
		return FALSE;
	if (gBattleStruct->choicedMove[bank] != MOVE_NONE
		&& gBattleStruct->choicedMove[bank] != 0xFFFF
		&& gBattleStruct->choicedMove[bank] != move)
		return FALSE;
	return TRUE;
}

/* One supported follow-up, not a class bonus. Unknown incoming threats do not
 * certify defensive utility. Stage changes never mutate engine state here. */
static u8 StandardAI_FollowupValue(u8 bank, u8 foe, u8 family, u8 afterStage)
{
	u8 slot, best = 0;
	for (slot = 0; slot < MAX_MON_MOVES; ++slot)
	{
		u16 move = gBattleMons[bank].moves[slot];
		struct StandardMechanicsInput before, after;
		struct StandardPolicyCandidate old = {0}, next = {0};
		struct StandardDamageEnvelope envelope;
		s32 gain;
		if (!StandardAI_IsSupportedDamage(move) || !StandardAI_MoveLegal(bank, slot, move, FALSE)) continue;
		/* Speed value is meaningful only for an ordinary-priority follow-up. */
		if (family == STANDARD_EFFECT_SPEED_DOWN || family == STANDARD_EFFECT_SPEED_UP)
		{
			if (gBattleMoves[move].priority != 0) continue;
		}
		else if (SPLIT(move) == SPLIT_PHYSICAL)
		{
			if (family != STANDARD_EFFECT_ATTACK_UP && family != STANDARD_EFFECT_DEFENSE_DOWN) continue;
		}
		else if (family != STANDARD_EFFECT_SPECIAL_ATTACK_UP && family != STANDARD_EFFECT_SPECIAL_DEFENSE_DOWN) continue;
		old.known_no_effect = StandardAI_KnownTypeImmunity(move, foe);
		StandardAI_ProjectDamage(bank, foe, move, &old, &before);
		after = before;
		if (family == STANDARD_EFFECT_ATTACK_UP || family == STANDARD_EFFECT_SPECIAL_ATTACK_UP)
			after.attack_stage = afterStage;
		if (family == STANDARD_EFFECT_DEFENSE_DOWN || family == STANDARD_EFFECT_SPECIAL_DEFENSE_DOWN)
			after.defense_stage = afterStage;
		StandardMechanicsDamage(&before, &old, &envelope);
		StandardMechanicsDamage(&after, &next, &envelope);
		gain = (next.opponent_hp_fraction_lost - old.opponent_hp_fraction_lost) * 100 / 256;
		if (family == STANDARD_EFFECT_SPEED_DOWN || family == STANDARD_EFFECT_SPEED_UP)
			gain = old.opponent_hp_fraction_lost * 100 / 256;
		if (gain > best) best = MathMin(40, gain);
	}
	return best;
}

bool8 StandardAI_FindSetupFollowup(u8 bank, u8 foe, u8 family, u8 afterStage,
	struct StandardSetupFollowup* out)
{
	u8 slot;
	Memset(out, 0, sizeof(*out));
	for (slot = 0; slot < MAX_MON_MOVES; ++slot)
	{
		u16 move = gBattleMons[bank].moves[slot];
		struct StandardMechanicsInput before, after;
		struct StandardPolicyCandidate old = {0}, next = {0};
		struct StandardDamageEnvelope envelope;
		if (!StandardAI_IsSupportedDamage(move)
			|| !StandardAI_MoveLegal(bank, slot, move, FALSE))
			continue;
		if (family == STANDARD_EFFECT_SPEED_DOWN || family == STANDARD_EFFECT_SPEED_UP)
		{
			if (gBattleMoves[move].priority != 0) continue;
		}
		else if (family == STANDARD_EFFECT_ATTACK_UP || family == STANDARD_EFFECT_DEFENSE_DOWN)
		{
			if (SPLIT(move) != SPLIT_PHYSICAL) continue;
		}
		else if (family == STANDARD_EFFECT_SPECIAL_ATTACK_UP
			|| family == STANDARD_EFFECT_SPECIAL_DEFENSE_DOWN)
		{
			if (SPLIT(move) != SPLIT_SPECIAL) continue;
		}
		else continue;
		old.known_no_effect = StandardAI_KnownTypeImmunity(move, foe);
		StandardAI_ProjectDamage(bank, foe, move, &old, &before);
		after = before;
		if (family == STANDARD_EFFECT_ATTACK_UP || family == STANDARD_EFFECT_SPECIAL_ATTACK_UP)
			after.attack_stage = afterStage;
		if (family == STANDARD_EFFECT_DEFENSE_DOWN || family == STANDARD_EFFECT_SPECIAL_DEFENSE_DOWN)
			after.defense_stage = afterStage;
		StandardMechanicsDamage(&before, &old, &envelope);
		StandardMechanicsDamage(&after, &next, &envelope);
		/* Keep a deterministic first slot on equal facts. */
		if (!out->found || next.opponent_hp_fraction_lost > out->after_fraction)
		{
			out->found = TRUE;
			out->slot = slot;
			out->split = SPLIT(move);
			out->priority = gBattleMoves[move].priority;
			out->move = move;
			out->before_fraction = old.opponent_hp_fraction_lost;
			out->after_fraction = next.opponent_hp_fraction_lost;
		}
	}
	return out->found;
}

/* Only certify an order flip across the ENTIRE public Speed interval. Unknown
 * ability/item multipliers preclude a certificate; the narrow suppression
 * context intentionally gives no Speed credit elsewhere. Public Trick Room
 * reverses comparisons. Ties and overlapping intervals earn no credit. */
static bool8 StandardAI_SpeedFlip(u8 bank, u8 foe, u8 family, u8 afterStage, bool8 paralysis)
{
	u16 species = gNewBS->ai.standardDisplayedSpecies[foe];
	u32 own, ownAfter, low, high, lowAfter, highAfter;
	u8 stage = gBattleMons[foe].statStages[STAT_STAGE_SPEED - 1];
	if (!species || species >= NUM_SPECIES || !gBattleMons[bank].speed
		|| !(gStatuses3[bank] & STATUS3_ABILITY_SUPPRESS)
		|| !(gStatuses3[foe] & STATUS3_ABILITY_SUPPRESS)
		|| gNewBS->MagicRoomTimer <= 1 || gBattleWeather || gNewBS->TerrainTimer
		|| gNewBS->TailwindTimers[0] || gNewBS->TailwindTimers[1]
		|| gNewBS->SwampTimers[0] || gNewBS->SwampTimers[1]
		|| gSideStatuses[0] || gSideStatuses[1]) return FALSE;
	#if defined(FLAG_WEIGHT_SPEED_BATTLE) || defined(FLAG_TAILWIND_BATTLE)
	return FALSE; /* Optional rule flags have no certified public model. */
	#endif
	own = StandardMechanicsStage(gBattleMons[bank].speed, gBattleMons[bank].statStages[STAT_STAGE_SPEED - 1]);
	ownAfter = family == STANDARD_EFFECT_SPEED_UP ? StandardMechanicsStage(gBattleMons[bank].speed, afterStage) : own;
	low = StandardMechanicsSpeed(gBaseStats[species].baseSpeed, gBattleMons[foe].level, stage, 0);
	high = StandardMechanicsSpeed(gBaseStats[species].baseSpeed, gBattleMons[foe].level, stage, 1);
	lowAfter = family == STANDARD_EFFECT_SPEED_DOWN ? StandardMechanicsSpeed(gBaseStats[species].baseSpeed, gBattleMons[foe].level, afterStage, 0) : low;
	highAfter = family == STANDARD_EFFECT_SPEED_DOWN ? StandardMechanicsSpeed(gBaseStats[species].baseSpeed, gBattleMons[foe].level, afterStage, 1) : high;
	#ifdef BADGE_BOOSTS
	/* Badge ownership is not observed here; conservatively include both cases. */
	high = high * 110 / 100; highAfter = highAfter * 110 / 100;
	#endif
	#ifdef OLD_PARALYSIS_SPD_DROP
	#define STANDARD_PARALYSIS_DIVISOR 4
	#else
	#define STANDARD_PARALYSIS_DIVISOR 2
	#endif
	if (gBattleMons[bank].status1 & STATUS_PARALYSIS) { own /= STANDARD_PARALYSIS_DIVISOR; ownAfter /= STANDARD_PARALYSIS_DIVISOR; }
	if (gBattleMons[foe].status1 & STATUS_PARALYSIS) { low /= STANDARD_PARALYSIS_DIVISOR; high /= STANDARD_PARALYSIS_DIVISOR; }
	if (paralysis || (gBattleMons[foe].status1 & STATUS_PARALYSIS)) { lowAfter /= STANDARD_PARALYSIS_DIVISOR; highAfter /= STANDARD_PARALYSIS_DIVISOR; }
	if (gNewBS->TrickRoomTimer > 1) return own > high && ownAfter < lowAfter;
	if (gNewBS->TrickRoomTimer) return FALSE; /* expires before this follow-up */
	return own < low && ownAfter > highAfter;
}

/* Revealed incoming moves only. This is a nominal one-exposure model, not a
 * prediction that the player selects that move. Attacking stats are bounded
 * from displayed species, never the player's private values. */
static u8 StandardAI_DefensiveValue(u8 bank, u8 foe, u8 family, u8 afterStage)
{
	u16 species = gNewBS->ai.standardDisplayedSpecies[foe];
	u8 slot, best = 0, types[3];
	if (!StandardAI_GetPublicTypes(foe, types)) return 0;
	if (gBattleWeather || gNewBS->TerrainTimer || gSideStatuses[SIDE(bank)]
		|| gBattleMons[bank].status2
		|| (!(gStatuses3[bank] & STATUS3_ABILITY_SUPPRESS) && gBattleMons[bank].ability != ABILITY_NONE)
		|| (!gNewBS->MagicRoomTimer && gBattleMons[bank].item != ITEM_NONE)) return 0;
	for (slot = 0; slot < MAX_MON_MOVES; ++slot)
	{
		u16 move = BATTLE_HISTORY->usedMoves[foe][slot], base;
		u8 split, type, ownTypes[3], i;
		struct StandardMechanicsInput before = {0}, after;
		struct StandardPolicyCandidate old = {0}, next = {0};
		struct StandardDamageEnvelope envelope;
		s32 gain;
		if (!StandardAI_IsSupportedDamage(move)) continue;
		split = SPLIT(move); type = gBattleMoves[move].type;
		if (split == SPLIT_PHYSICAL)
		{
			if (family != STANDARD_EFFECT_DEFENSE_UP && family != STANDARD_EFFECT_ATTACK_DOWN) continue;
			base = gBaseStats[species].baseAttack;
			before.known_defense = gBattleMons[bank].defense;
		}
		else
		{
			if (family != STANDARD_EFFECT_SPECIAL_DEFENSE_UP && family != STANDARD_EFFECT_SPECIAL_ATTACK_DOWN) continue;
			base = gBaseStats[species].baseSpAttack;
			before.known_defense = gBattleMons[bank].spDefense;
		}
		if (!before.known_defense || !gBattleMons[bank].maxHP) continue;
		before.attack = (StandardMechanicsSpeed(base, gBattleMons[foe].level, 6, 0)
			+ StandardMechanicsSpeed(base, gBattleMons[foe].level, 6, 1)) / 2;
		before.power = gBattleMoves[move].power;
		before.level = gBattleMons[foe].level; before.target_level = gBattleMons[bank].level;
		before.attack_stage = gBattleMons[foe].statStages[(split == SPLIT_PHYSICAL ? STAT_STAGE_ATK : STAT_STAGE_SPATK) - 1];
		before.defense_stage = gBattleMons[bank].statStages[(split == SPLIT_PHYSICAL ? STAT_STAGE_DEF : STAT_STAGE_SPDEF) - 1];
		before.known_max_hp = gBattleMons[bank].maxHP; before.known_hp = gBattleMons[bank].hp;
		before.hp_pixels = 255;
		before.accuracy = gBattleMoves[move].accuracy;
		before.accuracy_stage = gBattleMons[foe].statStages[STAT_STAGE_ACC - 1];
		before.evasion_stage = gBattleMons[bank].statStages[STAT_STAGE_EVASION - 1];
		before.stab = type == types[0] || type == types[1];
		before.own_burn = split == SPLIT_PHYSICAL && (gBattleMons[foe].status1 & STATUS_BURN);
		ownTypes[0] = gBattleMons[bank].type1; ownTypes[1] = gBattleMons[bank].type2; ownTypes[2] = gBattleMons[bank].type3;
		for (i = 0; i < 3; ++i)
		{
			before.effectiveness[i] = (i && ownTypes[i] == ownTypes[0]) || (i == 2 && ownTypes[i] == ownTypes[1])
				? 10 : StandardAI_PublicTypeMultiplier(type, ownTypes[i]);
			if (!before.effectiveness[i]) before.known_immunity = TRUE;
		}
		before.supported_damage = TRUE;
		after = before;
		if (family == STANDARD_EFFECT_DEFENSE_UP || family == STANDARD_EFFECT_SPECIAL_DEFENSE_UP) after.defense_stage = afterStage;
		else after.attack_stage = afterStage;
		StandardMechanicsDamage(&before, &old, &envelope);
		StandardMechanicsDamage(&after, &next, &envelope);
		gain = (old.opponent_hp_fraction_lost - next.opponent_hp_fraction_lost) * 100 / 256;
		if (gain > best) best = MathMin(40, gain);
	}
	return best;
}

static void StandardAI_StageMarginal(u8 bank, u8 foe, struct StandardPolicyCandidate* c)
{
	u8 family = c->effect_family;
	if (c->stat_stage_before == c->stat_stage_after) return;
	if (family == STANDARD_EFFECT_ACCURACY_DOWN) { StandardMechanicsAccuracy(c); return; }
	if ((family == STANDARD_EFFECT_SPEED_DOWN || family == STANDARD_EFFECT_SPEED_UP)
		&& !StandardAI_SpeedFlip(bank, foe, family, c->stat_stage_after, FALSE)) return;
	c->immediate_future_gain = StandardAI_FollowupValue(bank, foe, family, c->stat_stage_after);
	if (family == STANDARD_EFFECT_DEFENSE_UP || family == STANDARD_EFFECT_SPECIAL_DEFENSE_UP
		|| family == STANDARD_EFFECT_ATTACK_DOWN || family == STANDARD_EFFECT_SPECIAL_ATTACK_DOWN)
		c->immediate_future_gain = StandardAI_DefensiveValue(bank, foe, family, c->stat_stage_after);
	c->productive = c->immediate_future_gain > 0;
	/* Follow-up estimates retain uncertainty; no hidden modifier is assumed. */
	c->uncertainty_cost = c->immediate_future_gain / 2;
}

static void StandardAI_StatusMarginal(u8 bank, u8 foe, u8 effect, struct StandardPolicyCandidate* c)
{
	u8 types[3], fraction = 0;
	ability_t ability = StandardAI_RevealedAbility(foe);
	c->public_major_status = TRUE;
	c->redundant_status = (gBattleMons[foe].status1 & STATUS_ANY) != 0;
	if (c->redundant_status) return;
	if (!StandardAI_GetPublicTypes(foe, types)) return;
	if (((effect == EFFECT_POISON || effect == EFFECT_TOXIC) && ability == ABILITY_IMMUNITY)
		|| (effect == EFFECT_WILL_O_WISP && ability == ABILITY_WATERVEIL)
		|| (effect == EFFECT_PARALYZE && ability == ABILITY_LIMBER)
		|| (effect == EFFECT_SLEEP && ability == ABILITY_INSOMNIA))
	{ c->known_no_effect = TRUE; return; }
	if (((effect == EFFECT_POISON || effect == EFFECT_TOXIC)
		&& (types[0] == TYPE_POISON || types[1] == TYPE_POISON || types[0] == TYPE_STEEL || types[1] == TYPE_STEEL))
		|| (effect == EFFECT_WILL_O_WISP && (types[0] == TYPE_FIRE || types[1] == TYPE_FIRE))
		|| (effect == EFFECT_PARALYZE && (types[0] == TYPE_ELECTRIC || types[1] == TYPE_ELECTRIC)))
	{ c->known_no_effect = TRUE; return; }
	/* One end-turn residual only, clipped by the public remaining HP bar.
	 * Burn receives residual value only. Sleep/action-loss remains unsupported
	 * (zero), rather than receiving a generic major-status bonus. */
	if (effect == EFFECT_POISON) fraction = 32;
	if (effect == EFFECT_TOXIC || effect == EFFECT_WILL_O_WISP) fraction = 16;
	#ifdef OLD_BURN_DAMAGE
	if (effect == EFFECT_WILL_O_WISP) fraction = 32;
	#endif
	if (ability == ABILITY_MAGICGUARD || ((effect == EFFECT_POISON || effect == EFFECT_TOXIC)
		&& ability == ABILITY_POISONHEAL)) fraction = 0;
	if (fraction)
	{
		u8 pixels = StandardAI_PublicHpPixels(foe);
		if (pixels > 48) return;
		fraction = MathMin(fraction, pixels * 256 / 48);
		c->immediate_future_gain = fraction * 100 / 256;
	}
	if (effect == EFFECT_PARALYZE && StandardAI_SpeedFlip(bank, foe, STANDARD_EFFECT_NONE, 0, TRUE))
		c->immediate_future_gain = StandardAI_FollowupValue(bank, foe, STANDARD_EFFECT_SPEED_DOWN, 0);
	c->immediate_future_gain = c->immediate_future_gain * (c->accuracy ? c->accuracy : 100) / 100;
	c->productive = c->immediate_future_gain > 0;
	/* Unknown ability/item status blockers are uncertainty, not read or ruled out. */
	c->uncertainty_cost = c->immediate_future_gain / 2;
}

static void StandardAI_FillMoveCandidate(u8 bank, u8 foe, u8 movePos,
	struct StandardPolicyCandidate* candidate, u8 forcedMove)
{
	u16 move = gBattleMons[bank].moves[movePos];
	u8 effect = move == MOVE_NONE ? 0 : gBattleMoves[move].effect;
	u8 family = StandardAI_FamilyForEffect(effect);
	u8 stageId = StandardAI_StageForFamily(family);
	u8 targetBank = StandardAI_IsSelfStageEffect(effect) ? bank : foe;
	u8 stageBefore = stageId == 0 ? 0 : gBattleMons[targetBank].statStages[stageId - 1];
	u8 delta = StandardAI_EffectDelta(effect);
	u8 statusMove = move != MOVE_NONE && SPLIT(move) == SPLIT_STATUS;
	u8 knownNoEffect = StandardAI_KnownTypeImmunity(move, foe);
	u8 stageAfter = stageBefore;
	u16 missingHpFraction = 0;

	Memset(candidate, 0, sizeof(*candidate));
	candidate->id = movePos;
	candidate->kind = STANDARD_POLICY_MOVE;
	candidate->legal = StandardAI_MoveLegal(bank, movePos, move, forcedMove);
	candidate->forced = candidate->legal && forcedMove;
	candidate->switch_from = 0xFF;
	candidate->switch_to = 0xFF;
	candidate->entry_survives = TRUE;
	candidate->fallback_cost = 100 + movePos;
	candidate->accuracy = move == MOVE_NONE ? 0 : gBattleMoves[move].accuracy;
	candidate->priority = move == MOVE_NONE ? 0 : gBattleMoves[move].priority;
	candidate->survival_to_act = gBattleMons[bank].hp != 0;
	candidate->known_no_effect = knownNoEffect;
	candidate->pure_status = statusMove;
	candidate->effect_family = family;
	candidate->stat_stage_before = stageBefore;

	if (stageId != 0)
	{
		if (StandardAI_IsSelfStageEffect(effect))
			stageAfter = MathMin(STAT_STAGE_MAX, stageBefore + delta);
		else
			stageAfter = stageBefore >= delta ? stageBefore - delta : STAT_STAGE_MIN;
	}
	candidate->stat_stage_after = stageAfter;

	if (move != MOVE_NONE && !statusMove)
	{
		StandardAI_DeriveDamage(bank, foe, move, candidate, NULL);
	}
	else if (stageId != 0)
	{
		StandardAI_StageMarginal(bank, foe, candidate);
	}
	else if (effect == EFFECT_RESTORE_HP || effect == EFFECT_REST)
	{
		if (gNewBS->HealBlockTimers[bank]) candidate->known_no_effect = TRUE;
		else if (move == MOVE_PURIFY || move == MOVE_JUNGLEHEALING || move == MOVE_LUNARBLESSING)
			candidate->productive = FALSE; /* Additional prerequisites/effects unmodeled. */
		else if (gBattleMons[bank].maxHP != 0 && gBattleMons[bank].hp < gBattleMons[bank].maxHP)
		{
			u16 amount = gBattleMons[bank].maxHP;
			if (effect == EFFECT_RESTORE_HP) amount = MathMax(1, amount / (move == MOVE_LIFEDEW ? 4 : 2));
			amount = MathMin(amount, gBattleMons[bank].maxHP - gBattleMons[bank].hp);
			missingHpFraction = amount * STANDARD_POLICY_HP_SCALE / gBattleMons[bank].maxHP;
			candidate->productive = TRUE;
			candidate->own_hp_fraction_lost = -(s16)MathMin(STANDARD_POLICY_HP_SCALE, missingHpFraction);
		}
		else
			candidate->known_no_effect = TRUE;
	}
	else if (StandardAI_IsMajorStatusEffect(effect))
	{
		StandardAI_StatusMarginal(bank, foe, effect, candidate);
	}

	if (candidate->known_no_effect)
		candidate->productive = FALSE;
	return;
}

static u8 StandardAI_CanSwitchOut(u8 bank)
{
	u8 foe = FOE(bank);
	ability_t knownAbility = StandardAI_RevealedAbility(foe);
	bool8 canBeTrappedByUnknown = TRUE;
	/* Unknown opposing trap ability remains unknown. */

	/* Own Ghost/Shed Shell state is exact and certifies immunity to trapping. */
	if (gBattleMons[bank].type1 == TYPE_GHOST
		|| gBattleMons[bank].type2 == TYPE_GHOST
		|| gBattleMons[bank].type3 == TYPE_GHOST
		|| ItemId_GetHoldEffect(gBattleMons[bank].item) == ITEM_EFFECT_SHED_SHELL)
		canBeTrappedByUnknown = FALSE;
	else if (gBattleMons[bank].ability == ABILITY_SHADOWTAG)
		canBeTrappedByUnknown = FALSE;

	/* Unknown opposing ability means unknown switch legality; reject it unless
	 * the own public state proves that none of the trapping abilities can apply. */
	if (knownAbility == ABILITY_NONE && canBeTrappedByUnknown)
		return FALSE;
	if (canBeTrappedByUnknown && knownAbility == ABILITY_SHADOWTAG
		&& gBattleMons[bank].ability != ABILITY_SHADOWTAG)
		return FALSE;
	if (canBeTrappedByUnknown && knownAbility == ABILITY_ARENATRAP && CheckGrounding(bank) == GROUNDED)
		return FALSE;
	if (canBeTrappedByUnknown && knownAbility == ABILITY_MAGNETPULL
		&& (gBattleMons[bank].type1 == TYPE_STEEL
			|| gBattleMons[bank].type2 == TYPE_STEEL
			|| gBattleMons[bank].type3 == TYPE_STEEL))
		return FALSE;

	return !(gBattleMons[bank].status2 & (STATUS2_ESCAPE_PREVENTION | STATUS2_WRAPPED))
		&& !(gStatuses3[bank] & STATUS3_ROOTED)
		&& !(gStatuses3[bank] & STATUS3_SKY_DROP_TARGET)
		&& !(gNewBS->trappedByOctolock & gBitTable[bank])
		&& !(gNewBS->trappedByNoRetreat & gBitTable[bank])
		&& gNewBS->FairyLockTimer == 0
		&& gBattleStruct->battlerPreventingSwitchout != bank;
}

u32 StandardAI_GetSwitchEntryDamage(u8 bank, const struct Pokemon* mon)
{
	u8 side = SIDE(bank);
	u8 ability = GetMonAbility(mon);
	u8 item = GetMonItemEffect(mon);
	u8 type1 = gBaseStats[mon->species].type1, type2 = gBaseStats[mon->species].type2;
	u32 entryDamage = 0;
	/* Do not call GetMonEntryHazardDamage: its transitive type helper reads
	 * the active player's exact HP even for a party-mon calculation. This
	 * bounded own-party calculation uses the same divisors without that graph. */
	if (mon->species != SPECIES_NONE && (gSideStatuses[side] & SIDE_STATUS_SPIKES)
		&& ability != ABILITY_MAGICGUARD && item != ITEM_EFFECT_HEAVY_DUTY_BOOTS)
	{
		u8 hazard;
		for (hazard = 0; hazard < 2; ++hazard)
		{
			u8 type = hazard == 0 ? TYPE_ROCK : TYPE_STEEL;
			u32 factor = 40 * StandardAI_PublicTypeMultiplier(type, type1) / 10;
			if (type1 != type2) factor = factor * StandardAI_PublicTypeMultiplier(type, type2) / 10;
			if (hazard == 0 ? gSideTimers[side].srAmount : gSideTimers[side].steelsurge)
				entryDamage += MathMax(1, mon->maxHP * factor / 320);
		}
		if (gSideTimers[side].spikesAmount && (gNewBS->GravityTimer
			|| item == ITEM_EFFECT_IRON_BALL || (type1 != TYPE_FLYING && type2 != TYPE_FLYING
			&& ability != ABILITY_LEVITATE && item != ITEM_EFFECT_AIR_BALLOON)))
		{
			u8 layers = MathMin(3, gSideTimers[side].spikesAmount);
			entryDamage += MathMax(1, mon->maxHP / (layers == 1 ? 8 : layers == 2 ? 6 : 4));
		}
	}
	return entryDamage;
}

static void StandardAI_FillSwitchCandidate(u8 bank, u8 partyIndex, struct Pokemon* mon,
	struct StandardPolicyCandidate* candidate, u8 forced)
{
	u8 i;
	u32 entryDamage = StandardAI_GetSwitchEntryDamage(bank, mon);
	u32 entryFraction = mon->maxHP == 0 ? STANDARD_POLICY_HP_SCALE
		: (entryDamage * STANDARD_POLICY_HP_SCALE) / mon->maxHP;

	Memset(candidate, 0, sizeof(*candidate));
	candidate->id = STANDARD_AI_SWITCH_ID_BASE + partyIndex;
	candidate->kind = STANDARD_POLICY_SWITCH;
	candidate->legal = mon->species != SPECIES_NONE && mon->hp != 0 && !mon->isEgg;
	candidate->productive = FALSE;
	/* A live bench slot alone is not a productive escape. Certify at least
	 * one usable, supported attack against the same public active target. */
	for (i = 0; i < MAX_MON_MOVES; ++i)
		if (mon->pp[i] && StandardAI_IsSupportedDamage(mon->moves[i])
			&& !StandardAI_KnownTypeImmunity(mon->moves[i], FOE(bank)))
			candidate->productive = candidate->legal;
	candidate->switch_legal = forced ? candidate->legal : StandardAI_CanSwitchOut(bank) && candidate->legal;
	candidate->entry_survives = entryDamage < mon->hp;
	candidate->forced = forced;
	candidate->fallback_cost = 1000 + partyIndex;
	candidate->switch_from = gBattlerPartyIndexes[bank];
	candidate->switch_to = partyIndex;
	candidate->standard_switch_emergency = FALSE;
	candidate->entry_cost = MathMin(STANDARD_AI_INT32_MAX, entryFraction);
	if (!candidate->entry_survives)
		candidate->productive = FALSE;
}

void StandardAI_LoadMemory(u8 bank, struct StandardPolicyMemory* memory)
{
	u8 i;

	StandardPolicyResetMemory(memory);
	memory->count = MathMin(STANDARD_POLICY_MEMORY_LIMIT, gNewBS->ai.standardMemoryCount[bank]);
	for (i = 0; i < memory->count; ++i)
	{
		memory->decisions[i].kind = gNewBS->ai.standardMemoryKind[bank][i];
		memory->decisions[i].effect_family = gNewBS->ai.standardMemoryFamily[bank][i];
		memory->decisions[i].success = gNewBS->ai.standardMemorySuccess[bank][i];
		memory->decisions[i].forced = gNewBS->ai.standardMemoryForced[bank][i];
		memory->decisions[i].switch_from = gNewBS->ai.standardMemorySwitchFrom[bank][i];
		memory->decisions[i].switch_to = gNewBS->ai.standardMemorySwitchTo[bank][i];
		memory->decisions[i].public_stage_before = gNewBS->ai.standardMemoryStageBefore[bank][i];
		memory->decisions[i].public_stage_after = gNewBS->ai.standardMemoryStageAfter[bank][i];
	}
}

static void StandardAI_SaveMemory(u8 bank, const struct StandardPolicyMemory* memory)
{
	u8 i;

	gNewBS->ai.standardMemoryCount[bank] = memory->count;
	for (i = 0; i < memory->count; ++i)
	{
		gNewBS->ai.standardMemoryKind[bank][i] = memory->decisions[i].kind;
		gNewBS->ai.standardMemoryFamily[bank][i] = memory->decisions[i].effect_family;
		gNewBS->ai.standardMemorySuccess[bank][i] = memory->decisions[i].success;
		gNewBS->ai.standardMemoryForced[bank][i] = memory->decisions[i].forced;
		gNewBS->ai.standardMemorySwitchFrom[bank][i] = memory->decisions[i].switch_from;
		gNewBS->ai.standardMemorySwitchTo[bank][i] = memory->decisions[i].switch_to;
		gNewBS->ai.standardMemoryStageBefore[bank][i] = memory->decisions[i].public_stage_before;
		gNewBS->ai.standardMemoryStageAfter[bank][i] = memory->decisions[i].public_stage_after;
	}
}

static void StandardAI_FinalizeLastAction(u8 bank)
{
	struct StandardPolicyMemory memory;
	struct StandardPolicyMemoryDecision decision;
	u8 target;
	u8 stageId;

	if (!gNewBS->ai.standardLastValid[bank])
		return;
	StandardAI_LoadMemory(bank, &memory);
	Memset(&decision, 0, sizeof(decision));
	decision.kind = gNewBS->ai.standardLastKind[bank];
	decision.effect_family = gNewBS->ai.standardLastFamily[bank];
	decision.success = gNewBS->ai.standardLastSuccessHint[bank];
	decision.forced = gNewBS->ai.standardLastForced[bank];
	decision.switch_from = gNewBS->ai.standardLastSwitchFrom[bank];
	decision.switch_to = gNewBS->ai.standardLastSwitchTo[bank];
	decision.public_stage_before = gNewBS->ai.standardLastStageBefore[bank];
	decision.public_stage_after = gNewBS->ai.standardLastStageAfter[bank];
	target = gNewBS->ai.standardLastTargetBank[bank];
	stageId = StandardAI_StageForFamily(decision.effect_family);
	if (stageId != 0 && target < MAX_BATTLERS_COUNT)
		decision.success = gBattleMons[target].statStages[stageId - 1] != decision.public_stage_before;
	else if (decision.kind == STANDARD_POLICY_SWITCH)
		decision.success = gBattlerPartyIndexes[bank] == decision.switch_to;
	else if (gNewBS->ai.standardLastStatusChecked[bank])
		decision.success = gBattleMons[target].status1 != gNewBS->ai.standardLastStatusBefore[bank];
	StandardPolicyRecordMemory(&memory, &decision);
	StandardAI_SaveMemory(bank, &memory);
	gNewBS->ai.standardLastValid[bank] = FALSE;
}

void StandardAI_StageLastAction(u8 bank, const struct StandardPolicyCandidate* candidate)
{
	u8 family = StandardPolicyNormalizeEffectFamily(candidate->effect_family);
	u8 stageId = StandardAI_StageForFamily(family);

	gNewBS->ai.standardLastValid[bank] = TRUE;
	gNewBS->ai.standardLastKind[bank] = candidate->kind;
	gNewBS->ai.standardLastFamily[bank] = family;
	gNewBS->ai.standardLastSuccessHint[bank] = candidate->productive;
	gNewBS->ai.standardLastForced[bank] = candidate->forced;
	gNewBS->ai.standardLastSwitchFrom[bank] = candidate->switch_from;
	gNewBS->ai.standardLastSwitchTo[bank] = candidate->switch_to;
	gNewBS->ai.standardLastTargetBank[bank] = StandardAI_IsSelfStageFamily(family)
		? bank : FOE(bank);
	gNewBS->ai.standardLastStageBefore[bank] = candidate->stat_stage_before;
	gNewBS->ai.standardLastStageAfter[bank] = candidate->stat_stage_after;
	gNewBS->ai.standardLastStatusChecked[bank] = stageId == 0
		&& candidate->kind == STANDARD_POLICY_MOVE
		&& candidate->public_major_status;
	gNewBS->ai.standardLastStatusBefore[bank] = gNewBS->ai.standardLastStatusChecked[bank]
		? gBattleMons[FOE(bank)].status1 : 0;
}

void StandardAI_BuildObservation(u8 bank, bool8 includeSwitches,
	struct StandardPolicyObservation* observation)
{
	u8 foe = FOE(bank);
	u8 i;
	u8 forcedMove = FALSE;
	u8 firstId;
	u8 lastId;
	struct Pokemon* party;

	StandardAI_FinalizeLastAction(bank);
	observation->count = 0;

	if (gBattleMons[bank].status2 & (STATUS2_RECHARGE | STATUS2_MULTIPLETURNS))
		forcedMove = gLockedMoves[bank] != MOVE_NONE;
	else if (gDisableStructs[bank].encoreTimer && gDisableStructs[bank].encoredMove != MOVE_NONE)
		forcedMove = TRUE;

	for (i = 0; i < MAX_MON_MOVES; ++i)
	{
		struct StandardPolicyCandidate* candidate = &observation->candidates[observation->count++];
		StandardAI_FillMoveCandidate(bank, foe, i, candidate, forcedMove);
	}

	if (!includeSwitches)
		return;

	party = LoadPartyRange(bank, &firstId, &lastId);
	for (i = firstId; i < lastId && observation->count < STANDARD_POLICY_MAX_CANDIDATES; ++i)
	{
		struct StandardPolicyCandidate* candidate;
		if (i == gBattlerPartyIndexes[bank])
			continue;
		candidate = &observation->candidates[observation->count++];
		StandardAI_FillSwitchCandidate(bank, i, &party[i], candidate, !BATTLER_ALIVE(bank));
	}
	StandardMechanicsQualifySwitches(observation);

}

bool8 StandardAI_IsSupportedBattle(void)
{
	u32 excluded = BATTLE_TYPE_DOUBLE | BATTLE_TYPE_LINK | BATTLE_TYPE_OAK_TUTORIAL
		| BATTLE_TYPE_MULTI | BATTLE_TYPE_SAFARI | BATTLE_TYPE_ROAMER
		| BATTLE_TYPE_EREADER_TRAINER | BATTLE_TYPE_SCRIPTED_WILD_1
		| BATTLE_TYPE_SCRIPTED_WILD_2 | BATTLE_TYPE_LEGENDARY_FRLG
		| BATTLE_TYPE_TRAINER_TOWER | BATTLE_TYPE_TWO_OPPONENTS
		| BATTLE_TYPE_INGAME_PARTNER | BATTLE_TYPE_POKE_DUDE | BATTLE_TYPE_OLD_MAN
		| BATTLE_TYPE_FRONTIER | BATTLE_TYPE_SHADOW_WARRIOR | BATTLE_TYPE_DYNAMAX
		| BATTLE_TYPE_KYOGRE_GROUDON | BATTLE_TYPE_REGI | BATTLE_TYPE_GHOST
		| BATTLE_TYPE_RING_CHALLENGE | BATTLE_TYPE_MOCK_BATTLE
		| BATTLE_TYPE_BENJAMIN_BUTTERFREE | BATTLE_TYPE_CAMOMONS | BATTLE_TYPE_MEGA_BRAWL;

	return (gBattleTypeFlags & BATTLE_TYPE_TRAINER)
		&& !(gBattleTypeFlags & excluded)
		&& !IsRaidBattle()
		&& !IsInverseBattle()
		&& !IsFrontierTrainerId(gTrainerBattleOpponent_A)
		&& GetTrainerAIProfile() == TRAINER_AI_PROFILE_STANDARD;
}

static u32 StandardAI_GetPolicySeed(u8 bank)
{
	return STANDARD_AI_DEFAULT_SEED ^ ((u32)gTrainerBattleOpponent_A << 8) ^ bank;
}

static u32* StandardAI_GetPolicyRng(u8 bank)
{
	if (!gNewBS->ai.standardPolicySeeded[bank])
	{
		gNewBS->ai.standardPolicyRng[bank] = StandardAI_GetPolicySeed(bank);
		gNewBS->ai.standardPolicySeeded[bank] = TRUE;
	}
	return &gNewBS->ai.standardPolicyRng[bank];
}

void StandardAI_SetupAIData(void)
{
	gBankAttacker = gActiveBattler;
	gBankTarget = FOE(gActiveBattler);
	gBattleResources->AIScriptsStack->size = 0;
}

static u8 StandardAI_Choose(bool8 includeSwitches, struct StandardPolicyCandidate* selected)
{
	struct StandardPolicyObservation observation;
	struct StandardPolicyMemory memory;
	struct StandardPolicyResult result;
	u8 bank = gBankAttacker;
	u8 i;

	StandardAI_BuildObservation(bank, includeSwitches, &observation);
	StandardAI_LoadMemory(bank, &memory);
	if (StandardPolicyChoose(&observation, &memory, StandardAI_GetPolicyRng(bank), &result) != 0)
		goto FALLBACK_TO_ENGINE;
	for (i = 0; i < observation.count; ++i)
	{
		if (observation.candidates[i].id == result.selected_id)
		{
			*selected = observation.candidates[i];
			StandardAI_StageLastAction(bank, selected);
			return selected->id;
		}
	}

FALLBACK_TO_ENGINE:
	/*
	 * The controller still requires a real move-slot index when every
	 * candidate is unusable; for example, an all-PP-depleted turn.  Return
	 * the first occupied own slot without staging it in Standard memory; the
	 * normal engine limitation path can then resolve Struggle or a forced
	 * action.  This fallback reads only own moves and never submits or predicts
	 * a player action.
	 */
	for (i = 0; i < observation.count; ++i)
	{
		if (observation.candidates[i].kind == STANDARD_POLICY_MOVE
		&& observation.candidates[i].id < MAX_MON_MOVES
		&& gBattleMons[bank].moves[observation.candidates[i].id] != MOVE_NONE)
		{
			*selected = observation.candidates[i];
			return selected->id;
		}
	}
	return STANDARD_AI_PENDING_NONE;
}

u8 StandardAI_ChooseReplacement(void)
{
	struct StandardPolicyObservation observation;
	struct StandardPolicyMemory memory;
	struct StandardPolicyResult result;
	u8 bank = gActiveBattler, i;
	StandardAI_BuildObservation(bank, TRUE, &observation);
	StandardAI_LoadMemory(bank, &memory);
	for (i = 0; i < observation.count; ++i)
	{
		struct StandardPolicyCandidate* c = &observation.candidates[i];
		if (c->kind == STANDARD_POLICY_MOVE) c->legal = FALSE;
		else
		{
			/* Replacement/pivot has already been required by the engine. */
			c->forced = TRUE;
			c->switch_legal = c->legal;
			c->standard_switch_emergency = FALSE;
		}
	}
	if (StandardPolicyChoose(&observation, &memory, StandardAI_GetPolicyRng(bank), &result) == 0)
		for (i = 0; i < observation.count; ++i)
			if (observation.candidates[i].id == result.selected_id)
			{
				StandardAI_StageLastAction(bank, &observation.candidates[i]);
				return observation.candidates[i].switch_to;
			}
	return PARTY_SIZE;
}

u8 StandardAI_ChooseMoveOrAction(void)
{
	struct StandardPolicyCandidate selected;
	u8 bank = gBankAttacker;
	u8 choice;

	if (gNewBS->ai.standardPendingValid[bank])
	{
		choice = gNewBS->ai.standardPendingAction[bank];
		gNewBS->ai.standardPendingValid[bank] = FALSE;
		if (gNewBS->ai.standardPendingKind[bank] == STANDARD_POLICY_SWITCH)
			return 0;
		gBattleStruct->chosenMovePositions[bank] = choice;
		gChosenMovesByBanks[bank] = gBattleMons[bank].moves[choice];
		return choice;
	}

	choice = StandardAI_Choose(FALSE, &selected);
	if (choice == STANDARD_AI_PENDING_NONE || selected.kind != STANDARD_POLICY_MOVE)
		return 0;
	gBattleStruct->chosenMovePositions[bank] = choice;
	gChosenMovesByBanks[bank] = gBattleMons[bank].moves[choice];
	gBankTarget = FOE(bank);
	return choice;
}

void StandardAI_TrySwitchOrUseItem(void)
{
	struct StandardPolicyCandidate selected;
	u8 bank = gActiveBattler;
	u8 choice;

	gBankAttacker = bank;
	gBankTarget = FOE(bank);
	if (gNewBS->ai.standardPendingValid[bank])
	{
		if (gNewBS->ai.standardPendingKind[bank] == STANDARD_POLICY_SWITCH)
			EmitTwoReturnValues(1, ACTION_SWITCH, 0);
		else
			EmitTwoReturnValues(1, ACTION_USE_MOVE, (bank ^ BIT_SIDE) << 8);
		return;
	}

	choice = StandardAI_Choose(TRUE, &selected);
	if (choice == STANDARD_AI_PENDING_NONE)
	{
		EmitTwoReturnValues(1, ACTION_USE_MOVE, (bank ^ BIT_SIDE) << 8);
		return;
	}

	gNewBS->ai.standardPendingValid[bank] = TRUE;
	gNewBS->ai.standardPendingKind[bank] = selected.kind;
	if (selected.kind == STANDARD_POLICY_SWITCH)
	{
		/* The switch target is committed in BattleStruct; no move-phase pending state is needed. */
		gNewBS->ai.standardPendingValid[bank] = FALSE;
		gNewBS->ai.standardPendingSwitchTarget[bank] = selected.switch_to;
		gBattleStruct->switchoutIndex[SIDE(bank)] = selected.switch_to;
		gBattleStruct->monToSwitchIntoId[bank] = selected.switch_to;
		EmitTwoReturnValues(1, ACTION_SWITCH, 0);
	}
	else
	{
		gNewBS->ai.standardPendingAction[bank] = choice;
		gBattleStruct->chosenMovePositions[bank] = choice;
		gChosenMovesByBanks[bank] = gBattleMons[bank].moves[choice];
		EmitTwoReturnValues(1, ACTION_USE_MOVE, (bank ^ BIT_SIDE) << 8);
	}
}
