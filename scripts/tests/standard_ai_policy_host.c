#include <assert.h>
#include <stdint.h>
#include <string.h>

#include "../../include/new/ai_standard_policy.h"

static struct StandardPolicyCandidate Move(uint8_t id)
{
	struct StandardPolicyCandidate candidate;

	memset(&candidate, 0, sizeof(candidate));
	candidate.id = id;
	candidate.kind = STANDARD_POLICY_MOVE;
	candidate.legal = 1;
	candidate.productive = 1;
	candidate.entry_survives = 1;
	candidate.fallback_cost = 100;
	return candidate;
}

static struct StandardPolicyCandidate Switch(uint8_t id, uint8_t from, uint8_t to)
{
	struct StandardPolicyCandidate candidate = Move(id);

	candidate.kind = STANDARD_POLICY_SWITCH;
	candidate.switch_legal = 1;
	candidate.switch_from = from;
	candidate.switch_to = to;
	candidate.standard_switch_emergency = 1;
	candidate.entry_cost = 16;
	return candidate;
}

static void Choose(struct StandardPolicyObservation* observation,
	struct StandardPolicyMemory* memory, uint32_t seed,
	struct StandardPolicyResult* result)
{
	int rc;

	memset(result, 0, sizeof(*result));
	rc = StandardPolicyChoose(observation, memory, &seed, result);
	assert(rc == 0);
}

static void TestKoDominanceAndUtility(void)
{
	struct StandardPolicyObservation observation = {0};
	struct StandardPolicyMemory memory;
	struct StandardPolicyResult result;

	StandardPolicyResetMemory(&memory);
	observation.count = 2;
	observation.candidates[0] = Move(0);
	observation.candidates[0].robust_safe_ko = 1;
	observation.candidates[0].net_faints = 1;
	observation.candidates[1] = Move(1);
	observation.candidates[1].immediate_future_gain = 40;
	Choose(&observation, &memory, 0x12345678, &result);
	assert(result.selected_id == 0);
	assert(result.diagnostics[1].floor_reasons == STANDARD_FLOOR_ROBUST_KO_DOMINATES);

	observation.count = 1;
	observation.candidates[0] = Move(0);
	observation.candidates[0].opponent_hp_fraction_lost = 128;
	observation.candidates[0].own_hp_fraction_lost = 64;
	observation.candidates[0].immediate_future_gain = 10;
	observation.candidates[0].entry_cost = 2;
	observation.candidates[0].repeat_cost = 3;
	observation.candidates[0].uncertainty_cost = 4;
	Choose(&observation, &memory, 0x12345678, &result);
	assert(result.best_score == 26); /* 25 + 10 - 2 - 3 - 4 */
}

static void TestEpsilonAndRng(void)
{
	struct StandardPolicyObservation observation = {0};
	struct StandardPolicyMemory memory;
	struct StandardPolicyResult one;
	struct StandardPolicyResult two;
	uint32_t seedOne = 0xA5A5A5A5;
	uint32_t seedTwo = seedOne;

	StandardPolicyResetMemory(&memory);
	observation.count = 3;
	observation.candidates[0] = Move(0);
	observation.candidates[0].immediate_future_gain = 30;
	observation.candidates[1] = Move(1);
	observation.candidates[1].immediate_future_gain = 22; /* exactly inside epsilon */
	observation.candidates[2] = Move(2);
	observation.candidates[2].immediate_future_gain = 21; /* outside epsilon */

	assert(StandardPolicyChoose(&observation, &memory, &seedOne, &one) == 0);
	assert(StandardPolicyChoose(&observation, &memory, &seedTwo, &two) == 0);
	assert(one.near_best_count == 2);
	assert(one.policy_rng_draws == 1);
	assert(one.selected_id == two.selected_id);
	assert(seedOne == seedTwo);

	observation.count = 1;
	observation.candidates[0] = Move(0);
	seedOne = 0xA5A5A5A5;
	assert(StandardPolicyChoose(&observation, &memory, &seedOne, &one) == 0);
	assert(one.policy_rng_draws == 0);
	assert(seedOne == 0xA5A5A5A5);
}

