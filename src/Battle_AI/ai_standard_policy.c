#include <stdint.h>

#include "../../include/new/ai_standard_policy.h"

#define STANDARD_INT32_MIN (-2147483647 - 1)
#define STANDARD_INT32_MAX 2147483647

enum
{
	STANDARD_ERROR = -1,
	STANDARD_NO_ADMITTED_ACTION = -2,
	STANDARD_INVALID_CANDIDATE = -3,
};

static int32_t ClampInt32(int64_t value)
{
	if (value < STANDARD_INT32_MIN)
		return STANDARD_INT32_MIN;
	if (value > STANDARD_INT32_MAX)
		return STANDARD_INT32_MAX;
	return (int32_t)value;
}

static int32_t TowardZero(int64_t numerator, int32_t denominator)
{
	int64_t magnitude = numerator < 0 ? -numerator : numerator;
	int32_t result = (int32_t)(magnitude / denominator);
	return numerator < 0 ? -result : result;
}

static uint8_t IsStatChangeFamily(uint8_t family)
{
	family = StandardPolicyNormalizeEffectFamily(family);
	return family >= STANDARD_EFFECT_ACCURACY_DOWN
		&& family <= STANDARD_EFFECT_EVASION_DOWN;
}

uint8_t StandardPolicyNormalizeEffectFamily(uint8_t family)
{
	if (family == STANDARD_EFFECT_SAND_ATTACK || family == STANDARD_EFFECT_SMOKESCREEN)
		return STANDARD_EFFECT_ACCURACY_DOWN;
	if (family == STANDARD_EFFECT_STRING_SHOT || family == STANDARD_EFFECT_EQUIVALENT_SPEED_DOWN)
		return STANDARD_EFFECT_SPEED_DOWN;
	return family;
}

void StandardPolicyResetMemory(struct StandardPolicyMemory* memory)
{
	uint8_t i;

	memory->count = 0;
	for (i = 0; i < STANDARD_POLICY_MEMORY_LIMIT; ++i)
	{
		memory->decisions[i].kind = STANDARD_POLICY_MOVE;
		memory->decisions[i].effect_family = STANDARD_EFFECT_NONE;
		memory->decisions[i].success = 0;
		memory->decisions[i].forced = 0;
		memory->decisions[i].switch_from = 0xFF;
		memory->decisions[i].switch_to = 0xFF;
		memory->decisions[i].public_stage_before = 0;
		memory->decisions[i].public_stage_after = 0;
	}
}

void StandardPolicyRecordMemory(struct StandardPolicyMemory* memory,
	const struct StandardPolicyMemoryDecision* decision)
{
	uint8_t i;

	if (memory->count < STANDARD_POLICY_MEMORY_LIMIT)
	{
		memory->decisions[memory->count++] = *decision;
		return;
	}

	for (i = 1; i < STANDARD_POLICY_MEMORY_LIMIT; ++i)
		memory->decisions[i - 1] = memory->decisions[i];
	memory->decisions[STANDARD_POLICY_MEMORY_LIMIT - 1] = *decision;
}

static uint8_t ConsecutiveSuccessfulFamily(const struct StandardPolicyMemory* memory,
	uint8_t family)
{
	uint8_t normalized = StandardPolicyNormalizeEffectFamily(family);
	uint8_t count = 0;
	int i;

	if (normalized == STANDARD_EFFECT_NONE)
		return 0;

	for (i = (int)memory->count - 1; i >= 0; --i)
	{
		const struct StandardPolicyMemoryDecision* decision = &memory->decisions[i];

		if (decision->forced || !decision->success)
			break;
		if (StandardPolicyNormalizeEffectFamily(decision->effect_family) != normalized)
			break;
		++count;
	}
	return count;
}

static uint8_t WouldFormAbaSwitchLoop(const struct StandardPolicyMemory* memory,
	uint8_t switch_from, uint8_t switch_to)
{
	int i;

	if (switch_from == 0xFF || switch_to == 0xFF)
		return 0;

	for (i = (int)memory->count - 1; i >= 0; --i)
	{
		const struct StandardPolicyMemoryDecision* decision = &memory->decisions[i];

		if (decision->kind != STANDARD_POLICY_SWITCH || decision->forced)
			continue;
		return decision->switch_from == switch_to && decision->switch_to == switch_from;
	}
	return 0;
}

static uint16_t FloorReasons(const struct StandardPolicyCandidate* candidate,
	const struct StandardPolicyMemory* memory)
{
	uint16_t reasons = 0;
	uint8_t repeats;

	if (!candidate->legal)
		return STANDARD_FLOOR_ILLEGAL;
	if (candidate->kind == STANDARD_POLICY_SWITCH)
	{
		if (!candidate->switch_legal)
			reasons |= STANDARD_FLOOR_ILLEGAL_SWITCH;
		if (!candidate->entry_survives)
			reasons |= STANDARD_FLOOR_ENTRY_KO;
	}
	if (candidate->known_no_effect)
		reasons |= STANDARD_FLOOR_KNOWN_NO_EFFECT;
	if (candidate->redundant_status)
		reasons |= STANDARD_FLOOR_REDUNDANT_STATUS;
	if (candidate->pure_status
		&& IsStatChangeFamily(candidate->effect_family)
		&& candidate->stat_stage_before == candidate->stat_stage_after)
		reasons |= STANDARD_FLOOR_CAPPED_STAT_CHANGE;

	repeats = ConsecutiveSuccessfulFamily(memory, candidate->effect_family);
	if (candidate->pure_status && repeats >= 2 && !candidate->positive_marginal_exception)
		reasons |= STANDARD_FLOOR_HARMFUL_REPEAT;
	if (!candidate->productive && reasons == 0)
		reasons |= STANDARD_FLOOR_NO_MARGINAL_VALUE;
	return reasons;
}

