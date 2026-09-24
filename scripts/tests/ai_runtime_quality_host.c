/* Reuse the exact production adapter, source tables and host boundary stubs.
 * This executable adds #526 scenarios without copying its projection logic. */
#define main ExistingAdapterMain
#include "standard_ai_adapter_host.c"
#undef main

static const char* const reasonNames[] = {
	"none", "invalid", "status", "non_target", "power_bound",
	"engine_override", "multi_hit", "fixed_damage", "recoil", "drain",
	"self_ko", "two_turn", "counter", "ohko", "other_effect",
	"z_max_pseudo", "recharge_or_lock", "conditional_script"
};

static void DamageCensus(void)
{
	unsigned classes[4] = {0}, reasons[sizeof(reasonNames) / sizeof(reasonNames[0])] = {0};
	unsigned damaging = 0, status = 0, full = 0, directOnly = 0, unsupported = 0;
	u16 move;
	for (move = 1; move < MOVES_COUNT; ++move)
	{
		struct StandardAIDamageClassification c = StandardAI_ClassifyDamage(move);
		assert(c.reason < sizeof(reasons) / sizeof(reasons[0]));
		if (SPLIT(move) == SPLIT_STATUS) { ++status; assert(c.reason == STANDARD_DAMAGE_REASON_STATUS); continue; }
		++damaging;
		++classes[c.mechanics_class];
		if (c.direct_damage_supported)
		{
			assert(c.reason == STANDARD_DAMAGE_REASON_NONE && c.mechanics_class != STANDARD_DAMAGE_D3);
			if (c.secondary_unmodeled) ++directOnly; else ++full;
		}
		else
		{
			assert(c.mechanics_class == STANDARD_DAMAGE_D3 && c.reason != STANDARD_DAMAGE_REASON_NONE);
			++unsupported;
			++reasons[c.reason];
		}
	}
	assert(damaging + status == MOVES_COUNT - 1);
	assert(classes[0] + classes[1] + classes[2] + classes[3] == damaging);
	assert(full + directOnly + unsupported == damaging);
	assert(StandardAI_ClassifyDamage(MOVE_TACKLE).mechanics_class == STANDARD_DAMAGE_D0);
	assert(StandardAI_ClassifyDamage(MOVE_WATERGUN).mechanics_class == STANDARD_DAMAGE_D0);
	assert(StandardAI_ClassifyDamage(MOVE_ROCKTOMB).direct_damage_supported);
	assert(StandardAI_ClassifyDamage(MOVE_ROCKTOMB).secondary_unmodeled);
	assert(StandardAI_ClassifyDamage(MOVE_BIND).mechanics_class == STANDARD_DAMAGE_D3);
	printf("damage census: total=%u damaging=%u status=%u D0=%u D1=%u D2=%u D3=%u full=%u direct_only=%u unsupported=%u\n",
		MOVES_COUNT - 1, damaging, status, classes[0], classes[1], classes[2], classes[3], full, directOnly, unsupported);
	for (move = 1; move < sizeof(reasonNames) / sizeof(reasonNames[0]); ++move)
		if (reasons[move]) printf("unsupported %s=%u\n", reasonNames[move], reasons[move]);
}

static void SetupCharmanderSquirtle(void)
{
	Reset(); profile = TRAINER_AI_PROFILE_IRONMON_SMART;
	testBaseStats[SPECIES_CHARMANDER].baseHP = 39;
	testBaseStats[SPECIES_CHARMANDER].baseDefense = 43;
	testBaseStats[SPECIES_CHARMANDER].baseSpDefense = 50;
	testBaseStats[SPECIES_CHARMANDER].type1 = TYPE_FIRE;
	testBaseStats[SPECIES_CHARMANDER].type2 = TYPE_FIRE;
	gBattleMons[0].species = SPECIES_CHARMANDER;
	gBattleMons[0].level = 5;
	gBattleMons[0].hp = gBattleMons[0].maxHP = 20;
	gNewBS->ai.standardDisplayedSpecies[0] = SPECIES_CHARMANDER;
	gBattleMons[1].species = SPECIES_SQUIRTLE;
	gBattleMons[1].level = 5;
	gBattleMons[1].attack = gBattleMons[1].spAttack = 11;
	gBattleMons[1].type1 = gBattleMons[1].type2 = TYPE_WATER;
	gBattleMons[1].type3 = NUMBER_OF_MON_TYPES;
	gBattleMons[1].moves[0] = MOVE_TACKLE;
	gBattleMons[1].moves[1] = MOVE_WATERGUN;
	gBattleMons[1].moves[2] = gBattleMons[1].moves[3] = MOVE_NONE;
	gBattleMons[1].pp[0] = gBattleMons[1].pp[1] = 10;
	gBattleMons[1].pp[2] = gBattleMons[1].pp[3] = 0;
}

