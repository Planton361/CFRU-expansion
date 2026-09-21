#pragma once

/*
 * The Standard policy is deliberately a freestanding C module.  This header
 * contains only fixed-width integer types and bounded value objects; it must
 * not pull in battle globals, battle structs, or engine helpers.
 */
#include <stdint.h>

#define STANDARD_POLICY_MAX_CANDIDATES 9
#define STANDARD_POLICY_MEMORY_LIMIT 4
#define STANDARD_POLICY_EPSILON 8
#define STANDARD_POLICY_HP_SCALE 256

enum StandardPolicyActionKind
{
	STANDARD_POLICY_MOVE = 0,
	STANDARD_POLICY_SWITCH = 1,
};

/* Effect-family identifiers are adapter-owned facts, not move identifiers. */
enum StandardPolicyEffectFamily
{
	STANDARD_EFFECT_NONE = 0,
	STANDARD_EFFECT_ACCURACY_DOWN = 1,
	STANDARD_EFFECT_SPEED_DOWN = 2,
	STANDARD_EFFECT_ATTACK_UP = 3,
	STANDARD_EFFECT_DEFENSE_UP = 4,
	STANDARD_EFFECT_SPEED_UP = 5,
	STANDARD_EFFECT_SPECIAL_ATTACK_UP = 6,
	STANDARD_EFFECT_SPECIAL_DEFENSE_UP = 7,
	STANDARD_EFFECT_ACCURACY_UP = 8,
	STANDARD_EFFECT_ATTACK_DOWN = 9,
	STANDARD_EFFECT_DEFENSE_DOWN = 10,
	STANDARD_EFFECT_SPECIAL_ATTACK_DOWN = 11,
	STANDARD_EFFECT_SPECIAL_DEFENSE_DOWN = 12,
	STANDARD_EFFECT_EVASION_UP = 13,
	STANDARD_EFFECT_EVASION_DOWN = 14,
	STANDARD_EFFECT_SAND_ATTACK = 15,
	STANDARD_EFFECT_SMOKESCREEN = 16,
	STANDARD_EFFECT_STRING_SHOT = 17,
	STANDARD_EFFECT_EQUIVALENT_SPEED_DOWN = 18,
};

/* Reasons are bitmasks so host tests can compare diagnostics without strings. */
enum StandardPolicyFloorReason
{
	STANDARD_FLOOR_ILLEGAL = 1 << 0,
	STANDARD_FLOOR_ILLEGAL_SWITCH = 1 << 1,
	STANDARD_FLOOR_ENTRY_KO = 1 << 2,
	STANDARD_FLOOR_KNOWN_NO_EFFECT = 1 << 3,
	STANDARD_FLOOR_REDUNDANT_STATUS = 1 << 4,
	STANDARD_FLOOR_CAPPED_STAT_CHANGE = 1 << 5,
	STANDARD_FLOOR_HARMFUL_REPEAT = 1 << 6,
	STANDARD_FLOOR_NO_MARGINAL_VALUE = 1 << 7,
	STANDARD_FLOOR_FORCED_PRESENT = 1 << 8,
	STANDARD_FLOOR_ROBUST_KO_DOMINATES = 1 << 9,
};

enum StandardPolicyAdmissionReason
{
	STANDARD_ADMISSION_STAY = 1 << 0,
	STANDARD_ADMISSION_FORCED_REPLACEMENT = 1 << 1,
	STANDARD_ADMISSION_NON_EMERGENCY_SWITCH = 1 << 2,
	STANDARD_ADMISSION_SWITCH_LOOP = 1 << 3,
	STANDARD_ADMISSION_EMERGENCY_SWITCH = 1 << 4,
};

struct StandardPolicyCandidate
{
	uint8_t id;
	uint8_t kind;
	uint8_t legal;
	uint8_t productive;
	uint8_t known_no_effect;
	uint8_t pure_status;
	uint8_t public_major_status;
	uint8_t robust_safe_ko;
	uint8_t redundant_status;
	int8_t stat_stage_before;
	int8_t stat_stage_after;
	uint8_t effect_family;
	uint8_t positive_marginal_exception;
	uint16_t expected_damage;
	uint8_t switch_legal;
	uint8_t entry_survives;
	uint8_t forced;
	int32_t fallback_cost;
	uint8_t accuracy;
	int8_t priority;
	uint8_t survival_to_act;
	uint8_t switch_from;
	uint8_t switch_to;
	int8_t net_faints;
	int16_t opponent_hp_fraction_lost;
	int16_t own_hp_fraction_lost;
	int16_t immediate_future_gain;
	int32_t entry_cost;
	int32_t repeat_cost;
	int32_t uncertainty_cost;
	uint8_t standard_switch_emergency;
};

struct StandardPolicyObservation
{
	uint8_t count;
	struct StandardPolicyCandidate candidates[STANDARD_POLICY_MAX_CANDIDATES];
};

struct StandardPolicyMemoryDecision
{
	uint8_t kind;
	uint8_t effect_family;
	uint8_t success;
	uint8_t forced;
	uint8_t switch_from;
	uint8_t switch_to;
	int8_t public_stage_before;
	int8_t public_stage_after;
};

struct StandardPolicyMemory
{
	uint8_t count;
	struct StandardPolicyMemoryDecision decisions[STANDARD_POLICY_MEMORY_LIMIT];
};

struct StandardPolicyDiagnostic
{
	uint8_t id;
	uint8_t standard_eligible;
	uint8_t near_best;
	uint8_t selected;
	uint16_t floor_reasons;
	uint16_t admission_reasons;
	int32_t utility_total;
	int32_t hp_delta_term;
	int32_t net_faints_term;
};

struct StandardPolicyResult
{
	uint8_t selected_id;
	int32_t best_score;
	uint8_t near_best_count;
	uint8_t policy_rng_draws;
	uint8_t no_productive_fallback;
	struct StandardPolicyDiagnostic diagnostics[STANDARD_POLICY_MAX_CANDIDATES];
};

uint8_t StandardPolicyNormalizeEffectFamily(uint8_t family);
void StandardPolicyResetMemory(struct StandardPolicyMemory* memory);
void StandardPolicyRecordMemory(struct StandardPolicyMemory* memory,
	const struct StandardPolicyMemoryDecision* decision);
uint32_t StandardPolicyNextU32(uint32_t* state);
uint32_t StandardPolicyBounded(uint32_t* state, uint32_t upper, uint8_t* draws);
int StandardPolicyChoose(const struct StandardPolicyObservation* observation,
	const struct StandardPolicyMemory* memory, uint32_t* policy_rng_state,
	struct StandardPolicyResult* result);
