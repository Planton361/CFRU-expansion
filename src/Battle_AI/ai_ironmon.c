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

/* The bounded 9x8 observation is too large for the battle callback stack.
 * One non-reentrant ordinary-singles decision uses this EWRAM scratch. */
static EWRAM_DATA struct IronmonPolicyObservation sIronmonObservation;
static EWRAM_DATA struct IronmonPolicyResult sIronmonResult;

struct IronmonIncoming
{
	u16 minimum;
	u16 maximum;
	u16 fraction;
	u8 supported;
	u8 immune;
	u8 survives;
	u8 order_known;
	u8 opponent_first;
};

static u32 IronmonAI_Min(u32 left, u32 right) { return left < right ? left : right; }
static u32 IronmonAI_Max(u32 left, u32 right) { return left > right ? left : right; }

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

static u8 IronmonAI_CertifiedIncomingModifiers(u8 foe, u8 target)
{
	return (gStatuses3[foe] & STATUS3_ABILITY_SUPPRESS)
		&& (gStatuses3[target] & STATUS3_ABILITY_SUPPRESS)
		&& gNewBS->MagicRoomTimer > 1 && !gBattleWeather && !gNewBS->TerrainTimer
		&& !gNewBS->WonderRoomTimer && !gNewBS->IonDelugeTimer
		&& !gNewBS->ElectrifyTimers[foe] && !gNewBS->MudSportTimer
		&& !gNewBS->WaterSportTimer && !gNewBS->AuroraVeilTimers[SIDE(target)]
		&& !gSideStatuses[SIDE(foe)] && !gSideStatuses[SIDE(target)];
}

static void IronmonAI_Order(u8 bank, u8 foe, s8 ownPriority, u16 response,
	struct IronmonIncoming* incoming)
{
	u16 species = gNewBS->ai.standardDisplayedSpecies[foe];
	u32 ownSpeed, low, high;
	s8 responsePriority = gBattleMoves[response].priority;
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
	low = StandardMechanicsSpeed(gBaseStats[species].baseSpeed,
		gBattleMons[foe].level, gBattleMons[foe].statStages[STAT_STAGE_SPEED - 1], FALSE);
	high = StandardMechanicsSpeed(gBaseStats[species].baseSpeed,
		gBattleMons[foe].level, gBattleMons[foe].statStages[STAT_STAGE_SPEED - 1], TRUE);
	/* Hidden speed items remain possible unless their effect is suppressed. */
	if (gNewBS->MagicRoomTimer <= 1)
	{
		low = IronmonAI_Max(1, low / 2);
		high = IronmonAI_Min(65535, high * 2);
	}
	if (gBattleMons[bank].status1 & STATUS_PARALYSIS) ownSpeed /= 2;
	if (gBattleMons[foe].status1 & STATUS_PARALYSIS) { low /= 2; high /= 2; }
	if (gNewBS->TrickRoomTimer > 1)
	{
		if (ownSpeed < low) { incoming->order_known = TRUE; incoming->opponent_first = TRUE; }
		else if (ownSpeed > high) { incoming->order_known = TRUE; incoming->opponent_first = FALSE; }
	}
	else if (!gNewBS->TrickRoomTimer)
	{
		if (ownSpeed > high) { incoming->order_known = TRUE; incoming->opponent_first = FALSE; }
		else if (ownSpeed < low) { incoming->order_known = TRUE; incoming->opponent_first = TRUE; }
	}
}