static void RivalLifecycle(void)
{
	struct IronmonPolicyObservation o;
	struct IronmonPolicyResult r;
	struct StandardPolicyMemory memory;
	u32 seed;
	SetupCharmanderSquirtle();
	assert(IronmonAI_IsSupportedBattle());
	assert(gBattleMoves[MOVE_TACKLE].power == gBattleMoves[MOVE_WATERGUN].power);
	assert(gBattleMoves[MOVE_WATERGUN].type == TYPE_WATER
		&& gBattleMons[1].type1 == TYPE_WATER);
	assert(StandardAI_PublicTypeMultiplier(TYPE_WATER, TYPE_FIRE) == 20);
	seed = 0x12345678;
	IronmonAI_BuildObservation(1, FALSE, &o);
	StandardAI_LoadMemory(1, &memory);
	assert(IronmonPolicyChoose(&o, &memory, &seed, &r) == 0);
	assert(o.candidates[0].floor.legal && o.candidates[1].floor.legal);
	assert(o.candidates[1].floor.expected_damage > o.candidates[0].floor.expected_damage);
	assert(!r.diagnostics[0].near_best && r.diagnostics[1].near_best);
	assert(r.selected_id == 1 && r.selection_draws == 0);
	printf("Rival public-species witness: Tackle damage=%u utility=%ld near=%u; Water Gun damage=%u utility=%ld near=%u selected=%u draws=%u\n",
		o.candidates[0].floor.expected_damage, (long)r.diagnostics[0].utility_total,
		r.diagnostics[0].near_best, o.candidates[1].floor.expected_damage,
		(long)r.diagnostics[1].utility_total, r.diagnostics[1].near_best,
		r.selected_id, r.selection_draws);
	/* Before a public species reveal both attacks are intentionally UNKNOWN.
	 * This explains how the old single sprite-coordinate producer could admit
	 * Tackle, without asserting that the private runtime used this path. */
	gNewBS->ai.standardDisplayedSpecies[0] = SPECIES_NONE;
	seed = 0x12345678;
	IronmonAI_BuildObservation(1, FALSE, &o);
	assert(IronmonPolicyChoose(&o, &memory, &seed, &r) == 0);
	assert(o.candidates[0].floor.unknown_potentially_productive);
	assert(o.candidates[1].floor.unknown_potentially_productive);
	assert(!o.candidates[0].floor.expected_damage && !o.candidates[1].floor.expected_damage);
	seed = 2;
	assert(IronmonPolicyChoose(&o, &memory, &seed, &r) == 0);
	assert(r.selected_id == 0 && r.selection_draws == 1);
	printf("Rival missing-public-species witness: Tackle/Water Gun both UNKNOWN; near=%u/%u selected=%u draws=%u\n",
		r.diagnostics[0].near_best, r.diagnostics[1].near_best, r.selected_id, r.selection_draws);
}

static void BrockRockTomb(void)
{
	struct StandardPolicyObservation standard;
	struct StandardPolicyResult sr;
	struct IronmonPolicyObservation ironmon;
	struct IronmonPolicyResult ir;
	struct StandardPolicyMemory memory;
	u32 seed = 0x321;
	Reset();
	testBaseStats[SPECIES_CHARMANDER].baseHP = 39;
	testBaseStats[SPECIES_CHARMANDER].baseDefense = 43;
	testBaseStats[SPECIES_CHARMANDER].baseSpDefense = 50;
	testBaseStats[SPECIES_CHARMANDER].type1 = TYPE_FIRE;
	testBaseStats[SPECIES_CHARMANDER].type2 = TYPE_FIRE;
	gBattleMons[0].species = SPECIES_CHARMANDER;
	gBattleMons[0].level = 14;
	gBattleMons[0].hp = gBattleMons[0].maxHP = 38;
	gNewBS->ai.standardDisplayedSpecies[0] = SPECIES_CHARMANDER;
	gBattleMons[1].species = SPECIES_ONIX;
	gBattleMons[1].level = 14;
	gBattleMons[1].attack = 35;
	gBattleMons[1].type1 = TYPE_ROCK;
	gBattleMons[1].type2 = TYPE_GROUND;
	gBattleMons[1].type3 = NUMBER_OF_MON_TYPES;
	gBattleMons[1].moves[0] = MOVE_TACKLE;
	gBattleMons[1].moves[1] = MOVE_ROCKTOMB;
	gBattleMons[1].moves[2] = MOVE_BIND;
	gBattleMons[1].moves[3] = MOVE_NONE;
	gBattleMons[1].pp[0] = gBattleMons[1].pp[1] = gBattleMons[1].pp[2] = 10;
	gBattleMons[1].pp[3] = 0;
	StandardAI_BuildObservation(1, FALSE, &standard);
	StandardAI_LoadMemory(1, &memory);
	assert(StandardPolicyChoose(&standard, &memory, &seed, &sr) == 0);
	assert(StandardAI_ClassifyDamage(MOVE_ROCKTOMB).direct_damage_supported);
	assert(standard.candidates[1].expected_damage > standard.candidates[0].expected_damage);
	assert(sr.selected_id == 1 && !sr.diagnostics[0].near_best);
	printf("Brock Standard: Tackle power=%u damage=%u utility=%ld near=%u; Rock Tomb power=%u accuracy=%u effect=%u damage=%u fraction=%u utility=%ld near=%u; selected=%u draws=%u\n",
		gBattleMoves[MOVE_TACKLE].power, standard.candidates[0].expected_damage,
		(long)sr.diagnostics[0].utility_total, sr.diagnostics[0].near_best,
		gBattleMoves[MOVE_ROCKTOMB].power, gBattleMoves[MOVE_ROCKTOMB].accuracy,
		gBattleMoves[MOVE_ROCKTOMB].effect, standard.candidates[1].expected_damage,
		standard.candidates[1].opponent_hp_fraction_lost, (long)sr.diagnostics[1].utility_total,
		sr.diagnostics[1].near_best, sr.selected_id, sr.policy_rng_draws);
	profile = TRAINER_AI_PROFILE_IRONMON_SMART;
	seed = 0x321;
	IronmonAI_BuildObservation(1, FALSE, &ironmon);
	assert(IronmonPolicyChoose(&ironmon, &memory, &seed, &ir) == 0);
	assert(ir.selected_id == 1 && !ir.diagnostics[0].near_best);
	printf("Brock Ironmon: Tackle utility=%ld Rock Tomb utility=%ld selected=%u draws=%u\n",
		(long)ir.diagnostics[0].utility_total, (long)ir.diagnostics[1].utility_total,
		ir.selected_id, ir.selection_draws);
}

