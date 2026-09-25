#include "../defines.h"
#include "../defines_battle.h"
#include "../../include/constants/battle_move_effects.h"
#include "../../include/constants/trainers.h"

#include "../../include/new/ai_ironmon.h"
#include "../../include/new/ai_ironmon_policy.h"
#include "../../include/new/ai_standard.h"
#include "../../include/new/ai_standard_mechanics.h"
#include "../../include/new/battle_util.h"
#include "../../include/new/frontier.h"
#include "../../include/new/switching.h"
#include "../../include/new/util.h"

/*
 * CFRU-facing Ironmon adapter.  The pure policy below this boundary receives
 * only copied public/own facts.  No legacy prediction helper, submitted player
 * action, battle RNG, hidden player move/item/ability/stat, or unseen bench is
 * reachable from this file.
 */
#define IRONMON_AI_PENDING_NONE 0xFF
#define IRONMON_AI_DEFAULT_SEED 0x1A0B5157
#ifdef CFRU_AI_TEST_TRACE
int IronmonAI_TestLastPolicyRc;
u8 IronmonAI_TestLastFailureReason;
u8 IronmonAI_TestLastSelectedId;
int IronmonAI_TestPolicyRcOverride = -2147483647 - 1;
u8 IronmonAI_TestSelectedIdOverride = 0xFF;
#endif
#ifdef OLD_PARALYSIS_SPD_DROP
#define IRONMON_PARALYSIS_DIVISOR 4
#else
#define IRONMON_PARALYSIS_DIVISOR 2
#endif

/* The bounded 9x8 observation is too large for the battle callback stack.
 * One non-reentrant ordinary-singles decision uses this EWRAM scratch. */
static EWRAM_DATA struct IronmonPolicyObservation sIronmonObservation;
static EWRAM_DATA struct IronmonPolicyResult sIronmonResult;

struct IronmonIncoming
{
	u16 minimum;
	u16 maximum;
	u16 fraction;
	u16 target_hp;
	u16 target_max_hp;
	u8 supported;
	u8 immune;
	u8 survives;
	u8 modifiers_certified;
	u8 order_known;
	u8 opponent_first;
};

static u32 IronmonAI_Min(u32 left, u32 right) { return left < right ? left : right; }

void IronmonAI_ObservePublicMove(u8 bank, u16 move)
{
	u8 slot;
	if (gNewBS == NULL || bank >= MAX_BATTLERS_COUNT || move == MOVE_NONE
		|| !(gHitMarker & HITMARKER_ATTACKSTRING_PRINTED))
		return;
	for (slot = 0; slot < MAX_MON_MOVES; ++slot)
	{
		if (BATTLE_HISTORY->usedMoves[bank][slot] == move)
		{
			if (gNewBS->ai.ironmonMoveUseCounts[bank][slot] != 0xFFFF)
				++gNewBS->ai.ironmonMoveUseCounts[bank][slot];
			return;
		}
		if (BATTLE_HISTORY->usedMoves[bank][slot] == MOVE_NONE)
		{
			gNewBS->ai.ironmonMoveUseCounts[bank][slot] = 1;
			return;
		}
	}
}

void IronmonAI_ClearPublicMoveCounts(u8 bank)
{
	u8 slot;
	if (gNewBS == NULL || bank >= MAX_BATTLERS_COUNT)
		return;
	for (slot = 0; slot < MAX_MON_MOVES; ++slot)
		gNewBS->ai.ironmonMoveUseCounts[bank][slot] = 0;
}

static u8 IronmonAI_KnownOwnImmunity(u16 move, u8 type1, u8 type2, u8 type3,
	ability_t ability)
{
	u8 moveType = gBattleMoves[move].type;
	if ((ability == ABILITY_LEVITATE || ability == ABILITY_EARTHEATER) && moveType == TYPE_GROUND)
		return TRUE;
	if (ability == ABILITY_FLASHFIRE && moveType == TYPE_FIRE) return TRUE;
	if ((ability == ABILITY_WATERABSORB || ability == ABILITY_DRYSKIN
		|| ability == ABILITY_STORMDRAIN) && moveType == TYPE_WATER) return TRUE;
	if ((ability == ABILITY_VOLTABSORB || ability == ABILITY_LIGHTNINGROD
		|| ability == ABILITY_MOTORDRIVE) && moveType == TYPE_ELECTRIC) return TRUE;
	if (ability == ABILITY_SAPSIPPER && moveType == TYPE_GRASS) return TRUE;
	return StandardAI_PublicTypeMultiplier(moveType, type1) == 0
		|| StandardAI_PublicTypeMultiplier(moveType, type2) == 0
		|| (type3 < NUMBER_OF_MON_TYPES
			&& StandardAI_PublicTypeMultiplier(moveType, type3) == 0);
}

static u8 IronmonAI_PublicSideModifiersCertified(void)
{
	const u16 hazards = SIDE_STATUS_SPIKES | SIDE_STATUS_SPIKES_DAMAGED;
	const u16 unsupported = SIDE_STATUS_REFLECT | SIDE_STATUS_LIGHTSCREEN
		| SIDE_STATUS_X4 | SIDE_STATUS_CRAFTY_SHIELD | SIDE_STATUS_SAFEGUARD
		| SIDE_STATUS_FUTUREATTACK | SIDE_STATUS_MAT_BLOCK | SIDE_STATUS_MIST
		| SIDE_STATUS_QUICK_GUARD | SIDE_STATUS_WIDE_GUARD;
	return !(gSideStatuses[0] & unsupported) && !(gSideStatuses[1] & unsupported)
		&& !(gSideStatuses[0] & ~(unsupported | hazards))
		&& !(gSideStatuses[1] & ~(unsupported | hazards));
}

