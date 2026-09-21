#pragma once

/*
 * Freestanding Ironmon Smart v1 policy.  These bounded value objects are the
 * complete policy boundary: this header intentionally has no CFRU battle
 * declarations and the implementation reads no battle globals.
 */
#include <stdint.h>

#include "ai_standard_policy.h"

#define IRONMON_POLICY_MAX_CANDIDATES 9
#define IRONMON_POLICY_MAX_RESPONSES 8
#define IRONMON_POLICY_EPSILON 4
#define IRONMON_POLICY_UNKNOWN_RESPONSE 0xFFFF
#define IRONMON_POLICY_MAX_RESPONSE_WEIGHT 1048576u

enum IronmonPolicyRepeatReason
{
	IRONMON_REPEAT_NONE = 0,
	IRONMON_REPEAT_ORDER_THRESHOLD,
	IRONMON_REPEAT_KO_OR_2HKO_THRESHOLD,
	IRONMON_REPEAT_SURVIVAL_THRESHOLD,
	IRONMON_REPEAT_NET_POSITIVE_RECOVERY,
	IRONMON_REPEAT_RESIDUAL_WIN_LINE,
};

enum IronmonPolicyTacticalClass
{
	IRONMON_TACTICAL_DAMAGE = 0,
	IRONMON_TACTICAL_TWO_HKO,
	IRONMON_TACTICAL_SPEED_PLAN,
	IRONMON_TACTICAL_SETUP_PLAN,
	IRONMON_TACTICAL_RESIDUAL,
	IRONMON_TACTICAL_RECOVERY,
	IRONMON_TACTICAL_FIELD,
	IRONMON_TACTICAL_PROTECT,
	IRONMON_TACTICAL_PIVOT,
	IRONMON_TACTICAL_SWITCH,
	IRONMON_TACTICAL_FORCED_REPLACEMENT,
	IRONMON_TACTICAL_FALLBACK,
	IRONMON_TACTICAL_UNSUPPORTED,
};

enum IronmonPolicyThresholdClass
{
	IRONMON_THRESHOLD_FORCED_REPLACEMENT = 0,
	IRONMON_THRESHOLD_EMERGENCY,
	IRONMON_THRESHOLD_NO_ELIGIBLE_SWITCH,
	IRONMON_THRESHOLD_BELOW_12,
	IRONMON_THRESHOLD_RANDOM_12_19,
	IRONMON_THRESHOLD_AT_LEAST_20,
};

enum IronmonPolicyAdmittedClass
{
	IRONMON_ADMITTED_STAY = 0,
	IRONMON_ADMITTED_FORCED_REPLACEMENT,
	IRONMON_ADMITTED_EMERGENCY_SWITCH,
	IRONMON_ADMITTED_VOLUNTARY_SWITCH,
};

enum IronmonPolicyReason
{
	IRONMON_REASON_REPEAT_EXCEPTION_REJECTED = 1u << 16,
	IRONMON_REASON_ABA_LOOP_GUARD = 1u << 17,
	IRONMON_REASON_CONSECUTIVE_SWITCH_GUARD = 1u << 18,
};

struct IronmonPolicyResponse
{
	uint16_t id;
	uint32_t weight;
};

struct IronmonPolicyBranch
{
	uint16_t response_id;
	int8_t net_faints;
	int16_t opponent_hp_fraction_lost;
	int16_t own_hp_fraction_lost;
	int16_t future_gain_undiscounted;
	int32_t entry_cost;
};

struct IronmonPolicyCandidate
{
	struct StandardPolicyCandidate floor;
	uint8_t tactical_class;
	uint8_t ironmon_switch_emergency;
	uint8_t stay_defensible;
	uint8_t repeat_exception_reason;
	uint8_t public_threat_changed;
	uint8_t regenerator_only;
	int32_t progress_after_loop_cost;
	uint8_t response_count;
	struct IronmonPolicyBranch responses[IRONMON_POLICY_MAX_RESPONSES];
};

struct IronmonPolicyObservation
{
	uint8_t response_count;
	struct IronmonPolicyResponse responses[IRONMON_POLICY_MAX_RESPONSES];
	uint8_t count;
	struct IronmonPolicyCandidate candidates[IRONMON_POLICY_MAX_CANDIDATES];
};

struct IronmonPolicyDiagnostic
{
	uint8_t id;
	uint8_t ironmon_eligible;
	uint8_t switch_threshold_eligible;
	uint8_t near_best;
	uint8_t selected;
	uint8_t repeat_count;
	uint8_t repeat_cost;
	uint8_t loop_cost;
	uint8_t uncertainty_cost;
	uint8_t repeat_exception_admitted;
	uint32_t reasons;
	int32_t utility_total;
	int32_t expected_before_uncertainty;
	int32_t switch_advantage;
};

struct IronmonPolicyResult
{
	uint8_t selected_id;
	int32_t best_score;
	uint8_t near_best_count;
	uint8_t admission_draws;
	uint8_t selection_draws;
	uint8_t total_draws;
	uint8_t threshold_class;
	uint8_t admitted_class;
	uint8_t admission_result;
	uint16_t admitted_pool;
	uint16_t near_best_pool;
	uint32_t admission_rng_pre;
	uint32_t admission_rng_post;
	uint32_t rng_post;
	uint8_t best_stay_id;
	uint8_t best_switch_id;
	int32_t best_stay_score;
	int32_t best_switch_score;
	int32_t switch_advantage;
	int32_t selected_switch_advantage;
	struct IronmonPolicyDiagnostic diagnostics[IRONMON_POLICY_MAX_CANDIDATES];
};

/* Build the exact 75% known / 25% aggregate UNKNOWN response distribution.
 * MOVE_NONE is represented by zero and public counts are uint16-saturating. */
int IronmonPolicyBuildResponses(const uint16_t moves[4],
	const uint16_t counts[4], uint8_t unknown_slots,
	struct IronmonPolicyResponse out[5],
	uint8_t* out_count);

int IronmonPolicyChoose(const struct IronmonPolicyObservation* observation,
	const struct StandardPolicyMemory* memory, uint32_t* policy_rng_state,
	struct IronmonPolicyResult* result);
