#include <stdint.h>

#include "../../include/new/ai_ironmon_policy.h"

#define IRONMON_INT32_MIN (-2147483647 - 1)
#define IRONMON_INT32_MAX 2147483647
#define IRONMON_SWITCH_RANDOM_MIN 12
#define IRONMON_SWITCH_RANDOM_MAX 19
#define IRONMON_SWITCH_DETERMINISTIC_MIN 20
#define IRONMON_SWITCH_LOOP_COST 16
#define IRONMON_PROGRESS_EXCEPTION_MIN 8
#define IRONMON_REPEAT_EXCEPTION_MARGIN 8

enum
{
	IRONMON_ERROR = IRONMON_POLICY_ERROR,
	IRONMON_NO_ADMITTED_ACTION = IRONMON_POLICY_NO_ADMITTED_ACTION,
	IRONMON_INVALID_CANDIDATE = IRONMON_POLICY_INVALID_CANDIDATE,
};

struct Unsigned64
{
	uint32_t hi;
	uint32_t lo;
};

struct SignedMagnitude
{
	uint8_t negative;
	struct Unsigned64 magnitude;
};

struct SignedValue
{
	uint8_t negative;
	uint32_t magnitude;
};

static struct Unsigned64 Multiply32(uint32_t left, uint32_t right)
{
	uint32_t a = left >> 16, b = left & 0xFFFF;
	uint32_t c = right >> 16, d = right & 0xFFFF;
	uint32_t middle = a * d + b * c;
	struct Unsigned64 result;
	result.lo = b * d + (middle << 16);
	result.hi = a * c + (middle >> 16) + (result.lo < b * d);
	return result;
}

static int Compare64(struct Unsigned64 left, struct Unsigned64 right)
{
	if (left.hi != right.hi)
		return left.hi < right.hi ? -1 : 1;
	if (left.lo != right.lo)
		return left.lo < right.lo ? -1 : 1;
	return 0;
}

static struct Unsigned64 Add64(struct Unsigned64 left, struct Unsigned64 right)
{
	struct Unsigned64 result;
	result.lo = left.lo + right.lo;
	result.hi = left.hi + right.hi + (result.lo < left.lo);
	return result;
}

static struct Unsigned64 Subtract64(struct Unsigned64 left, struct Unsigned64 right)
{
	struct Unsigned64 result;
	result.lo = left.lo - right.lo;
	result.hi = left.hi - right.hi - (left.lo < right.lo);
	return result;
}

static void AddSignedProduct(struct SignedMagnitude* total, struct SignedValue value,
	uint32_t weight)
{
	struct Unsigned64 product = Multiply32(value.magnitude, weight);
	int comparison;

	if ((product.hi | product.lo) == 0)
		return;
	if ((total->magnitude.hi | total->magnitude.lo) == 0)
	{
		total->negative = value.negative;
		total->magnitude = product;
		return;
	}
	if (total->negative == value.negative)
	{
		total->magnitude = Add64(total->magnitude, product);
		return;
	}
	comparison = Compare64(total->magnitude, product);
	if (comparison >= 0)
		total->magnitude = Subtract64(total->magnitude, product);
	else
	{
		total->magnitude = Subtract64(product, total->magnitude);
		total->negative = value.negative;
	}
	if ((total->magnitude.hi | total->magnitude.lo) == 0)
		total->negative = 0;
}

/* The validated divisor is at most 2^20, so the shifted remainder is bounded
 * below 2^21.  This is exact unsigned long division using only 32-bit ops. */
static uint32_t Divide64By32(struct Unsigned64 numerator, uint32_t denominator)
{
	uint32_t quotient = 0;
	uint32_t remainder = 0;
	int bit;

	for (bit = 63; bit >= 0; --bit)
	{
		uint32_t incoming = bit >= 32
			? (numerator.hi >> (bit - 32)) & 1
			: (numerator.lo >> bit) & 1;
		remainder = (remainder << 1) | incoming;
		if (remainder >= denominator)
		{
			remainder -= denominator;
			if (bit < 32)
				quotient |= (uint32_t)1 << bit;
		}
	}
	return quotient;
}