static void TestSaturationAndFloorWitnesses(void)
{
	struct StandardPolicyObservation observation = {0};
	struct StandardPolicyMemory memory;
	struct StandardPolicyMemoryDecision decision;
	struct StandardPolicyResult result;

	StandardPolicyResetMemory(&memory);
	observation.count = 2;
	observation.candidates[0] = Move(0);
	observation.candidates[0].immediate_future_gain = 40;
	observation.candidates[0].entry_cost = 0;
	observation.candidates[1] = Move(1);
	observation.candidates[1].productive = 0;
	observation.candidates[1].fallback_cost = 1;
	Choose(&observation, &memory, 0xCAFEBABE, &result);
	assert(result.selected_id == 0);

	observation.count = 1;
	observation.candidates[0] = Move(0);
	observation.candidates[0].net_faints = 1;
	observation.candidates[0].entry_cost = 0;
	observation.candidates[0].repeat_cost = 0;
	observation.candidates[0].uncertainty_cost = 0;
	Choose(&observation, &memory, 0xCAFEBABE, &result);
	assert(result.best_score == 200);

	observation.count = 2;
	observation.candidates[0] = Move(0);
	observation.candidates[0].legal = 0;
	observation.candidates[1] = Move(1);
	observation.candidates[1].productive = 0;
	observation.candidates[1].fallback_cost = 7;
	Choose(&observation, &memory, 0xCAFEBABE, &result);
	assert(result.no_productive_fallback == 1);
	assert(result.selected_id == 1);

	observation.count = 1;
	observation.candidates[0] = Move(0);
	observation.candidates[0].net_faints = 1;
	observation.candidates[0].opponent_hp_fraction_lost = 256;
	observation.candidates[0].own_hp_fraction_lost = -256;
	observation.candidates[0].immediate_future_gain = 40;
	observation.candidates[0].entry_cost = 0;
	observation.candidates[0].repeat_cost = 0;
	observation.candidates[0].uncertainty_cost = 0;
	Choose(&observation, &memory, 0xCAFEBABE, &result);
	assert(result.best_score == 440);

	observation.candidates[0].net_faints = -1;
	observation.candidates[0].opponent_hp_fraction_lost = 0;
	observation.candidates[0].own_hp_fraction_lost = 256;
	observation.candidates[0].immediate_future_gain = -40;
	observation.candidates[0].entry_cost = 2147483647;
	observation.candidates[0].repeat_cost = 2147483647;
	observation.candidates[0].uncertainty_cost = 2147483647;
	Choose(&observation, &memory, 0xCAFEBABE, &result);
	assert(result.best_score == (-2147483647 - 1));

	memset(&decision, 0, sizeof(decision));
	decision.kind = STANDARD_POLICY_MOVE;
	decision.effect_family = STANDARD_EFFECT_SAND_ATTACK;
	decision.success = 1;
	StandardPolicyRecordMemory(&memory, &decision);
	decision.effect_family = STANDARD_EFFECT_SMOKESCREEN;
	StandardPolicyRecordMemory(&memory, &decision);
	observation.count = 2;
	observation.candidates[0] = Move(0);
	observation.candidates[0].pure_status = 1;
	observation.candidates[0].effect_family = STANDARD_EFFECT_ACCURACY_DOWN;
	observation.candidates[0].positive_marginal_exception = 0;
	observation.candidates[1] = Move(1);
	observation.candidates[1].expected_damage = 30;
	Choose(&observation, &memory, 0xCAFEBABE, &result);
	assert(result.selected_id == 1);
	assert(result.diagnostics[0].floor_reasons & STANDARD_FLOOR_HARMFUL_REPEAT);
}

static void TestSwitchMemoryAndForcedReplacement(void)
{
	struct StandardPolicyObservation observation = {0};
	struct StandardPolicyMemory memory;
	struct StandardPolicyMemoryDecision decision;
	struct StandardPolicyResult result;

	StandardPolicyResetMemory(&memory);
	memset(&decision, 0, sizeof(decision));
	decision.kind = STANDARD_POLICY_SWITCH;
	decision.switch_from = 0;
	decision.switch_to = 1;
	decision.success = 1;
	StandardPolicyRecordMemory(&memory, &decision);

	observation.count = 2;
	observation.candidates[0] = Switch(0, 1, 0);
	observation.candidates[0].productive = 1;
	observation.candidates[1] = Move(2);
	observation.candidates[1].immediate_future_gain = 10;
	Choose(&observation, &memory, 0x10203040, &result);
	assert(result.selected_id == 2);
	assert(result.diagnostics[0].admission_reasons == STANDARD_ADMISSION_SWITCH_LOOP);

	observation.count = 2;
	observation.candidates[0] = Switch(0, 1, 0);
	observation.candidates[0].forced = 1;
	observation.candidates[1] = Move(2);
	observation.candidates[1].productive = 1;
	Choose(&observation, &memory, 0x10203040, &result);
	assert(result.selected_id == 0);
	assert(result.diagnostics[0].admission_reasons == STANDARD_ADMISSION_FORCED_REPLACEMENT);
	assert(result.diagnostics[1].floor_reasons == STANDARD_FLOOR_FORCED_PRESENT);
}