static u8 IronmonAI_PublicModifierCertificate(u8 foe, u8 target, u8 allowTrickRoom,
	u16 targetSpeciesOverride)
{
	u16 publicSpecies = gNewBS->ai.standardDisplayedSpecies[foe];
	u16 targetSpecies = targetSpeciesOverride == SPECIES_NONE
		? gBattleMons[target].species : targetSpeciesOverride;
	if (gStatuses3[foe] != STATUS3_ABILITY_SUPPRESS
		|| gStatuses3[target] != STATUS3_ABILITY_SUPPRESS
		|| gNewBS->MagicRoomTimer <= 1 || gBattleWeather || gNewBS->TerrainTimer
		|| gNewBS->WonderRoomTimer || gNewBS->IonDelugeTimer
		|| gNewBS->ElectrifyTimers[foe] || gNewBS->ElectrifyTimers[target]
		|| gNewBS->MudSportTimer || gNewBS->WaterSportTimer
		|| gNewBS->GravityTimer || gNewBS->AuroraVeilTimers[SIDE(target)]
		|| !IronmonAI_PublicSideModifiersCertified()
		|| gBattleMons[foe].status2 || gBattleMons[target].status2
		|| (gBattleMons[foe].status1 & ~(STATUS1_BURN | STATUS1_PARALYSIS))
		|| (gBattleMons[target].status1 & ~(STATUS1_BURN | STATUS1_PARALYSIS))
		|| gNewBS->teraData.done[SIDE(foe)][gBattlerPartyIndexes[foe]]
		|| gNewBS->teraData.done[SIDE(target)][gBattlerPartyIndexes[target]])
		return FALSE;
	if (!allowTrickRoom && gNewBS->TrickRoomTimer) return FALSE;
	#if defined(FLAG_WEIGHT_SPEED_BATTLE) || defined(FLAG_TAILWIND_BATTLE)
	return FALSE;
	#endif
	if (gNewBS->TailwindTimers[0] || gNewBS->TailwindTimers[1]
		|| gNewBS->SwampTimers[0] || gNewBS->SwampTimers[1])
		return FALSE;
	if (publicSpecies == SPECIES_TERAPAGOS
	#ifdef SPECIES_TERAPAGOS_TERA
		|| publicSpecies == SPECIES_TERAPAGOS_TERA
	#endif
	)
		return FALSE;
	/* StandardMechanicsDamage does not model Shedinja's one-HP exception in
	 * the revealed incoming adapter, so its survival/order certificate fails
	 * closed rather than treating it as an ordinary HP target. */
	if (targetSpecies == SPECIES_SHEDINJA)
		return FALSE;
	return StandardAI_GetPublicTypes(foe, (u8[3]){0, 0, 0});
}

static u8 IronmonAI_CertifiedIncomingModifiers(u8 foe, u8 target,
	const struct Pokemon* partyMon)
{
	return IronmonAI_PublicModifierCertificate(foe, target, TRUE,
		partyMon == NULL ? SPECIES_NONE : partyMon->species);
}

static void IronmonAI_Order(u8 bank, u8 foe, s8 ownPriority, u16 response,
	struct IronmonIncoming* incoming)
{
	u16 species = gNewBS->ai.standardDisplayedSpecies[foe];
	u32 ownSpeed, ownHigh, low, high;
	s8 responsePriority = gBattleMoves[response].priority;
	if (!incoming->modifiers_certified) return;
	if (!IronmonAI_PublicModifierCertificate(foe, bank, TRUE, SPECIES_NONE)) return;
	if (ownPriority != responsePriority)
	{
		incoming->order_known = TRUE;
		incoming->opponent_first = responsePriority > ownPriority;
		return;
	}
	if (species == SPECIES_NONE || species >= NUM_SPECIES || !gBattleMons[bank].speed)
		return;
	ownSpeed = StandardMechanicsStage(gBattleMons[bank].speed,
		gBattleMons[bank].statStages[STAT_STAGE_SPEED - 1]);
	ownHigh = ownSpeed;
	low = StandardMechanicsSpeed(gBaseStats[species].baseSpeed,
		gBattleMons[foe].level, gBattleMons[foe].statStages[STAT_STAGE_SPEED - 1], FALSE);
	high = StandardMechanicsSpeed(gBaseStats[species].baseSpeed,
		gBattleMons[foe].level, gBattleMons[foe].statStages[STAT_STAGE_SPEED - 1], TRUE);
	if (StandardAI_PublicBadgeBoost(bank, STANDARD_AI_BADGE_SPEED))
		ownHigh = ownHigh * 11 / 10;
	if (StandardAI_PublicBadgeBoost(foe, STANDARD_AI_BADGE_SPEED))
		high = high * 11 / 10;
	if (gBattleMons[bank].status1 & STATUS_PARALYSIS)
	{
		ownSpeed /= IRONMON_PARALYSIS_DIVISOR;
		ownHigh /= IRONMON_PARALYSIS_DIVISOR;
	}
	if (gBattleMons[foe].status1 & STATUS_PARALYSIS)
	{
		low /= IRONMON_PARALYSIS_DIVISOR;
		high /= IRONMON_PARALYSIS_DIVISOR;
	}
	if (gNewBS->TrickRoomTimer > 1)
	{
		if (ownHigh < low) { incoming->order_known = TRUE; incoming->opponent_first = FALSE; }
		else if (ownSpeed > high) { incoming->order_known = TRUE; incoming->opponent_first = TRUE; }
	}
	else if (!gNewBS->TrickRoomTimer)
	{
		if (ownSpeed > high) { incoming->order_known = TRUE; incoming->opponent_first = FALSE; }
		else if (ownHigh < low) { incoming->order_known = TRUE; incoming->opponent_first = TRUE; }
	}
}