static void AccuracyLifecycle(void)
{
	struct StandardPolicyObservation o;
	struct StandardPolicyResult r;
	struct StandardPolicyMemory memory;
	u32 seed = 28; /* Smoke then Sand across the same normalized family. */
	u8 first, second;
	Reset();
	gBattleMons[1].species = SPECIES_SANDSHREW;
	gBattleMons[1].attack = 1;
	/* A bulky randomized target leaves the second drop genuinely marginally
	 * useful compared with this very weak direct attack. */
	testBaseStats[SPECIES_RATTATA].baseHP = 255;
	gBattleMons[0].level = 100;
	gBattleMons[0].hp = gBattleMons[0].maxHP = 500;
	gBattleMons[1].moves[0] = MOVE_SANDATTACK;
	gBattleMons[1].moves[1] = MOVE_SMOKESCREEN;
	gBattleMons[1].moves[2] = MOVE_TACKLE;
	gBattleMons[1].moves[3] = MOVE_NONE;
	gBattleMons[1].pp[3] = 0;
	Build(&o, &r, &seed);
	assert(o.candidates[0].effect_family == STANDARD_EFFECT_ACCURACY_DOWN);
	assert(o.candidates[1].effect_family == STANDARD_EFFECT_ACCURACY_DOWN);
	assert(o.candidates[0].immediate_future_gain == 25);
	assert(r.selected_id < 2);
	first = r.selected_id;
	StandardAI_StageLastAction(1, &o.candidates[first]);
	gBattleMons[0].statStages[STAT_STAGE_ACC - 1] = 5;
	Build(&o, &r, &seed);
	StandardAI_LoadMemory(1, &memory);
	assert(memory.count == 1 && memory.decisions[0].success);
	assert(o.candidates[0].immediate_future_gain == 15);
	assert(r.selected_id < 2);
	second = r.selected_id;
	StandardAI_StageLastAction(1, &o.candidates[second]);
	gBattleMons[0].statStages[STAT_STAGE_ACC - 1] = 4;
	Build(&o, &r, &seed);
	StandardAI_LoadMemory(1, &memory);
	assert(memory.count == 2 && memory.decisions[1].success);
	assert(o.candidates[0].immediate_future_gain == 10);
	assert((r.diagnostics[0].floor_reasons & STANDARD_FLOOR_HARMFUL_REPEAT)
		&& (r.diagnostics[1].floor_reasons & STANDARD_FLOOR_HARMFUL_REPEAT));
	assert(r.selected_id == 2);
	/* Turn progression and a different move ID do not clear the family. */
	Build(&o, &r, &seed);
	StandardAI_LoadMemory(1, &memory);
	assert(memory.count == 2 && r.selected_id == 2);
	/* The accepted memory is battle-local and carries across own replacement;
	 * a new target still cannot bypass the same-family repeat gate. */
	gBattleMons[1].species = SPECIES_SANDSHREW;
	gNewBS->ai.standardDisplayedSpecies[0] = SPECIES_CHARMANDER;
	gBattleMons[0].statStages[STAT_STAGE_ACC - 1] = 6;
	Build(&o, &r, &seed);
	assert(r.diagnostics[0].floor_reasons & STANDARD_FLOOR_HARMFUL_REPEAT);
	assert(r.selected_id == 2);
	printf("Accuracy lifecycle: marginal=25,15,10; first=%u second=%u third=damage; family/switch/replacement memory PASS\n",
		first, second);
	/* A miss leaves the public stage unchanged and records failure, not a
	 * successful drop. Switch/faint hook resolves against the old target. */
	Reset(); gBattleMons[1].species = SPECIES_SANDSHREW; gBattleMons[1].attack = 1;
	gBattleMons[1].moves[0] = MOVE_SANDATTACK;
	gBattleMons[1].moves[1] = MOVE_TACKLE;
	gBattleMons[1].moves[2] = gBattleMons[1].moves[3] = MOVE_NONE;
	gBattleMons[1].pp[2] = gBattleMons[1].pp[3] = 0;
	Build(&o, &r, &seed);
	StandardAI_StageLastAction(1, &o.candidates[0]);
	StandardAI_FinalizePendingForTarget(0);
	StandardAI_LoadMemory(1, &memory);
	assert(memory.count == 1 && !memory.decisions[0].success);
	assert(!gNewBS->ai.standardLastValid[1]);
	Reset(); gBattleMons[1].species = SPECIES_SANDSHREW; gBattleMons[1].attack = 1;
	gBattleMons[1].moves[0] = MOVE_SANDATTACK;
	gBattleMons[1].moves[1] = MOVE_TACKLE;
	gBattleMons[1].moves[2] = gBattleMons[1].moves[3] = MOVE_NONE;
	gBattleMons[1].pp[2] = gBattleMons[1].pp[3] = 0;
	Build(&o, &r, &seed);
	StandardAI_StageLastAction(1, &o.candidates[0]);
	gBattleMons[0].statStages[STAT_STAGE_ACC - 1] = 5;
	StandardAI_FinalizePendingForTarget(0);
	StandardAI_LoadMemory(1, &memory);
	assert(memory.count == 1 && memory.decisions[0].success);
	printf("Accuracy miss/switch-old-target finalization: failure=0 success=1 PASS\n");
	Reset();
	gBattleMons[1].species = SPECIES_SANDSHREW;
	gBattleMons[1].moves[0] = MOVE_SANDATTACK;
	gBattleMons[1].moves[1] = MOVE_TACKLE;
	gBattleMons[1].moves[2] = gBattleMons[1].moves[3] = MOVE_NONE;
	gBattleMons[1].pp[2] = gBattleMons[1].pp[3] = 0;
	gBattleMons[0].statStages[STAT_STAGE_ACC - 1] = STAT_STAGE_MIN;
	Build(&o, &r, &seed);
	assert(!o.candidates[0].productive);
	assert(r.diagnostics[0].floor_reasons & STANDARD_FLOOR_CAPPED_STAT_CHANGE);
	assert(r.selected_id == 1);
}