static int32_t SaturateSigned(uint8_t negative, uint32_t magnitude)
{
	if (!negative)
		return magnitude > (uint32_t)IRONMON_INT32_MAX
			? IRONMON_INT32_MAX : (int32_t)magnitude;
	if (magnitude >= 0x80000000u)
		return IRONMON_INT32_MIN;
	return -(int32_t)magnitude;
}

static int32_t SubtractSmallAndSaturate(uint8_t negative, uint32_t magnitude,
	uint8_t cost)
{
	if (negative)
	{
		if (magnitude > 0x80000000u - cost)
			return IRONMON_INT32_MIN;
		return SaturateSigned(1, magnitude + cost);
	}
	if (magnitude >= cost)
		return SaturateSigned(0, magnitude - cost);
	return -(int32_t)(cost - magnitude);
}

static uint8_t IsStatChangeFamily(uint8_t family)
{
	family = StandardPolicyNormalizeEffectFamily(family);
	return family >= STANDARD_EFFECT_ACCURACY_DOWN
		&& family <= STANDARD_EFFECT_EVASION_DOWN;
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
		const struct StandardPolicyMemoryDecision* d = &memory->decisions[i];
		if (d->forced || !d->success)
			break;
		if (StandardPolicyNormalizeEffectFamily(d->effect_family) != normalized)
			break;
		++count;
	}
	return count;
}

static uint8_t AbaWithinThree(const struct StandardPolicyMemory* memory,
	const struct IronmonPolicyCandidate* candidate)
{
	int i, inspected = 0;
	if (candidate->floor.kind != STANDARD_POLICY_SWITCH || candidate->floor.forced)
		return 0;
	for (i = (int)memory->count - 1; i >= 0 && inspected < 3; --i, ++inspected)
	{
		const struct StandardPolicyMemoryDecision* d = &memory->decisions[i];
		if (d->kind == STANDARD_POLICY_SWITCH && !d->forced
			&& d->switch_from == candidate->floor.switch_to
			&& d->switch_to == candidate->floor.switch_from)
			return 1;
	}
	return 0;
}

static uint8_t ConsecutiveVoluntarySwitches(const struct StandardPolicyMemory* memory)
{
	uint8_t count = 0;
	int i;
	for (i = (int)memory->count - 1; i >= 0; --i)
	{
		const struct StandardPolicyMemoryDecision* d = &memory->decisions[i];
		if (d->kind == STANDARD_POLICY_SWITCH && d->forced)
			continue;
		if (d->kind != STANDARD_POLICY_SWITCH)
			break;
		++count;
	}
	return count;
}

static uint32_t FloorReasons(const struct IronmonPolicyCandidate* candidate,
	const struct StandardPolicyMemory* memory)
{
	const struct StandardPolicyCandidate* c = &candidate->floor;
	uint32_t reasons = 0;
	uint8_t repeats;
	if (!c->legal)
		return STANDARD_FLOOR_ILLEGAL;
	if (c->kind == STANDARD_POLICY_SWITCH)
	{
		if (!c->switch_legal) reasons |= STANDARD_FLOOR_ILLEGAL_SWITCH;
		if (!c->entry_survives) reasons |= STANDARD_FLOOR_ENTRY_KO;
	}
	if (c->known_no_effect) reasons |= STANDARD_FLOOR_KNOWN_NO_EFFECT;
	if (c->redundant_status) reasons |= STANDARD_FLOOR_REDUNDANT_STATUS;
	if (c->pure_status && IsStatChangeFamily(c->effect_family)
		&& c->stat_stage_before == c->stat_stage_after)
		reasons |= STANDARD_FLOOR_CAPPED_STAT_CHANGE;
	repeats = ConsecutiveSuccessfulFamily(memory, c->effect_family);
	if (c->pure_status && repeats >= 2 && !c->positive_marginal_exception)
		reasons |= STANDARD_FLOOR_HARMFUL_REPEAT;
	if (!c->productive && !c->unknown_potentially_productive && reasons == 0)
		reasons |= STANDARD_FLOOR_NO_MARGINAL_VALUE;
	return reasons;
}

