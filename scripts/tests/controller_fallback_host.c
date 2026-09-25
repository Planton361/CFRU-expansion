/* Exercise the real adapter globals and policy projection from the existing
 * source host, then link the production AI master and supported controller
 * handoff around them. EmitMoveChosen is the transport boundary recorded here. */
#define CFRU_AI_TEST_TRACE 1
#define CFRU_AI_CONTROLLER_TEST 1
#define main StandardAdapterHarnessMain
#include "standard_ai_adapter_host.c"
#undef main
#undef gBitTable

#include <stddef.h>
#include "../../src/Tables/trainer_parties.h"
#include "../../include/new/ai_master.h"
#include "../../include/new/battle_controller_opponent.h"
#include "../../include/new/move_menu.h"
#include "../../include/new/species_tables.h"

extern enum TrainerAIProfile GetTrainerAIProfileFromRaw(void);
extern int StandardAI_TestLastPolicyRc;
extern u8 StandardAI_TestLastFailureReason;
extern u8 StandardAI_TestLastSelectedId;
extern int StandardAI_TestPolicyRcOverride;
extern u8 StandardAI_TestSelectedIdOverride;
extern int IronmonAI_TestLastPolicyRc;
extern u8 IronmonAI_TestLastFailureReason;
extern u8 IronmonAI_TestLastSelectedId;
extern int IronmonAI_TestPolicyRcOverride;
extern u8 IronmonAI_TestSelectedIdOverride;
extern u8 OpponentAI_TestLastBufferMismatch;
extern u8 OpponentAI_TestLastBoundedFallback;

u8 gBattleBufferA[MAX_BATTLERS_COUNT][0x200];
static u8 sEmitCount;
static u8 sEmittedPosition;
static u8 sEmittedTarget;
static u8 sOpponentCompleted;
static u16 sRawTrainerAIProfile;
static struct AI_ThinkingStruct sThinking;
static struct BattleScriptsStack sAIScriptsStack;

void EmitMoveChosen(u8 bufferId, u8 chosenMoveIndex, u8 target, u8 megaState,
	u8 ultraState, u8 zMoveState, u8 dynamaxState, u8 teraState)
{
	(void)bufferId;
	(void)megaState;
	(void)ultraState;
	(void)zMoveState;
	(void)dynamaxState;
	(void)teraState;
	++sEmitCount;
	sEmittedPosition = chosenMoveIndex;
	sEmittedTarget = target;
}

void OpponentBufferExecCompleted(void)
{
	++sOpponentCompleted;
}

u32 ControllerTestGetAIFlags(void) { return 0; }
u16 AIRandom(void) { return 1; }
u8 CheckMoveLimitations(u8 bank, u8 move, u8 flags)
{ (void)bank; (void)move; (void)flags; return 0; }
u8 AdjustMoveLimitationFlagsForAI(u8 bank) { (void)bank; return 0; }
u32 GetAIFlagsInBattleFrontier(u8 bank) { (void)bank; return 0; }
bool8 IsBluePrimalSpecies(u16 species) { (void)species; return FALSE; }
bool8 IsRedPrimalSpecies(u16 species) { (void)species; return FALSE; }
bool8 IsMegaSpecies(u16 species) { (void)species; return FALSE; }
bool8 IsUltraNecrozmaSpecies(u16 species) { (void)species; return FALSE; }
u16 VarGet(u16 variable)
{ return variable == VAR_TRAINER_AI_PROFILE ? sRawTrainerAIProfile : 0; }
u8 gAbsentBattlerFlags;
const u32 gBitTable[] = {1, 2, 4, 8};
const struct Trainer gTrainers[1024] = {
	[TRAINER_RIVAL_CERULEAN_SQUIRTLE] = {.aiFlags = AI_SCRIPT_CHECK_BAD_MOVE}
};
const struct SpecialSpeciesFlags gSpecialSpeciesFlags[NUM_SPECIES] = {{0}};

static void SetControllerMoves(u8 bank)
{
	struct ChooseMoveStruct *moveInfo =
		(struct ChooseMoveStruct *)&gBattleBufferA[bank][4];
	u8 i;
	memset(gBattleBufferA[bank], 0, sizeof(gBattleBufferA[bank]));
	for (i = 0; i < MAX_MON_MOVES; ++i)
		moveInfo->moves[i] = gBattleMons[bank].moves[i];
}