static void StringShotAndWeedle(void)
{
	struct StandardPolicyObservation o;
	struct StandardPolicyResult r;
	u32 seed = 0x526;
	Reset(); Certify();
	gBattleMons[0].hp = gBattleMons[0].maxHP;
	testBaseStats[SPECIES_RATTATA].baseSpeed = 150;
	gBattleMons[1].species = SPECIES_CATERPIE;
	gBattleMons[1].speed = 125;
	gBattleMons[1].attack = 1;
	gBattleMons[1].moves[0] = MOVE_STRINGSHOT;
	gBattleMons[1].moves[1] = MOVE_TACKLE;
	gBattleMons[1].moves[2] = gBattleMons[1].moves[3] = MOVE_NONE;
	gBattleMons[1].pp[2] = gBattleMons[1].pp[3] = 0;
	Build(&o, &r, &seed);
	assert(o.candidates[0].productive && o.candidates[0].immediate_future_gain > 0);
	assert(r.selected_id == 0);
	StandardAI_StageLastAction(1, &o.candidates[0]);
	gBattleMons[0].statStages[STAT_STAGE_SPEED - 1] = o.candidates[0].stat_stage_after;
	Build(&o, &r, &seed);
	assert(!o.candidates[0].immediate_future_gain && r.selected_id == 1);
	printf("Caterpie: String Shot flips certified order; next marginal=0 -> Tackle PASS\n");
	Reset();
	gBattleMons[1].species = SPECIES_WEEDLE;
	gBattleMons[1].attack = 15;
	gBattleMons[1].moves[0] = MOVE_STRINGSHOT;
	gBattleMons[1].moves[1] = MOVE_POISONSTING;
	gBattleMons[1].moves[2] = gBattleMons[1].moves[3] = MOVE_NONE;
	gBattleMons[1].pp[2] = gBattleMons[1].pp[3] = 0;
	Build(&o, &r, &seed);
	assert(!o.candidates[0].productive && o.candidates[1].productive);
	assert(r.selected_id == 1);
	printf("Weedle: no certified order flip -> Poison Sting direct damage PASS\n");
}