static void TestMechanicsWitnesses(void)
{
	struct StandardPolicyObservation observation = {0};
	struct StandardPolicyMemory memory;
	struct StandardPolicyResult result;

	assert(StandardPolicyNormalizeEffectFamily(STANDARD_EFFECT_SAND_ATTACK)
		== STANDARD_EFFECT_ACCURACY_DOWN);
	assert(StandardPolicyNormalizeEffectFamily(STANDARD_EFFECT_SMOKESCREEN)
		== STANDARD_EFFECT_ACCURACY_DOWN);
	assert(StandardPolicyNormalizeEffectFamily(STANDARD_EFFECT_STRING_SHOT)
		== STANDARD_EFFECT_SPEED_DOWN);
	assert(StandardPolicyNormalizeEffectFamily(STANDARD_EFFECT_EQUIVALENT_SPEED_DOWN)
		== STANDARD_EFFECT_SPEED_DOWN);

	StandardPolicyResetMemory(&memory);
	observation.count = 2;
	observation.candidates[0] = Move(0);
	observation.candidates[0].pure_status = 1;
	observation.candidates[0].effect_family = STANDARD_EFFECT_ACCURACY_DOWN;
	observation.candidates[0].stat_stage_before = 6;
	observation.candidates[0].stat_stage_after = 5;
	observation.candidates[0].immediate_future_gain = 12;
	observation.candidates[1] = Move(1);
	observation.candidates[1].immediate_future_gain = 8;
	Choose(&observation, &memory, 0x11111111, &result);
	assert(result.selected_id == 0); /* useful accuracy drop */

	observation.candidates[0].effect_family = STANDARD_EFFECT_SPEED_DOWN;
	observation.candidates[0].stat_stage_before = 0;
	observation.candidates[0].stat_stage_after = 0;
	observation.candidates[0].productive = 0;
	observation.candidates[0].immediate_future_gain = 0;
	Choose(&observation, &memory, 0x11111111, &result);
	assert(result.selected_id == 1); /* no-benefit String Shot/speed drop */
	assert(result.diagnostics[0].floor_reasons & STANDARD_FLOOR_CAPPED_STAT_CHANGE);

	observation.candidates[0] = Move(0);
	observation.candidates[0].pure_status = 1;
	observation.candidates[0].effect_family = STANDARD_EFFECT_ATTACK_UP;
	observation.candidates[0].stat_stage_before = 12;
	observation.candidates[0].stat_stage_after = 12;
	observation.candidates[0].productive = 0;
	observation.candidates[1] = Move(1);
	Choose(&observation, &memory, 0x11111111, &result);
	assert(result.diagnostics[0].floor_reasons & STANDARD_FLOOR_CAPPED_STAT_CHANGE);

	observation.candidates[0] = Move(0);
	observation.candidates[0].pure_status = 1;
	observation.candidates[0].immediate_future_gain = 20;
	observation.candidates[1] = Move(1);
	observation.candidates[1].pure_status = 1;
	observation.candidates[1].redundant_status = 1;
	observation.candidates[1].productive = 0;
	Choose(&observation, &memory, 0x11111111, &result);
	assert(result.selected_id == 0); /* useful status beats redundant status */
	assert(result.diagnostics[1].floor_reasons & STANDARD_FLOOR_REDUNDANT_STATUS);

	observation.candidates[0] = Move(0);
	observation.candidates[0].immediate_future_gain = 10;
	observation.candidates[1] = Switch(1, 0, 1);
	observation.candidates[1].standard_switch_emergency = 0;
	Choose(&observation, &memory, 0x11111111, &result);
	assert(result.selected_id == 0); /* tactical non-emergency switch rejected */
	assert(result.diagnostics[1].admission_reasons == STANDARD_ADMISSION_NON_EMERGENCY_SWITCH);

	observation.candidates[1] = Switch(1, 0, 1);
	observation.candidates[1].entry_survives = 0;
	Choose(&observation, &memory, 0x11111111, &result);
	assert(result.selected_id == 0); /* entry-KO switch rejected */
	assert(result.diagnostics[1].floor_reasons & STANDARD_FLOOR_ENTRY_KO);
}