static void IronmonAI_ProjectIncoming(u8 bank, u16 response, const struct Pokemon* partyMon,
	s8 ownPriority, u16 hpOverride, struct IronmonIncoming* incoming)
{
	u8 foe = FOE(bank), publicTypes[3], ownTypes[3], split, type, i;
	u16 defense, hp, maxHP;
	u8 level, defenseStage, ability;
	struct StandardMechanicsInput input;
	struct StandardPolicyCandidate projected;
	struct StandardDamageEnvelope envelope;
	u16 species = gNewBS->ai.standardDisplayedSpecies[foe];

	Memset(incoming, 0, sizeof(*incoming));
	if (!StandardAI_IsSupportedDamage(response) || species == SPECIES_NONE
		|| species >= NUM_SPECIES || !StandardAI_GetPublicTypes(foe, publicTypes))
		return;
	split = SPLIT(response); type = gBattleMoves[response].type;
	if (partyMon == NULL)
	{
		ownTypes[0] = gBattleMons[bank].type1; ownTypes[1] = gBattleMons[bank].type2;
		ownTypes[2] = gBattleMons[bank].type3; ability = gBattleMons[bank].ability;
		defense = split == SPLIT_PHYSICAL ? gBattleMons[bank].defense : gBattleMons[bank].spDefense;
		defenseStage = gBattleMons[bank].statStages[(split == SPLIT_PHYSICAL ? STAT_STAGE_DEF : STAT_STAGE_SPDEF) - 1];
		hp = hpOverride == 0xFFFF ? gBattleMons[bank].hp : hpOverride;
		maxHP = gBattleMons[bank].maxHP; level = gBattleMons[bank].level;
	}
	else
	{
		u32 entryDamage;
		ownTypes[0] = gBaseStats[partyMon->species].type1;
		ownTypes[1] = gBaseStats[partyMon->species].type2;
		ownTypes[2] = NUMBER_OF_MON_TYPES; ability = GetMonAbility(partyMon);
		defense = split == SPLIT_PHYSICAL ? partyMon->defense : partyMon->spDefense;
		defenseStage = 6; maxHP = partyMon->maxHP; level = partyMon->level;
		entryDamage = StandardAI_GetSwitchEntryDamage(bank, partyMon);
		hp = entryDamage >= partyMon->hp ? 0 : partyMon->hp - entryDamage;
	}
	incoming->supported = TRUE;
	incoming->target_hp = hp;
	incoming->target_max_hp = maxHP;
	incoming->modifiers_certified = IronmonAI_CertifiedIncomingModifiers(foe, bank, partyMon);
	incoming->immune = IronmonAI_KnownOwnImmunity(response, ownTypes[0], ownTypes[1], ownTypes[2], ability);
	if (incoming->immune)
	{
		incoming->survives = TRUE;
		IronmonAI_Order(bank, foe, ownPriority, response, incoming);
		return;
	}
	Memset(&input, 0, sizeof(input)); Memset(&projected, 0, sizeof(projected));
	input.power = gBattleMoves[response].power;
	input.attack = StandardMechanicsSpeed(
		split == SPLIT_PHYSICAL ? gBaseStats[species].baseAttack : gBaseStats[species].baseSpAttack,
		gBattleMons[foe].level, 6, TRUE);
	if (StandardAI_PublicBadgeBoost(foe, split == SPLIT_PHYSICAL
		? STANDARD_AI_BADGE_ATTACK : STANDARD_AI_BADGE_SPECIAL_ATTACK))
		input.attack = MathMin(2048, input.attack * 11 / 10);
	input.possible_defense_badge = StandardAI_PublicBadgeBoost(bank, split == SPLIT_PHYSICAL
		? STANDARD_AI_BADGE_DEFENSE : STANDARD_AI_BADGE_SPECIAL_DEFENSE);
	input.known_defense = defense; input.known_hp = hp; input.known_max_hp = maxHP;
	input.level = gBattleMons[foe].level; input.target_level = level;
	input.attack_stage = gBattleMons[foe].statStages[(split == SPLIT_PHYSICAL ? STAT_STAGE_ATK : STAT_STAGE_SPATK) - 1];
	input.defense_stage = defenseStage; input.hp_pixels = 255;
	input.accuracy = gBattleMoves[response].accuracy;
	input.accuracy_stage = gBattleMons[foe].statStages[STAT_STAGE_ACC - 1];
	input.evasion_stage = partyMon == NULL ? gBattleMons[bank].statStages[STAT_STAGE_EVASION - 1] : 6;
	input.stab = type == publicTypes[0] || type == publicTypes[1];
	input.own_burn = split == SPLIT_PHYSICAL && (gBattleMons[foe].status1 & STATUS_BURN);
	input.supported_damage = TRUE; input.known_immunity = FALSE;
	input.certified_modifiers = incoming->modifiers_certified
		&& (partyMon == NULL || ability == ABILITY_NONE);
	for (i = 0; i < 3; ++i)
		input.effectiveness[i] = ownTypes[i] >= NUMBER_OF_MON_TYPES
			|| (i && ownTypes[i] == ownTypes[0]) || (i == 2 && ownTypes[i] == ownTypes[1])
			? 10 : StandardAI_PublicTypeMultiplier(type, ownTypes[i]);
	StandardMechanicsDamage(&input, &projected, &envelope);
	incoming->minimum = envelope.minimum;
	incoming->maximum = envelope.maximum;
	incoming->modifiers_certified = input.certified_modifiers;
	incoming->fraction = maxHP == 0 ? 256
		: IronmonAI_Min(256, IronmonAI_Min(envelope.maximum, hp) * 256 / maxHP);
	incoming->survives = envelope.maximum < hp;
	IronmonAI_Order(bank, foe, ownPriority, response, incoming);
}