static void TwoMoveDamageCase(const char* label, u16 firstMove, u16 secondMove,
	u8 ownType, u8 targetType, u8 expectedBest)
{
	struct StandardPolicyObservation o;
	struct StandardPolicyResult r;
	u32 seed = 0x526;
	Reset();
	gBattleMons[1].type1 = gBattleMons[1].type2 = ownType;
	gBattleMons[1].type3 = NUMBER_OF_MON_TYPES;
	testBaseStats[SPECIES_RATTATA].type1 = testBaseStats[SPECIES_RATTATA].type2 = targetType;
	gBattleMons[1].moves[0] = firstMove;
	gBattleMons[1].moves[1] = secondMove;
	gBattleMons[1].moves[2] = gBattleMons[1].moves[3] = MOVE_NONE;
	gBattleMons[1].pp[2] = gBattleMons[1].pp[3] = 0;
	Build(&o, &r, &seed);
	assert(o.candidates[expectedBest].expected_damage > o.candidates[1 - expectedBest].expected_damage);
	assert(r.diagnostics[expectedBest].utility_total > r.diagnostics[1 - expectedBest].utility_total);
	assert(r.diagnostics[expectedBest].near_best);
	assert(r.diagnostics[r.selected_id].near_best);
	printf("%s: move0 damage=%u utility=%ld; move1 damage=%u utility=%ld selected=%u near=%u/%u\n",
		label, o.candidates[0].expected_damage, (long)r.diagnostics[0].utility_total,
		o.candidates[1].expected_damage, (long)r.diagnostics[1].utility_total,
		r.selected_id, r.diagnostics[0].near_best, r.diagnostics[1].near_best);
}

static void DamageComparisons(void)
{
	TwoMoveDamageCase("STAB vs weaker non-STAB", MOVE_TACKLE, MOVE_PECK,
		TYPE_NORMAL, TYPE_NORMAL, 0);
	TwoMoveDamageCase("weaker super-effective vs stronger neutral", MOVE_WATERGUN,
		MOVE_SLAM, TYPE_WATER, TYPE_FIRE, 0);
	TwoMoveDamageCase("resisted STAB vs neutral non-STAB", MOVE_WATERGUN,
		MOVE_BITE, TYPE_WATER, TYPE_GRASS, 1);
	TwoMoveDamageCase("reliable vs high-power lower-accuracy", MOVE_ICEBEAM,
		MOVE_BLIZZARD, TYPE_ICE, TYPE_NORMAL, 0);
	TwoMoveDamageCase("unsupported secondary retains direct damage", MOVE_ROCKTOMB,
		MOVE_TACKLE, TYPE_ROCK, TYPE_FIRE, 0);
}

static void FloorFallbackAndEntropy(void)
{
	struct StandardPolicyObservation o;
	struct StandardPolicyResult r;
	struct IronmonPolicyObservation io;
	struct IronmonPolicyResult ir;
	struct StandardPolicyMemory memory;
	u32 seed;
	unsigned seen = 0, i;
	Reset(); Certify();
	gBattleMons[1].moves[0] = MOVE_STRENGTH;
	gBattleMons[1].moves[1] = MOVE_SANDATTACK;
	gBattleMons[1].moves[2] = gBattleMons[1].moves[3] = MOVE_NONE;
	gBattleMons[1].pp[2] = gBattleMons[1].pp[3] = 0;
	seed = 1;
	StandardAI_BuildObservation(1, FALSE, &o);
	StandardAI_LoadMemory(1, &memory);
	assert(StandardPolicyChoose(&o, &memory, &seed, &r) == 0);
	assert(o.candidates[0].robust_safe_ko && r.selected_id == 0);
	assert(!r.diagnostics[1].near_best && r.policy_rng_draws == 0);
	Reset();
	gBattleMons[0].statStages[STAT_STAGE_ACC - 1] = STAT_STAGE_MIN;
	gBattleMons[1].moves[0] = MOVE_SANDATTACK;
	gBattleMons[1].moves[1] = MOVE_HARDEN;
	gBattleMons[1].moves[2] = gBattleMons[1].moves[3] = MOVE_NONE;
	gBattleMons[1].pp[2] = gBattleMons[1].pp[3] = 0;
	seed = 1;
	StandardAI_BuildObservation(1, FALSE, &o);
	StandardAI_LoadMemory(1, &memory);
	assert(StandardPolicyChoose(&o, &memory, &seed, &r) == 0);
	assert(r.no_productive_fallback && r.selected_id == 0 && r.policy_rng_draws == 0);
	assert(r.diagnostics[1].floor_reasons & STANDARD_FLOOR_NO_MARGINAL_VALUE);
	printf("floor: robust KO over status; all-futile legal fallback=1 reason=NO_PRODUCTIVE_ACTION PASS\n");
	Reset();
	gBattleMons[1].moves[0] = MOVE_TACKLE;
	gBattleMons[1].moves[1] = MOVE_POUND;
	gBattleMons[1].moves[2] = gBattleMons[1].moves[3] = MOVE_NONE;
	gBattleMons[1].pp[2] = gBattleMons[1].pp[3] = 0;
	for (i = 1; i <= 16; ++i)
	{
		seed = i;
		Build(&o, &r, &seed);
		assert(r.near_best_count == 2 && r.policy_rng_draws == 1);
		assert(r.diagnostics[r.selected_id].near_best);
		seen |= 1u << r.selected_id;
	}
	assert(seen == 3);
	profile = TRAINER_AI_PROFILE_IRONMON_SMART;
	IronmonAI_BuildObservation(1, FALSE, &io);
	StandardAI_LoadMemory(1, &memory);
	seen = 0;
	for (i = 1; i <= 16; ++i)
	{
		seed = i;
		assert(IronmonPolicyChoose(&io, &memory, &seed, &ir) == 0);
		assert(ir.near_best_count == 2 && ir.selection_draws == 1);
		assert(ir.diagnostics[ir.selected_id].near_best);
		seen |= 1u << ir.selected_id;
	}
	assert(seen == 3);
	printf("near-best: Standard epsilon=%u Ironmon epsilon=%u; seeded equal-pair entropy both IDs; singleton zero draws PASS\n",
		STANDARD_POLICY_EPSILON, IRONMON_POLICY_EPSILON);
}