static int ValidateObservation(const struct IronmonPolicyObservation* observation,
	const struct StandardPolicyMemory* memory)
{
	uint32_t totalWeight = 0;
	uint8_t i, j;
	if (observation == 0 || memory == 0 || observation->count == 0
		|| observation->count > IRONMON_POLICY_MAX_CANDIDATES
		|| observation->response_count == 0
		|| observation->response_count > IRONMON_POLICY_MAX_RESPONSES
		|| memory->count > STANDARD_POLICY_MEMORY_LIMIT)
		return 0;
	for (i = 0; i < observation->response_count; ++i)
	{
		if (!observation->responses[i].weight
			|| observation->responses[i].weight > IRONMON_POLICY_MAX_RESPONSE_WEIGHT
			|| totalWeight > IRONMON_POLICY_MAX_RESPONSE_WEIGHT - observation->responses[i].weight)
			return 0;
		totalWeight += observation->responses[i].weight;
		for (j = 0; j < i; ++j)
			if (observation->responses[j].id == observation->responses[i].id)
				return 0;
	}
	for (i = 0; i < observation->count; ++i)
	{
		const struct IronmonPolicyCandidate* c = &observation->candidates[i];
		if (c->response_count != observation->response_count
			|| c->repeat_exception_reason > IRONMON_REPEAT_RESIDUAL_WIN_LINE)
			return 0;
		for (j = 0; j < i; ++j)
			if (observation->candidates[j].floor.id == c->floor.id)
				return 0;
		for (j = 0; j < c->response_count; ++j)
		{
			const struct IronmonPolicyBranch* b = &c->responses[j];
			if (b->response_id != observation->responses[j].id
				|| b->net_faints < -1 || b->net_faints > 1
				|| b->opponent_hp_fraction_lost < 0
				|| b->opponent_hp_fraction_lost > STANDARD_POLICY_HP_SCALE
				|| b->own_hp_fraction_lost < -STANDARD_POLICY_HP_SCALE
				|| b->own_hp_fraction_lost > STANDARD_POLICY_HP_SCALE
				|| b->future_gain_undiscounted < -80
				|| b->future_gain_undiscounted > 80
				|| b->entry_cost < 0)
				return 0;
		}
	}
	return 1;
}

static struct SignedValue BranchValue(const struct IronmonPolicyBranch* branch,
	uint8_t repeatCost, uint8_t loopCost)
{
	int32_t future = branch->future_gain_undiscounted / 2;
	int32_t hp = 100 * ((int32_t)branch->opponent_hp_fraction_lost
		- branch->own_hp_fraction_lost) / STANDARD_POLICY_HP_SCALE;
	int32_t prefix = 200 * branch->net_faints + hp + future;
	uint32_t costs = (uint32_t)repeatCost + loopCost;
	struct SignedValue result;
	costs += (uint32_t)branch->entry_cost;
	if (prefix >= 0 && (uint32_t)prefix >= costs)
	{
		result.negative = 0;
		result.magnitude = (uint32_t)prefix - costs;
	}
	else
	{
		result.negative = 1;
		result.magnitude = costs + (prefix < 0 ? (uint32_t)-prefix : 0)
			- (prefix > 0 ? (uint32_t)prefix : 0);
	}
	if (!result.magnitude) result.negative = 0;
	return result;
}

static int CompareSignedValue(struct SignedValue left, struct SignedValue right)
{
	if (left.negative != right.negative)
		return left.negative ? -1 : 1;
	if (left.magnitude == right.magnitude) return 0;
	if (left.negative) return left.magnitude > right.magnitude ? -1 : 1;
	return left.magnitude < right.magnitude ? -1 : 1;
}