static u8 IronmonAI_TwoStepSpeedThreshold(u8 bank,
	const struct StandardPolicyCandidate* candidate)
{
	u8 foe = FOE(bank), afterTwo;
	u16 species = gNewBS->ai.standardDisplayedSpecies[foe];
	u32 own, afterOneLow, afterOneHigh, afterTwoLow, afterTwoHigh;
	u8 delta;
	if (candidate->effect_family != STANDARD_EFFECT_SPEED_DOWN
		|| species == SPECIES_NONE || species >= NUM_SPECIES
		|| !IronmonAI_PublicModifierCertificate(foe, bank, TRUE, SPECIES_NONE)
		|| (gBattleMons[bank].status1 & STATUS_PARALYSIS)
		|| (gBattleMons[foe].status1 & STATUS_PARALYSIS))
		return FALSE;
	delta = candidate->stat_stage_before - candidate->stat_stage_after;
	afterTwo = candidate->stat_stage_after >= delta
		? candidate->stat_stage_after - delta : STAT_STAGE_MIN;
	own = StandardMechanicsStage(gBattleMons[bank].speed,
		gBattleMons[bank].statStages[STAT_STAGE_SPEED - 1]);
	{
		u32 ownHigh = own;
		if (StandardAI_PublicBadgeBoost(bank, STANDARD_AI_BADGE_SPEED))
			ownHigh = ownHigh * 11 / 10;
		afterOneLow = StandardMechanicsSpeed(gBaseStats[species].baseSpeed,
			gBattleMons[foe].level, candidate->stat_stage_after, FALSE);
		afterOneHigh = StandardMechanicsSpeed(gBaseStats[species].baseSpeed,
			gBattleMons[foe].level, candidate->stat_stage_after, TRUE);
		afterTwoLow = StandardMechanicsSpeed(gBaseStats[species].baseSpeed,
			gBattleMons[foe].level, afterTwo, FALSE);
		afterTwoHigh = StandardMechanicsSpeed(gBaseStats[species].baseSpeed,
			gBattleMons[foe].level, afterTwo, TRUE);
		if (StandardAI_PublicBadgeBoost(foe, STANDARD_AI_BADGE_SPEED))
		{
			afterOneHigh = afterOneHigh * 11 / 10;
			afterTwoHigh = afterTwoHigh * 11 / 10;
		}
		if (gNewBS->TrickRoomTimer > 2)
			return !(own < afterOneLow) && ownHigh < afterTwoLow;
		if (gNewBS->TrickRoomTimer) return FALSE;
		return !(ownHigh > afterOneHigh) && own > afterTwoHigh;
	}
}

static u8 IronmonAI_Classify(u8 bank, struct IronmonPolicyCandidate* candidate)
{
	u16 move;
	u8 effect;
	if (candidate->floor.kind == STANDARD_POLICY_SWITCH)
		return candidate->floor.forced ? IRONMON_TACTICAL_FORCED_REPLACEMENT : IRONMON_TACTICAL_SWITCH;
	move = gBattleMons[bank].moves[candidate->floor.id];
	if (move == MOVE_NONE) return IRONMON_TACTICAL_FALLBACK;
	effect = gBattleMoves[move].effect;
	if (SPLIT(move) != SPLIT_STATUS) return IRONMON_TACTICAL_DAMAGE;
	if (candidate->floor.effect_family == STANDARD_EFFECT_SPEED_DOWN
		|| candidate->floor.effect_family == STANDARD_EFFECT_SPEED_UP)
		return IRONMON_TACTICAL_SPEED_PLAN;
	if (candidate->floor.effect_family >= STANDARD_EFFECT_ATTACK_UP
		&& candidate->floor.effect_family <= STANDARD_EFFECT_SPECIAL_DEFENSE_DOWN)
		return IRONMON_TACTICAL_SETUP_PLAN;
	if (effect == EFFECT_POISON || effect == EFFECT_TOXIC || effect == EFFECT_WILL_O_WISP
		|| effect == EFFECT_LEECH_SEED || effect == EFFECT_YAWN)
		return IRONMON_TACTICAL_RESIDUAL;
	if (effect == EFFECT_RESTORE_HP || effect == EFFECT_REST) return IRONMON_TACTICAL_RECOVERY;
	if (effect == EFFECT_PROTECT) return IRONMON_TACTICAL_PROTECT;
	return IRONMON_TACTICAL_UNSUPPORTED;
}

static void IronmonAI_AssignFamily(u8 bank, struct IronmonPolicyCandidate* candidate)
{
	u16 move;
	u8 effect;
	if (candidate->floor.kind == STANDARD_POLICY_SWITCH) return;
	move = gBattleMons[bank].moves[candidate->floor.id];
	if (move == MOVE_NONE) return;
	effect = gBattleMoves[move].effect;
	if (SPLIT(move) != SPLIT_STATUS) candidate->floor.effect_family = STANDARD_EFFECT_DAMAGE;
	else if (effect == EFFECT_TOXIC) candidate->floor.effect_family = STANDARD_EFFECT_TOXIC;
	else if (effect == EFFECT_POISON || effect == EFFECT_WILL_O_WISP)
		candidate->floor.effect_family = STANDARD_EFFECT_MAJOR_STATUS;
	else if (effect == EFFECT_LEECH_SEED) candidate->floor.effect_family = STANDARD_EFFECT_LEECH_SEED;
	else if (effect == EFFECT_YAWN) candidate->floor.effect_family = STANDARD_EFFECT_YAWN;
	else if (effect == EFFECT_RESTORE_HP || effect == EFFECT_REST)
		candidate->floor.effect_family = STANDARD_EFFECT_RECOVERY;
	else if (effect == EFFECT_PROTECT) candidate->floor.effect_family = STANDARD_EFFECT_PROTECT;
}