static void PriorityKO(void)
{
	struct IronmonPolicyObservation o;
	struct IronmonPolicyResult r;
	struct StandardPolicyMemory memory;
	u32 seed = 9;
	Reset(); profile = TRAINER_AI_PROFILE_IRONMON_SMART; IronmonCertify();
	gBattleMons[0].hp = 5;
	gBattleMons[1].hp = 10;
	gBattleMons[1].speed = 1;
	gBattleMons[1].moves[0] = MOVE_QUICKATTACK;
	gBattleMons[1].moves[1] = MOVE_STRENGTH;
	gBattleMons[1].moves[2] = gBattleMons[1].moves[3] = MOVE_NONE;
	gBattleMons[1].pp[2] = gBattleMons[1].pp[3] = 0;
	RevealIronmonResponse(MOVE_STRENGTH);
	IronmonAI_BuildObservation(1, FALSE, &o);
	StandardAI_LoadMemory(1, &memory);
	assert(IronmonPolicyChoose(&o, &memory, &seed, &r) == 0);
	assert(FindIronmonBranch(&o.candidates[0], MOVE_STRENGTH)->opponent_hp_fraction_lost > 0);
	assert(FindIronmonBranch(&o.candidates[1], MOVE_STRENGTH)->opponent_hp_fraction_lost == 0);
	assert(r.selected_id == 0 && !r.diagnostics[1].near_best);
	printf("priority KO: Quick Attack precedes revealed lethal response; stronger Strength cannot act; selected priority PASS\n");
}

/* Machine-readable production observations for the accepted Workspace host
 * policy. The host script reconstructs the same public candidates and checks
 * every transferred fact plus admission, utility, selection and RNG state. */
#define CVAL(field) printf(",\"" #field "\":%ld", (long)c->field)
#define DVAL(field) printf(",\"" #field "\":%ld", (long)d->field)
static void TraceCandidate(const struct StandardPolicyCandidate* c,
	const struct StandardPolicyDiagnostic* d, u16 move)
{
	struct StandardAIDamageClassification classification = StandardAI_ClassifyDamage(move);
	printf("{\"type\":\"candidate\",\"move\":%u,\"mechanics_class\":%u,\"mechanics_reason\":%u,\"secondary_unmodeled\":%u",
		move, classification.mechanics_class, classification.reason, classification.secondary_unmodeled);
	CVAL(id); CVAL(kind); CVAL(legal); CVAL(productive); CVAL(known_no_effect);
	CVAL(pure_status); CVAL(robust_safe_ko); CVAL(redundant_status);
	CVAL(stat_stage_before); CVAL(stat_stage_after); CVAL(effect_family);
	CVAL(positive_marginal_exception); CVAL(expected_damage); CVAL(switch_legal);
	CVAL(entry_survives); CVAL(forced); CVAL(fallback_cost); CVAL(switch_from);
	CVAL(switch_to); CVAL(net_faints); CVAL(opponent_hp_fraction_lost);
	CVAL(own_hp_fraction_lost); CVAL(immediate_future_gain); CVAL(entry_cost);
	CVAL(repeat_cost); CVAL(uncertainty_cost); CVAL(standard_switch_emergency);
	CVAL(unknown_potentially_productive); CVAL(accuracy); CVAL(priority);
	if (d != NULL)
	{
		DVAL(standard_eligible); DVAL(near_best); DVAL(selected); DVAL(floor_reasons);
		DVAL(admission_reasons); DVAL(utility_total);
	}
	printf("}\n");
}
#undef DVAL
#undef CVAL