static void RunHandoff(u8 expectedPosition, u16 expectedMove, u8 bufferFault)
{
	struct ChooseMoveStruct *moveInfo =
		(struct ChooseMoveStruct *)&gBattleBufferA[gActiveBattler][4];
	u8 i;
	if (bufferFault == 1)
		moveInfo->moves[expectedPosition] = MOVE_TACKLE;
	else if (bufferFault == 2)
	{
		u16 move = moveInfo->moves[0];
		moveInfo->moves[0] = moveInfo->moves[expectedPosition];
		moveInfo->moves[expectedPosition] = move;
	}
	if (bufferFault)
	{
		assert(moveInfo->moves[expectedPosition] != gBattleMons[gActiveBattler].moves[expectedPosition]);
		printf("  controller buffer fault=%s before emit; ",
			bufferFault == 1 ? "stale-selected-slot" : "permuted-slots");
	}
	sEmitCount = 0;
	sOpponentCompleted = 0;
	OpponentHandleChooseMove();
	assert(sEmitCount == 1);
	assert(sEmittedPosition == expectedPosition);
	assert(sEmittedTarget == FOE(gActiveBattler));
	assert(moveInfo->moves[expectedPosition] == expectedMove);
	assert(gBattleMons[gActiveBattler].moves[expectedPosition] == expectedMove);
	for (i = 0; i < MAX_MON_MOVES; ++i)
		assert(moveInfo->moves[i] == gBattleMons[gActiveBattler].moves[i]);
	assert(OpponentAI_TestLastBufferMismatch == (bufferFault != 0));
	assert(sOpponentCompleted == 1);
}

static void SetWitnessMon(u8 bank, u16 species, u8 level, u16 hp, u16 attack,
	u16 defense, u16 spAttack, u16 spDefense, u16 speed, u8 type1, u8 type2,
	const u16 moves[MAX_MON_MOVES])
{
	u8 i;
	gBattleMons[bank].species = species;
	gBattleMons[bank].level = level;
	gBattleMons[bank].hp = gBattleMons[bank].maxHP = hp;
	gBattleMons[bank].attack = attack;
	gBattleMons[bank].defense = defense;
	gBattleMons[bank].spAttack = spAttack;
	gBattleMons[bank].spDefense = spDefense;
	gBattleMons[bank].speed = speed;
	gBattleMons[bank].type1 = type1;
	gBattleMons[bank].type2 = type2;
	gBattleMons[bank].type3 = NUMBER_OF_MON_TYPES;
	newBattle.ai.standardDisplayedSpecies[bank] = species;
	for (i = 0; i < MAX_MON_MOVES; ++i)
	{
		gBattleMons[bank].moves[i] = moves[i];
		gBattleMons[bank].pp[i] = moves[i] == MOVE_NONE ? 0 : 10;
	}
}

static void SetSourceSpeciesBaseStats(u16 species, u8 hp, u8 attack, u8 defense,
	u8 spAttack, u8 spDefense, u8 speed, u8 type1, u8 type2)
{
	testBaseStats[species].baseHP = hp;
	testBaseStats[species].baseAttack = attack;
	testBaseStats[species].baseDefense = defense;
	testBaseStats[species].baseSpAttack = spAttack;
	testBaseStats[species].baseSpDefense = spDefense;
	testBaseStats[species].baseSpeed = speed;
	testBaseStats[species].type1 = type1;
	testBaseStats[species].type2 = type2;
}

static u16 SourceWitnessHp(u8 base, u8 iv, u8 level)
{
	return ((2 * base + iv) * level) / 100 + level + 10;
}

static u16 SourceWitnessStat(u8 base, u8 iv, u8 level)
{
	/* Source CalculateMonStatsNew with 0 EV and a neutral nature. */
	return ((2 * base + iv) * level) / 100 + 5;
}

static u8 SourceTrainerIV(u16 trainerId)
{
	switch (trainerId)
	{
	case TRAINER_RIVAL_CERULEAN_SQUIRTLE: return 25; // CLASS_RIVAL
	case TRAINER_LEADER_BROCK: return 31; // CLASS_LEADER
	case TRAINER_CAMPER_LIAM: return 5; // CLASS_CAMPER
	case TRAINER_BUG_CATCHER_RICK: return 1; // CLASS_BUG_CATCHER
	default: assert(FALSE); return 0;
	}
}