static void TestAcceptedHostVectorParity(void)
{
	struct StandardPolicyObservation observation = {0};
	struct StandardPolicyMemory memory;
	struct StandardPolicyResult result;

	/* standard_damage_vs_low_accuracy: the host vector scores damage at 37. */
	StandardPolicyResetMemory(&memory);
	observation.count = 2;
	observation.candidates[0] = Move(0);
	observation.candidates[0].opponent_hp_fraction_lost = 96;
	observation.candidates[1] = Move(1);
	observation.candidates[1].pure_status = 1;
	observation.candidates[1].effect_family = STANDARD_EFFECT_SAND_ATTACK;
	observation.candidates[1].immediate_future_gain = 10;
	Choose(&observation, &memory, 1021892788, &result);
	assert(result.selected_id == 0);
	assert(result.best_score == 37);

	/* standard_recovery_useful: -128 own HP fraction gives a +50 HP term. */
	observation.candidates[0] = Move(0);
	observation.candidates[0].pure_status = 1;
	observation.candidates[0].own_hp_fraction_lost = -128;
	observation.candidates[0].uncertainty_cost = 5;
	observation.candidates[1] = Move(1);
	observation.candidates[1].opponent_hp_fraction_lost = 64;
	Choose(&observation, &memory, 1221440649, &result);
	assert(result.selected_id == 0);
	assert(result.best_score == 45);

	/* Host epsilon boundary: 30 vs 22 is exactly an eight-point near-best tie. */
	observation.count = 2;
	observation.candidates[0] = Move(0);
	observation.candidates[0].opponent_hp_fraction_lost = 77;
	observation.candidates[1] = Move(1);
	observation.candidates[1].opponent_hp_fraction_lost = 57;
	Choose(&observation, &memory, 2381340652, &result);
	assert(result.near_best_count == 2);
	assert(result.policy_rng_draws == 1);
	assert(result.selected_id == 0);

	/* The outside boundary is nine points away and must not draw. */
	observation.candidates[1].opponent_hp_fraction_lost = 56;
	Choose(&observation, &memory, 2206094032, &result);
	assert(result.near_best_count == 1);
	assert(result.policy_rng_draws == 0);
	assert(result.selected_id == 0);

	/* Exact accepted host RNG streams for the equal-action vectors. */
	observation.candidates[0].opponent_hp_fraction_lost = 52;
	observation.candidates[1].opponent_hp_fraction_lost = 52;
	{
		uint32_t stream = 1538344410;
		memset(&result, 0, sizeof(result));
		assert(StandardPolicyChoose(&observation, &memory, &stream, &result) == 0);
		assert(stream == 307083199);
	}
	assert(result.selected_id == 1);
	assert(result.policy_rng_draws == 1);
	assert(result.diagnostics[0].utility_total == 20);
	assert(result.diagnostics[1].utility_total == 20);

	observation.count = 4;
	observation.candidates[2] = Move(2);
	observation.candidates[2].opponent_hp_fraction_lost = 52;
	observation.candidates[3] = Move(3);
	observation.candidates[3].opponent_hp_fraction_lost = 52;
	{
		uint32_t stream = 4021793640;
		memset(&result, 0, sizeof(result));
		assert(StandardPolicyChoose(&observation, &memory, &stream, &result) == 0);
		assert(stream == 579686181);
	}
	assert(result.selected_id == 1);
	assert(result.near_best_count == 4);

	/* standard_switch_emergency: the host's safe switch score is -30. */
	observation.count = 2;
	observation.candidates[0] = Move(0);
	observation.candidates[0].net_faints = -1;
	observation.candidates[0].own_hp_fraction_lost = 256;
	observation.candidates[1] = Switch(1, 0, 1);
	observation.candidates[1].own_hp_fraction_lost = 64;
	observation.candidates[1].entry_cost = 5;
	Choose(&observation, &memory, 3234846217, &result);
	assert(result.selected_id == 1);
	assert(result.diagnostics[1].utility_total == -30);

	/* standard_switch_loop_guard and standard_forced_replacement. */
	{
		struct StandardPolicyMemoryDecision edge = {0};
		edge.kind = STANDARD_POLICY_SWITCH;
		edge.switch_from = 0;
		edge.switch_to = 1;
		edge.success = 1;
		StandardPolicyRecordMemory(&memory, &edge);
	}
	observation.count = 2;
	observation.candidates[0] = Move(0);
	observation.candidates[0].opponent_hp_fraction_lost = 52;
	observation.candidates[1] = Switch(1, 1, 0);
	observation.candidates[1].immediate_future_gain = 40;
	observation.candidates[1].entry_cost = 16;
	Choose(&observation, &memory, 1920768135, &result);
	assert(result.selected_id == 0);
	assert(result.diagnostics[1].admission_reasons == STANDARD_ADMISSION_SWITCH_LOOP);

	observation.candidates[0] = Switch(0, 0, 1);
	observation.candidates[0].forced = 1;
	observation.candidates[1] = Move(1);
	Choose(&observation, &memory, 785788004, &result);
	assert(result.selected_id == 0);
	assert(result.diagnostics[1].floor_reasons == STANDARD_FLOOR_FORCED_PRESENT);
}