static void TraceStandard(const char* name, u32 seed)
{
	struct StandardPolicyObservation o;
	struct StandardPolicyResult r;
	struct StandardPolicyMemory memory;
	u8 i;
	u32 pre = seed;
	StandardAI_BuildObservation(1, FALSE, &o);
	StandardAI_LoadMemory(1, &memory);
	assert(StandardPolicyChoose(&o, &memory, &seed, &r) == 0);
	printf("{\"type\":\"case\",\"name\":\"%s\",\"profile\":\"standard\",\"pre\":%lu,\"post\":%lu,\"draws\":%u,\"selected\":%u,\"fallback\":%u,\"count\":%u,\"memory_count\":%u}\n",
		name, (unsigned long)pre, (unsigned long)seed, r.policy_rng_draws,
		r.selected_id, r.no_productive_fallback, o.count, memory.count);
	for (i = 0; i < memory.count; ++i)
	{
		const struct StandardPolicyMemoryDecision* d = &memory.decisions[i];
		printf("{\"type\":\"memory\",\"kind\":%u,\"effect_family\":%u,\"success\":%u,\"forced\":%u,\"switch_from\":%u,\"switch_to\":%u}\n",
			d->kind, d->effect_family, d->success, d->forced, d->switch_from, d->switch_to);
	}
	for (i = 0; i < o.count; ++i)
		TraceCandidate(&o.candidates[i], &r.diagnostics[i], gBattleMons[1].moves[i]);
}

static void TraceIronmon(const char* name, u32 seed)
{
	struct IronmonPolicyObservation o;
	struct IronmonPolicyResult r;
	struct StandardPolicyMemory memory;
	u32 pre = seed;
	u8 i, j;
	IronmonAI_BuildObservation(1, FALSE, &o);
	StandardAI_LoadMemory(1, &memory);
	assert(IronmonPolicyChoose(&o, &memory, &seed, &r) == 0);
	printf("{\"type\":\"case\",\"name\":\"%s\",\"profile\":\"ironmon\",\"pre\":%lu,\"post\":%lu,\"draws\":%u,\"selected\":%u,\"fallback\":0,\"count\":%u,\"memory_count\":%u,\"response_count\":%u,\"admitted_pool\":%u,\"near_pool\":%u}\n",
		name, (unsigned long)pre, (unsigned long)seed, r.total_draws,
		r.selected_id, o.count, memory.count, o.response_count,
		r.admitted_pool, r.near_best_pool);
	for (i = 0; i < memory.count; ++i)
	{
		const struct StandardPolicyMemoryDecision* d = &memory.decisions[i];
		printf("{\"type\":\"memory\",\"kind\":%u,\"effect_family\":%u,\"success\":%u,\"forced\":%u,\"switch_from\":%u,\"switch_to\":%u}\n",
			d->kind, d->effect_family, d->success, d->forced, d->switch_from, d->switch_to);
	}
	for (i = 0; i < o.response_count; ++i)
		printf("{\"type\":\"response\",\"id\":%u,\"weight\":%lu}\n",
			o.responses[i].id, (unsigned long)o.responses[i].weight);
	for (i = 0; i < o.count; ++i)
	{
		const struct IronmonPolicyCandidate* c = &o.candidates[i];
		const struct IronmonPolicyDiagnostic* d = &r.diagnostics[i];
		TraceCandidate(&c->floor, NULL, gBattleMons[1].moves[i]);
		printf("{\"type\":\"ironmon_candidate\",\"id\":%u,\"tactical_class\":%u,\"ironmon_switch_emergency\":%u,\"stay_defensible\":%u,\"repeat_exception_reason\":%u,\"public_threat_changed\":%u,\"regenerator_only\":%u,\"progress_after_loop_cost\":%ld,\"ironmon_eligible\":%u,\"near_best\":%u,\"utility_total\":%ld,\"repeat_count\":%u,\"repeat_cost\":%u,\"uncertainty_cost\":%u,\"reasons\":%lu}\n",
			c->floor.id, c->tactical_class, c->ironmon_switch_emergency,
			c->stay_defensible, c->repeat_exception_reason, c->public_threat_changed,
			c->regenerator_only, (long)c->progress_after_loop_cost,
			d->ironmon_eligible, d->near_best, (long)d->utility_total,
			d->repeat_count, d->repeat_cost, d->uncertainty_cost, (unsigned long)d->reasons);
		for (j = 0; j < c->response_count; ++j)
		{
			const struct IronmonPolicyBranch* b = &c->responses[j];
			printf("{\"type\":\"branch\",\"candidate_id\":%u,\"response_id\":%u,\"net_faints\":%d,\"opponent_hp_fraction_lost\":%d,\"own_hp_fraction_lost\":%d,\"future_gain_undiscounted\":%d,\"entry_cost\":%ld}\n",
				c->floor.id, b->response_id, b->net_faints,
				b->opponent_hp_fraction_lost, b->own_hp_fraction_lost,
				b->future_gain_undiscounted, (long)b->entry_cost);
		}
	}
}

