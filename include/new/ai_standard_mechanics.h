#pragma once
#include "ai_standard_policy.h"

/* Values, never pointers into battle/party state. Unknown flags default to 0. */
struct StandardMechanicsInput
{
	uint16_t power, attack, base_defense, base_hp;
	uint8_t level, target_level, attack_stage, defense_stage;
	uint8_t hp_pixels; /* floor(48 * HP/max HP), at least 1 if alive; 255 = unknown */
	uint8_t accuracy, accuracy_stage, evasion_stage, stab;
	uint8_t effectiveness[3]; /* CFRU factors /10; duplicates already removed */
	uint8_t supported_damage, known_immunity, certified_modifiers;
	uint8_t can_act_safely, own_burn, shedinja;
	/* Nonzero ONLY for an own-trainer target in the public threat model. */
	uint16_t known_defense, known_max_hp, known_hp;
	/* Apply the possible player Badge Defense/SpDef modifier after the full
	 * base+IV/EV+nature bound is built, before stat stages. */
	uint8_t possible_defense_badge;
};

struct StandardDamageEnvelope
{
	uint16_t minimum, estimate, maximum;
	uint16_t hp_minimum, hp_maximum, max_hp_minimum, max_hp_maximum;
	uint8_t possible_ko, uncertain;
};

/* Same implementation used by the production projection and host harness. */
void StandardMechanicsDamage(const struct StandardMechanicsInput* input,
	struct StandardPolicyCandidate* candidate, struct StandardDamageEnvelope* envelope);
void StandardMechanicsAccuracy(struct StandardPolicyCandidate* candidate);
/* Public stat interval, all legal IV/EV/nature values. */
uint32_t StandardMechanicsSpeed(uint16_t base, uint8_t level, uint8_t stage, uint8_t high);
uint32_t StandardMechanicsStage(uint32_t value, uint8_t stage);
uint32_t StandardMechanicsDefenseMaximum(const struct StandardMechanicsInput* input);
void StandardMechanicsQualifySwitches(struct StandardPolicyObservation* observation);