static void ConfigureSourceWitness(u16 trainerId, enum TrainerAIProfile aiProfile,
	u16 trainerSpecies, u8 trainerLevel, u8 partyIndex,
	const u16 trainerMoves[MAX_MON_MOVES], u8 trainerType1, u8 trainerType2)
{
	static const u16 playerMoves[MAX_MON_MOVES] =
		{MOVE_TACKLE, MOVE_NONE, MOVE_NONE, MOVE_NONE};
	u8 i, trainerIV = SourceTrainerIV(trainerId);
	u16 trainerHp;
	const struct BaseStats* playerBase;
	const struct BaseStats* trainerBase;
	Reset();
	sRawTrainerAIProfile = aiProfile + 1;
	profile = GetTrainerAIProfileFromRaw();
	assert(profile == aiProfile);
	gTrainerBattleOpponent_A = trainerId;
	gBattleTypeFlags = BATTLE_TYPE_TRAINER;
	gActiveBattler = gBankAttacker = 1;
	gBankTarget = 0;
	gBattlerPartyIndexes[1] = partyIndex;
	SetSourceSpeciesBaseStats(SPECIES_CHARMANDER, 39, 52, 43, 60, 50, 65,
		TYPE_FIRE, TYPE_FIRE);
	SetSourceSpeciesBaseStats(SPECIES_SQUIRTLE, 44, 48, 65, 50, 64, 43,
		TYPE_WATER, TYPE_WATER);
	SetSourceSpeciesBaseStats(SPECIES_ONIX, 35, 45, 160, 30, 45, 70,
		TYPE_ROCK, TYPE_GROUND);
	SetSourceSpeciesBaseStats(SPECIES_SANDSHREW, 50, 75, 85, 20, 30, 40,
		TYPE_GROUND, TYPE_GROUND);
	SetSourceSpeciesBaseStats(SPECIES_WEEDLE, 40, 35, 30, 20, 20, 50,
		TYPE_BUG, TYPE_POISON);
	playerBase = &testBaseStats[SPECIES_CHARMANDER];
	trainerBase = &testBaseStats[trainerSpecies];
	trainerHp = SourceWitnessHp(trainerBase->baseHP, trainerIV, trainerLevel);
	SetWitnessMon(0, SPECIES_CHARMANDER, 15,
		SourceWitnessHp(playerBase->baseHP, 31, 15),
		SourceWitnessStat(playerBase->baseAttack, 31, 15),
		SourceWitnessStat(playerBase->baseDefense, 31, 15),
		SourceWitnessStat(playerBase->baseSpAttack, 31, 15),
		SourceWitnessStat(playerBase->baseSpDefense, 31, 15),
		SourceWitnessStat(playerBase->baseSpeed, 31, 15),
		TYPE_FIRE, TYPE_FIRE, playerMoves);
	SetWitnessMon(1, trainerSpecies, trainerLevel, trainerHp,
		SourceWitnessStat(trainerBase->baseAttack, trainerIV, trainerLevel),
		SourceWitnessStat(trainerBase->baseDefense, trainerIV, trainerLevel),
		SourceWitnessStat(trainerBase->baseSpAttack, trainerIV, trainerLevel),
		SourceWitnessStat(trainerBase->baseSpDefense, trainerIV, trainerLevel),
		SourceWitnessStat(trainerBase->baseSpeed, trainerIV, trainerLevel),
		trainerType1, trainerType2, trainerMoves);
	for (i = 0; i < MAX_MON_MOVES; ++i)
		memset(&gEnemyParty[i], 0, sizeof(gEnemyParty[i]));
	gEnemyParty[0].species = trainerSpecies;
	gEnemyParty[0].hp = gEnemyParty[0].maxHP = trainerHp;
	gEnemyParty[1].species = trainerSpecies;
	gEnemyParty[1].hp = gEnemyParty[1].maxHP = trainerHp;
	resources.ai = &sThinking;
	resources.AIScriptsStack = &sAIScriptsStack;
	resources.battleHistory = (void *)&history;
	memset(&sThinking, 0, sizeof(sThinking));
	memset(&sAIScriptsStack, 0, sizeof(sAIScriptsStack));
	SetControllerMoves(gActiveBattler);
}

