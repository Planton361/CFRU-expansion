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
#include "../../include/new/battle_strings.h"
#include "../../include/new/learn_move.h"
#include "../../include/battle_string_ids.h"
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
extern bool8 StandardAI_GetPublicTypes(u8 foe, u8 types[3]);

u8 gBattleBufferA[MAX_BATTLERS_COUNT][0x200];
struct BattleResults gBattleResults;
u8 ControllerHost_ActionCount, ControllerHost_ActionCode;
u16 ControllerHost_ActionValue;
static u8 sEmitCount;
static u8 sEmittedPosition;
static u8 sEmittedTarget;
static u8 sOpponentCompleted;
static u16 sRawTrainerAIProfile;
static u8 sMoveLimitationMask;
static struct AI_ThinkingStruct sThinking;
static struct BattleScriptsStack sAIScriptsStack;
static u16 sLastPreparedString;
static u8 sLastPreparedBank;
static u8 sPreparedStringCount;
static struct BoxPokemon sInitialMovesetBox;
static u16 sInitialMovesetSpecies;
static u8 sInitialMovesetLevel;
static u16 sGeneratedInitialMoves[MAX_MON_MOVES];
static u8 sGeneratedInitialMoveCount;

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
{ (void)bank; (void)move; (void)flags; return sMoveLimitationMask; }
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
	[TRAINER_RIVAL_CERULEAN_SQUIRTLE] = {.aiFlags = AI_SCRIPT_CHECK_BAD_MOVE},
	[TRAINER_RIVAL_OAKS_LAB_SQUIRTLE] = {
		.aiFlags = AI_SCRIPT_CHECK_BAD_MOVE | AI_SCRIPT_CHECK_GOOD_MOVE | AI_SCRIPT_SEMI_SMART
	}
};
const struct SpecialSpeciesFlags gSpecialSpeciesFlags[NUM_SPECIES] = {{0}};

struct Pokemon *GetIllusionPartyData(u8 bank)
{
	assert(bank < MAX_BATTLERS_COUNT);
	return SIDE(bank) == B_SIDE_PLAYER
		? &gPlayerParty[gBattlerPartyIndexes[bank]]
		: &gEnemyParty[gBattlerPartyIndexes[bank]];
}

u32 GetMonData(const struct Pokemon *mon, s32 field, const void *data)
{
	(void)data;
	assert(field == MON_DATA_SPECIES);
	return mon->species;
}

void EmitPrintString(u8 bufferId, u16 stringId)
{
	assert(bufferId == 0);
	sLastPreparedString = stringId;
	++sPreparedStringCount;
}

void MarkBufferBankForExecution(u8 bank)
{
	sLastPreparedBank = bank;
}

u32 GetBoxMonData(struct BoxPokemon *boxMon, s32 field, u8 *data)
{
	(void)data;
	assert(boxMon == &sInitialMovesetBox);
	if (field == MON_DATA_SPECIES)
		return sInitialMovesetSpecies;
	if (field >= MON_DATA_MOVE1 && field <= MON_DATA_MOVE4)
		return sGeneratedInitialMoves[field - MON_DATA_MOVE1];
	if (field >= MON_DATA_PP1 && field <= MON_DATA_PP4)
		return 0;
	assert(FALSE);
	return 0;
}

void SetBoxMonData(struct BoxPokemon *boxMon, s32 field, const void *data)
{
	assert(boxMon == &sInitialMovesetBox);
	if (field >= MON_DATA_MOVE1 && field <= MON_DATA_MOVE4)
	{
		sGeneratedInitialMoves[field - MON_DATA_MOVE1] = *(const u16 *)data;
		++sGeneratedInitialMoveCount;
		return;
	}
	if (field >= MON_DATA_PP1 && field <= MON_DATA_PP4)
		return;
	assert(FALSE);
}

u8 GetLevelFromBoxMonExp(struct BoxPokemon *boxMon)
{
	assert(boxMon == &sInitialMovesetBox);
	return sInitialMovesetLevel;
}

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
	case TRAINER_RIVAL_OAKS_LAB_SQUIRTLE: return 25; // CLASS_RIVAL
	case TRAINER_LEADER_BROCK: return 31; // CLASS_LEADER
	case TRAINER_CAMPER_LIAM: return 5; // CLASS_CAMPER
	case TRAINER_BUG_CATCHER_RICK: return 1; // CLASS_BUG_CATCHER
	default: assert(FALSE); return 0;
	}
}

static void DeriveSourceInitialMoveset(u16 species, u8 level,
	u16 moves[MAX_MON_MOVES])
{
	u8 i;
	sInitialMovesetSpecies = species;
	sInitialMovesetLevel = level;
	sGeneratedInitialMoveCount = 0;
	memset(sGeneratedInitialMoves, 0, sizeof(sGeneratedInitialMoves));
	GiveBoxMonInitialMoveset(&sInitialMovesetBox);
	for (i = 0; i < MAX_MON_MOVES; ++i)
		moves[i] = i < sGeneratedInitialMoveCount
			? sGeneratedInitialMoves[i] : MOVE_NONE;
}

/* BufferStringBattle is too engine-coupled for a useful host translation
 * unit. This bounded path calls the production PrepareStringBattle, then the
 * exact exported helper invoked by its retained STRINGID_INTROSENDOUT case. */
static void RunIntroSendoutReveal(u8 bank)
{
	PrepareStringBattle(STRINGID_INTROSENDOUT, bank);
	assert(gActiveBattler == bank);
	assert(sLastPreparedString == STRINGID_INTROSENDOUT);
	assert(sLastPreparedBank == bank);
	StandardAI_RecordPublicSendoutSpecies(gActiveBattler);
}