static uint32_t SignedRange(struct SignedValue minimum, struct SignedValue maximum)
{
	if (minimum.negative != maximum.negative)
		return UINT32_MAX - minimum.magnitude < maximum.magnitude
			? UINT32_MAX : minimum.magnitude + maximum.magnitude;
	return minimum.magnitude > maximum.magnitude
		? minimum.magnitude - maximum.magnitude
		: maximum.magnitude - minimum.magnitude;
}

static int32_t SaturatingDifference(int32_t left, int32_t right)
{
	if (right > 0 && left < IRONMON_INT32_MIN + right)
		return IRONMON_INT32_MIN;
	if (right < 0 && left > IRONMON_INT32_MAX + right)
		return IRONMON_INT32_MAX;
	return left - right;
}

static uint8_t BeatsByMargin(int32_t left, int32_t right, uint8_t margin)
{
	if (left < right || right > IRONMON_INT32_MAX - margin)
		return 0;
	return left >= right + margin;
}

static int32_t ScoreCandidate(const struct IronmonPolicyObservation* observation,
	const struct StandardPolicyMemory* memory, uint8_t index,
	struct IronmonPolicyDiagnostic* diagnostic)
{
	const struct IronmonPolicyCandidate* candidate = &observation->candidates[index];
	struct SignedMagnitude weighted = {0, {0, 0}};
	uint32_t totalWeight = 0;
	struct SignedValue minimum = {0, 0}, maximum = {0, 0};
	uint8_t haveRange = 0;
	uint8_t repeats = candidate->floor.pure_status
		? ConsecutiveSuccessfulFamily(memory, candidate->floor.effect_family) : 0;
	uint8_t repeatCost = 8 * (repeats > 3 ? 3 : repeats);
	uint8_t loopCost = AbaWithinThree(memory, candidate) ? IRONMON_SWITCH_LOOP_COST : 0;
	uint8_t i, uncertainty;
	uint32_t expectedMagnitude;
	int32_t result;

	for (i = 0; i < observation->response_count; ++i)
	{
		struct SignedValue branch = BranchValue(&candidate->responses[i], repeatCost, loopCost);
		AddSignedProduct(&weighted, branch, observation->responses[i].weight);
		totalWeight += observation->responses[i].weight;
		if (!haveRange || CompareSignedValue(branch, minimum) < 0) minimum = branch;
		if (!haveRange || CompareSignedValue(branch, maximum) > 0) maximum = branch;
		haveRange = 1;
	}
	expectedMagnitude = Divide64By32(weighted.magnitude, totalWeight);
	uncertainty = SignedRange(minimum, maximum) > 100
		? 25 : (uint8_t)(SignedRange(minimum, maximum) / 4);
	result = SubtractSmallAndSaturate(weighted.negative, expectedMagnitude, uncertainty);
	diagnostic->repeat_count = repeats;
	diagnostic->repeat_cost = repeatCost;
	diagnostic->loop_cost = loopCost;
	diagnostic->uncertainty_cost = uncertainty;
	diagnostic->expected_before_uncertainty = SaturateSigned(weighted.negative, expectedMagnitude);
	diagnostic->utility_total = result;
	return result;
}

static uint8_t Better(uint8_t left, uint8_t right, const int32_t scores[],
	const struct IronmonPolicyObservation* observation)
{
	return right == 0xFF || scores[left] > scores[right]
		|| (scores[left] == scores[right]
			&& observation->candidates[left].floor.id < observation->candidates[right].floor.id);
}