static int TraceCurrentPolicy(const char *name, u8 *selectedId)
{
	u8 i;
	int rc;
	struct ChooseMoveStruct *moveInfo = (struct ChooseMoveStruct *)&gBattleBufferA[1][4];
	printf("  actors active=%u target=%u own species=%u level=%u hp=%u/%u stats=%u,%u,%u,%u,%u foe species=%u level=%u hp=%u/%u stats=%u,%u,%u,%u,%u raid=%u inverse=%u frontier=%u\n",
		gActiveBattler, gBankTarget, gBattleMons[1].species, gBattleMons[1].level,
		gBattleMons[1].hp, gBattleMons[1].maxHP, gBattleMons[1].attack,
		gBattleMons[1].defense, gBattleMons[1].spAttack, gBattleMons[1].spDefense,
		gBattleMons[1].speed, gBattleMons[0].species, gBattleMons[0].level,
		gBattleMons[0].hp, gBattleMons[0].maxHP, gBattleMons[0].attack,
		gBattleMons[0].defense, gBattleMons[0].spAttack, gBattleMons[0].spDefense,
		gBattleMons[0].speed,
		IsRaidBattle(), IsInverseBattle(), IsFrontierTrainerId(gTrainerBattleOpponent_A));
	printf("  moves gBattleMons=[%u,%u,%u,%u] controller=[%u,%u,%u,%u]\n",
		gBattleMons[1].moves[0], gBattleMons[1].moves[1],
		gBattleMons[1].moves[2], gBattleMons[1].moves[3],
		moveInfo->moves[0], moveInfo->moves[1], moveInfo->moves[2], moveInfo->moves[3]);
	if (profile == TRAINER_AI_PROFILE_STANDARD)
	{
		struct StandardPolicyObservation observation;
		struct StandardPolicyMemory memory;
		struct StandardPolicyResult result;
		u32 seed = StandardAI_GetPolicySeed(1);
		StandardAI_BuildObservation(1, FALSE, &observation);
		StandardAI_LoadMemory(1, &memory);
		rc = StandardPolicyChoose(&observation, &memory, &seed, &result);
		printf("%s route raw=%u resolved=%u standard_supported=%u ironmon_supported=%u flags=%08X bank=%u target=%u observations=%u policy_rc=%d selected_id=%u pending=%u rng=%08X->%08X draws=%u\n",
			name, sRawTrainerAIProfile, GetTrainerAIProfile(), StandardAI_IsSupportedBattle(),
			IronmonAI_IsSupportedBattle(), gBattleTypeFlags, gBankAttacker,
			gBankTarget, observation.count, rc, result.selected_id,
			gNewBS->ai.standardPendingValid[1], StandardAI_GetPolicySeed(1), seed,
			result.policy_rng_draws);
		for (i = 0; i < observation.count; ++i)
		{
			const struct StandardPolicyCandidate *c = &observation.candidates[i];
			const struct StandardPolicyDiagnostic *d = &result.diagnostics[i];
			struct StandardAIDamageClassification mechanics = {0};
			if (c->kind == STANDARD_POLICY_MOVE && c->id < MAX_MON_MOVES
				&& gBattleMons[1].moves[c->id] != MOVE_NONE)
				mechanics = StandardAI_ClassifyDamage(gBattleMons[1].moves[c->id]);
			printf("  candidate id=%u kind=%u legal=%u slot=%u move=%u class=%u reason=%u damage=%u utility=%d floor=%u admission=%u near=%u productive=%u unknown=%u no_effect=%u net_faints=%d foe_hp=%d own_hp=%d future=%d entry=%d repeat=%u uncertainty=%u\n",
				c->id, c->kind, c->legal, c->id < MAX_MON_MOVES ? c->id : 255,
				c->id < MAX_MON_MOVES ? gBattleMons[1].moves[c->id] : MOVE_NONE,
				mechanics.mechanics_class, mechanics.reason, c->expected_damage,
				d->utility_total, d->floor_reasons,
				d->admission_reasons, d->near_best, c->productive,
				c->unknown_potentially_productive, c->known_no_effect,
				c->net_faints, c->opponent_hp_fraction_lost, c->own_hp_fraction_lost,
				c->immediate_future_gain, c->entry_cost, c->repeat_cost,
				c->uncertainty_cost);
		}
		*selectedId = result.selected_id;
	}
	else
	{
		struct StandardPolicyMemory memory;
		struct IronmonPolicyObservation observation;
		struct IronmonPolicyResult result;
		u32 seed = IRONMON_AI_DEFAULT_SEED ^ ((u32)gTrainerBattleOpponent_A << 8) ^ 1;
		IronmonAI_BuildObservation(1, FALSE, &observation);
		StandardAI_LoadMemory(1, &memory);
		rc = IronmonPolicyChoose(&observation, &memory, &seed, &result);
		printf("%s route raw=%u resolved=%u standard_supported=%u ironmon_supported=%u flags=%08X bank=%u target=%u observations=%u responses=%u policy_rc=%d selected_id=%u pending=%u rng=%08X->%08X draws=%u\n",
			name, sRawTrainerAIProfile, GetTrainerAIProfile(), StandardAI_IsSupportedBattle(),
			IronmonAI_IsSupportedBattle(), gBattleTypeFlags, gBankAttacker,
			gBankTarget, observation.count, observation.response_count, rc,
			result.selected_id, gNewBS->ai.standardPendingValid[1],
			IRONMON_AI_DEFAULT_SEED ^ ((u32)gTrainerBattleOpponent_A << 8) ^ 1,
			seed, result.selection_draws);
		for (i = 0; i < observation.response_count; ++i)
			printf("  response id=%u weight=%u\n", observation.responses[i].id,
				observation.responses[i].weight);
		for (i = 0; i < observation.count; ++i)
		{
			const struct IronmonPolicyCandidate *c = &observation.candidates[i];
			const struct IronmonPolicyDiagnostic *d = &result.diagnostics[i];
			u8 branch;
			struct StandardAIDamageClassification mechanics = {0};
			if (c->floor.kind == STANDARD_POLICY_MOVE && c->floor.id < MAX_MON_MOVES
				&& gBattleMons[1].moves[c->floor.id] != MOVE_NONE)
				mechanics = StandardAI_ClassifyDamage(gBattleMons[1].moves[c->floor.id]);
			printf("  candidate id=%u kind=%u legal=%u slot=%u move=%u class=%u reason=%u damage=%u utility=%d floor=%u admission=%u near=%u admitted=%u no_effect=%u floor_future=%d net_faints=%d foe_hp=%d own_hp=%d future=%d entry=%d repeat=%u\n",
				c->floor.id, c->floor.kind, c->floor.legal,
				c->floor.id < MAX_MON_MOVES ? c->floor.id : 255,
				c->floor.id < MAX_MON_MOVES ? gBattleMons[1].moves[c->floor.id] : MOVE_NONE,
				mechanics.mechanics_class, mechanics.reason,
				c->floor.expected_damage, d->utility_total, d->reasons,
				d->reasons, d->near_best, d->ironmon_eligible,
				c->floor.known_no_effect, c->floor.immediate_future_gain,
				c->floor.net_faints, c->floor.opponent_hp_fraction_lost,
				c->floor.own_hp_fraction_lost,
				c->responses[0].future_gain_undiscounted,
				c->responses[0].entry_cost, c->floor.repeat_cost);
			for (branch = 0; branch < c->response_count; ++branch)
				printf("    branch response=%u net_faints=%d foe_hp=%d own_hp=%d future=%d entry=%d\n",
					c->responses[branch].response_id, c->responses[branch].net_faints,
					c->responses[branch].opponent_hp_fraction_lost,
					c->responses[branch].own_hp_fraction_lost,
					c->responses[branch].future_gain_undiscounted,
					c->responses[branch].entry_cost);
		}
		*selectedId = result.selected_id;
	}
	return rc;
}