static uint16_t AdmissionReasons(const struct StandardPolicyCandidate* candidate,
	const struct StandardPolicyMemory* memory, uint8_t floor_eligible)
{
	if (!floor_eligible)
		return 0;
	if (candidate->kind != STANDARD_POLICY_SWITCH)
		return STANDARD_ADMISSION_STAY;
	if (candidate->forced)
		return STANDARD_ADMISSION_FORCED_REPLACEMENT;
	if (!candidate->standard_switch_emergency)
		return STANDARD_ADMISSION_NON_EMERGENCY_SWITCH;
	if (WouldFormAbaSwitchLoop(memory, candidate->switch_from, candidate->switch_to)
		&& !candidate->positive_marginal_exception)
		return STANDARD_ADMISSION_SWITCH_LOOP;
	return STANDARD_ADMISSION_EMERGENCY_SWITCH;
}

static int IsUtilityValid(const struct StandardPolicyCandidate* candidate)
{
	return candidate->net_faints >= -1 && candidate->net_faints <= 1
		&& candidate->opponent_hp_fraction_lost >= 0
		&& candidate->opponent_hp_fraction_lost <= STANDARD_POLICY_HP_SCALE
		&& candidate->own_hp_fraction_lost >= -STANDARD_POLICY_HP_SCALE
		&& candidate->own_hp_fraction_lost <= STANDARD_POLICY_HP_SCALE
		&& candidate->immediate_future_gain >= -40
		&& candidate->immediate_future_gain <= 40
		&& candidate->entry_cost >= 0
		&& candidate->repeat_cost >= 0
		&& candidate->uncertainty_cost >= 0;
}

static int32_t Utility(const struct StandardPolicyCandidate* candidate,
	struct StandardPolicyDiagnostic* diagnostic)
{
	int64_t hp_delta = (int64_t)candidate->opponent_hp_fraction_lost
		- candidate->own_hp_fraction_lost;
	int64_t net_faints_term = 200LL * candidate->net_faints;
	int32_t hp_delta_term = TowardZero(100LL * hp_delta, STANDARD_POLICY_HP_SCALE);
	int64_t raw = net_faints_term + hp_delta_term + candidate->immediate_future_gain
		- candidate->entry_cost - candidate->repeat_cost - candidate->uncertainty_cost;
	int32_t total = ClampInt32(raw);

	diagnostic->hp_delta_term = hp_delta_term;
	diagnostic->net_faints_term = (int32_t)net_faints_term;
	return total;
}

uint32_t StandardPolicyNextU32(uint32_t* state)
{
	if (*state == 0)
		*state = 0x6D2B79F5;
	*state ^= *state << 13;
	*state ^= *state >> 17;
	*state ^= *state << 5;
	return *state;
}

uint32_t StandardPolicyBounded(uint32_t* state, uint32_t upper, uint8_t* draws)
{
	uint32_t threshold;
	uint32_t value;

	if (upper <= 1)
		return 0;

	/* Rejection threshold is (2^32 mod upper) without overflowing uint32_t. */
	threshold = (uint32_t)(-upper) % upper;
	do
	{
		value = StandardPolicyNextU32(state);
		++*draws;
	} while (value < threshold);
	return value % upper;
}

int StandardPolicyChoose(const struct StandardPolicyObservation* observation,
	const struct StandardPolicyMemory* memory, uint32_t* policy_rng_state,
	struct StandardPolicyResult* result)
{
	uint8_t floorEligible[STANDARD_POLICY_MAX_CANDIDATES] = {0};
	uint8_t admitted[STANDARD_POLICY_MAX_CANDIDATES] = {0};
	int32_t scores[STANDARD_POLICY_MAX_CANDIDATES] = {0};
	uint8_t legalCount = 0;
	uint8_t forcedCount = 0;
	uint8_t safeCount = 0;
	uint8_t koCount = 0;
	uint8_t admittedCount = 0;
	uint8_t nearCount = 0;
	uint8_t nearIndices[STANDARD_POLICY_MAX_CANDIDATES];
	uint8_t selectedIndex = 0xFF;
	uint8_t i;
	int32_t bestScore = STANDARD_INT32_MIN;

	if (observation == 0 || memory == 0 || policy_rng_state == 0 || result == 0
		|| observation->count == 0 || observation->count > STANDARD_POLICY_MAX_CANDIDATES
		|| memory->count > STANDARD_POLICY_MEMORY_LIMIT)
		return STANDARD_ERROR;