static uint8_t ChooseNearBest(const struct IronmonPolicyObservation* observation,
	const uint8_t pool[], const int32_t scores[], uint32_t* rng,
	struct IronmonPolicyResult* result)
{
	uint8_t ordered[IRONMON_POLICY_MAX_CANDIDATES], count = 0, i, j, selected;
	int32_t best = IRONMON_INT32_MIN;
	int32_t nearFloor;
	for (i = 0; i < observation->count; ++i)
		if (pool[i] && scores[i] > best) best = scores[i];
	nearFloor = best < IRONMON_INT32_MIN + IRONMON_POLICY_EPSILON
		? IRONMON_INT32_MIN : best - IRONMON_POLICY_EPSILON;
	for (i = 0; i < observation->count; ++i)
		if (pool[i] && scores[i] >= nearFloor) ordered[count++] = i;
	for (i = 0; i < count; ++i)
		for (j = i + 1; j < count; ++j)
			if (observation->candidates[ordered[j]].floor.id
				< observation->candidates[ordered[i]].floor.id)
			{
				uint8_t swap = ordered[i]; ordered[i] = ordered[j]; ordered[j] = swap;
			}
	if (count == 1) selected = ordered[0];
	else
	{
		uint8_t before = result->total_draws;
		selected = ordered[StandardPolicyBounded(rng, count, &result->total_draws)];
		result->selection_draws = result->total_draws - before;
	}
	result->best_score = best;
	result->near_best_count = count;
	for (i = 0; i < count; ++i)
	{
		result->near_best_pool |= (uint16_t)1 << ordered[i];
		result->diagnostics[ordered[i]].near_best = 1;
	}
	return selected;
}

int IronmonPolicyBuildResponses(const uint16_t moves[4],
	const uint16_t counts[4], uint8_t unknown_slots,
	struct IronmonPolicyResponse out[5],
	uint8_t* out_count)
{
	uint8_t order[4], known = 0, i, j;
	uint32_t total = 0;
	if (moves == 0 || counts == 0 || out == 0 || out_count == 0
		|| unknown_slots > 4)
		return IRONMON_ERROR;
	for (i = 0; i < 4; ++i)
		if (moves[i] != 0)
		{
			for (j = 0; j < known; ++j)
				if (moves[order[j]] == moves[i]) return IRONMON_INVALID_CANDIDATE;
			order[known++] = i;
		}
	for (i = 0; i < known; ++i)
		for (j = i + 1; j < known; ++j)
			if (moves[order[j]] < moves[order[i]])
			{ uint8_t swap = order[i]; order[i] = order[j]; order[j] = swap; }
	if (!known)
	{
		out[0].id = IRONMON_POLICY_UNKNOWN_RESPONSE;
		out[0].weight = 1;
		*out_count = 1;
		return 0;
	}
	for (i = 0; i < known; ++i) total += (uint32_t)counts[order[i]] + 1;
	for (i = 0; i < known; ++i)
	{
		out[i].id = moves[order[i]];
		out[i].weight = ((uint32_t)counts[order[i]] + 1) * (unknown_slots ? 3 : 1);
	}
	if (unknown_slots)
	{
		out[known].id = IRONMON_POLICY_UNKNOWN_RESPONSE;
		out[known].weight = total;
		++known;
	}
	*out_count = known;
	return 0;
}

int IronmonPolicyChoose(const struct IronmonPolicyObservation* observation,
	const struct StandardPolicyMemory* memory, uint32_t* policy_rng_state,
	struct IronmonPolicyResult* result)
{
	uint8_t floorEligible[IRONMON_POLICY_MAX_CANDIDATES] = {0};
	uint8_t admitted[IRONMON_POLICY_MAX_CANDIDATES] = {0};
	uint8_t repeatVisited[IRONMON_POLICY_MAX_CANDIDATES] = {0};
	uint8_t pool[IRONMON_POLICY_MAX_CANDIDATES] = {0};
	uint8_t thresholdEligible[IRONMON_POLICY_MAX_CANDIDATES] = {0};
	int32_t scores[IRONMON_POLICY_MAX_CANDIDATES] = {0};
	uint8_t i, j, legal = 0, forced = 0, safe = 0, kos = 0;
	uint8_t consecutiveSwitches, bestStay = 0xFF, bestSwitch = 0xFF;
	uint8_t eligibleEmergency = 0, voluntary = 0, selected;
	int32_t advantage = 0;