static u16 IronmonAI_RecoveryAmount(u8 bank, u16 move, u16 hp)
{
	u16 maxHP = gBattleMons[bank].maxHP;
	u16 amount = maxHP;
	u8 effect = move == MOVE_NONE ? 0 : gBattleMoves[move].effect;
	if (!maxHP || hp >= maxHP || (effect != EFFECT_RESTORE_HP && effect != EFFECT_REST))
		return 0;
	if (effect == EFFECT_RESTORE_HP)
		amount = MathMax(1, maxHP / (move == MOVE_LIFEDEW ? 4 : 2));
	return MathMin(amount, maxHP - hp);
}

static u8 IronmonAI_SetupThreshold(u8 bank, const struct StandardPolicyCandidate* candidate,
	struct StandardSetupFollowup* followup)
{
	if (candidate->effect_family != STANDARD_EFFECT_ATTACK_UP
		&& candidate->effect_family != STANDARD_EFFECT_SPECIAL_ATTACK_UP
		&& candidate->effect_family != STANDARD_EFFECT_DEFENSE_DOWN
		&& candidate->effect_family != STANDARD_EFFECT_SPECIAL_DEFENSE_DOWN)
		return FALSE;
	if (!IronmonAI_PublicModifierCertificate(FOE(bank), bank, TRUE, SPECIES_NONE))
		return FALSE;
	if (!StandardAI_FindSetupFollowup(bank, FOE(bank), candidate->effect_family,
		candidate->stat_stage_after, followup))
		return FALSE;
	/* A threshold belongs to this one follow-up, never to another move's
	 * current damage.  Fractions are the shared 1/256 HP scale. */
	return followup->before_fraction * 2 < 256
		&& followup->before_fraction * 3 >= 256
		&& followup->after_fraction * 2 >= 256;
}

static u8 IronmonAI_NextTurnCertified(u8 bank, u16 response, u16 hp,
	s8 priority, struct IronmonIncoming* next)
{
	if (!hp) return FALSE;
	IronmonAI_ProjectIncoming(bank, response, NULL, priority, hp, next);
	return next->supported && next->modifiers_certified && next->order_known
		&& next->survives;
}

static s32 IronmonAI_ClampFraction(s32 value)
{
	if (value < -256) return -256;
	if (value > 256) return 256;
	return value;
}