static void RunSourceWitness(const char *name, u16 trainerId,
	enum TrainerAIProfile aiProfile, u16 species, u8 level, u8 partyIndex,
	const u16 moves[MAX_MON_MOVES], u8 type1, u8 type2)
{
	u8 selectedId;
	int rc;
	struct ChooseMoveStruct *moveInfo =
		(struct ChooseMoveStruct *)&gBattleBufferA[1][4];
	ConfigureSourceWitness(trainerId, aiProfile, species, level, partyIndex,
		moves, type1, type2);
	assert(StandardAI_IsSupportedBattle() == (aiProfile == TRAINER_AI_PROFILE_STANDARD));
	assert(IronmonAI_IsSupportedBattle() == (aiProfile == TRAINER_AI_PROFILE_IRONMON_SMART));
	rc = TraceCurrentPolicy(name, &selectedId);
	assert(rc == 0);
	assert(selectedId < MAX_MON_MOVES);
	assert(gBattleMons[1].moves[selectedId] != MOVE_NONE);
	assert(!gNewBS->ai.standardPendingValid[1]);
	RunHandoff(selectedId, moves[selectedId],
		(trainerId == TRAINER_RIVAL_CERULEAN_SQUIRTLE
		|| trainerId == TRAINER_LEADER_BROCK)
			? (aiProfile == TRAINER_AI_PROFILE_STANDARD ? 1 : 2) : 0);
	assert(!gNewBS->ai.standardPendingValid[1]);
	assert(gBattleStruct->chosenMovePositions[1] == selectedId);
	assert(gChosenMovesByBanks[1] == moves[selectedId]);
	assert(!OpponentAI_TestLastBoundedFallback);
	assert(sThinking.aiFlags == 0);
	if (aiProfile == TRAINER_AI_PROFILE_STANDARD)
	{
		assert(StandardAI_TestLastPolicyRc == STANDARD_POLICY_OK);
		assert(StandardAI_TestLastFailureReason == AI_ADAPTER_FAILURE_NONE);
		assert(StandardAI_TestLastSelectedId == selectedId);
		printf("  production adapter rc=%d failure=%u selected_id=%u pending_before=0 pending_after=0 returned=%u emitted=%u final_move=%u target=%u PASS\n",
			StandardAI_TestLastPolicyRc, StandardAI_TestLastFailureReason,
			StandardAI_TestLastSelectedId, gBattleStruct->chosenMovePositions[1],
			sEmittedPosition, moveInfo->moves[sEmittedPosition], sEmittedTarget);
	}
	else
	{
		assert(IronmonAI_TestLastPolicyRc == IRONMON_POLICY_OK);
		assert(IronmonAI_TestLastFailureReason == AI_ADAPTER_FAILURE_NONE);
		assert(IronmonAI_TestLastSelectedId == selectedId);
		printf("  production adapter rc=%d failure=%u selected_id=%u pending_before=0 pending_after=0 returned=%u emitted=%u final_move=%u target=%u PASS\n",
			IronmonAI_TestLastPolicyRc, IronmonAI_TestLastFailureReason,
			IronmonAI_TestLastSelectedId, gBattleStruct->chosenMovePositions[1],
			sEmittedPosition, moveInfo->moves[sEmittedPosition], sEmittedTarget);
	}
}