static void IronmonAI_ProjectIncoming(u8 bank, u16 response, const struct Pokemon* partyMon,
	s8 ownPriority, struct IronmonIncoming* incoming)
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
		hp = gBattleMons[bank].hp; maxHP = gBattleMons[bank].maxHP; level = gBattleMons[bank].level;
	}
	else
	{
		ownTypes[0] = gBaseStats[partyMon->species].type1;
		ownTypes[1] = gBaseStats[partyMon->species].type2;
		ownTypes[2] = NUMBER_OF_MON_TYPES; ability = GetMonAbility(partyMon);
		defense = split == SPLIT_PHYSICAL ? partyMon->defense : partyMon->spDefense;
		defenseStage = 6; hp = partyMon->hp; maxHP = partyMon->maxHP; level = partyMon->level;
	}
	incoming->supported = TRUE;
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
	input.certified_modifiers = IronmonAI_CertifiedIncomingModifiers(foe, bank)
		&& (partyMon == NULL || ability == ABILITY_NONE);
	for (i = 0; i < 3; ++i)
		input.effectiveness[i] = ownTypes[i] >= NUMBER_OF_MON_TYPES
			|| (i && ownTypes[i] == ownTypes[0]) || (i == 2 && ownTypes[i] == ownTypes[1])
			? 10 : StandardAI_PublicTypeMultiplier(type, ownTypes[i]);
	StandardMechanicsDamage(&input, &projected, &envelope);
	incoming->minimum = envelope.minimum;
	incoming->maximum = envelope.maximum;
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
		|| !(gStatuses3[bank] & STATUS3_ABILITY_SUPPRESS)
		|| !(gStatuses3[foe] & STATUS3_ABILITY_SUPPRESS)
		|| gNewBS->MagicRoomTimer <= 1 || gBattleWeather || gNewBS->TerrainTimer)
		return FALSE;
	delta = candidate->stat_stage_before - candidate->stat_stage_after;
	afterTwo = candidate->stat_stage_after >= delta
		? candidate->stat_stage_after - delta : STAT_STAGE_MIN;
	own = StandardMechanicsStage(gBattleMons[bank].speed,
		gBattleMons[bank].statStages[STAT_STAGE_SPEED - 1]);
	afterOneLow = StandardMechanicsSpeed(gBaseStats[species].baseSpeed,
		gBattleMons[foe].level, candidate->stat_stage_after, FALSE);
	afterOneHigh = StandardMechanicsSpeed(gBaseStats[species].baseSpeed,
		gBattleMons[foe].level, candidate->stat_stage_after, TRUE);
	afterTwoLow = StandardMechanicsSpeed(gBaseStats[species].baseSpeed,
		gBattleMons[foe].level, afterTwo, FALSE);
	afterTwoHigh = StandardMechanicsSpeed(gBaseStats[species].baseSpeed,
		gBattleMons[foe].level, afterTwo, TRUE);
	if (gNewBS->TrickRoomTimer > 2)
		return !(own < afterOneLow) && own < afterTwoLow;
	if (gNewBS->TrickRoomTimer) return FALSE;
	return !(own > afterOneHigh) && own > afterTwoHigh;
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