static void IronmonAI_FillBranches(u8 bank, struct IronmonPolicyObservation* observation,
	struct IronmonPolicyCandidate* candidate)
{
	u8 branchIndex;
	u8 firstId, lastId;
	struct Pokemon* party = LoadPartyRange(bank, &firstId, &lastId);
	const struct Pokemon* switchTarget = candidate->floor.kind == STANDARD_POLICY_SWITCH
		? &party[candidate->floor.switch_to] : NULL;
	struct StandardSetupFollowup setupFollowup;
	u8 setupThreshold = IronmonAI_SetupThreshold(bank, &candidate->floor, &setupFollowup);
	u8 tactical = candidate->tactical_class;
	u16 actionMove = candidate->floor.kind == STANDARD_POLICY_MOVE
		? gBattleMons[bank].moves[candidate->floor.id] : MOVE_NONE;
	u16 startHp = gBattleMons[bank].hp;
	u16 maxHP = gBattleMons[bank].maxHP;
	(void)firstId; (void)lastId;
	if (tactical != IRONMON_TACTICAL_SETUP_PLAN) setupThreshold = FALSE;
	for (branchIndex = 0; branchIndex < observation->response_count; ++branchIndex)
	{
		struct IronmonPolicyBranch* branch = &candidate->responses[branchIndex];
		u16 response = observation->responses[branchIndex].id;
		struct IronmonIncoming incoming;
		struct IronmonIncoming next;
		s32 ownLoss;
		u16 postHp;
		u8 actionFirst, recovery = tactical == IRONMON_TACTICAL_RECOVERY;
		u8 recoveryRace = FALSE;
		s8 nextPriority = candidate->floor.priority;
		branch->response_id = response;
		branch->net_faints = candidate->floor.net_faints;
		branch->opponent_hp_fraction_lost = candidate->floor.opponent_hp_fraction_lost;
		branch->own_hp_fraction_lost = candidate->floor.own_hp_fraction_lost;
		branch->future_gain_undiscounted = 0;
		branch->entry_cost = candidate->floor.entry_cost;
		if (response == IRONMON_POLICY_UNKNOWN_RESPONSE)
			continue;
		IronmonAI_ProjectIncoming(bank, response, switchTarget,
			candidate->floor.kind == STANDARD_POLICY_SWITCH ? -128 : candidate->floor.priority,
			0xFFFF, &incoming);
		if (!incoming.supported || !incoming.modifiers_certified)
			continue;
		/* An unresolved order cannot certify that the trainer action occurs. */
		if (!incoming.order_known)
		{
			if (candidate->floor.kind == STANDARD_POLICY_MOVE)
			{
				branch->net_faints = 0;
				branch->opponent_hp_fraction_lost = 0;
				branch->own_hp_fraction_lost = 0;
			}
			continue;
		}
		actionFirst = !incoming.opponent_first
			&& candidate->floor.kind != STANDARD_POLICY_SWITCH;
		/* A robust terminal KO prevents the response entirely, but only after
		 * the public order certificate says the trainer acts first. */
		if (actionFirst && candidate->floor.robust_safe_ko)
		{
			continue;
		}
		/* The response acts before a switch, and before a slower move.  A
		 * certified lethal response ends the branch before any outgoing action. */
		if (!incoming.survives && !(actionFirst && recovery))
		{
			branch->net_faints = -1;
			if (!actionFirst)
				branch->opponent_hp_fraction_lost = 0;
			branch->own_hp_fraction_lost = 256;
			branch->future_gain_undiscounted = 0;
			continue;
		}
		postHp = incoming.target_hp - IronmonAI_Min(incoming.maximum, incoming.target_hp);
		if (actionFirst)
		{
			if (recovery)
			{
				u16 heal = IronmonAI_RecoveryAmount(bank, actionMove, startHp);
				u16 healedHp = IronmonAI_Min(maxHP, startHp + heal);
				IronmonAI_ProjectIncoming(bank, response, NULL, candidate->floor.priority,
					healedHp, &next);
				if (!next.supported || !next.modifiers_certified || !next.order_known)
					continue;
				if (!next.survives)
				{
					branch->net_faints = -1;
					branch->opponent_hp_fraction_lost = candidate->floor.opponent_hp_fraction_lost;
					branch->own_hp_fraction_lost = 256;
					continue;
				}
				if (!incoming.survives) recoveryRace = TRUE;
				postHp = next.target_hp - IronmonAI_Min(next.maximum, next.target_hp);
				ownLoss = ((s32)startHp - healedHp) * 256 / (s32)MathMax(1, maxHP);
				ownLoss += next.fraction;
			}
			else
			{
				ownLoss = candidate->floor.own_hp_fraction_lost + incoming.fraction;
			}
		}
		else if (recovery)
		{
			/* Opponent-first recovery heals from the post-hit HP, not the stale
			 * pre-response amount used by the floor candidate. */
			u16 heal = IronmonAI_RecoveryAmount(bank, actionMove, postHp);
			u16 healedHp = IronmonAI_Min(maxHP, postHp + heal);
			ownLoss = ((s32)startHp - healedHp) * 256 / (s32)MathMax(1, maxHP);
			postHp = healedHp;
		}
		else
		{
			ownLoss = candidate->floor.own_hp_fraction_lost + incoming.fraction;
		}
		branch->own_hp_fraction_lost = IronmonAI_ClampFraction(ownLoss);
		if (branch->own_hp_fraction_lost >= 256)
		{
			branch->net_faints = -1;
			branch->future_gain_undiscounted = 0;
			continue;
		}
		/* No tactical future is credited until the next exposed response has a
		 * complete public modifier/order/survival certificate. */
		if (setupThreshold) nextPriority = setupFollowup.priority;
		if (!IronmonAI_NextTurnCertified(bank, response, postHp,
			candidate->floor.kind == STANDARD_POLICY_SWITCH ? -128 : nextPriority,
			&next))
		{
			if (recoveryRace) branch->future_gain_undiscounted = 40;
			continue;
		}
		if (tactical == IRONMON_TACTICAL_DAMAGE
			&& candidate->floor.opponent_hp_fraction_lost > 0
			&& candidate->floor.opponent_hp_fraction_lost * 2 >= 256)
		{
			u8 value = candidate->floor.opponent_hp_fraction_lost * 100 / 256;
			branch->future_gain_undiscounted = IronmonAI_Min(80, value * 2);
			candidate->tactical_class = IRONMON_TACTICAL_TWO_HKO;
		}
		else if (tactical == IRONMON_TACTICAL_SPEED_PLAN
			&& IronmonAI_TwoStepSpeedThreshold(bank, &candidate->floor)
			&& next.order_known)
			branch->future_gain_undiscounted = 80;
		else if (tactical == IRONMON_TACTICAL_SETUP_PLAN && setupThreshold)
			branch->future_gain_undiscounted = IronmonAI_Min(80,
				candidate->floor.immediate_future_gain * 2);
		else if (tactical == IRONMON_TACTICAL_RESIDUAL)
			branch->future_gain_undiscounted = IronmonAI_Min(80,
				candidate->floor.immediate_future_gain * 2);
		else if ((recovery && branch->own_hp_fraction_lost < 0) || recoveryRace)
			branch->future_gain_undiscounted = 40;
	}
	if (candidate->tactical_class == IRONMON_TACTICAL_SPEED_PLAN
		&& IronmonAI_TwoStepSpeedThreshold(bank, &candidate->floor))
	{
		candidate->floor.positive_marginal_exception = TRUE;
		candidate->repeat_exception_reason = IRONMON_REPEAT_ORDER_THRESHOLD;
	}
	else if (candidate->tactical_class == IRONMON_TACTICAL_TWO_HKO || setupThreshold)
	{
		candidate->floor.positive_marginal_exception = TRUE;
		candidate->repeat_exception_reason = IRONMON_REPEAT_KO_OR_2HKO_THRESHOLD;
	}
	else if (candidate->tactical_class == IRONMON_TACTICAL_RECOVERY
		&& candidate->floor.own_hp_fraction_lost < 0)
	{
		candidate->floor.positive_marginal_exception = TRUE;
		candidate->repeat_exception_reason = IRONMON_REPEAT_NET_POSITIVE_RECOVERY;
	}
}