static void ProfileDispatchAndLegacyIsolation(void)
{
	unsigned raw;
	for (raw = 0; raw <= TRAINER_AI_PROFILE_IRONMON_SMART + 1; ++raw)
	{
		sRawTrainerAIProfile = raw;
		profile = GetTrainerAIProfileFromRaw();
		assert(profile == (raw == 0 ? TRAINER_AI_PROFILE_NORMAL : raw - 1));
	}
	ConfigureSourceWitness(TRAINER_RIVAL_CERULEAN_SQUIRTLE,
		TRAINER_AI_PROFILE_STANDARD, SPECIES_SQUIRTLE, 18, 3,
		sParty_TrainerRivalCeruleanSquirtle[3].moves, TYPE_WATER, TYPE_WATER);
	sRawTrainerAIProfile = TRAINER_AI_PROFILE_SMART_AI + 1;
	profile = GetTrainerAIProfileFromRaw();
	assert(profile == TRAINER_AI_PROFILE_SMART_AI);
	assert(!StandardAI_IsSupportedBattle() && !IronmonAI_IsSupportedBattle());
	memset(&sThinking, 0, sizeof(sThinking));
	memset(&sAIScriptsStack, 0, sizeof(sAIScriptsStack));
	BattleAI_SetupAIData(0xF);
	assert(sThinking.aiFlags & AI_SCRIPT_CHECK_GOOD_MOVE);
	assert(sThinking.aiFlags & AI_SCRIPT_SEMI_SMART);
	assert(sThinking.aiFlags & AI_SCRIPT_CHECK_BAD_MOVE);
	sEmitCount = sOpponentCompleted = 0;
	OpponentHandleChooseMove();
	assert(sEmitCount == 0 && sOpponentCompleted == 0);
	puts("profile raw dispatch: Standard=7, Ironmon Smart=8; Legacy Smart=6 remains legacy PASS");
}

static void ExactPolicyReturnCodes(void)
{
	struct StandardPolicyObservation standard;
	struct StandardPolicyMemory memory;
	struct StandardPolicyResult standardResult;
	struct IronmonPolicyObservation ironmon;
	struct IronmonPolicyResult ironmonResult;
	struct IronmonPolicyResponse responses[5];
	uint16_t duplicateMoves[4] = {MOVE_TACKLE, MOVE_TACKLE, MOVE_NONE, MOVE_NONE};
	uint16_t duplicateCounts[4] = {0, 0, 0, 0};
	uint8_t responseCount = 0;
	u32 standardSeed = 1, ironmonSeed = 1;
	u8 i;
ConfigureSourceWitness(TRAINER_LEADER_BROCK, TRAINER_AI_PROFILE_STANDARD,
		SPECIES_ONIX, 14, 1, sParty_TrainerLeaderBrock[1].moves,
		TYPE_ROCK, TYPE_GROUND);
	StandardAI_BuildObservation(1, TRUE, &standard);
	StandardAI_LoadMemory(1, &memory);
	assert(StandardPolicyChoose(&standard, &memory, &standardSeed, &standardResult)
		== STANDARD_POLICY_OK);
	standardSeed = 1;
	{
		struct StandardPolicyObservation invalid = standard;
		invalid.candidates[0].immediate_future_gain = 41;
		assert(StandardPolicyChoose(&invalid, &memory, &standardSeed, &standardResult)
			== STANDARD_POLICY_INVALID_CANDIDATE);
	}
	standardSeed = 1;
	{
		struct StandardPolicyObservation noLegal = standard;
		for (i = 0; i < noLegal.count; ++i) noLegal.candidates[i].legal = FALSE;
		assert(StandardPolicyChoose(&noLegal, &memory, &standardSeed, &standardResult)
			== STANDARD_POLICY_NO_ADMITTED_ACTION);
	}
	standardSeed = 1;
	assert(StandardPolicyChoose(NULL, &memory, &standardSeed, &standardResult)
		== STANDARD_POLICY_ERROR);

	ConfigureSourceWitness(TRAINER_LEADER_BROCK, TRAINER_AI_PROFILE_IRONMON_SMART,
		SPECIES_ONIX, 14, 1, sParty_TrainerLeaderBrock[1].moves,
		TYPE_ROCK, TYPE_GROUND);
	IronmonAI_BuildObservation(1, TRUE, &ironmon);
	StandardAI_LoadMemory(1, &memory);
	assert(IronmonPolicyChoose(&ironmon, &memory, &ironmonSeed, &ironmonResult)
		== IRONMON_POLICY_OK);
	ironmonSeed = 1;
	{
		struct IronmonPolicyObservation invalid = ironmon;
		invalid.response_count = 0;
		assert(IronmonPolicyChoose(&invalid, &memory, &ironmonSeed, &ironmonResult)
			== IRONMON_POLICY_ERROR);
	}
	ironmonSeed = 1;
	{
		struct IronmonPolicyObservation noLegal = ironmon;
		for (i = 0; i < noLegal.count; ++i) noLegal.candidates[i].floor.legal = FALSE;
		assert(IronmonPolicyChoose(&noLegal, &memory, &ironmonSeed, &ironmonResult)
			== IRONMON_POLICY_NO_ADMITTED_ACTION);
	}
	assert(IronmonPolicyBuildResponses(duplicateMoves, duplicateCounts, 0,
		responses, &responseCount) == IRONMON_POLICY_INVALID_CANDIDATE);
	puts("exact policy rc: Standard Choose 0/-1/-2/-3; Ironmon Choose 0/-1/-2; Ironmon response builder -3 PASS");
}