static void IronmonAI_FillBranches(u8 bank, struct IronmonPolicyObservation* observation,
	struct IronmonPolicyCandidate* candidate)
{
	u8 branchIndex;
	u8 firstId, lastId;
	struct Pokemon* party = LoadPartyRange(bank, &firstId, &lastId);
	const struct Pokemon* switchTarget = candidate->floor.kind == STANDARD_POLICY_SWITCH
		? &party[candidate->floor.switch_to] : NULL;
	u8 setupThreshold = FALSE;
	(void)firstId; (void)lastId;
	if (candidate->tactical_class == IRONMON_TACTICAL_SETUP_PLAN
		&& candidate->floor.immediate_future_gain > 0)
	{
		u8 slot; u16 best = 0;
		for (slot = 0; slot < MAX_MON_MOVES; ++slot)
			if (observation->candidates[slot].floor.kind == STANDARD_POLICY_MOVE)
				best = IronmonAI_Max(best, observation->candidates[slot].floor.opponent_hp_fraction_lost);
		if (best * 2 < 256 && best * 3 >= 256
			&& (best + candidate->floor.immediate_future_gain * 256 / 100) * 2 >= 256)
			setupThreshold = TRUE;
	}
	for (branchIndex = 0; branchIndex < observation->response_count; ++branchIndex)
	{
		struct IronmonPolicyBranch* branch = &candidate->responses[branchIndex];
		u16 response = observation->responses[branchIndex].id;
		struct IronmonIncoming incoming;
		s32 ownLoss = candidate->floor.own_hp_fraction_lost;
		u8 horizonSurvives;
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
			&incoming);
		if (!incoming.supported)
			continue;
		if (candidate->floor.kind == STANDARD_POLICY_MOVE
			&& candidate->floor.robust_safe_ko && incoming.order_known && !incoming.opponent_first)
			incoming.fraction = 0;
		ownLoss += incoming.fraction;
		if (ownLoss < -256) ownLoss = -256;
		if (ownLoss > 256) ownLoss = 256;
		branch->own_hp_fraction_lost = ownLoss;
		if (!incoming.survives && (candidate->floor.kind == STANDARD_POLICY_SWITCH
			|| !incoming.order_known || incoming.opponent_first))
		{
			branch->net_faints = -1;
			branch->own_hp_fraction_lost = 256;
			continue;
		}
		if (!incoming.order_known || !incoming.survives)
			continue;
		horizonSurvives = !incoming.opponent_first
			|| (u32)incoming.maximum * 2 < gBattleMons[bank].hp;
		if (candidate->tactical_class == IRONMON_TACTICAL_DAMAGE
			&& candidate->floor.opponent_hp_fraction_lost > 0
			&& candidate->floor.opponent_hp_fraction_lost * 2 >= 256
			&& horizonSurvives)
		{
			u8 value = candidate->floor.opponent_hp_fraction_lost * 100 / 256;
			branch->future_gain_undiscounted = IronmonAI_Min(80, value * 2);
			candidate->tactical_class = IRONMON_TACTICAL_TWO_HKO;
		}
		else if (candidate->tactical_class == IRONMON_TACTICAL_SPEED_PLAN
			&& IronmonAI_TwoStepSpeedThreshold(bank, &candidate->floor)
			&& incoming.maximum * 2 < gBattleMons[bank].hp)
			branch->future_gain_undiscounted = 80;
		else if (candidate->tactical_class == IRONMON_TACTICAL_SETUP_PLAN
			&& setupThreshold && horizonSurvives)
			branch->future_gain_undiscounted = IronmonAI_Min(80,
				candidate->floor.immediate_future_gain * 2);
		else if (candidate->tactical_class == IRONMON_TACTICAL_RESIDUAL)
			branch->future_gain_undiscounted = IronmonAI_Min(80,
				candidate->floor.immediate_future_gain * 2);
		else if (candidate->tactical_class == IRONMON_TACTICAL_RECOVERY
			&& incoming.maximum >= gBattleMons[bank].hp
			&& incoming.maximum < gBattleMons[bank].hp
				- candidate->floor.own_hp_fraction_lost * gBattleMons[bank].maxHP / 256)
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
	IronmonAI_BuildObservation(bank, includeSwitches, observation);
	StandardAI_LoadMemory(bank, &memory);
	if (IronmonPolicyChoose(observation, &memory, IronmonAI_GetPolicyRng(bank), result) != 0)
		goto FALLBACK_TO_ENGINE;
	for (i = 0; i < observation->count; ++i)
		if (observation->candidates[i].floor.id == result->selected_id)
		{
			*selected = observation->candidates[i].floor;
			StandardAI_StageLastAction(bank, selected);
			return selected->id;
		}
FALLBACK_TO_ENGINE:
	for (i = 0; i < observation->count; ++i)
		if (observation->candidates[i].floor.kind == STANDARD_POLICY_MOVE
			&& observation->candidates[i].floor.id < MAX_MON_MOVES
			&& gBattleMons[bank].moves[observation->candidates[i].floor.id] != MOVE_NONE)
		{
			*selected = observation->candidates[i].floor;
			return selected->id;
		}
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
		if (gNewBS->ai.standardPendingKind[bank] == STANDARD_POLICY_SWITCH) return 0;
		gBattleStruct->chosenMovePositions[bank] = choice;
		gChosenMovesByBanks[bank] = gBattleMons[bank].moves[choice];
		return choice;
	}
	choice = IronmonAI_Choose(FALSE, &selected);
	if (choice == IRONMON_AI_PENDING_NONE || selected.kind != STANDARD_POLICY_MOVE) return 0;
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