static void IronmonAI_BuildObservation(u8 bank, bool8 includeSwitches,
	struct IronmonPolicyObservation* observation)
{
	struct StandardPolicyObservation standard;
	u16 moves[MAX_MON_MOVES], counts[MAX_MON_MOVES];
	u8 foe = FOE(bank), i, known = 0;
	Memset(observation, 0, sizeof(*observation));
	StandardAI_BuildObservation(bank, includeSwitches, &standard);
	for (i = 0; i < MAX_MON_MOVES; ++i)
	{
		counts[i] = gNewBS->ai.ironmonMoveUseCounts[foe][i];
		/* Generic battle history can record an unprinted attempt.  Ironmon
		 * treats the aligned slot as revealed only after its public producer
		 * has incremented the count. */
		moves[i] = counts[i] ? BATTLE_HISTORY->usedMoves[foe][i] : MOVE_NONE;
		if (moves[i] != MOVE_NONE) ++known;
	}
	if (IronmonPolicyBuildResponses(moves, counts, MAX_MON_MOVES - known,
		observation->responses,
		&observation->response_count) != 0)
		return;
	observation->count = standard.count;
	for (i = 0; i < standard.count; ++i)
	{
		struct IronmonPolicyCandidate* candidate = &observation->candidates[i];
		candidate->floor = standard.candidates[i];
		/* The common Standard floor owns the projection.  Ironmon may widen its
		 * robust-KO certificate only in the same narrow public modifier context
		 * used for revealed responses; it never reads private opponent facts. */
		if (candidate->floor.kind == STANDARD_POLICY_MOVE
			&& candidate->floor.legal
			&& SPLIT(gBattleMons[bank].moves[candidate->floor.id]) != SPLIT_STATUS
			&& IronmonAI_CertifiedIncomingModifiers(foe, bank, NULL))
			StandardAI_DeriveDamageWithCertificate(bank, foe,
				gBattleMons[bank].moves[candidate->floor.id], &candidate->floor, TRUE);
		candidate->ironmon_switch_emergency = candidate->floor.standard_switch_emergency;
		candidate->stay_defensible = candidate->floor.kind == STANDARD_POLICY_MOVE
			&& candidate->floor.legal && !candidate->floor.known_no_effect
			&& (candidate->floor.productive || candidate->floor.unknown_potentially_productive);
		candidate->response_count = observation->response_count;
		candidate->tactical_class = IronmonAI_Classify(bank, candidate);
		IronmonAI_AssignFamily(bank, candidate);
	}
	for (i = 0; i < standard.count; ++i)
		IronmonAI_FillBranches(bank, observation, &observation->candidates[i]);
	/* A response-derived emergency is certified only with no aggregate UNKNOWN:
	 * every defensible stay loses the active and every admitted entry survives. */
	if (includeSwitches
		&& observation->responses[observation->response_count - 1].id
			!= IRONMON_POLICY_UNKNOWN_RESPONSE)
	{
		u8 defensibleSurvives = FALSE;
		for (i = 0; i < standard.count; ++i)
		{
			u8 branch;
			struct IronmonPolicyCandidate* candidate = &observation->candidates[i];
			if (!candidate->stay_defensible) continue;
			for (branch = 0; branch < candidate->response_count; ++branch)
				if (candidate->responses[branch].net_faints >= 0)
					defensibleSurvives = TRUE;
		}
		if (!defensibleSurvives)
			for (i = 0; i < standard.count; ++i)
			{
				u8 branch, safe = TRUE;
				struct IronmonPolicyCandidate* candidate = &observation->candidates[i];
				if (candidate->floor.kind != STANDARD_POLICY_SWITCH
					|| !candidate->floor.legal || !candidate->floor.switch_legal
					|| !candidate->floor.entry_survives || candidate->floor.forced) continue;
				for (branch = 0; branch < candidate->response_count; ++branch)
					if (candidate->responses[branch].net_faints < 0) safe = FALSE;
				if (safe) candidate->ironmon_switch_emergency = TRUE;
			}
	}
}

bool8 IronmonAI_IsSupportedBattle(void)
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
	return (gBattleTypeFlags & BATTLE_TYPE_TRAINER) && !(gBattleTypeFlags & excluded)
		&& !IsRaidBattle() && !IsInverseBattle()
		&& !IsFrontierTrainerId(gTrainerBattleOpponent_A)
		&& GetTrainerAIProfile() == TRAINER_AI_PROFILE_IRONMON_SMART;
}

static u32* IronmonAI_GetPolicyRng(u8 bank)
{
	if (!gNewBS->ai.ironmonPolicySeeded[bank])
	{
		gNewBS->ai.ironmonPolicyRng[bank] = IRONMON_AI_DEFAULT_SEED
			^ ((u32)gTrainerBattleOpponent_A << 8) ^ bank;
		gNewBS->ai.ironmonPolicySeeded[bank] = TRUE;
	}
	return &gNewBS->ai.ironmonPolicyRng[bank];
}

void IronmonAI_SetupAIData(void)
{
	gBankAttacker = gActiveBattler;
	gBankTarget = FOE(gActiveBattler);
	gBattleResources->AIScriptsStack->size = 0;
}

static u8 IronmonAI_Choose(bool8 includeSwitches, struct StandardPolicyCandidate* selected)
{
	struct StandardPolicyMemory memory;
	struct IronmonPolicyObservation* observation = &sIronmonObservation;
	struct IronmonPolicyResult* result = &sIronmonResult;
	u8 bank = gBankAttacker, i;
	int policyRc;
	IronmonAI_BuildObservation(bank, includeSwitches, observation);
	StandardAI_LoadMemory(bank, &memory);
	policyRc = IronmonPolicyChoose(observation, &memory, IronmonAI_GetPolicyRng(bank), result);
#ifdef CFRU_AI_TEST_TRACE
	if (IronmonAI_TestPolicyRcOverride != -2147483647 - 1)
		policyRc = IronmonAI_TestPolicyRcOverride;
	if (IronmonAI_TestSelectedIdOverride != 0xFF)
		result->selected_id = IronmonAI_TestSelectedIdOverride;
	IronmonAI_TestLastPolicyRc = policyRc;
	IronmonAI_TestLastSelectedId = IRONMON_AI_PENDING_NONE;
	IronmonAI_TestLastFailureReason = policyRc == IRONMON_POLICY_OK
		? AI_ADAPTER_FAILURE_NONE
		: policyRc == IRONMON_POLICY_NO_ADMITTED_ACTION
			? AI_ADAPTER_FAILURE_NO_ADMITTED_ACTION : AI_ADAPTER_FAILURE_POLICY_ERROR;
#endif
	if (policyRc != IRONMON_POLICY_OK)
		return IRONMON_AI_PENDING_NONE;
	for (i = 0; i < observation->count; ++i)
		if (observation->candidates[i].floor.id == result->selected_id)
		{
			*selected = observation->candidates[i].floor;
			StandardAI_StageLastAction(bank, selected);
		#ifdef CFRU_AI_TEST_TRACE
			IronmonAI_TestLastSelectedId = result->selected_id;
			IronmonAI_TestLastFailureReason = AI_ADAPTER_FAILURE_NONE;
		#endif
			return selected->id;
		}
#ifdef CFRU_AI_TEST_TRACE
	IronmonAI_TestLastFailureReason = AI_ADAPTER_FAILURE_SELECTED_ID_LOOKUP;
#endif
	return IRONMON_AI_PENDING_NONE;
}