static void RunPublicRevealLifecycle(void)
{
	/* BattleIntroPrintOpponentSendsOut precedes BattleIntroPrintPlayerSendsOut. */
	RunIntroSendoutReveal(1);
	RunIntroSendoutReveal(0);
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
	sMoveLimitationMask = 0;
	sPreparedStringCount = 0;
	for (i = 0; i < MAX_BATTLERS_COUNT; ++i)
		newBattle.ai.standardDisplayedSpecies[i] = SPECIES_NONE;
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
	memset(gEnemyParty, 0, sizeof(gEnemyParty));
	memset(gPlayerParty, 0, sizeof(gPlayerParty));
	gPlayerParty[0].species = SPECIES_CHARMANDER;
	gEnemyParty[partyIndex].species = trainerSpecies;
	gEnemyParty[partyIndex].hp = gEnemyParty[partyIndex].maxHP = trainerHp;
	for (i = 0; i < MAX_MON_MOVES; ++i)
	{
		gEnemyParty[partyIndex].moves[i] = trainerMoves[i];
		gEnemyParty[partyIndex].pp[i] = trainerMoves[i] == MOVE_NONE ? 0 : 10;
	}
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
	u8 publicTypes[3] = {TYPE_NORMAL, TYPE_NORMAL, TYPE_NORMAL};
	bool8 publicTypesAvailable = StandardAI_GetPublicTypes(0, publicTypes);
	int rc;
	struct ChooseMoveStruct *moveInfo = (struct ChooseMoveStruct *)&gBattleBufferA[1][4];
	printf("  public player species bank0=%u types_available=%u types=[%u,%u,%u]; actors active=%u target=%u own species=%u level=%u hp=%u/%u stats=%u,%u,%u,%u,%u foe species=%u level=%u hp=%u/%u stats=%u,%u,%u,%u,%u raid=%u inverse=%u frontier=%u\n",
		newBattle.ai.standardDisplayedSpecies[0], publicTypesAvailable,
		publicTypes[0], publicTypes[1], publicTypes[2],
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
			printf("  candidate id=%u kind=%u legal=%u slot=%u move=%u class=%u reason=%u damage=%u utility=%d floor=%u admission=%u near=%u admitted=%u productive=%u unknown_potentially_productive=%u no_effect=%u floor_future=%d net_faints=%d foe_hp=%d own_hp=%d future=%d entry=%d repeat=%u\n",
				c->floor.id, c->floor.kind, c->floor.legal,
				c->floor.id < MAX_MON_MOVES ? c->floor.id : 255,
				c->floor.id < MAX_MON_MOVES ? gBattleMons[1].moves[c->floor.id] : MOVE_NONE,
				mechanics.mechanics_class, mechanics.reason,
				c->floor.expected_damage, d->utility_total, d->reasons,
				d->reasons, d->near_best, d->ironmon_eligible,
				c->floor.productive, c->floor.unknown_potentially_productive,
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
	RunPublicRevealLifecycle();
	gActiveBattler = gBankAttacker = 1;
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
	RunPublicRevealLifecycle();
	gActiveBattler = gBankAttacker = 1;
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
	RunPublicRevealLifecycle();
	gActiveBattler = gBankAttacker = 1;
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

static void OpeningOakLabWitness(enum TrainerAIProfile aiProfile, bool8 reveal,
	bool8 cappedDefense)
{
	static const u16 expectedTrainerMoves[MAX_MON_MOVES] = {
		MOVE_TACKLE, MOVE_TAILWHIP, MOVE_WATERGUN, MOVE_NONE
	};
	const struct TrainerMonNoItemDefaultMoves *oakMon =
		&sParty_TrainerRivalOaksLabSquirtle[0];
	const struct BaseStats *playerBase = &testBaseStats[SPECIES_CHARMANDER];
	u16 trainerMoves[MAX_MON_MOVES], playerMoves[MAX_MON_MOVES];
	u8 i;
	u8 selectedId;
	int rc;
	struct ChooseMoveStruct *moveInfo = (struct ChooseMoveStruct *)&gBattleBufferA[1][4];
	u8 publicTypes[3] = {TYPE_NORMAL, TYPE_NORMAL, TYPE_NORMAL};

	assert(oakMon->lvl == 5 && oakMon->species == SPECIES_SQUIRTLE);
	DeriveSourceInitialMoveset(oakMon->species, oakMon->lvl, trainerMoves);
	DeriveSourceInitialMoveset(SPECIES_CHARMANDER, 5, playerMoves);
	for (i = 0; i < MAX_MON_MOVES; ++i)
		assert(trainerMoves[i] == expectedTrainerMoves[i]);
	printf("Oak's Lab source moves: trainer=%u level=%u initial=[%u,%u,%u,%u]; player Charmander level=5 initial=[%u,%u,%u,%u]\n",
		oakMon->species, oakMon->lvl, trainerMoves[0], trainerMoves[1],
		trainerMoves[2], trainerMoves[3], playerMoves[0], playerMoves[1],
		playerMoves[2], playerMoves[3]);

	ConfigureSourceWitness(TRAINER_RIVAL_OAKS_LAB_SQUIRTLE, aiProfile,
		oakMon->species, oakMon->lvl, 0, trainerMoves,
		TYPE_WATER, TYPE_WATER);
	SetWitnessMon(0, SPECIES_CHARMANDER, 5,
		SourceWitnessHp(playerBase->baseHP, 31, 5),
		SourceWitnessStat(playerBase->baseAttack, 31, 5),
		SourceWitnessStat(playerBase->baseDefense, 31, 5),
		SourceWitnessStat(playerBase->baseSpAttack, 31, 5),
		SourceWitnessStat(playerBase->baseSpDefense, 31, 5),
		SourceWitnessStat(playerBase->baseSpeed, 31, 5),
		TYPE_FIRE, TYPE_FIRE, playerMoves);
	gPlayerParty[0].species = SPECIES_CHARMANDER;
	for (i = 0; i < MAX_MON_MOVES; ++i)
	{
		gPlayerParty[0].moves[i] = playerMoves[i];
		gPlayerParty[0].pp[i] = playerMoves[i] == MOVE_NONE ? 0 : 10;
	}
	SetControllerMoves(1);
	if (cappedDefense)
		gBattleMons[0].statStages[STAT_STAGE_DEF - 1] = STAT_STAGE_MIN;
	assert(gBattleMons[1].moves[0] == MOVE_TACKLE);
	assert(gBattleMons[1].moves[1] == MOVE_TAILWHIP);
	assert(gBattleMons[1].moves[2] == MOVE_WATERGUN);
	assert(gBattleMons[1].moves[3] == MOVE_NONE);
	assert(gNewBS->ai.standardDisplayedSpecies[0] == SPECIES_NONE);
	assert(!StandardAI_GetPublicTypes(0, publicTypes));
	printf("Oak's Lab %s profile=%u raw=%u pre-reveal displayed_species[0]=%u public_types_available=0\n",
		reveal ? "positive" : "negative/omitted-reveal",
		aiProfile, sRawTrainerAIProfile,
		gNewBS->ai.standardDisplayedSpecies[0]);

	if (reveal)
	{
		RunPublicRevealLifecycle();
		assert(sPreparedStringCount == 2);
		assert(gNewBS->ai.standardDisplayedSpecies[0] == SPECIES_CHARMANDER);
		assert(gNewBS->ai.standardDisplayedSpecies[1] == SPECIES_SQUIRTLE);
		assert(StandardAI_GetPublicTypes(0, publicTypes));
		printf("Oak's Lab public reveal after STRINGID_INTROSENDOUT producer: displayed_species[0]=%u types_available=1 types=[%u,%u,%u] strings=%u\n",
			gNewBS->ai.standardDisplayedSpecies[0], publicTypes[0],
			publicTypes[1], publicTypes[2], sPreparedStringCount);
	}
	else
	{
		assert(sPreparedStringCount == 0);
		assert(gNewBS->ai.standardDisplayedSpecies[0] == SPECIES_NONE);
		assert(!StandardAI_GetPublicTypes(0, publicTypes));
	}

	/* The battle intro has completed; the engine now asks the opponent bank. */
	gActiveBattler = gBankAttacker = 1;
	gBankTarget = 0;
	assert(gBattleTypeFlags == BATTLE_TYPE_TRAINER);
	assert(!IsRaidBattle() && !IsInverseBattle());
	assert(!IsFrontierTrainerId(TRAINER_RIVAL_OAKS_LAB_SQUIRTLE));
	assert(StandardAI_IsSupportedBattle() == (aiProfile == TRAINER_AI_PROFILE_STANDARD));
	assert(IronmonAI_IsSupportedBattle() == (aiProfile == TRAINER_AI_PROFILE_IRONMON_SMART));
	rc = TraceCurrentPolicy(reveal
		? "Oak's Lab Rival Squirtle L5, revealed"
		: "Oak's Lab Rival Squirtle L5, omitted reveal", &selectedId);
	assert(rc == 0);
	assert(selectedId < MAX_MON_MOVES);
	assert(gBattleMons[1].moves[selectedId] != MOVE_NONE);
	if (cappedDefense)
		assert(selectedId != 1 && gBattleMons[1].moves[selectedId] != MOVE_TAILWHIP);
	assert(!gNewBS->ai.standardPendingValid[1]);
	if (reveal && !cappedDefense)
	{
		assert(selectedId == 2 && gBattleMons[1].moves[selectedId] == MOVE_WATERGUN);
		assert(moveInfo->moves[2] == MOVE_WATERGUN);
	}
	RunHandoff(selectedId, gBattleMons[1].moves[selectedId], 0);
	assert(gNewBS->ai.standardPendingValid[1] == FALSE);
	assert(gBattleStruct->chosenMovePositions[1] == selectedId);
	assert(sEmittedPosition == selectedId);
	assert(moveInfo->moves[sEmittedPosition] == gBattleMons[1].moves[selectedId]);
	assert(gChosenMovesByBanks[1] == gBattleMons[1].moves[selectedId]);
	assert(!OpponentAI_TestLastBoundedFallback);
	assert(OpponentAI_DispatchTrace.rawProfile == sRawTrainerAIProfile);
	assert(OpponentAI_DispatchTrace.profile == aiProfile);
	assert(OpponentAI_DispatchTrace.trainerId == TRAINER_RIVAL_OAKS_LAB_SQUIRTLE);
	assert(OpponentAI_DispatchTrace.battleFlags == BATTLE_TYPE_TRAINER);
	assert(OpponentAI_DispatchTrace.exclusionBits == 0);
	assert(!OpponentAI_DispatchTrace.raid && !OpponentAI_DispatchTrace.inverse
		&& !OpponentAI_DispatchTrace.frontierTrainer);
	assert(OpponentAI_DispatchTrace.standardSupported ==
		(aiProfile == TRAINER_AI_PROFILE_STANDARD));
	assert(OpponentAI_DispatchTrace.ironmonSupported ==
		(aiProfile == TRAINER_AI_PROFILE_IRONMON_SMART));
	assert(OpponentAI_DispatchTrace.activeBattler == 1);
	assert(OpponentAI_DispatchTrace.bankAttacker == 1);
	assert(OpponentAI_DispatchTrace.bankTarget == 0);
	assert(OpponentAI_DispatchTrace.publicPlayerSpecies ==
		(reveal ? SPECIES_CHARMANDER : SPECIES_NONE));
	assert(OpponentAI_DispatchTrace.publicOpponentSpecies ==
		(reveal ? SPECIES_SQUIRTLE : SPECIES_NONE));
	assert(OpponentAI_DispatchTrace.defenseStage ==
		(cappedDefense ? STAT_STAGE_MIN : 6));
	for (i = 0; i < MAX_MON_MOVES; ++i)
		assert(OpponentAI_DispatchTrace.moves[i] == expectedTrainerMoves[i]);
	assert(OpponentAI_DispatchTrace.adapter ==
		(aiProfile == TRAINER_AI_PROFILE_STANDARD ? 1 : 2));
	assert(OpponentAI_DispatchTrace.policyRc == 0);
	assert(OpponentAI_DispatchTrace.selectedSlot == selectedId);
	assert(OpponentAI_DispatchTrace.selectedMove == gBattleMons[1].moves[selectedId]);
	assert(OpponentAI_DispatchTrace.emittedSlot == sEmittedPosition);
	assert(OpponentAI_DispatchTrace.emittedMove == moveInfo->moves[sEmittedPosition]);
	printf("Oak outer dispatch: raw=%u profile=%u trainer=%u flags=%08x exclusions=%08x support=%u/%u banks=%u/%u/%u public=%u/%u defense=%u moves=%u/%u/%u/%u adapter=%u rc=%d selected=%u/%u emitted=%u/%u\n",
		OpponentAI_DispatchTrace.rawProfile, OpponentAI_DispatchTrace.profile,
		OpponentAI_DispatchTrace.trainerId, OpponentAI_DispatchTrace.battleFlags,
		OpponentAI_DispatchTrace.exclusionBits, OpponentAI_DispatchTrace.standardSupported,
		OpponentAI_DispatchTrace.ironmonSupported, OpponentAI_DispatchTrace.activeBattler,
		OpponentAI_DispatchTrace.bankAttacker, OpponentAI_DispatchTrace.bankTarget,
		OpponentAI_DispatchTrace.publicPlayerSpecies,
		OpponentAI_DispatchTrace.publicOpponentSpecies,
		OpponentAI_DispatchTrace.defenseStage,
		OpponentAI_DispatchTrace.moves[0], OpponentAI_DispatchTrace.moves[1],
		OpponentAI_DispatchTrace.moves[2], OpponentAI_DispatchTrace.moves[3],
		OpponentAI_DispatchTrace.adapter, OpponentAI_DispatchTrace.policyRc,
		OpponentAI_DispatchTrace.selectedSlot, OpponentAI_DispatchTrace.selectedMove,
		OpponentAI_DispatchTrace.emittedSlot, OpponentAI_DispatchTrace.emittedMove);
	if (aiProfile == TRAINER_AI_PROFILE_STANDARD)
	{
		assert(StandardAI_TestLastPolicyRc == STANDARD_POLICY_OK);
		assert(StandardAI_TestLastSelectedId == selectedId);
	}
	else
	{
		assert(IronmonAI_TestLastPolicyRc == IRONMON_POLICY_OK);
		assert(IronmonAI_TestLastSelectedId == selectedId);
	}
	printf("Oak's Lab %s production handoff: rc=%d selected_id=%u returned_slot=%u emitted_slot=%u emitted_move=%u pending=%u controller_parity=PASS\n",
		reveal ? "revealed" : "omitted-reveal", rc, selectedId,
		gBattleStruct->chosenMovePositions[1], sEmittedPosition,
		moveInfo->moves[sEmittedPosition], gNewBS->ai.standardPendingValid[1]);
}

#ifdef TRAINER_AI_RUNTIME_DISPATCH_TRACE
static void OakDispatchMarkerMatrix(void)
{
	static const u16 moves[MAX_MON_MOVES] =
		{MOVE_TACKLE, MOVE_TAILWHIP, MOVE_WATERGUN, MOVE_NONE};
	const enum TrainerAIProfile profiles[] = {
		TRAINER_AI_PROFILE_STANDARD, TRAINER_AI_PROFILE_IRONMON_SMART,
		TRAINER_AI_PROFILE_NORMAL};
	const u16 publicSpecies[] = {SPECIES_CHARMANDER, SPECIES_NONE, SPECIES_SQUIRTLE};
	u8 p, excluded, identity, turn;
	for (p = 0; p < ARRAY_COUNT(profiles); ++p)
	for (excluded = 0; excluded < 2; ++excluded)
	for (identity = 0; identity < ARRAY_COUNT(publicSpecies); ++identity)
	{
		u8 expected[3];
		ConfigureSourceWitness(TRAINER_RIVAL_OAKS_LAB_SQUIRTLE, profiles[p],
			SPECIES_SQUIRTLE, 5, 0, moves, TYPE_WATER, TYPE_WATER);
		RunPublicRevealLifecycle();
		gNewBS->ai.standardDisplayedSpecies[0] = publicSpecies[identity];
		gBattleTypeFlags = BATTLE_TYPE_TRAINER
			| (excluded ? BATTLE_TYPE_OAK_TUTORIAL : 0);
		expected[0] = excluded ? 1 : p == 0 ? 0 : p == 1 ? 2 : 1;
		expected[1] = p == 0 ? 0 : p == 1 ? 2 : 1;
		expected[2] = identity == 0 ? 2 : identity == 1 ? 0 : 1;
		for (turn = 0; turn < 3; ++turn)
		{
			u32 battleRng = gRngValue, battleRng2 = gRng2Value;
			u32 standardRng = gNewBS->ai.standardPolicyRng[1];
			u32 ironmonRng = gNewBS->ai.ironmonPolicyRng[1];
			gBattleResults.battleTurnCounter = turn;
			gActiveBattler = 1;
			sEmitCount = sOpponentCompleted = 0;
			OpponentHandleChooseMove();
			assert(sEmitCount == 1 && sOpponentCompleted == 1);
			assert(sEmittedPosition == expected[turn]);
			assert(OpponentAI_DispatchTrace.adapter == 3);
			assert(OpponentAI_DispatchTrace.emittedSlot == expected[turn]);
			assert(OpponentAI_DispatchTrace.emittedMove == moves[expected[turn]]);
			assert(gRngValue == battleRng && gRng2Value == battleRng2);
			assert(gNewBS->ai.standardPolicyRng[1] == standardRng);
			assert(gNewBS->ai.ironmonPolicyRng[1] == ironmonRng);
		}
		printf("Oak marker profile=%u excluded=%u public=%u slots=%u/%u/%u\n",
			profiles[p], excluded, publicSpecies[identity],
			expected[0], expected[1], expected[2]);
	}
	puts("Oak dispatch marker 18-state matrix: PASS");
}
#endif

static void ConfigureOakLifecycleWitness(enum TrainerAIProfile aiProfile)
{
	static const u16 expectedMoves[MAX_MON_MOVES] =
		{MOVE_TACKLE, MOVE_TAILWHIP, MOVE_WATERGUN, MOVE_NONE};
	const struct BaseStats *playerBase;
	u16 trainerMoves[MAX_MON_MOVES], playerMoves[MAX_MON_MOVES];
	u8 i;

	DeriveSourceInitialMoveset(SPECIES_SQUIRTLE, 5, trainerMoves);
	DeriveSourceInitialMoveset(SPECIES_CHARMANDER, 5, playerMoves);
	for (i = 0; i < MAX_MON_MOVES; ++i)
		assert(trainerMoves[i] == expectedMoves[i]);
	ConfigureSourceWitness(TRAINER_RIVAL_OAKS_LAB_SQUIRTLE, aiProfile,
		SPECIES_SQUIRTLE, 5, 0, trainerMoves, TYPE_WATER, TYPE_WATER);
	gBattleResults.battleTurnCounter = 0;
	playerBase = &testBaseStats[SPECIES_CHARMANDER];
	SetWitnessMon(0, SPECIES_CHARMANDER, 5,
		SourceWitnessHp(playerBase->baseHP, 31, 5),
		SourceWitnessStat(playerBase->baseAttack, 31, 5),
		SourceWitnessStat(playerBase->baseDefense, 31, 5),
		SourceWitnessStat(playerBase->baseSpAttack, 31, 5),
		SourceWitnessStat(playerBase->baseSpDefense, 31, 5),
		SourceWitnessStat(playerBase->baseSpeed, 31, 5),
		TYPE_FIRE, TYPE_FIRE, playerMoves);
	SetControllerMoves(1);
	RunPublicRevealLifecycle();
	gActiveBattler = gBankAttacker = 1;
	gBankTarget = 0;
	assert(gNewBS->ai.standardDisplayedSpecies[0] == SPECIES_CHARMANDER);
	assert(gBattleTypeFlags == BATTLE_TYPE_TRAINER);
	assert(StandardAI_IsSupportedBattle() ==
		(aiProfile == TRAINER_AI_PROFILE_STANDARD));
	assert(IronmonAI_IsSupportedBattle() ==
		(aiProfile == TRAINER_AI_PROFILE_IRONMON_SMART));
}

static void OakFullLifecycleReleaseWitness(enum TrainerAIProfile aiProfile,
	bool8 cappedDefense)
{
	u8 bank = 1, actionSelected, actionFailure;
	int actionPolicyRc;
	u32 battleRng, battleRng2, standardRng, ironmonRng;
	ConfigureOakLifecycleWitness(aiProfile);
	if (cappedDefense)
		gBattleMons[0].statStages[STAT_STAGE_DEF - 1] = STAT_STAGE_MIN;
	gBattleResults.battleTurnCounter = 0;
	assert(!gNewBS->ai.standardPendingValid[bank]);
	assert(!gNewBS->ai.standardLastValid[bank]);
	battleRng = gRngValue;
	battleRng2 = gRng2Value;
	standardRng = gNewBS->ai.standardPolicyRng[bank];
	ironmonRng = gNewBS->ai.ironmonPolicyRng[bank];
	ControllerHost_ActionCount = 0;
	AI_TrySwitchOrUseItem();
	assert(ControllerHost_ActionCount == 1);
	assert(ControllerHost_ActionCode == ACTION_USE_MOVE);
	assert(ControllerHost_ActionValue == (bank ^ BIT_SIDE) << 8);
	assert(gNewBS->ai.standardPendingValid[bank]);
	assert(gNewBS->ai.standardPendingKind[bank] == STANDARD_POLICY_MOVE);
	assert(gNewBS->ai.standardLastValid[bank]);
	actionSelected = aiProfile == TRAINER_AI_PROFILE_STANDARD
		? StandardAI_TestLastSelectedId : IronmonAI_TestLastSelectedId;
	actionPolicyRc = aiProfile == TRAINER_AI_PROFILE_STANDARD
		? StandardAI_TestLastPolicyRc : IronmonAI_TestLastPolicyRc;
	actionFailure = aiProfile == TRAINER_AI_PROFILE_STANDARD
		? StandardAI_TestLastFailureReason : IronmonAI_TestLastFailureReason;
	assert(actionPolicyRc == 0 && actionFailure == AI_ADAPTER_FAILURE_NONE);
	assert(actionSelected == gNewBS->ai.standardPendingAction[bank]);
	assert(actionSelected == (cappedDefense ? 0 : 2));
	assert(gBattleMons[bank].moves[actionSelected] != MOVE_TAILWHIP);
	sEmitCount = sOpponentCompleted = 0;
	OpponentHandleChooseMove();
	assert(sEmitCount == 1 && sOpponentCompleted == 1);
	assert(!gNewBS->ai.standardPendingValid[bank]);
	assert(OpponentAI_DispatchTrace.adapter ==
		(aiProfile == TRAINER_AI_PROFILE_STANDARD ? 1 : 2));
	assert(OpponentAI_DispatchTrace.defenseStage ==
		(cappedDefense ? STAT_STAGE_MIN : 6));
	assert(OpponentAI_DispatchTrace.selectedSlot == actionSelected);
	assert(OpponentAI_DispatchTrace.emittedSlot == actionSelected);
	assert(sEmittedPosition == actionSelected);
	assert(gChosenMovesByBanks[bank] == gBattleMons[bank].moves[actionSelected]);
	assert(!OpponentAI_TestLastBufferMismatch);
	assert(!OpponentAI_TestLastBoundedFallback);
	assert((aiProfile == TRAINER_AI_PROFILE_STANDARD
		? StandardAI_TestLastFailureReason : IronmonAI_TestLastFailureReason)
		== AI_ADAPTER_FAILURE_NONE);
	assert(gRngValue == battleRng && gRng2Value == battleRng2);
	printf("Oak full lifecycle profile=%u defense=%u support=%u/%u pending=0->%u/%u/%u->0 last=0->%u action=%u rc=%d selected_id=%u failure=%u raw=%u buffer_mismatch=%u bounded=%u resolved=%u emitted=%u/%u rng_battle=%08x/%08x->%08x/%08x rng_policy=%08x/%08x->%08x/%08x\n",
		aiProfile, cappedDefense ? STAT_STAGE_MIN : 6,
		StandardAI_IsSupportedBattle(), IronmonAI_IsSupportedBattle(),
		TRUE, STANDARD_POLICY_MOVE, actionSelected,
		gNewBS->ai.standardLastValid[bank], ControllerHost_ActionCode,
		actionPolicyRc, actionSelected, actionFailure,
		OpponentAI_DispatchTrace.selectedSlot,
		OpponentAI_TestLastBufferMismatch, OpponentAI_TestLastBoundedFallback,
		OpponentAI_DispatchTrace.emittedSlot, sEmittedPosition,
		gChosenMovesByBanks[bank], battleRng, battleRng2, gRngValue,
		gRng2Value, standardRng, ironmonRng,
		gNewBS->ai.standardPolicyRng[bank], gNewBS->ai.ironmonPolicyRng[bank]);
}

static void OakEmergencySlotOneReleaseWitnesses(void)
{
	const enum TrainerAIProfile profiles[] = {
		TRAINER_AI_PROFILE_STANDARD, TRAINER_AI_PROFILE_IRONMON_SMART};
	u8 p, failure;
	for (p = 0; p < ARRAY_COUNT(profiles); ++p)
	for (failure = AI_ADAPTER_FAILURE_POLICY_ERROR;
		failure <= AI_ADAPTER_FAILURE_SELECTED_ID_LOOKUP; ++failure)
	{
		ConfigureOakLifecycleWitness(profiles[p]);
		gBattleMons[0].statStages[STAT_STAGE_DEF - 1] = STAT_STAGE_MIN;
		assert(StandardAI_ChooseEmergencyMoveSlot(1) == 1);
		if (profiles[p] == TRAINER_AI_PROFILE_STANDARD)
		{
			StandardAI_TestPolicyRcOverride = failure == AI_ADAPTER_FAILURE_POLICY_ERROR
				? STANDARD_POLICY_ERROR : failure == AI_ADAPTER_FAILURE_NO_ADMITTED_ACTION
					? STANDARD_POLICY_NO_ADMITTED_ACTION : STANDARD_POLICY_OK;
			if (failure == AI_ADAPTER_FAILURE_SELECTED_ID_LOOKUP)
				StandardAI_TestSelectedIdOverride = 0xFE;
		}
		else
		{
			IronmonAI_TestPolicyRcOverride = failure == AI_ADAPTER_FAILURE_POLICY_ERROR
				? IRONMON_POLICY_ERROR : failure == AI_ADAPTER_FAILURE_NO_ADMITTED_ACTION
					? IRONMON_POLICY_NO_ADMITTED_ACTION : IRONMON_POLICY_OK;
			if (failure == AI_ADAPTER_FAILURE_SELECTED_ID_LOOKUP)
				IronmonAI_TestSelectedIdOverride = 0xFE;
		}
		ControllerHost_ActionCount = 0;
		AI_TrySwitchOrUseItem();
		assert(ControllerHost_ActionCount == 1
			&& ControllerHost_ActionCode == ACTION_USE_MOVE);
		assert(!gNewBS->ai.standardPendingValid[1]);
		assert(!gNewBS->ai.standardLastValid[1]);
		sEmitCount = sOpponentCompleted = 0;
		OpponentHandleChooseMove();
		assert(sEmitCount == 1 && sOpponentCompleted == 1);
		assert(OpponentAI_DispatchTrace.selectedSlot >= MAX_MON_MOVES);
		assert(OpponentAI_DispatchTrace.resolvedBeforeMarker == 1);
		assert(OpponentAI_DispatchTrace.adapterFailureReason == failure);
		assert(OpponentAI_DispatchTrace.boundedFallback);
		assert(sEmittedPosition == 1 && gChosenMovesByBanks[1] == MOVE_TAILWHIP);
		assert(gBattleStruct->chosenMovePositions[1] == 1);
		printf("Oak release emergency profile=%u failure=%u raw=%u resolved=1 emitted=1/%u\n",
			profiles[p], failure, OpponentAI_DispatchTrace.selectedSlot,
			gChosenMovesByBanks[1]);
		StandardAI_TestPolicyRcOverride = -2147483647 - 1;
		StandardAI_TestSelectedIdOverride = 0xFF;
		IronmonAI_TestPolicyRcOverride = -2147483647 - 1;
		IronmonAI_TestSelectedIdOverride = 0xFF;
	}
	puts("Oak #529 bounded emergency slot 1 under release controller: PASS");
}

#ifdef TRAINER_AI_RUNTIME_CAPPED_TAILWHIP_PROBE
static void OakCappedProbeDecision(enum TrainerAIProfile aiProfile, u8 stage,
	bool8 forced)
{
	struct ChooseMoveStruct *moveInfo = (struct ChooseMoveStruct *)&gBattleBufferA[1][4];
	u32 battleRng = gRngValue, battleRng2 = gRng2Value;
	u32 standardRng = gNewBS->ai.standardPolicyRng[1];
	u32 ironmonRng = gNewBS->ai.ironmonPolicyRng[1];
	int standardRcBefore = StandardAI_TestLastPolicyRc;
	int ironmonRcBefore = IronmonAI_TestLastPolicyRc;
	u8 standardIdBefore = StandardAI_TestLastSelectedId;
	u8 ironmonIdBefore = IronmonAI_TestLastSelectedId;
	u8 slot, actionSelected = 0xFF;
	int actionRc = -1;

	gBattleMons[0].statStages[STAT_STAGE_DEF - 1] = stage;
	assert(!gNewBS->ai.standardPendingValid[1]);
	assert(!gNewBS->ai.standardLastValid[1]);
	ControllerHost_ActionCount = 0;
	AI_TrySwitchOrUseItem();
	assert(ControllerHost_ActionCount == 1);
	assert(ControllerHost_ActionCode == ACTION_USE_MOVE);
	assert(ControllerHost_ActionValue == (1 ^ BIT_SIDE) << 8);
	assert(gOakCappedTailWhipProbeState.actionStage == stage);
	assert(gOakCappedTailWhipProbeState.forcedSetupAction == forced);
	if (forced)
	{
		assert(!gNewBS->ai.standardPendingValid[1]);
		assert(!gNewBS->ai.standardLastValid[1]);
		assert(gRngValue == battleRng && gRng2Value == battleRng2);
		assert(gNewBS->ai.standardPolicyRng[1] == standardRng);
		assert(gNewBS->ai.ironmonPolicyRng[1] == ironmonRng);
		assert(StandardAI_TestLastPolicyRc == standardRcBefore);
		assert(IronmonAI_TestLastPolicyRc == ironmonRcBefore);
		assert(StandardAI_TestLastSelectedId == standardIdBefore);
		assert(IronmonAI_TestLastSelectedId == ironmonIdBefore);
	}
	else
	{
		assert(gNewBS->ai.standardPendingValid[1]);
		assert(gNewBS->ai.standardPendingKind[1] == STANDARD_POLICY_MOVE);
		assert(gNewBS->ai.standardLastValid[1]);
		actionSelected = aiProfile == TRAINER_AI_PROFILE_STANDARD
			? StandardAI_TestLastSelectedId : IronmonAI_TestLastSelectedId;
		actionRc = aiProfile == TRAINER_AI_PROFILE_STANDARD
			? StandardAI_TestLastPolicyRc : IronmonAI_TestLastPolicyRc;
		assert(actionRc == 0 && actionSelected == gNewBS->ai.standardPendingAction[1]);
		if (stage == STAT_STAGE_MIN)
		{
			assert(gOakCappedTailWhipProbeState.cappedEntryClean);
			assert(gOakCappedTailWhipProbeState.cappedActionReady);
			assert(gOakCappedTailWhipProbeState.actionPendingValid);
			assert(gOakCappedTailWhipProbeState.actionLastValid);
			assert(gOakCappedTailWhipProbeState.actionLastKind == STANDARD_POLICY_MOVE);
			assert(gOakCappedTailWhipProbeState.actionPendingSlot == actionSelected);
		}
	}
	sEmitCount = sOpponentCompleted = 0;
	if (forced)
		moveInfo->moves[1] = MOVE_TACKLE; /* stale controller view */
	OpponentHandleChooseMove();
	assert(sEmitCount == 1 && sOpponentCompleted == 1);
	assert(OpponentAI_DispatchTrace.defenseStage == stage);
	assert(OpponentAI_DispatchTrace.profile == aiProfile);
	assert(OpponentAI_DispatchTrace.publicPlayerSpecies == SPECIES_CHARMANDER);
	assert(OpponentAI_DispatchTrace.battleFlags == BATTLE_TYPE_TRAINER);
	slot = sEmittedPosition;
	assert(slot < MAX_MON_MOVES);
	assert(gBattleStruct->chosenMovePositions[1] == slot);
	assert(gBattleStruct->moveTarget[1] == 0 && sEmittedTarget == 0);
	assert(gChosenMovesByBanks[1] == gBattleMons[1].moves[slot]);
	assert(moveInfo->moves[slot] == gBattleMons[1].moves[slot]);
	assert(OpponentAI_DispatchTrace.emittedSlot == slot);
	assert(OpponentAI_DispatchTrace.emittedMove == moveInfo->moves[slot]);
	if (forced)
	{
		assert(stage > STAT_STAGE_MIN);
		assert(OpponentAI_DispatchTrace.adapter == 4);
		assert(slot == 1 && gChosenMovesByBanks[1] == MOVE_TAILWHIP);
		assert(moveInfo->moves[1] == MOVE_TAILWHIP);
		assert(OpponentAI_DispatchTrace.policyRc == -1);
		assert(!gNewBS->ai.standardPendingValid[1]);
		assert(!gNewBS->ai.standardLastValid[1]);
		assert(gRngValue == battleRng && gRng2Value == battleRng2);
		assert(gNewBS->ai.standardPolicyRng[1] == standardRng);
		assert(gNewBS->ai.ironmonPolicyRng[1] == ironmonRng);
	}
	else
	{
		assert(OpponentAI_DispatchTrace.adapter ==
			(aiProfile == TRAINER_AI_PROFILE_STANDARD ? 1 : 2));
		assert(OpponentAI_DispatchTrace.policyRc == 0);
		assert(!gNewBS->ai.standardPendingValid[1]);
		assert(OpponentAI_DispatchTrace.selectedSlot == actionSelected);
		assert(OpponentAI_DispatchTrace.resolvedBeforeMarker == actionSelected);
		assert(OpponentAI_DispatchTrace.adapterFailureReason == AI_ADAPTER_FAILURE_NONE);
		assert(!OpponentAI_DispatchTrace.controllerBufferMismatch);
		assert(!OpponentAI_DispatchTrace.boundedFallback);
		if (stage == STAT_STAGE_MIN)
		{
			assert(OpponentAI_DispatchTrace.diagnosticClass == 1);
			assert(slot == 2 && gChosenMovesByBanks[1] == MOVE_WATERGUN);
		}
		else
			assert(OpponentAI_DispatchTrace.diagnosticClass == 0);
		assert(slot != 1 && gChosenMovesByBanks[1] != MOVE_TAILWHIP);
		assert(gChosenMovesByBanks[1] == MOVE_TACKLE
			|| gChosenMovesByBanks[1] == MOVE_WATERGUN);
	}
	printf("Oak capped probe profile=%u turn=%u defense=%u action=%u pending=%u/%u/%u last=%u action_rc=%d selected_id=%u adapter=%u move_rc=%d failure=%u raw=%u buffer_mismatch=%u bounded=%u resolved=%u class=%u emitted=%u/%u rng_battle=%08x/%08x->%08x/%08x rng_policy=%08x/%08x->%08x/%08x\n",
		aiProfile, gBattleResults.battleTurnCounter, stage,
		ControllerHost_ActionCode, gOakCappedTailWhipProbeState.actionPendingValid,
		gOakCappedTailWhipProbeState.actionPendingKind,
		gOakCappedTailWhipProbeState.actionPendingSlot,
		gOakCappedTailWhipProbeState.actionLastValid, actionRc, actionSelected,
		OpponentAI_DispatchTrace.adapter, OpponentAI_DispatchTrace.policyRc,
		OpponentAI_DispatchTrace.adapterFailureReason,
		OpponentAI_DispatchTrace.selectedSlot,
		OpponentAI_DispatchTrace.controllerBufferMismatch,
		OpponentAI_DispatchTrace.boundedFallback,
		OpponentAI_DispatchTrace.resolvedBeforeMarker,
		OpponentAI_DispatchTrace.diagnosticClass,
		slot, gChosenMovesByBanks[1], battleRng, battleRng2,
		gRngValue, gRng2Value, standardRng, ironmonRng,
		gNewBS->ai.standardPolicyRng[1], gNewBS->ai.ironmonPolicyRng[1]);
}

static void OakCappedTailWhipProbeMatrix(void)
{
	const enum TrainerAIProfile profiles[] = {
		TRAINER_AI_PROFILE_STANDARD, TRAINER_AI_PROFILE_IRONMON_SMART};
	const u8 stages[] = {6, 5, 5, 1, STAT_STAGE_MIN};
	u8 p, i;
	for (p = 0; p < ARRAY_COUNT(profiles); ++p)
	{
		ConfigureOakLifecycleWitness(profiles[p]);
		for (i = 0; i < ARRAY_COUNT(stages); ++i)
		{
			gBattleResults.battleTurnCounter = i;
			OakCappedProbeDecision(profiles[p], stages[i],
				stages[i] > STAT_STAGE_MIN);
		}
		/* An already capped first decision must use the normal profile path. */
		ConfigureOakLifecycleWitness(profiles[p]);
		OakCappedProbeDecision(profiles[p], STAT_STAGE_MIN, FALSE);
		/* A legal-move guard failure must also leave setup to production AI. */
		ConfigureOakLifecycleWitness(profiles[p]);
		gBattleMons[1].pp[1] = 0;
		OakCappedProbeDecision(profiles[p], 6, FALSE);
		ConfigureOakLifecycleWitness(profiles[p]);
		sMoveLimitationMask = gBitTable[1];
		OakCappedProbeDecision(profiles[p], 6, FALSE);
		/* The probe must never force a move in a different trainer or mode. */
		ConfigureOakLifecycleWitness(profiles[p]);
		gTrainerBattleOpponent_A = TRAINER_RIVAL_CERULEAN_SQUIRTLE;
		ControllerHost_ActionCount = 0;
		AI_TrySwitchOrUseItem();
		assert(ControllerHost_ActionCount == 1);
		sEmitCount = sOpponentCompleted = 0;
		OpponentHandleChooseMove();
		assert(OpponentAI_DispatchTrace.adapter != 4);
		assert(sEmitCount == 1 && sOpponentCompleted == 1);
		ConfigureOakLifecycleWitness(profiles[p]);
		gBattleMons[1].moves[1] = MOVE_GROWL;
		SetControllerMoves(1);
		ControllerHost_ActionCount = 0;
		AI_TrySwitchOrUseItem();
		assert(ControllerHost_ActionCount == 1);
		sEmitCount = sOpponentCompleted = 0;
		OpponentHandleChooseMove();
		assert(OpponentAI_DispatchTrace.adapter != 4);
		assert(sEmitCount == 1 && sOpponentCompleted == 1);
		ConfigureOakLifecycleWitness(profiles[p]);
		gBattleTypeFlags |= BATTLE_TYPE_OAK_TUTORIAL;
		sEmitCount = sOpponentCompleted = 0;
		OpponentHandleChooseMove();
		assert(OpponentAI_DispatchTrace.adapter != 4);
		assert(sEmitCount == 0 && sOpponentCompleted == 0);
		ConfigureOakLifecycleWitness(profiles[p]);
		gBattleTypeFlags |= BATTLE_TYPE_MOCK_BATTLE;
		sEmitCount = sOpponentCompleted = 0;
		OpponentHandleChooseMove();
		assert(OpponentAI_DispatchTrace.adapter != 4);
		assert(sEmitCount == 0 && sOpponentCompleted == 0);
	}
	puts("Oak capped Tail Whip probe and normal dispatch transition: PASS");
}

static void OakCappedProbeClassificationMatrix(void)
{
	const enum TrainerAIProfile profiles[] = {
		TRAINER_AI_PROFILE_STANDARD, TRAINER_AI_PROFILE_IRONMON_SMART};
	u8 p, caseId;
	for (p = 0; p < ARRAY_COUNT(profiles); ++p)
	for (caseId = 0; caseId < 7; ++caseId)
	{
		u8 expectedFailure = caseId == 0 ? AI_ADAPTER_FAILURE_NONE
			: caseId == 1 ? AI_ADAPTER_FAILURE_POLICY_ERROR
			: caseId == 2 ? AI_ADAPTER_FAILURE_NO_ADMITTED_ACTION
			: caseId == 3 ? AI_ADAPTER_FAILURE_SELECTED_ID_LOOKUP
			: caseId == 4 ? AI_ADAPTER_FAILURE_PENDING_STATE
			: AI_ADAPTER_FAILURE_NONE;
		u8 expectedClass = caseId == 0 ? 2 : 3;
		u8 expectedSlot = caseId == 0 ? 1 : 0;
		ConfigureOakLifecycleWitness(profiles[p]);
		gBattleMons[0].statStages[STAT_STAGE_DEF - 1] = STAT_STAGE_MIN;
		if (caseId == 5)
		{
			/* A valid slot-1 pending value inherited from an earlier turn is
			 * not a fresh capped action choice. */
			gNewBS->ai.standardPendingValid[1] = TRUE;
			gNewBS->ai.standardPendingKind[1] = STANDARD_POLICY_MOVE;
			gNewBS->ai.standardPendingAction[1] = 1;
			gNewBS->ai.standardLastValid[1] = TRUE;
			StandardAI_TestLastFailureReason = AI_ADAPTER_FAILURE_NONE;
			IronmonAI_TestLastFailureReason = AI_ADAPTER_FAILURE_NONE;
		}
		if (caseId == 0 || caseId == 3)
		{
			if (profiles[p] == TRAINER_AI_PROFILE_STANDARD)
				StandardAI_TestSelectedIdOverride = caseId == 0 ? 1 : 0xFE;
			else
				IronmonAI_TestSelectedIdOverride = caseId == 0 ? 1 : 0xFE;
		}
		if (caseId == 1 || caseId == 2)
		{
			int rc = caseId == 1 ? -1 : -2;
			if (profiles[p] == TRAINER_AI_PROFILE_STANDARD)
				StandardAI_TestPolicyRcOverride = rc;
			else
				IronmonAI_TestPolicyRcOverride = rc;
		}
		ControllerHost_ActionCount = 0;
		AI_TrySwitchOrUseItem();
		assert(ControllerHost_ActionCount == 1
			&& ControllerHost_ActionCode == ACTION_USE_MOVE);
		assert(gOakCappedTailWhipProbeState.cappedEntryClean == (caseId != 5));
		assert(gOakCappedTailWhipProbeState.cappedActionReady);
		if (caseId == 4)
		{
			assert(gNewBS->ai.standardPendingValid[1]);
			gNewBS->ai.standardPendingAction[1] = 0xFF;
		}
		if (caseId == 6)
			((struct ChooseMoveStruct *)&gBattleBufferA[1][4])->moves[0] = MOVE_WATERGUN;
		sEmitCount = sOpponentCompleted = 0;
		OpponentHandleChooseMove();
		assert(sEmitCount == 1 && sOpponentCompleted == 1);
		assert(OpponentAI_DispatchTrace.adapterFailureReason == expectedFailure);
		assert(OpponentAI_DispatchTrace.diagnosticClass == expectedClass);
		assert(OpponentAI_DispatchTrace.boundedFallback ==
			(caseId >= 1 && caseId <= 4));
		assert(OpponentAI_DispatchTrace.controllerBufferMismatch == (caseId == 6));
		assert(OpponentAI_DispatchTrace.resolvedBeforeMarker == (caseId == 6 ? 0 : 1));
		assert(sEmittedPosition == expectedSlot);
		assert(gChosenMovesByBanks[1] ==
			(caseId == 0 ? MOVE_TAILWHIP : MOVE_TACKLE));
		assert(OpponentAI_DispatchTrace.selectedSlot ==
			(caseId == 0 || caseId == 5 ? 1 : caseId == 6 ? 0 : 0xFF));
		printf("Oak capped class profile=%u case=%u action_pending=%u/%u/%u action_last=%u action_rc=%d selected_id=%u move_rc=%d failure=%u raw=%u bounded=%u resolved=%u class=%u emitted=%u/%u\n",
			profiles[p], caseId,
			gOakCappedTailWhipProbeState.actionPendingValid,
			gOakCappedTailWhipProbeState.actionPendingKind,
			gOakCappedTailWhipProbeState.actionPendingSlot,
			gOakCappedTailWhipProbeState.actionLastValid,
			profiles[p] == TRAINER_AI_PROFILE_STANDARD
				? StandardAI_TestLastPolicyRc : IronmonAI_TestLastPolicyRc,
			profiles[p] == TRAINER_AI_PROFILE_STANDARD
				? StandardAI_TestLastSelectedId : IronmonAI_TestLastSelectedId,
			OpponentAI_DispatchTrace.policyRc, expectedFailure,
			OpponentAI_DispatchTrace.selectedSlot,
			OpponentAI_DispatchTrace.boundedFallback,
			OpponentAI_DispatchTrace.resolvedBeforeMarker,
			OpponentAI_DispatchTrace.diagnosticClass,
			sEmittedPosition, gChosenMovesByBanks[1]);
		StandardAI_TestPolicyRcOverride = -2147483647 - 1;
		StandardAI_TestSelectedIdOverride = 0xFF;
		IronmonAI_TestPolicyRcOverride = -2147483647 - 1;
		IronmonAI_TestSelectedIdOverride = 0xFF;
	}
	puts("Oak capped current-slot/failure marker classification: PASS");
}
#endif

int main(void)
{
#ifdef TRAINER_AI_RUNTIME_CAPPED_TAILWHIP_PROBE
	OakCappedTailWhipProbeMatrix();
	OakCappedProbeClassificationMatrix();
	return 0;
#elif defined(TRAINER_AI_RUNTIME_DISPATCH_TRACE)
	OakDispatchMarkerMatrix();
	return 0;
#else
	static const u16 weedleMoves[MAX_MON_MOVES] = {
		MOVE_POISONSTING, MOVE_STRINGSHOT, MOVE_NONE, MOVE_NONE};
	const enum TrainerAIProfile profiles[] = {
		TRAINER_AI_PROFILE_STANDARD, TRAINER_AI_PROFILE_IRONMON_SMART};
	unsigned p;
	setbuf(stdout, NULL);
	ProfileDispatchAndLegacyIsolation();
	ExactPolicyReturnCodes();
	FailureFallbackWitnesses();
	OakEmergencySlotOneReleaseWitnesses();
	for (p = 0; p < ARRAY_COUNT(profiles); ++p)
	{
		OakFullLifecycleReleaseWitness(profiles[p], FALSE);
		OakFullLifecycleReleaseWitness(profiles[p], TRUE);
		OpeningOakLabWitness(profiles[p], TRUE, FALSE);
		OpeningOakLabWitness(profiles[p], FALSE, FALSE);
		OpeningOakLabWitness(profiles[p], TRUE, TRUE);
	}
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
#endif
}