static void DifferentialTraces(void)
{
	SetupCharmanderSquirtle(); TraceIronmon("rival", 0x12345678);
	Reset(); gBattleMons[1].moves[0] = MOVE_TACKLE;
	gBattleMons[1].moves[1] = MOVE_POUND;
	gBattleMons[1].moves[2] = gBattleMons[1].moves[3] = MOVE_NONE;
	gBattleMons[1].pp[2] = gBattleMons[1].pp[3] = 0;
	TraceStandard("near_best", 9);
	Reset(); gBattleMons[1].species = SPECIES_SANDSHREW; gBattleMons[1].attack = 1;
	gBattleMons[1].moves[0] = MOVE_SANDATTACK;
	gBattleMons[1].moves[1] = MOVE_SMOKESCREEN;
	gBattleMons[1].moves[2] = MOVE_TACKLE;
	gBattleMons[1].moves[3] = MOVE_NONE; gBattleMons[1].pp[3] = 0;
	TraceStandard("accuracy_first", 28);
	StandardAI_StageLastAction(1, (const struct StandardPolicyCandidate[1]){{.kind=STANDARD_POLICY_MOVE,.effect_family=STANDARD_EFFECT_ACCURACY_DOWN,.productive=TRUE,.stat_stage_before=6,.stat_stage_after=5}});
	gBattleMons[0].statStages[STAT_STAGE_ACC - 1] = 5;
	TraceStandard("accuracy_second", 28);
	StandardAI_StageLastAction(1, (const struct StandardPolicyCandidate[1]){{.kind=STANDARD_POLICY_MOVE,.effect_family=STANDARD_EFFECT_ACCURACY_DOWN,.productive=TRUE,.stat_stage_before=5,.stat_stage_after=4}});
	gBattleMons[0].statStages[STAT_STAGE_ACC - 1] = 4;
	TraceStandard("accuracy_third", 28);
	Reset(); gBattleMons[1].moves[0] = MOVE_SEISMICTOSS;
	gBattleMons[1].moves[1] = MOVE_TACKLE;
	gBattleMons[1].moves[2] = gBattleMons[1].moves[3] = MOVE_NONE;
	gBattleMons[1].pp[2] = gBattleMons[1].pp[3] = 0;
	TraceStandard("unsupported_fixed", 17);
	Reset(); gBattleMons[1].moves[0] = MOVE_TACKLE;
	gBattleMons[1].moves[1] = MOVE_WATERGUN;
	gBattleMons[1].moves[2] = gBattleMons[1].moves[3] = MOVE_NONE;
	gBattleMons[1].pp[2] = gBattleMons[1].pp[3] = 0;
	testBaseStats[SPECIES_RATTATA].type1 = testBaseStats[SPECIES_RATTATA].type2 = TYPE_GHOST;
	TraceStandard("known_immunity", 19);
	Reset(); gBattleMons[0].statStages[STAT_STAGE_ACC - 1] = STAT_STAGE_MIN;
	gBattleMons[1].moves[0] = MOVE_SANDATTACK;
	gBattleMons[1].moves[1] = MOVE_HARDEN;
	gBattleMons[1].moves[2] = gBattleMons[1].moves[3] = MOVE_NONE;
	gBattleMons[1].pp[2] = gBattleMons[1].pp[3] = 0;
	TraceStandard("all_futile", 23);
	Reset(); gBattleMons[1].type1 = gBattleMons[1].type2 = TYPE_ROCK;
	gBattleMons[1].moves[0] = MOVE_ROCKTOMB;
	gBattleMons[1].moves[1] = MOVE_TACKLE;
	gBattleMons[1].moves[2] = gBattleMons[1].moves[3] = MOVE_NONE;
	gBattleMons[1].pp[2] = gBattleMons[1].pp[3] = 0;
	TraceStandard("secondary_damage", 31);
	Reset(); profile = TRAINER_AI_PROFILE_IRONMON_SMART; IronmonCertify();
	gBattleMons[0].hp = 5; gBattleMons[1].hp = 10; gBattleMons[1].speed = 1;
	gBattleMons[1].moves[0] = MOVE_QUICKATTACK;
	gBattleMons[1].moves[1] = MOVE_STRENGTH;
	gBattleMons[1].moves[2] = gBattleMons[1].moves[3] = MOVE_NONE;
	gBattleMons[1].pp[2] = gBattleMons[1].pp[3] = 0;
	RevealIronmonResponse(MOVE_STRENGTH);
	TraceIronmon("priority_ko", 9);
}

int main(int argc, char** argv)
{
	if (argc == 2 && strcmp(argv[1], "--differential") == 0)
	{
		DifferentialTraces();
		return 0;
	}
	DamageCensus();
	RivalLifecycle();
	BrockRockTomb();
	AccuracyLifecycle();
	StringShotAndWeedle();
	DamageComparisons();
	FloorFallbackAndEntropy();
	PriorityKO();
	return 0;
}