static void RunErrorFallback(const char *name, u16 trainerId,
	enum TrainerAIProfile aiProfile, u16 species, u8 level, u8 partyIndex,
	const u16 moves[MAX_MON_MOVES], u8 type1, u8 type2,
	int policyRcOverride, u8 selectedIdOverride, u8 pendingFault,
	u8 requireNonzero)
{
	struct ChooseMoveStruct *moveInfo =
		(struct ChooseMoveStruct *)&gBattleBufferA[1][4];
	u8 emittedSlot;
	ConfigureSourceWitness(trainerId, aiProfile, species, level, partyIndex,
		moves, type1, type2);
	StandardAI_TestPolicyRcOverride = -2147483647 - 1;
	StandardAI_TestSelectedIdOverride = 0xFF;
	IronmonAI_TestPolicyRcOverride = -2147483647 - 1;
	IronmonAI_TestSelectedIdOverride = 0xFF;
	if (aiProfile == TRAINER_AI_PROFILE_STANDARD)
	{
		StandardAI_TestPolicyRcOverride = policyRcOverride;
		StandardAI_TestSelectedIdOverride = selectedIdOverride;
	}
	else
	{
		IronmonAI_TestPolicyRcOverride = policyRcOverride;
		IronmonAI_TestSelectedIdOverride = selectedIdOverride;
	}
	if (pendingFault)
	{
		gNewBS->ai.standardPendingValid[1] = TRUE;
		gNewBS->ai.standardPendingKind[1] = pendingFault == 1
			? STANDARD_POLICY_MOVE : STANDARD_POLICY_SWITCH;
		gNewBS->ai.standardPendingAction[1] = 0xFF;
	}
	sEmitCount = sOpponentCompleted = 0;
	OpponentHandleChooseMove();
	assert(sEmitCount == 1 && sOpponentCompleted == 1);
	emittedSlot = sEmittedPosition;
	assert(emittedSlot < MAX_MON_MOVES);
	assert(!requireNonzero || emittedSlot != 0);
	assert(moveInfo->moves[emittedSlot] == gBattleMons[1].moves[emittedSlot]);
	assert(moveInfo->moves[emittedSlot] == gChosenMovesByBanks[1]);
	assert(gBattleStruct->chosenMovePositions[1] == emittedSlot);
	assert(OpponentAI_TestLastBoundedFallback);
	assert(sThinking.aiFlags == 0);
	if (pendingFault)
	{
		if (aiProfile == TRAINER_AI_PROFILE_STANDARD)
			assert(StandardAI_TestLastFailureReason == AI_ADAPTER_FAILURE_PENDING_STATE);
		else
			assert(IronmonAI_TestLastFailureReason == AI_ADAPTER_FAILURE_PENDING_STATE);
	}
	else if (selectedIdOverride != 0xFF)
	{
		if (aiProfile == TRAINER_AI_PROFILE_STANDARD)
			assert(StandardAI_TestLastFailureReason == AI_ADAPTER_FAILURE_SELECTED_ID_LOOKUP);
		else
			assert(IronmonAI_TestLastFailureReason == AI_ADAPTER_FAILURE_SELECTED_ID_LOOKUP);
	}
	else if (aiProfile == TRAINER_AI_PROFILE_STANDARD)
	{
		assert(StandardAI_TestLastPolicyRc == policyRcOverride);
		assert(StandardAI_TestLastFailureReason == (policyRcOverride == STANDARD_POLICY_NO_ADMITTED_ACTION
			? AI_ADAPTER_FAILURE_NO_ADMITTED_ACTION : AI_ADAPTER_FAILURE_POLICY_ERROR));
	}
	else
	{
		assert(IronmonAI_TestLastPolicyRc == policyRcOverride);
		assert(IronmonAI_TestLastFailureReason == (policyRcOverride == IRONMON_POLICY_NO_ADMITTED_ACTION
			? AI_ADAPTER_FAILURE_NO_ADMITTED_ACTION : AI_ADAPTER_FAILURE_POLICY_ERROR));
	}
	printf("%s fallback: rc=%d selected_override=%u pending_fault=%u failure=%u returned=%u emitted=%u move=%u bounded=1 controller_parity=PASS\n",
		name, policyRcOverride, selectedIdOverride, pendingFault,
		aiProfile == TRAINER_AI_PROFILE_STANDARD
			? StandardAI_TestLastFailureReason : IronmonAI_TestLastFailureReason,
		emittedSlot, sEmittedPosition, moveInfo->moves[emittedSlot]);
	StandardAI_TestPolicyRcOverride = -2147483647 - 1;
	StandardAI_TestSelectedIdOverride = 0xFF;
	IronmonAI_TestPolicyRcOverride = -2147483647 - 1;
	IronmonAI_TestSelectedIdOverride = 0xFF;
}