struct HiddenTwin
{
	struct StandardPolicyObservation public_observation;
	uint16_t hidden_player_move;
	uint16_t hidden_player_item;
	uint8_t hidden_player_ability;
	uint8_t unseen_bench_species;
	uint16_t hidden_stats;
	uint8_t submitted_action;
	uint32_t future_battle_rng;
};

static void TestHiddenInformationTwinsAndReveal(void)
{
	struct HiddenTwin first;
	struct HiddenTwin second;
	struct StandardPolicyMemory memory;
	struct StandardPolicyResult firstResult;
	struct StandardPolicyResult secondResult;
	uint32_t firstSeed = 0xDEADBEEF;
	uint32_t secondSeed = firstSeed;

	memset(&first, 0, sizeof(first));
	first.public_observation.count = 2;
	first.public_observation.candidates[0] = Move(0);
	first.public_observation.candidates[0].immediate_future_gain = 8;
	first.public_observation.candidates[1] = Move(1);
	first.public_observation.candidates[1].immediate_future_gain = 8;
	second = first;
	second.hidden_player_move = 99;
	second.hidden_player_item = 88;
	second.hidden_player_ability = 77;
	second.unseen_bench_species = 66;
	second.hidden_stats = 55;
	second.submitted_action = 44;
	second.future_battle_rng = 0x12345678;
	StandardPolicyResetMemory(&memory);
	memset(&firstResult, 0, sizeof(firstResult));
	memset(&secondResult, 0, sizeof(secondResult));
	assert(StandardPolicyChoose(&first.public_observation, &memory, &firstSeed, &firstResult) == 0);
	assert(StandardPolicyChoose(&second.public_observation, &memory, &secondSeed, &secondResult) == 0);
	assert(memcmp(&firstResult, &secondResult, sizeof(firstResult)) == 0);
	assert(firstSeed == secondSeed);

	/* A legitimate public reveal changes the projected candidate, not hidden data. */
	second.public_observation.candidates[0].known_no_effect = 1;
	second.public_observation.candidates[0].productive = 0;
	assert(StandardPolicyChoose(&second.public_observation, &memory, &secondSeed, &secondResult) == 0);
	assert(secondResult.selected_id == 1);
}

static void TestBoundedSaturationOracle(void)
{
	static const int32_t costs[] = {0, 1, 440, 2147483207, 2147483646, 2147483647};
	struct StandardPolicyObservation o = {0};
	struct StandardPolicyMemory m = {0};
	struct StandardPolicyResult r;
	unsigned a,b,c,count=0;
	int faint, hp, own, future;
	uint32_t seed=123;
	o.count=1; o.candidates[0]=Move(0);
	for(faint=-1;faint<=1;++faint) for(hp=0;hp<=256;hp+=128)
	for(own=-256;own<=256;own+=256) for(future=-40;future<=40;future+=40)
	for(a=0;a<6;++a) for(b=0;b<6;++b) for(c=0;c<6;++c)
	{
		int64_t exact=200*faint+100*(hp-own)/256+future;
		exact-=costs[a]; exact-=costs[b]; exact-=costs[c];
		if(exact < (-2147483647LL-1)) exact=(-2147483647LL-1);
		if(exact > 2147483647) exact=2147483647;
		o.candidates[0].net_faints=faint;
		o.candidates[0].opponent_hp_fraction_lost=hp;
		o.candidates[0].own_hp_fraction_lost=own;
		o.candidates[0].immediate_future_gain=future;
		o.candidates[0].entry_cost=costs[a];
		o.candidates[0].repeat_cost=costs[b];
		o.candidates[0].uncertainty_cost=costs[c];
		assert(StandardPolicyChoose(&o,&m,&seed,&r)==0);
		assert(r.diagnostics[0].utility_total==exact && r.near_best_count==1);
		assert(r.policy_rng_draws==0 && seed==123); ++count;
	}
	assert(count==17496);
}

int main(void)
{
	TestKoDominanceAndUtility();
	TestEpsilonAndRng();
	TestSaturationAndFloorWitnesses();
	TestSwitchMemoryAndForcedReplacement();
	TestMechanicsWitnesses();
	TestAcceptedHostVectorParity();
	TestHiddenInformationTwinsAndReveal();
	TestBoundedSaturationOracle();
	return 0;
}