u8 IronmonAI_ChooseReplacement(void)
{
	struct StandardPolicyMemory memory;
	struct IronmonPolicyObservation* observation = &sIronmonObservation;
	struct IronmonPolicyResult* result = &sIronmonResult;
	u8 bank = gActiveBattler, i;
	IronmonAI_BuildObservation(bank, TRUE, observation);
	StandardAI_LoadMemory(bank, &memory);
	for (i = 0; i < observation->count; ++i)
	{
		struct IronmonPolicyCandidate* c = &observation->candidates[i];
		if (c->floor.kind == STANDARD_POLICY_MOVE) c->floor.legal = FALSE;
		else
		{
			u8 branch;
			c->floor.forced = TRUE;
			c->floor.switch_legal = c->floor.legal;
			c->ironmon_switch_emergency = FALSE;
			c->tactical_class = IRONMON_TACTICAL_FORCED_REPLACEMENT;
			/* Replacement happens after the active has fainted.  Preserve the
			 * candidate's public entry cost, but remove the current-turn response
			 * that voluntary switches must take on entry. */
			for (branch = 0; branch < c->response_count; ++branch)
			{
				c->responses[branch].net_faints = c->floor.net_faints;
				c->responses[branch].opponent_hp_fraction_lost =
					c->floor.opponent_hp_fraction_lost;
				c->responses[branch].own_hp_fraction_lost =
					c->floor.own_hp_fraction_lost;
				c->responses[branch].future_gain_undiscounted = 0;
				c->responses[branch].entry_cost = c->floor.entry_cost;
			}
		}
	}
	if (IronmonPolicyChoose(observation, &memory, IronmonAI_GetPolicyRng(bank), result) == 0)
		for (i = 0; i < observation->count; ++i)
			if (observation->candidates[i].floor.id == result->selected_id)
			{
				StandardAI_StageLastAction(bank, &observation->candidates[i].floor);
				return observation->candidates[i].floor.switch_to;
			}
	return PARTY_SIZE;
}

u8 IronmonAI_ChooseMoveOrAction(void)
{
	struct StandardPolicyCandidate selected;
	u8 bank = gBankAttacker, choice;
	if (gNewBS->ai.standardPendingValid[bank])
	{
		choice = gNewBS->ai.standardPendingAction[bank];
		gNewBS->ai.standardPendingValid[bank] = FALSE;
		if (gNewBS->ai.standardPendingKind[bank] == STANDARD_POLICY_SWITCH
			|| choice >= MAX_MON_MOVES || gBattleMons[bank].moves[choice] == MOVE_NONE)
		{
#ifdef CFRU_AI_TEST_TRACE
			IronmonAI_TestLastFailureReason = AI_ADAPTER_FAILURE_PENDING_STATE;
#endif
			return IRONMON_AI_PENDING_NONE;
		}
		gBattleStruct->chosenMovePositions[bank] = choice;
		gChosenMovesByBanks[bank] = gBattleMons[bank].moves[choice];
		return choice;
	}
	choice = IronmonAI_Choose(FALSE, &selected);
	if (choice == IRONMON_AI_PENDING_NONE || selected.kind != STANDARD_POLICY_MOVE)
	{
#ifdef CFRU_AI_TEST_TRACE
		if (choice != IRONMON_AI_PENDING_NONE)
			IronmonAI_TestLastFailureReason = AI_ADAPTER_FAILURE_NON_MOVE_STATE;
#endif
		return IRONMON_AI_PENDING_NONE;
	}
	gBattleStruct->chosenMovePositions[bank] = choice;
	gChosenMovesByBanks[bank] = gBattleMons[bank].moves[choice];
	gBankTarget = FOE(bank);
	return choice;
}

void IronmonAI_TrySwitchOrUseItem(void)
{
	struct StandardPolicyCandidate selected;
	u8 bank = gActiveBattler, choice;
	gBankAttacker = bank; gBankTarget = FOE(bank);
	if (gNewBS->ai.standardPendingValid[bank])
	{
		EmitTwoReturnValues(1, gNewBS->ai.standardPendingKind[bank] == STANDARD_POLICY_SWITCH
			? ACTION_SWITCH : ACTION_USE_MOVE, (bank ^ BIT_SIDE) << 8);
		return;
	}
	choice = IronmonAI_Choose(TRUE, &selected);
	if (choice == IRONMON_AI_PENDING_NONE)
	{ EmitTwoReturnValues(1, ACTION_USE_MOVE, (bank ^ BIT_SIDE) << 8); return; }
	gNewBS->ai.standardPendingValid[bank] = TRUE;
	gNewBS->ai.standardPendingKind[bank] = selected.kind;
	if (selected.kind == STANDARD_POLICY_SWITCH)
	{
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