static void FailureFallbackWitnesses(void)
{
	RunErrorFallback("Rival Standard policy validation error", TRAINER_RIVAL_CERULEAN_SQUIRTLE,
		TRAINER_AI_PROFILE_STANDARD, SPECIES_SQUIRTLE, 18, 3,
		sParty_TrainerRivalCeruleanSquirtle[3].moves, TYPE_WATER, TYPE_WATER,
		STANDARD_POLICY_ERROR, 0xFF, 0, TRUE);
	RunErrorFallback("Brock Standard no admitted action", TRAINER_LEADER_BROCK,
		TRAINER_AI_PROFILE_STANDARD, SPECIES_ONIX, 14, 1,
		sParty_TrainerLeaderBrock[1].moves, TYPE_ROCK, TYPE_GROUND,
		STANDARD_POLICY_NO_ADMITTED_ACTION, 0xFF, 0, TRUE);
	RunErrorFallback("Rival Standard selected-ID lookup failure", TRAINER_RIVAL_CERULEAN_SQUIRTLE,
		TRAINER_AI_PROFILE_STANDARD, SPECIES_SQUIRTLE, 18, 3,
		sParty_TrainerRivalCeruleanSquirtle[3].moves, TYPE_WATER, TYPE_WATER,
		STANDARD_POLICY_OK, 0xFE, 0, TRUE);
	RunErrorFallback("Sandshrew invalid pending action", TRAINER_CAMPER_LIAM,
		TRAINER_AI_PROFILE_STANDARD, SPECIES_SANDSHREW, 11, 1,
		sParty_TrainerCamperLiam[1].moves, TYPE_GROUND, TYPE_GROUND,
		0, 0xFF, 1, FALSE);
	RunErrorFallback("Brock Ironmon policy validation error", TRAINER_LEADER_BROCK,
		TRAINER_AI_PROFILE_IRONMON_SMART, SPECIES_ONIX, 14, 1,
		sParty_TrainerLeaderBrock[1].moves, TYPE_ROCK, TYPE_GROUND,
		IRONMON_POLICY_ERROR, 0xFF, 0, TRUE);
}

int main(void)
{
	static const u16 weedleMoves[MAX_MON_MOVES] = {
		MOVE_POISONSTING, MOVE_STRINGSHOT, MOVE_NONE, MOVE_NONE};
	const enum TrainerAIProfile profiles[] = {
		TRAINER_AI_PROFILE_STANDARD, TRAINER_AI_PROFILE_IRONMON_SMART};
	unsigned p;
	setbuf(stdout, NULL);
	ProfileDispatchAndLegacyIsolation();
	ExactPolicyReturnCodes();
	FailureFallbackWitnesses();
	for (p = 0; p < ARRAY_COUNT(profiles); ++p)
	{
		RunSourceWitness("Rival/Cerulean Squirtle vs Charmander", TRAINER_RIVAL_CERULEAN_SQUIRTLE,
			profiles[p], SPECIES_SQUIRTLE, 18, 3, sParty_TrainerRivalCeruleanSquirtle[3].moves,
			TYPE_WATER, TYPE_WATER);
		RunSourceWitness("Brock/Onix", TRAINER_LEADER_BROCK, profiles[p], SPECIES_ONIX,
			14, 1, sParty_TrainerLeaderBrock[1].moves, TYPE_ROCK, TYPE_GROUND);
		RunSourceWitness("Camper Liam/Sandshrew", TRAINER_CAMPER_LIAM, profiles[p],
			SPECIES_SANDSHREW, 11, 1, sParty_TrainerCamperLiam[1].moves,
			TYPE_GROUND, TYPE_GROUND);
		RunSourceWitness("Bug Catcher Rick/Weedle", TRAINER_BUG_CATCHER_RICK,
			profiles[p], SPECIES_WEEDLE, 6, 0, weedleMoves,
			TYPE_BUG, TYPE_POISON);
	}
	puts("production controller/fallback witnesses: PASS");
	return 0;
}