	if (policy_rng_state == 0 || result == 0 || !ValidateObservation(observation, memory))
		return IRONMON_ERROR;
	*result = (struct IronmonPolicyResult){0};
	result->best_stay_id = result->best_switch_id = 0xFF;
	result->selected_switch_advantage = IRONMON_INT32_MIN;
	for (i = 0; i < observation->count; ++i)
	{
		struct IronmonPolicyDiagnostic* d = &result->diagnostics[i];
		d->id = observation->candidates[i].floor.id;
		d->switch_advantage = IRONMON_INT32_MIN;
		scores[i] = ScoreCandidate(observation, memory, i, d);
		if (observation->candidates[i].floor.legal)
		{
			++legal;
			if (observation->candidates[i].floor.forced) ++forced;
		}
	}
	if (!legal) return IRONMON_NO_ADMITTED_ACTION;
	if (forced)
	{
		for (i = 0; i < observation->count; ++i)
			if (observation->candidates[i].floor.legal
				&& observation->candidates[i].floor.forced)
				floorEligible[i] = 1;
			else result->diagnostics[i].reasons = observation->candidates[i].floor.legal
				? STANDARD_FLOOR_FORCED_PRESENT : STANDARD_FLOOR_ILLEGAL;
	}
	else
	{
		for (i = 0; i < observation->count; ++i)
		{
			uint32_t reasons = FloorReasons(&observation->candidates[i], memory);
			result->diagnostics[i].reasons = reasons;
			if (!reasons)
			{
				floorEligible[i] = 1; ++safe;
				if (observation->candidates[i].floor.robust_safe_ko) ++kos;
			}
		}
		if (!safe)
		{
			uint8_t fallback = 0xFF;
			for (i = 0; i < observation->count; ++i)
				if (observation->candidates[i].floor.legal
					&& (fallback == 0xFF
						|| observation->candidates[i].floor.fallback_cost
						< observation->candidates[fallback].floor.fallback_cost
						|| (observation->candidates[i].floor.fallback_cost
							== observation->candidates[fallback].floor.fallback_cost
							&& observation->candidates[i].floor.id
							< observation->candidates[fallback].floor.id))) fallback = i;
			floorEligible[fallback] = 1;
			result->diagnostics[fallback].reasons = 0;
		}
		else if (kos)
			for (i = 0; i < observation->count; ++i)
				if (floorEligible[i] && !observation->candidates[i].floor.robust_safe_ko)
				{
					floorEligible[i] = 0;
					result->diagnostics[i].reasons = STANDARD_FLOOR_ROBUST_KO_DOMINATES;
				}
	}
	for (i = 0; i < observation->count; ++i) admitted[i] = floorEligible[i];
	/* Repeat exception proof is deliberately evaluated in stable ID order. */
	for (j = 0; j < observation->count; ++j)
	{
		uint8_t index = 0xFF, alternative = 0xFF;
		for (i = 0; i < observation->count; ++i)
			if (admitted[i] && !repeatVisited[i] && (index == 0xFF
				|| observation->candidates[i].floor.id < observation->candidates[index].floor.id))
				index = i;
		if (index == 0xFF) break;
		repeatVisited[index] = 1;
		if (result->diagnostics[index].repeat_count < 2
			|| !observation->candidates[index].floor.pure_status) continue;
		for (i = 0; i < observation->count; ++i)
			if (i != index && admitted[i] && observation->candidates[i].floor.productive
				&& StandardPolicyNormalizeEffectFamily(observation->candidates[i].floor.effect_family)
				!= StandardPolicyNormalizeEffectFamily(observation->candidates[index].floor.effect_family)
				&& Better(i, alternative, scores, observation)) alternative = i;
		if (!observation->candidates[index].floor.positive_marginal_exception
			|| observation->candidates[index].repeat_exception_reason == IRONMON_REPEAT_NONE
			|| alternative == 0xFF || !BeatsByMargin(scores[index], scores[alternative],
				IRONMON_REPEAT_EXCEPTION_MARGIN))
		{
			admitted[index] = 0;
			result->diagnostics[index].reasons |= IRONMON_REASON_REPEAT_EXCEPTION_REJECTED;
		}
		else result->diagnostics[index].repeat_exception_admitted = 1;
	}
	consecutiveSwitches = ConsecutiveVoluntarySwitches(memory);
	for (i = 0; i < observation->count; ++i)
	{
		const struct IronmonPolicyCandidate* c = &observation->candidates[i];
		uint8_t progress;
		if (!admitted[i] || c->floor.kind != STANDARD_POLICY_SWITCH || c->floor.forced) continue;
		progress = c->progress_after_loop_cost >= IRONMON_PROGRESS_EXCEPTION_MIN
			&& !c->regenerator_only;
		if (AbaWithinThree(memory, c) && !c->public_threat_changed && !progress)
		{
			admitted[i] = 0; result->diagnostics[i].reasons |= IRONMON_REASON_ABA_LOOP_GUARD;
		}
		else if (consecutiveSwitches >= 2 && !c->ironmon_switch_emergency && !progress)
		{
			admitted[i] = 0; result->diagnostics[i].reasons |= IRONMON_REASON_CONSECUTIVE_SWITCH_GUARD;
		}
	}
	for (i = 0; i < observation->count; ++i)
		if (admitted[i] && observation->candidates[i].floor.kind != STANDARD_POLICY_SWITCH
			&& observation->candidates[i].stay_defensible && Better(i, bestStay, scores, observation))
			bestStay = i;
	if (bestStay != 0xFF)
	{
		result->best_stay_id = observation->candidates[bestStay].floor.id;
		result->best_stay_score = scores[bestStay];
		for (i = 0; i < observation->count; ++i)
			if (observation->candidates[i].floor.kind == STANDARD_POLICY_SWITCH)
				result->diagnostics[i].switch_advantage = SaturatingDifference(scores[i], scores[bestStay]);
	}
	for (i = 0; i < observation->count; ++i)
	{
		const struct IronmonPolicyCandidate* c = &observation->candidates[i];
		int32_t candidateAdvantage;
		if (!admitted[i] || c->floor.kind != STANDARD_POLICY_SWITCH) continue;
		if (c->floor.forced)
		{
			thresholdEligible[i] = 1;
			continue;
		}
		if (!c->ironmon_switch_emergency) ++voluntary;
		candidateAdvantage = bestStay == 0xFF ? IRONMON_INT32_MAX
			: SaturatingDifference(scores[i], scores[bestStay]);
		if (c->ironmon_switch_emergency)
		{
			if (bestStay == 0xFF || candidateAdvantage > 0)
			{ thresholdEligible[i] = 1; ++eligibleEmergency; }
		}
		else if (bestStay != 0xFF && candidateAdvantage >= IRONMON_SWITCH_RANDOM_MIN)
			thresholdEligible[i] = 1;
	}
	/* Match host best-switch reporting and class decision. */
	for (i = 0; i < observation->count; ++i)
		if (thresholdEligible[i] && observation->candidates[i].ironmon_switch_emergency
			&& Better(i, bestSwitch, scores, observation)) bestSwitch = i;
	if (bestSwitch == 0xFF)
		for (i = 0; i < observation->count; ++i)
			if (admitted[i] && observation->candidates[i].floor.kind == STANDARD_POLICY_SWITCH
				&& !observation->candidates[i].floor.forced
				&& !observation->candidates[i].ironmon_switch_emergency
				&& Better(i, bestSwitch, scores, observation)) bestSwitch = i;
	if (bestSwitch == 0xFF)
		for (i = 0; i < observation->count; ++i)
			if (admitted[i] && observation->candidates[i].ironmon_switch_emergency
				&& Better(i, bestSwitch, scores, observation)) bestSwitch = i;
	if (bestSwitch != 0xFF)
	{
		result->best_switch_id = observation->candidates[bestSwitch].floor.id;
		result->best_switch_score = scores[bestSwitch];
		if (bestStay != 0xFF)
			advantage = SaturatingDifference(scores[bestSwitch], scores[bestStay]);
		result->switch_advantage = advantage;
	}
	result->admission_rng_pre = *policy_rng_state ? *policy_rng_state : 0x6D2B79F5;
	for (i = 0; i < observation->count; ++i)
		if (admitted[i] && observation->candidates[i].floor.forced) pool[i] = 1;
	if (forced)
	{
		result->threshold_class = IRONMON_THRESHOLD_FORCED_REPLACEMENT;
		result->admitted_class = IRONMON_ADMITTED_FORCED_REPLACEMENT;
		result->admission_result = 1;
	}
	else if (eligibleEmergency)
	{
		for (i = 0; i < observation->count; ++i)
			pool[i] = thresholdEligible[i] && observation->candidates[i].ironmon_switch_emergency;
		result->threshold_class = IRONMON_THRESHOLD_EMERGENCY;
		result->admitted_class = IRONMON_ADMITTED_EMERGENCY_SWITCH;
		result->admission_result = 1;
	}
	else if (!voluntary)
	{
		for (i = 0; i < observation->count; ++i)
			pool[i] = admitted[i] && observation->candidates[i].floor.kind != STANDARD_POLICY_SWITCH;
		result->threshold_class = IRONMON_THRESHOLD_NO_ELIGIBLE_SWITCH;
		result->admitted_class = IRONMON_ADMITTED_STAY;
	}
	else if (bestStay == 0xFF)
		return IRONMON_NO_ADMITTED_ACTION;
	else if (advantage < IRONMON_SWITCH_RANDOM_MIN)
	{
		for (i = 0; i < observation->count; ++i)
			pool[i] = admitted[i] && observation->candidates[i].floor.kind != STANDARD_POLICY_SWITCH
				&& observation->candidates[i].stay_defensible;
		result->threshold_class = IRONMON_THRESHOLD_BELOW_12;
		result->admitted_class = IRONMON_ADMITTED_STAY;
	}
	else if (advantage <= IRONMON_SWITCH_RANDOM_MAX)
	{
		result->threshold_class = IRONMON_THRESHOLD_RANDOM_12_19;
		result->admission_result = (uint8_t)StandardPolicyBounded(policy_rng_state, 2, &result->total_draws);
		result->admission_draws = result->total_draws;
		result->admitted_class = result->admission_result
			? IRONMON_ADMITTED_VOLUNTARY_SWITCH : IRONMON_ADMITTED_STAY;
		for (i = 0; i < observation->count; ++i)
			pool[i] = result->admission_result
				? thresholdEligible[i] && !observation->candidates[i].ironmon_switch_emergency
				: admitted[i] && observation->candidates[i].floor.kind != STANDARD_POLICY_SWITCH
					&& observation->candidates[i].stay_defensible;
	}
	else if (advantage >= IRONMON_SWITCH_DETERMINISTIC_MIN)
	{
		for (i = 0; i < observation->count; ++i)
			pool[i] = thresholdEligible[i] && !observation->candidates[i].ironmon_switch_emergency;
		result->threshold_class = IRONMON_THRESHOLD_AT_LEAST_20;
		result->admitted_class = IRONMON_ADMITTED_VOLUNTARY_SWITCH;
		result->admission_result = 1;
	}
	result->admission_rng_post = *policy_rng_state ? *policy_rng_state : 0x6D2B79F5;
	for (i = 0; i < observation->count; ++i)
	{
		result->diagnostics[i].switch_threshold_eligible = thresholdEligible[i];
		result->diagnostics[i].ironmon_eligible = pool[i];
		if (pool[i]) result->admitted_pool |= (uint16_t)1 << i;
	}
	if (!result->admitted_pool) return IRONMON_NO_ADMITTED_ACTION;
	selected = ChooseNearBest(observation, pool, scores, policy_rng_state, result);
	result->selected_id = observation->candidates[selected].floor.id;
	result->diagnostics[selected].selected = 1;
	if (observation->candidates[selected].floor.kind == STANDARD_POLICY_SWITCH
		&& bestStay != 0xFF)
		result->selected_switch_advantage = SaturatingDifference(scores[selected], scores[bestStay]);
	result->rng_post = *policy_rng_state ? *policy_rng_state : 0x6D2B79F5;
	return 0;
}
