#include "../defines.h"
#include "../defines_battle.h"
#include "../../include/constants/battle_move_effects.h"
#include "../../include/constants/trainers.h"

#include "../../include/new/ai_master.h"
#include "../../include/new/ai_standard.h"
#include "../../include/new/ai_standard_policy.h"
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

static void StandardAI_LoadMemory(u8 bank, struct StandardPolicyMemory* memory);
static void StandardAI_SaveMemory(u8 bank, const struct StandardPolicyMemory* memory);
static void StandardAI_FinalizeLastAction(u8 bank);
static void StandardAI_StageLastAction(u8 bank, const struct StandardPolicyCandidate* candidate);
static void StandardAI_BuildObservation(u8 bank, bool8 includeSwitches,
	struct StandardPolicyObservation* observation);

static u16 StandardAI_OwnHpFraction(u8 bank)
{
	u32 hp = gBattleMons[bank].hp;
	u32 maxHp = gBattleMons[bank].maxHP;

	/* Own trainer HP is exact; no opponent max-HP or hidden stat is projected. */
	if (maxHp == 0)
		return 0;
	return (u16)MathMin(STANDARD_POLICY_HP_SCALE, (hp * STANDARD_POLICY_HP_SCALE + maxHp / 2) / maxHp);
}

static u8 StandardAI_KnownTypeImmunity(u16 move, u8 bankDef)
{
	ability_t knownAbility;
	u8 type;
	u8 type1;
	u8 type2;
	u8 type3;

	if (move == MOVE_NONE || gBattleMoves[move].power == 0 || SPLIT(move) == SPLIT_STATUS)
		return FALSE;
	type = gBattleMoves[move].type;
	if (type >= NUMBER_OF_MON_TYPES)
		return FALSE;
	knownAbility = GetRecordedAbility(bankDef);
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
	type1 = gBattleMons[bankDef].type1;
	type2 = gBattleMons[bankDef].type2;
	type3 = gBattleMons[bankDef].type3;
	return gTypeEffectiveness[type][type1] == TYPE_MUL_NO_EFFECT
		|| gTypeEffectiveness[type][type2] == TYPE_MUL_NO_EFFECT
		|| (type3 < NUMBER_OF_MON_TYPES && gTypeEffectiveness[type][type3] == TYPE_MUL_NO_EFFECT);
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

static u8 StandardAI_IsForcedMove(u8 bank, u8 move)
{
	if (gBattleMons[bank].status2 & (STATUS2_RECHARGE | STATUS2_MULTIPLETURNS))
		return gLockedMoves[bank] != MOVE_NONE && gLockedMoves[bank] == move;
	if (gDisableStructs[bank].encoreTimer && gDisableStructs[bank].encoredMove == move)
		return TRUE;
	return FALSE;
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

	if (stageId != 0)
	{
		candidate->productive = stageBefore != stageAfter;
		candidate->immediate_future_gain = candidate->productive ? 8 + 4 * delta : 0;
		if (family == STANDARD_EFFECT_ACCURACY_DOWN || family == STANDARD_EFFECT_SPEED_DOWN)
			candidate->uncertainty_cost = candidate->productive ? 4 : 0;
	}
	else if (effect == EFFECT_RESTORE_HP || effect == EFFECT_REST)
	{
		if (gBattleMons[bank].maxHP != 0 && gBattleMons[bank].hp < gBattleMons[bank].maxHP)
		{
			missingHpFraction = (gBattleMons[bank].maxHP - gBattleMons[bank].hp)
				* STANDARD_POLICY_HP_SCALE / gBattleMons[bank].maxHP;
			candidate->productive = TRUE;
			candidate->own_hp_fraction_lost = -(s16)MathMin(STANDARD_POLICY_HP_SCALE, missingHpFraction);
			candidate->immediate_future_gain = MathMin(40, missingHpFraction / 4);
		}
		else
			candidate->known_no_effect = TRUE;
	}
	else if (StandardAI_IsMajorStatusEffect(effect))
	{
		candidate->public_major_status = TRUE;
		candidate->productive = (gBattleMons[foe].status1 & STATUS_ANY) == 0;
		candidate->redundant_status = !candidate->productive;
		candidate->immediate_future_gain = candidate->productive ? 20 : 0;
		candidate->uncertainty_cost = candidate->productive ? 4 : 0;
	}
	else if (move != MOVE_NONE && !statusMove && gBattleMoves[move].power != 0)
	{
		/* Damage is unknown until a fair public/revealed damage bound exists. */
		candidate->productive = !knownNoEffect;
		candidate->uncertainty_cost = candidate->productive ? 8 : 0;
	}

	if (candidate->known_no_effect)
		candidate->productive = FALSE;
	return;
}

static u8 StandardAI_CanSwitchOut(u8 bank)
{
	u8 foe = FOE(bank);
	ability_t knownAbility = GetRecordedAbility(foe);
	bool8 canBeTrappedByUnknown = TRUE;
	/* GetRecordedAbility is fail-closed: it returns only a recorded or
	 * species-unambiguous ability and otherwise returns ABILITY_NONE. */

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

static void StandardAI_FillSwitchCandidate(u8 bank, u8 partyIndex, struct Pokemon* mon,
	struct StandardPolicyCandidate* candidate, u8 forced)
{
	u32 entryDamage = GetMonEntryHazardDamage(mon, SIDE(bank));
	u32 entryFraction = mon->maxHP == 0 ? STANDARD_POLICY_HP_SCALE
		: (entryDamage * STANDARD_POLICY_HP_SCALE) / mon->maxHP;

	Memset(candidate, 0, sizeof(*candidate));
	candidate->id = STANDARD_AI_SWITCH_ID_BASE + partyIndex;
	candidate->kind = STANDARD_POLICY_SWITCH;
	candidate->legal = mon->species != SPECIES_NONE && mon->hp != 0 && !mon->isEgg;
	candidate->productive = candidate->legal;
	candidate->switch_legal = forced ? candidate->legal : StandardAI_CanSwitchOut(bank) && candidate->legal;
	candidate->entry_survives = !WillFaintFromEntryHazards(mon, SIDE(bank));
	candidate->forced = forced;
	candidate->fallback_cost = 1000 + partyIndex;
	candidate->switch_from = gBattlerPartyIndexes[bank];
	candidate->switch_to = partyIndex;
	candidate->standard_switch_emergency = FALSE;
	candidate->entry_cost = MathMin(STANDARD_AI_INT32_MAX, entryFraction);
	if (!candidate->entry_survives)
		candidate->productive = FALSE;
}

static void StandardAI_LoadMemory(u8 bank, struct StandardPolicyMemory* memory)
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

static void StandardAI_StageLastAction(u8 bank, const struct StandardPolicyCandidate* candidate)
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

static void StandardAI_BuildObservation(u8 bank, bool8 includeSwitches,
	struct StandardPolicyObservation* observation)
{
	u8 foe = FOE(bank);
	u8 i;
	u8 forcedMove = FALSE;
	u8 hasProductiveMove = FALSE;
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
		if (candidate->legal && candidate->productive)
			hasProductiveMove = TRUE;
	}

	if (!includeSwitches)
		return;

	party = LoadPartyRange(bank, &firstId, &lastId);
	/* A low own health-bar fraction is an emergency signal, not matchup prediction. */
	if (StandardAI_OwnHpFraction(bank) <= 64)
		hasProductiveMove = FALSE;
	for (i = firstId; i < lastId && observation->count < STANDARD_POLICY_MAX_CANDIDATES; ++i)
	{
		struct StandardPolicyCandidate* candidate;
		if (i == gBattlerPartyIndexes[bank])
			continue;
		candidate = &observation->candidates[observation->count++];
		StandardAI_FillSwitchCandidate(bank, i, &party[i], candidate, !BATTLER_ALIVE(bank));
		if (!hasProductiveMove && candidate->legal && candidate->switch_legal && candidate->entry_survives)
			candidate->standard_switch_emergency = TRUE;
	}

}

bool8 StandardAI_IsSupportedBattle(void)
{
	u32 excluded = BATTLE_TYPE_DOUBLE | BATTLE_TYPE_LINK | BATTLE_TYPE_OAK_TUTORIAL
		| BATTLE_TYPE_MULTI | BATTLE_TYPE_SAFARI | BATTLE_TYPE_ROAMER
		| BATTLE_TYPE_EREADER_TRAINER | BATTLE_TYPE_SCRIPTED_WILD_1
		| BATTLE_TYPE_SCRIPTED_WILD_2 | BATTLE_TYPE_LEGENDARY_FRLG
		| BATTLE_TYPE_TRAINER_TOWER | BATTLE_TYPE_TWO_OPPONENTS
		| BATTLE_TYPE_INGAME_PARTNER | BATTLE_TYPE_POKE_DUDE | BATTLE_TYPE_OLD_MAN
		| BATTLE_TYPE_FRONTIER | BATTLE_TYPE_SHADOW_WARRIOR | BATTLE_TYPE_DYNAMAX;

	return (gBattleTypeFlags & BATTLE_TYPE_TRAINER)
		&& !(gBattleTypeFlags & excluded)
		&& !IsRaidBattle()
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
		return STANDARD_AI_PENDING_NONE;
	for (i = 0; i < observation.count; ++i)
	{
		if (observation.candidates[i].id == result.selected_id)
		{
			*selected = observation.candidates[i];
			StandardAI_StageLastAction(bank, selected);
			return selected->id;
		}
	}
	return STANDARD_AI_PENDING_NONE;
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