	result->policy_rng_draws = 0;
	result->no_productive_fallback = 0;
	for (i = 0; i < observation->count; ++i)
	{
		const struct StandardPolicyCandidate* candidate = &observation->candidates[i];
		struct StandardPolicyDiagnostic* diagnostic = &result->diagnostics[i];

		if (!IsUtilityValid(candidate))
			return STANDARD_INVALID_CANDIDATE;
		diagnostic->id = candidate->id;
		diagnostic->utility_total = Utility(candidate, diagnostic);
		diagnostic->floor_reasons = 0;
		diagnostic->admission_reasons = 0;
		diagnostic->standard_eligible = 0;
		diagnostic->near_best = 0;
		diagnostic->selected = 0;
		scores[i] = diagnostic->utility_total;
		if (candidate->legal)
		{
			++legalCount;
			if (candidate->forced)
				++forcedCount;
		}
	}
	if (legalCount == 0)
		return STANDARD_NO_ADMITTED_ACTION;

	if (forcedCount != 0)
	{
		for (i = 0; i < observation->count; ++i)
		{
			if (observation->candidates[i].legal && observation->candidates[i].forced)
			{
				floorEligible[i] = 1;
				++safeCount;
			}
			else if (observation->candidates[i].legal)
				result->diagnostics[i].floor_reasons = STANDARD_FLOOR_FORCED_PRESENT;
			else
				result->diagnostics[i].floor_reasons = STANDARD_FLOOR_ILLEGAL;
		}
	}
	else
	{
		for (i = 0; i < observation->count; ++i)
		{
			uint16_t reasons = FloorReasons(&observation->candidates[i], memory);
			result->diagnostics[i].floor_reasons = reasons;
			if (reasons == 0)
			{
				floorEligible[i] = 1;
				++safeCount;
				if (observation->candidates[i].robust_safe_ko)
					++koCount;
			}
		}

		if (safeCount == 0)
		{
			uint8_t fallback = 0xFF;
			for (i = 0; i < observation->count; ++i)
			{
				if (!observation->candidates[i].legal)
					continue;
				if (fallback == 0xFF
					|| observation->candidates[i].fallback_cost < observation->candidates[fallback].fallback_cost
					|| (observation->candidates[i].fallback_cost == observation->candidates[fallback].fallback_cost
						&& observation->candidates[i].id < observation->candidates[fallback].id))
					fallback = i;
			}
			floorEligible[fallback] = 1;
			result->diagnostics[fallback].floor_reasons = 0;
			result->no_productive_fallback = 1;
			safeCount = 1;
		}
		else if (koCount != 0)
		{
			for (i = 0; i < observation->count; ++i)
			{
				if (floorEligible[i] && !observation->candidates[i].robust_safe_ko)
				{
					floorEligible[i] = 0;
					result->diagnostics[i].floor_reasons = STANDARD_FLOOR_ROBUST_KO_DOMINATES;
					--safeCount;
				}
			}
		}
	}

	for (i = 0; i < observation->count; ++i)
	{
		uint16_t reasons = AdmissionReasons(&observation->candidates[i], memory, floorEligible[i]);
		result->diagnostics[i].admission_reasons = floorEligible[i] ? reasons
			: result->diagnostics[i].floor_reasons;
		if (floorEligible[i] && reasons != STANDARD_ADMISSION_NON_EMERGENCY_SWITCH
			&& reasons != STANDARD_ADMISSION_SWITCH_LOOP)
		{
			admitted[i] = 1;
			++admittedCount;
		}
	}
	if (admittedCount == 0)
		return STANDARD_NO_ADMITTED_ACTION;

	for (i = 0; i < observation->count; ++i)
	{
		if (admitted[i] && scores[i] > bestScore)
			bestScore = scores[i];
	}
	for (i = 0; i < observation->count; ++i)
	{
		if (admitted[i] && scores[i] >= bestScore - STANDARD_POLICY_EPSILON)
			nearIndices[nearCount++] = i;
	}
	/* The host policy sorts stable action IDs before calculating near-best. */
	for (i = 0; i < nearCount; ++i)
	{
		uint8_t j;
		for (j = i + 1; j < nearCount; ++j)
		{
			if (observation->candidates[nearIndices[j]].id < observation->candidates[nearIndices[i]].id)
			{
				uint8_t swap = nearIndices[i];
				nearIndices[i] = nearIndices[j];
				nearIndices[j] = swap;
			}
		}
	}
	if (nearCount == 1)
		selectedIndex = nearIndices[0];
	else
		selectedIndex = nearIndices[StandardPolicyBounded(policy_rng_state, nearCount, &result->policy_rng_draws)];

	result->selected_id = observation->candidates[selectedIndex].id;
	result->best_score = bestScore;
	result->near_best_count = nearCount;
	for (i = 0; i < observation->count; ++i)
	{
		result->diagnostics[i].near_best = admitted[i] && scores[i] >= bestScore - STANDARD_POLICY_EPSILON;
		result->diagnostics[i].selected = i == selectedIndex;
		result->diagnostics[i].standard_eligible = admitted[i];
	}
	return 0;
}
