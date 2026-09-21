/* Compile the PRODUCTION projection, not a reimplementation of it. Only ROM
 * tables/storage and boundary I/O are replaced. Hidden twins mutate the same
 * engine structs the production function could accidentally read. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "../../src/defines.h"
#include "../../src/defines_battle.h"
#include "../../include/constants/items.h"
#undef gBaseStats
#undef gBitTable
#undef gTrainerBattleOpponent_A
u16 gTrainerBattleOpponent_A;
static struct BaseStats testBaseStats[NUM_SPECIES];
static const u32 testBitTable[] = {1, 2, 4, 8};
#define gBaseStats testBaseStats
#define gBitTable testBitTable
#include "../../src/Battle_AI/ai_standard.c"
#undef EWRAM_DATA
#define EWRAM_DATA
#include "../../src/Battle_AI/ai_ironmon.c"

struct BattlePokemon gBattleMons[4];
struct DisableStruct gDisableStructs[4];
struct ProtectStruct gProtectStructs[4];
struct SideTimer gSideTimers[2];
struct Pokemon gEnemyParty[6], gPlayerParty[6];
static struct NewBattleStruct newBattle;
static struct BattleStruct battle;
static struct BattleHistory history;
static struct BattleResources resources;
struct NewBattleStruct* gNewBS = &newBattle;
struct BattleStruct* gBattleStruct = &battle;
struct BattleResources* gBattleResources = &resources;
u8 gActiveBattler = 1, gBankAttacker = 1, gBankTarget = 0;
u16 gBattlerPartyIndexes[4], gLastUsedMoves[4], gLockedMoves[4], gChosenMovesByBanks[4];
u16 gSideStatuses[2], gBattleWeather;
u32 gStatuses3[4], gBattleTypeFlags = BATTLE_TYPE_TRAINER, gHitMarker;
u32 gRngValue, gRng2Value;
u8 gChosenActionByBank[4];
static enum TrainerAIProfile profile = TRAINER_AI_PROFILE_STANDARD;
/* Private save/progression harness state. Fair production code must never
 * call FlagGet for these IDs; Badge twins vary this mask to prove that. */
static u8 testBadgeMask;

/* The real source tables, including their nonstandard 0/1 neutral/immunity
 * encoding. No hand-authored substitute move/type table can hide drift. */
#include "../../src/Tables/battle_moves.c"
#include "../../src/Tables/type_tables.h"

void* Memset(void* dst, u8 value, u32 size) { return memset(dst, value, size); }
u32 MathMin(u32 a, u32 b) { return a < b ? a : b; }
u32 MathMax(u32 a, u32 b) { return a > b ? a : b; }
u8 GetBattlerSide(u8 bank) { return bank & 1; }
struct Pokemon* LoadPartyRange(u8 bank, u8* first, u8* last)
{ assert(bank == 1); *first=0; *last=2; return gEnemyParty; }
u8 GetMonAbility(const struct Pokemon* mon)
{ assert(mon >= gEnemyParty && mon < gEnemyParty+6); return ABILITY_NONE; }
u8 GetMonItemEffect(const struct Pokemon* mon)
{ assert(mon >= gEnemyParty && mon < gEnemyParty+6); return 0; }
u8 ItemId_GetHoldEffect(u16 item) { (void)item; return 0; }
u8 CheckGrounding(u8 bank) { assert(bank == 1); return GROUNDED; }
bool8 IsRaidBattle(void) { return FALSE; }
bool8 IsInverseBattle(void) { return FALSE; }
bool8 IsFrontierTrainerId(u16 trainer) { (void)trainer; return FALSE; }
bool8 FlagGet(u16 id)
{
	switch (id)
	{
	case FLAG_BADGE01_GET: return testBadgeMask & 1;
	case FLAG_BADGE03_GET: return testBadgeMask & 2;
	case FLAG_BADGE05_GET: return testBadgeMask & 4;
	case FLAG_BADGE07_GET: return testBadgeMask & 8;
	default: return FALSE;
	}
}
enum TrainerAIProfile GetTrainerAIProfile(void) { return profile; }
void EmitTwoReturnValues(u8 buffer, u8 action, u16 value)
{ (void)buffer; (void)action; (void)value; }

static void Reset(void)
{
	unsigned i;
	memset(gBattleMons, 0, sizeof(gBattleMons));
	memset(gEnemyParty, 0, sizeof(gEnemyParty));
	memset(gPlayerParty, 0, sizeof(gPlayerParty));
	memset(&newBattle, 0, sizeof(newBattle));
	memset(&battle, 0, sizeof(battle));
	memset(&history, 0, sizeof(history));
	testBadgeMask = 0;
	gTrainerBattleOpponent_A = 0x400;
	memset(gDisableStructs, 0, sizeof(gDisableStructs));
	memset(gStatuses3, 0, sizeof(gStatuses3));
	memset(gSideStatuses, 0, sizeof(gSideStatuses));
	memset(gSideTimers, 0, sizeof(gSideTimers));
	memset(gLockedMoves, 0, sizeof(gLockedMoves));
	resources.battleHistory = (void*)&history;
	battle.battlerPreventingSwitchout = 0xFF;
	gBattleTypeFlags = BATTLE_TYPE_TRAINER;
	gBattleWeather = 0;
	gHitMarker = 0;
	for (i=0; i<2; ++i)
	{
		gBattleMons[i].species = SPECIES_RATTATA;
		newBattle.ai.standardDisplayedSpecies[i] = SPECIES_RATTATA;
		gBattleMons[i].level = 50;
		gBattleMons[i].hp = gBattleMons[i].maxHP = 100;
		gBattleMons[i].attack = gBattleMons[i].spAttack = 150;
		gBattleMons[i].defense = gBattleMons[i].spDefense = 100;
		gBattleMons[i].type1 = gBattleMons[i].type2 = TYPE_NORMAL;
		gBattleMons[i].type3 = NUMBER_OF_MON_TYPES;
		memset(gBattleMons[i].statStages, 6, sizeof(gBattleMons[i].statStages));
		gBattlerPartyIndexes[i] = 0;
	}
	testBaseStats[SPECIES_RATTATA].baseHP = 30;
	testBaseStats[SPECIES_RATTATA].baseDefense = 35;
	testBaseStats[SPECIES_RATTATA].baseSpDefense = 35;
	testBaseStats[SPECIES_RATTATA].baseSpeed = 72;
	testBaseStats[SPECIES_RATTATA].baseAttack = testBaseStats[SPECIES_RATTATA].baseSpAttack = 56;
	testBaseStats[SPECIES_RATTATA].type1 = testBaseStats[SPECIES_RATTATA].type2 = TYPE_NORMAL;
	gBattleMons[1].speed = 100;
	gBattleMons[1].moves[0] = MOVE_STRENGTH;
	gBattleMons[1].moves[1] = MOVE_SANDATTACK;
	gBattleMons[1].moves[2] = MOVE_SMOKESCREEN;
	gBattleMons[1].moves[3] = MOVE_TACKLE;
	memset(gBattleMons[1].pp, 10, 4);
	gEnemyParty[1].species = SPECIES_RATTATA;
	gEnemyParty[1].hp = gEnemyParty[1].maxHP = 100;
	gEnemyParty[1].moves[0] = MOVE_TACKLE;
	gEnemyParty[1].pp[0] = 10;
	/* Own Ghost type certifies absence of unknown ability trapping. */
	gBattleMons[1].type3 = TYPE_GHOST;
}

static void Build(struct StandardPolicyObservation* o, struct StandardPolicyResult* r, u32* seed)
{
	struct StandardPolicyMemory memory;
	memset(o, 0, sizeof(*o));
	memset(r, 0, sizeof(*r));
	StandardAI_BuildObservation(1, TRUE, o);
	StandardAI_LoadMemory(1, &memory);
	assert(StandardPolicyChoose(o, &memory, seed, r) == 0);
}

static void Certify(void)
{
	gStatuses3[0] = gStatuses3[1] = STATUS3_ABILITY_SUPPRESS;
	newBattle.MagicRoomTimer = 3;
	gBattleMons[0].status2 = STATUS2_RECHARGE;
	gBattleMons[0].hp = 5;
}

/* Ironmon's response certificate is intentionally narrower than the Standard
 * host fixture: the revealed response must not carry the Standard recharge
 * sentinel, and both battlers need a clean public status2 surface. */
static void IronmonCertify(void)
{
	Certify();
	gTrainerBattleOpponent_A = 0;
	gBattleMons[0].status2 = 0;
	gBattleMons[0].hp = gBattleMons[0].maxHP;
	gBattleMons[1].status2 = 0;
	gBattleMons[1].type3 = NUMBER_OF_MON_TYPES;
}

static void Behavior(void)
{
	struct StandardPolicyObservation o;
	struct StandardPolicyResult r;
	struct StandardDamageEnvelope envelope;
	u32 seed=1;
	int first;
	Reset(); Certify(); Build(&o,&r,&seed);
	assert(o.candidates[0].robust_safe_ko && o.candidates[0].net_faints == 1);
	assert(!r.diagnostics[1].standard_eligible && !r.diagnostics[2].standard_eligible);
	assert(r.selected_id == 0 || r.selected_id == 3);
	assert(!o.candidates[4].standard_switch_emergency);
	Reset(); Build(&o,&r,&seed);
	assert(o.candidates[0].expected_damage > o.candidates[3].expected_damage);
	assert(o.candidates[0].opponent_hp_fraction_lost > 0 && !o.candidates[0].robust_safe_ko);
	assert(r.selected_id == 0); /* Meaningful damage beats low-marginal Accuracy. */
	first=o.candidates[1].immediate_future_gain;
	gBattleMons[0].statStages[STAT_STAGE_ACC-1]=5; Build(&o,&r,&seed);
	assert(o.candidates[1].immediate_future_gain < first);
	gBattleMons[0].statStages[STAT_STAGE_ACC-1]=0; Build(&o,&r,&seed);
	assert(!o.candidates[1].productive && !r.diagnostics[1].standard_eligible);
	Reset(); gBattleMons[1].attack=1; Build(&o,&r,&seed);
	assert(r.diagnostics[1].near_best && r.diagnostics[2].near_best); /* useful first drop viable */
	Reset(); Certify(); gBattleMons[0].hp=100; gBattleMons[1].attack=50;
	Build(&o,&r,&seed);
	StandardAI_DeriveDamage(1,0,MOVE_STRENGTH,&o.candidates[0],&envelope);
	assert(envelope.possible_ko && !o.candidates[0].robust_safe_ko);
	/* Low HP with productive stay never enables voluntary switching. */
	Reset(); gBattleMons[1].hp=1; Build(&o,&r,&seed);
	assert(!o.candidates[4].standard_switch_emergency);
	memset(gBattleMons[1].pp,0,4); Build(&o,&r,&seed);
	assert(o.candidates[4].standard_switch_emergency && r.selected_id == 5);
	gSideStatuses[1]=SIDE_STATUS_SPIKES; gSideTimers[1].spikesAmount=3; gEnemyParty[1].hp=20;
	StandardAI_BuildObservation(1,TRUE,&o);
	assert(!o.candidates[4].entry_survives && !o.candidates[4].standard_switch_emergency);
	gSideStatuses[1]=0; gEnemyParty[1].pp[0]=0; StandardAI_BuildObservation(1,TRUE,&o);
	assert(!o.candidates[4].productive && !o.candidates[4].standard_switch_emergency);
	gEnemyParty[1].pp[0]=10; gBattleMons[1].hp=0; StandardAI_BuildObservation(1,TRUE,&o);
	assert(o.candidates[4].forced && !o.candidates[4].standard_switch_emergency);
	/* Actual adapter memory -> accepted policy loop guard. */
	Reset(); memset(gBattleMons[1].pp,0,4);
	{
		struct StandardPolicyMemory memory;
		struct StandardPolicyMemoryDecision d={0};
		StandardPolicyResetMemory(&memory);
		d.kind=STANDARD_POLICY_SWITCH; d.success=1; d.switch_from=1; d.switch_to=0;
		StandardPolicyRecordMemory(&memory,&d); StandardAI_SaveMemory(1,&memory);
		memset(&o,0,sizeof(o)); StandardAI_BuildObservation(1,TRUE,&o);
		assert(StandardPolicyChoose(&o,&memory,&seed,&r)!=0);
		d.forced=1; StandardPolicyResetMemory(&memory); StandardPolicyRecordMemory(&memory,&d);
		assert(StandardPolicyChoose(&o,&memory,&seed,&r)==0 && r.selected_id==5);
	}
	puts("adapter behavior: KO/Sand/Smoke, damage ordering, Accuracy, switching PASS");
}

static void Twins(void)
{
	struct StandardPolicyObservation a,b;
	struct StandardPolicyResult ra,rb;
	struct StandardDamageEnvelope ea,eb;
	struct StandardPolicyCandidate da,db;
	unsigned mode,field,k,count=0;
	for (mode=0;mode<16;++mode) for(field=0;field<8;++field) for(k=1;k<=32;++k)
	{
		u32 sa=12345,sb=12345;
		Reset();
		if(mode==1) Certify();
		if(mode==2) memset(gBattleMons[1].pp,0,4);
		if(mode==3) {gSideStatuses[1]=SIDE_STATUS_SPIKES; gSideTimers[1].srAmount=1; gSideTimers[1].spikesAmount=3;}
		if(mode==4) gBattleMons[1].attack=1;
		if(mode==5 || mode==12 || mode==13)
		{
			Certify(); gBattleMons[0].hp=100; testBaseStats[SPECIES_RATTATA].baseSpeed=150;
			gBattleMons[1].speed=125;
			gBattleMons[1].moves[1]= mode==12 ? MOVE_THUNDERWAVE : MOVE_STRINGSHOT;
			if(mode==13) newBattle.MagicRoomTimer=0;
		}
		if(mode==6) {gBattleMons[1].attack=30; gBattleMons[1].moves[1]=MOVE_SWORDSDANCE;}
		if(mode==7) {gBattleMons[1].moves[1]=MOVE_POISONPOWDER; gBattleMons[1].moves[2]=MOVE_WILLOWISP;}
		if(mode==8) {gBattleMons[1].hp=60; gBattleMons[1].moves[1]=MOVE_RECOVER;}
		if(mode==9) {memset(gBattleMons[1].pp,0,4); gBattleMons[1].pp[0]=10; gBattleMons[1].moves[0]=MOVE_SEISMICTOSS;}
		if(mode==10) StandardAI_ObservePublicMove(MOVE_SOAK);
		if(mode==11) {gBattleMons[1].attack=30; gBattleMons[1].moves[1]=MOVE_TAILWHIP;}
		if(mode==14) {history.abilities[0]=ABILITY_WATERABSORB; gBattleMons[1].moves[0]=MOVE_WATERGUN;}
		if(mode==15) {history.usedMoves[0][0]=MOVE_WATERGUN; gBattleMons[1].moves[1]=MOVE_AMNESIA;}
		Build(&a,&ra,&sa);
		memset(&da,0,sizeof(da)); StandardAI_DeriveDamage(1,0,MOVE_STRENGTH,&da,&ea);
		switch(field)
		{
		case 0: gBattleMons[0].moves[0]=k; gPlayerParty[0].moves[0]=k; break;
		case 1:
			gBattleMons[0].item=k==1 ? ITEM_FOCUS_SASH : k==2 ? ITEM_FOCUS_BAND : k*37;
			gPlayerParty[0].item=gBattleMons[0].item; break;
		case 2:
			gBattleMons[0].ability=k==1 ? ABILITY_STURDY : k==2 ? ABILITY_WATERABSORB : k;
			gPlayerParty[0].hiddenAbility=k&1; break;
		case 3:
			memset(&gPlayerParty[1],k,sizeof(gPlayerParty[1])*5);
			/* Public appearance remains fixed, including an Illusion's real identity. */
			gBattleMons[0].species=k; break;
		case 4:
			gBattleMons[0].attack=k; gBattleMons[0].defense=k*10;
			gBattleMons[0].spAttack=k; gBattleMons[0].spDefense=k*10; gBattleMons[0].speed=k;
			gPlayerParty[0].personality=k; gPlayerParty[0].hpIV=k&31;
			gPlayerParty[0].defenseIV=k&31; gPlayerParty[0].defEv=k*7;
			/* Equal displayed ratio despite different private exact HP. */
			gBattleMons[0].hp*=2; gBattleMons[0].maxHP*=2;
			break;
		case 5: gChosenActionByBank[0]=k; gChosenMovesByBanks[0]=k; battle.moveTarget[0]=k; battle.monToSwitchIntoId[0]=k; break;
		case 6: gRngValue=k; gRng2Value=k*999; newBattle.ai.randSeed=k; break;
		case 7:
			gBattleMons[0].species=k;
			gBattleMons[0].type1=k%NUMBER_OF_MON_TYPES;
			gBattleMons[0].type2=(k+4)%NUMBER_OF_MON_TYPES;
			gBattleMons[0].type3=(k+7)%NUMBER_OF_MON_TYPES;
			break;
		}
		Build(&b,&rb,&sb);
		memset(&db,0,sizeof(db)); StandardAI_DeriveDamage(1,0,MOVE_STRENGTH,&db,&eb);
		assert(memcmp(&a,&b,sizeof(a))==0);
		assert(memcmp(&da,&db,sizeof(da))==0);
		assert(memcmp(&ea,&eb,sizeof(ea))==0);
		assert(memcmp(&ra,&rb,sizeof(ra))==0 && sa==sb);
		++count;
	}
	/* Actual public ability-history reveal, not a handcrafted candidate edit. */
	Reset(); gBattleMons[1].moves[0]=MOVE_WATERGUN;
	{u32 seed=3; Build(&a,&ra,&seed);}
	gBattleMons[0].ability=ABILITY_WATERABSORB;
	{u32 seed=3; Build(&b,&rb,&seed);}
	assert(memcmp(&a,&b,sizeof(a))==0);
	history.abilities[0]=ABILITY_WATERABSORB;
	{u32 seed=3; Build(&b,&rb,&seed);}
	assert(b.candidates[0].known_no_effect && !b.candidates[0].productive);
	assert(!a.candidates[0].known_no_effect);
	Reset(); newBattle.ai.standardDisplayedSpecies[0]=SPECIES_GASTLY;
	testBaseStats[SPECIES_GASTLY].type1=testBaseStats[SPECIES_GASTLY].type2=TYPE_GHOST;
	{u32 seed=3; Build(&b,&rb,&seed);}
	assert(b.candidates[0].known_no_effect && !b.candidates[0].productive);
	Reset(); gBattleMons[0].hp=1;
	{u32 seed=3; Build(&a,&ra,&seed);}
	gBattleMons[0].hp=3; /* Same minimum one-pixel public bar. */
	{u32 seed=3; Build(&b,&rb,&seed);}
	assert(memcmp(&a,&b,sizeof(a))==0 && memcmp(&ra,&rb,sizeof(ra))==0);
	printf("production adapter twins: %u pairs, 0 mismatches; public reveal PASS\n",count);
}

static void MarginalBehavior(void)
{
	struct StandardPolicyObservation o,a;
	struct StandardPolicyResult r,ra;
	u32 seed=7;
	Reset(); Certify(); gBattleMons[0].hp=100;
	testBaseStats[SPECIES_RATTATA].baseSpeed=150; gBattleMons[1].speed=125;
	gBattleMons[1].moves[1]=MOVE_STRINGSHOT;
	Build(&o,&r,&seed);
	assert(o.candidates[1].productive && o.candidates[1].immediate_future_gain>0);
	assert(StandardMechanicsSpeed(150,50,6,0)==139 && StandardMechanicsSpeed(150,50,6,1)==222);
	gBattleMons[1].speed=250; Build(&o,&r,&seed); /* Already definitely faster. */
	assert(!o.candidates[1].productive && !o.candidates[1].immediate_future_gain);
	gBattleMons[1].speed=170; Build(&o,&r,&seed); /* Before interval overlaps. */
	assert(!o.candidates[1].immediate_future_gain);
	gBattleMons[1].speed=125; newBattle.MagicRoomTimer=0; Build(&o,&r,&seed);
	assert(!o.candidates[1].immediate_future_gain); /* Unknown speed item. */
	newBattle.MagicRoomTimer=3; newBattle.TrickRoomTimer=3; Build(&o,&r,&seed);
	assert(!o.candidates[1].immediate_future_gain); /* Drop cannot help under TR. */
	newBattle.TrickRoomTimer=0; gBattleMons[1].moves[1]=MOVE_THUNDERWAVE;
	Build(&o,&r,&seed); assert(o.candidates[1].immediate_future_gain>0);
	gBattleMons[1].speed=250; Build(&o,&r,&seed); assert(!o.candidates[1].immediate_future_gain);
	Reset(); gBattleMons[1].attack=30; gBattleMons[1].moves[1]=MOVE_SWORDSDANCE;
	Build(&o,&r,&seed); assert(o.candidates[1].productive && o.candidates[1].immediate_future_gain>0);
	gBattleMons[1].attack=150; gBattleMons[0].hp=1; Build(&o,&r,&seed);
	assert(!o.candidates[1].immediate_future_gain); /* Follow-up HP already saturated. */
	gBattleMons[1].statStages[STAT_STAGE_ATK-1]=12; Build(&o,&r,&seed);
	assert(r.diagnostics[1].floor_reasons & STANDARD_FLOOR_CAPPED_STAT_CHANGE);
	Reset(); gBattleMons[1].moves[1]=MOVE_HARDEN; Build(&o,&r,&seed);
	assert(!o.candidates[1].immediate_future_gain); /* No public incoming threat. */
	gBattleMons[1].moves[1]=MOVE_GROWL; Build(&o,&r,&seed);
	assert(!o.candidates[1].immediate_future_gain);
	gBattleMons[1].type3=NUMBER_OF_MON_TYPES; history.usedMoves[0][0]=MOVE_STRENGTH;
	Build(&o,&r,&seed); assert(o.candidates[1].immediate_future_gain>0);
	gBattleMons[1].moves[1]=MOVE_HARDEN; Build(&o,&r,&seed);
	assert(o.candidates[1].immediate_future_gain>0);
	gBattleMons[1].type3=TYPE_GHOST; Build(&o,&r,&seed);
	assert(!o.candidates[1].immediate_future_gain); /* public threat already ineffective */
	Reset(); gBattleMons[1].attack=30; gBattleMons[1].moves[1]=MOVE_TAILWHIP;
	Build(&o,&r,&seed); assert(o.candidates[1].immediate_future_gain>0);
	Reset(); gBattleMons[1].moves[1]=MOVE_POISONPOWDER; Build(&o,&r,&seed);
	assert(o.candidates[1].immediate_future_gain==9); /* floor(100/8) * .75 */
	gBattleMons[1].moves[1]=MOVE_TOXIC; Build(&o,&r,&seed);
	assert(o.candidates[1].immediate_future_gain==5); /* first 1/16, 90% */
	gBattleMons[1].moves[1]=MOVE_WILLOWISP; Build(&o,&r,&seed);
	assert(o.candidates[1].immediate_future_gain==5); /* 1/16, 85%; no guessed threat */
	gBattleMons[0].status1=STATUS_POISON; Build(&o,&r,&seed);
	assert(o.candidates[1].redundant_status && !r.diagnostics[1].standard_eligible);
	Reset(); gBattleMons[1].moves[1]=MOVE_HYPNOSIS; Build(&o,&r,&seed);
	assert(!o.candidates[1].immediate_future_gain); /* Unmodeled sleep duration/action loss. */
	Reset(); gBattleMons[1].moves[1]=MOVE_RECOVER;
	gBattleMons[1].hp=60; Build(&o,&r,&seed);
	assert(o.candidates[1].own_hp_fraction_lost==-102 && !o.candidates[1].immediate_future_gain);
	assert(r.diagnostics[1].utility_total==39); /* accepted host: trunc(100*102/256), once */
	gBattleMons[1].hp=10; Build(&o,&r,&seed);
	assert(o.candidates[1].own_hp_fraction_lost==-128 && r.diagnostics[1].utility_total==50);
	gBattleMons[1].hp=100; Build(&o,&r,&seed);
	assert(!o.candidates[1].productive && !r.diagnostics[1].standard_eligible);
	Reset(); memset(gBattleMons[1].pp,0,4); gBattleMons[1].pp[0]=10;
	gBattleMons[1].moves[0]=MOVE_SEISMICTOSS; Build(&o,&r,&seed);
	assert(o.candidates[0].unknown_potentially_productive && r.diagnostics[0].standard_eligible);
	assert(!o.candidates[0].productive && !o.candidates[0].robust_safe_ko);
	assert(!o.candidates[0].expected_damage && !o.candidates[0].opponent_hp_fraction_lost);
	assert(!o.candidates[4].standard_switch_emergency && r.selected_id==0);
	assert(!r.policy_rng_draws); /* singleton unknown attack must not draw */
	newBattle.ai.standardDisplayedSpecies[0]=SPECIES_GASTLY;
	testBaseStats[SPECIES_GASTLY].type1=testBaseStats[SPECIES_GASTLY].type2=TYPE_GHOST;
	gBattleMons[1].pp[1]=10; /* Keep a productive alternative; no all-futile fallback. */
	Build(&o,&r,&seed);
	assert(o.candidates[0].known_no_effect && !o.candidates[0].unknown_potentially_productive);
	assert(r.diagnostics[0].floor_reasons & STANDARD_FLOOR_KNOWN_NO_EFFECT);
	Reset(); Build(&a,&ra,&seed);
	gBattleMons[0].type1=gBattleMons[0].type2=gBattleMons[0].type3=TYPE_GHOST;
	seed=7; Build(&o,&r,&seed); assert(memcmp(&a,&o,sizeof(o))==0);
	StandardAI_ObservePublicMove(MOVE_SOAK); Build(&o,&r,&seed);
	assert(o.candidates[0].unknown_potentially_productive && !o.candidates[0].expected_damage);
	memset(&history,0,sizeof(history)); Build(&o,&r,&seed);
	assert(o.candidates[0].unknown_potentially_productive); /* sticky across history eviction */
	puts("adapter marginals: Speed flip/no-benefit/uncertain/TR; setup useful/useless/capped; residual status; recovery HP-only parity; unknown damage; public types PASS");
}

static void EnvelopeOracle(void)
{
	struct StandardPolicyCandidate c={0};
	struct StandardDamageEnvelope e;
	unsigned iv,ev,nature,roll,count=0;
	Reset(); Certify();
	StandardAI_DeriveDamage(1,0,MOVE_STRENGTH,&c,&e);
	/* Hand calculation: defenses 36..95, HP 90..137, neutral nominal
	 * defense 65 -> base 83 -> STAB 124 -> 93% = 115. Minimum = 72. */
	assert(e.max_hp_minimum==90 && e.max_hp_maximum==137);
	assert(e.minimum==72 && e.estimate==115 && c.robust_safe_ko);
	for(iv=0;iv<=31;++iv) for(ev=0;ev<=63;++ev)
	for(nature=90;nature<=110;nature+=10) for(roll=85;roll<=100;++roll)
	{
		unsigned defense=(((70+iv+ev)*50/100)+5)*nature/100;
		unsigned damage=((22*80*150/defense)/50+2)*15/10*roll/100;
		assert(damage>=e.minimum && damage<=e.maximum); ++count;
	}
	/* High-roll-only damage, low accuracy, missing item suppression, and
	 * hidden/revealed immunities never gain a spurious robust flag. */
	gBattleMons[0].hp=70; gBattleMons[0].maxHP=100;
	StandardAI_DeriveDamage(1,0,MOVE_STRENGTH,&c,&e);
	assert(e.possible_ko && !c.robust_safe_ko);
	gBattleMons[0].hp=5; gBattleMons[1].statStages[STAT_STAGE_ACC-1]=5;
	StandardAI_DeriveDamage(1,0,MOVE_STRENGTH,&c,&e);
	assert(!c.robust_safe_ko && e.minimum==0);
	gBattleMons[1].statStages[STAT_STAGE_ACC-1]=6; newBattle.MagicRoomTimer=0;
	StandardAI_DeriveDamage(1,0,MOVE_STRENGTH,&c,&e);
	assert(!c.robust_safe_ko && e.minimum==0 && e.uncertain);
	printf("damage envelope oracle: %u IV/EV/nature/roll cases PASS\n",count);
}

static void Dispatch(void)
{
	unsigned bit,p;
	Reset(); assert(StandardAI_IsSupportedBattle());
	for(bit=0;bit<32;++bit)
	{
		u32 flag=1u<<bit;
		if(flag==BATTLE_TYPE_TRAINER || flag==BATTLE_TYPE_IS_MASTER
			|| flag==BATTLE_TYPE_LINK_ESTABLISHED || flag==0x100000) continue;
		gBattleTypeFlags=BATTLE_TYPE_TRAINER|flag;
		assert(!StandardAI_IsSupportedBattle());
	}
	gBattleTypeFlags=0; assert(!StandardAI_IsSupportedBattle());
	gBattleTypeFlags=BATTLE_TYPE_TRAINER;
	for(p=0;p<TRAINER_AI_PROFILE_STANDARD;++p)
	{profile=p; assert(!StandardAI_IsSupportedBattle());}
	profile=TRAINER_AI_PROFILE_STANDARD;
	puts("production dispatch: all named excluded flags and Legacy profiles PASS");
}

static void HazardsAndReplacement(void)
{
	struct StandardPolicyCandidate c;
	Reset();
	testBaseStats[SPECIES_RATTATA].type1=testBaseStats[SPECIES_RATTATA].type2=TYPE_NORMAL;
	gSideStatuses[1]=SIDE_STATUS_SPIKES; gSideTimers[1].srAmount=1;
	StandardAI_FillSwitchCandidate(1,1,&gEnemyParty[1],&c,0);
	assert(c.entry_survives && c.entry_cost==12*256/100);
	gSideTimers[1].spikesAmount=3;
	StandardAI_FillSwitchCandidate(1,1,&gEnemyParty[1],&c,0);
	assert(c.entry_cost==37*256/100);
	gEnemyParty[1].hp=37;
	StandardAI_FillSwitchCandidate(1,1,&gEnemyParty[1],&c,0);
	assert(!c.entry_survives);
	Reset(); gBattleMons[1].hp=0;
	assert(StandardAI_ChooseReplacement()==1);
	assert(newBattle.ai.standardLastForced[1]);
	assert(newBattle.ai.standardPolicyRng[1]
		== (STANDARD_AI_DEFAULT_SEED ^ ((u32)gTrainerBattleOpponent_A << 8) ^ 1));
	puts("production hazards/replacement: exact entry costs, entry KO, forced/singleton RNG PASS");
}

static void ArithmeticBounds(void)
{
	struct StandardMechanicsInput s={0}, invalid;
	struct StandardPolicyCandidate c={0};
	struct StandardDamageEnvelope e;
	unsigned i;
	s.power=150; s.attack=2048; s.level=s.target_level=100;
	s.attack_stage=12; s.defense_stage=6; s.known_defense=1;
	s.base_hp=255; s.hp_pixels=48; s.stab=1;
	s.accuracy=s.accuracy_stage=s.evasion_stage=0;
	s.supported_damage=s.certified_modifiers=1;
	s.effectiveness[0]=s.effectiveness[1]=s.effectiveness[2]=20;
	StandardMechanicsDamage(&s,&c,&e);
	assert(e.estimate==65535 && e.minimum==65535 && !c.unknown_potentially_productive);
	for(i=0;i<10;++i)
	{
		invalid=s;
		switch(i) {
		case 0: invalid.power=151; break;
		case 1: invalid.attack=2049; break;
		case 2: invalid.level=101; break;
		case 3: invalid.target_level=101; break;
		case 4: invalid.attack_stage=13; break;
		case 5: invalid.defense_stage=13; break;
		case 6: invalid.base_defense=256; break;
		case 7: invalid.base_hp=256; break;
		case 8: invalid.effectiveness[2]=21; break;
		case 9: invalid.accuracy=101; break;
		}
		StandardMechanicsDamage(&invalid,&c,&e);
		assert(c.unknown_potentially_productive && !c.expected_damage && !c.robust_safe_ko);
		assert(!e.minimum && e.maximum==65535 && e.uncertain);
	}
	puts("mechanics arithmetic bounds: maximum product + 10 fail-closed boundaries PASS");
}

static void IronmonPublicCounts(void)
{
	unsigned i;
	Reset(); profile=TRAINER_AI_PROFILE_IRONMON_SMART;
	gBattleMons[0].moves[0]=MOVE_STRENGTH;
	IronmonAI_ObservePublicMove(0,MOVE_STRENGTH);
	assert(newBattle.ai.ironmonMoveUseCounts[0][0]==0); /* hidden slot/no string */
	gHitMarker=HITMARKER_ATTACKSTRING_PRINTED;
	IronmonAI_ObservePublicMove(0,MOVE_TACKLE);
	assert(newBattle.ai.ironmonMoveUseCounts[0][0]==1);
	history.usedMoves[0][0]=MOVE_TACKLE; /* battle_util records it after observers */
	IronmonAI_ObservePublicMove(0,MOVE_TACKLE);
	assert(newBattle.ai.ironmonMoveUseCounts[0][0]==2);
	history.usedMoves[0][1]=MOVE_WATERGUN;
	IronmonAI_ObservePublicMove(0,MOVE_WATERGUN);
	assert(newBattle.ai.ironmonMoveUseCounts[0][1]==1);
	newBattle.ai.ironmonMoveUseCounts[0][0]=0xFFFF;
	IronmonAI_ObservePublicMove(0,MOVE_TACKLE);
	assert(newBattle.ai.ironmonMoveUseCounts[0][0]==0xFFFF);
	IronmonAI_ClearPublicMoveCounts(0);
	for(i=0;i<MAX_MON_MOVES;++i) assert(!newBattle.ai.ironmonMoveUseCounts[0][i]);
	puts("Ironmon public history: first/repeat/distinct/saturation/clear PASS");
}

static void IronmonProductionTwins(void)
{
	struct IronmonPolicyObservation a,b;
	struct StandardPolicyMemory memory;
	struct IronmonPolicyResult ra,rb;
	unsigned mode,field,k,count=0;
	for(mode=0;mode<8;++mode) for(field=0;field<8;++field) for(k=1;k<=16;++k)
	{
		u32 sa=12345,sb=12345;
		Reset(); profile=TRAINER_AI_PROFILE_IRONMON_SMART;
		if(mode&1) { history.usedMoves[0][0]=MOVE_STRENGTH; newBattle.ai.ironmonMoveUseCounts[0][0]=mode; }
		if(mode&2) Certify();
		if(mode&4) { gBattleMons[1].hp=60; gBattleMons[1].moves[1]=MOVE_RECOVER; }
		IronmonAI_BuildObservation(1,TRUE,&a); StandardAI_LoadMemory(1,&memory);
		assert(IronmonPolicyChoose(&a,&memory,&sa,&ra)==0);
		switch(field)
		{
		case 0: gBattleMons[0].moves[0]=k; gPlayerParty[0].moves[0]=k; break;
		case 1: gBattleMons[0].item=k*37; gPlayerParty[0].item=k*37; break;
		case 2: gBattleMons[0].ability=k; gPlayerParty[0].hiddenAbility=k&1; break;
		case 3: memset(&gPlayerParty[1],k,sizeof(gPlayerParty[1])*5); gBattleMons[0].species=k; break;
		case 4:
			gBattleMons[0].attack=k; gBattleMons[0].defense=k*10;
			gBattleMons[0].spAttack=k; gBattleMons[0].spDefense=k*10; gBattleMons[0].speed=k;
			gPlayerParty[0].personality=k;
			gPlayerParty[0].hpIV=k&31; gPlayerParty[0].attackIV=(k+1)&31;
			gPlayerParty[0].defenseIV=(k+2)&31; gPlayerParty[0].speedIV=(k+3)&31;
			gPlayerParty[0].spAttackIV=(k+4)&31; gPlayerParty[0].spDefenseIV=(k+5)&31;
			gPlayerParty[0].hpEv=k*3; gPlayerParty[0].atkEv=k*5;
			gPlayerParty[0].defEv=k*7; gPlayerParty[0].spdEv=k*9;
			gPlayerParty[0].spAtkEv=k*11; gPlayerParty[0].spDefEv=k*13;
			gBattleMons[0].hp*=2; gBattleMons[0].maxHP*=2; break;
		case 5: gChosenActionByBank[0]=k; gChosenMovesByBanks[0]=k; battle.moveTarget[0]=k; battle.monToSwitchIntoId[0]=k; break;
		case 6: gRngValue=k; gRng2Value=k*999; newBattle.ai.randSeed=k; break;
		case 7:
			gBattleMons[0].species=k; gBattleMons[0].type1=k%NUMBER_OF_MON_TYPES;
			gBattleMons[0].type2=(k+4)%NUMBER_OF_MON_TYPES; gBattleMons[0].type3=(k+7)%NUMBER_OF_MON_TYPES; break;
		}
		IronmonAI_BuildObservation(1,TRUE,&b);
		assert(IronmonPolicyChoose(&b,&memory,&sb,&rb)==0);
		assert(memcmp(&a,&b,sizeof(a))==0);
		assert(memcmp(&ra,&rb,sizeof(ra))==0 && sa==sb);
		++count;
	}
	printf("Ironmon production twins: %u pairs (128 each hidden move/item/ability/bench/stats, submitted action, future RNG, hidden identity), 0 mismatches\n",count);
}

static void IronmonProductionBadgeTwins(void)
{
	struct IronmonPolicyObservation a, b;
	struct StandardPolicyMemory memory;
	struct IronmonPolicyResult ra, rb;
	u8 mask;
	for (mask = 0; mask < 16; ++mask)
	{
		u32 sa = 0x515A0000u + mask, sb = sa;
		Reset(); profile = TRAINER_AI_PROFILE_IRONMON_SMART;
		IronmonCertify(); testBadgeMask = mask;
		history.usedMoves[0][0] = MOVE_STRENGTH;
		newBattle.ai.ironmonMoveUseCounts[0][0] = 1;
		IronmonAI_BuildObservation(1, TRUE, &a);
		StandardAI_LoadMemory(1, &memory);
		assert(IronmonPolicyChoose(&a, &memory, &sa, &ra) == 0);
		Reset(); profile = TRAINER_AI_PROFILE_IRONMON_SMART;
		IronmonCertify(); testBadgeMask = mask ^ 0x0F;
		history.usedMoves[0][0] = MOVE_STRENGTH;
		newBattle.ai.ironmonMoveUseCounts[0][0] = 1;
		IronmonAI_BuildObservation(1, TRUE, &b);
		StandardAI_LoadMemory(1, &memory);
		assert(IronmonPolicyChoose(&b, &memory, &sb, &rb) == 0);
		assert(memcmp(&a, &b, sizeof(a)) == 0);
		assert(memcmp(&ra, &rb, sizeof(ra)) == 0 && sa == sb);
	}
	puts("Ironmon Badge-ownership twins: 16 pairs, 0 mismatches; fair state unaffected PASS");
}

static void IronmonProductionBadgeBounds(void)
{
	struct IronmonIncoming physicalPossible, physicalAbsent;
	struct IronmonIncoming specialPossible, specialAbsent;
	struct StandardPolicyCandidate damagePossible = {0}, damageAbsent = {0};
	Reset(); profile = TRAINER_AI_PROFILE_IRONMON_SMART; IronmonCertify();
	/* Ordinary public context permits the possible 1.1x states, regardless of
	 * the private ownership mask. */
	testBadgeMask = 0;
	IronmonAI_ProjectIncoming(1, MOVE_POUND, NULL, 0, 0xFFFF, &physicalPossible);
	IronmonAI_ProjectIncoming(1, MOVE_EMBER, NULL, 0, 0xFFFF, &specialPossible);
	StandardAI_DeriveDamageWithCertificate(1, 0, MOVE_STRENGTH, &damagePossible, TRUE);
	/* A public context that excludes the CFRU Badge modifier is a boundary
	 * oracle for the conservative interval, not an ownership observation. */
	gTrainerBattleOpponent_A = 0x400;
	IronmonAI_ProjectIncoming(1, MOVE_POUND, NULL, 0, 0xFFFF, &physicalAbsent);
	IronmonAI_ProjectIncoming(1, MOVE_EMBER, NULL, 0, 0xFFFF, &specialAbsent);
	StandardAI_DeriveDamageWithCertificate(1, 0, MOVE_STRENGTH, &damageAbsent, TRUE);
	assert(physicalPossible.maximum >= physicalAbsent.maximum);
	assert(specialPossible.maximum >= specialAbsent.maximum);
	assert(damagePossible.expected_damage <= damageAbsent.expected_damage);
	assert(damagePossible.opponent_hp_fraction_lost <= damageAbsent.opponent_hp_fraction_lost);
	puts("Ironmon possible Badge Speed/Attack/SpA/Defense bounds PASS");
}

static void StandardProductionBadgeRobustKO(void)
{
	struct StandardPolicyCandidate possible = {0}, absent = {0};
	struct StandardDamageEnvelope envelope;
	u16 attack;
	bool8 found = FALSE;
	Reset(); profile = TRAINER_AI_PROFILE_STANDARD; Certify();
	gBattleMons[0].hp = 5; gBattleMons[1].speed = 200;
	for (attack = 1; attack <= 500; ++attack)
	{
		gBattleMons[1].attack = attack;
		gTrainerBattleOpponent_A = 0x400;
		StandardAI_DeriveDamage(1, 0, MOVE_STRENGTH, &absent, &envelope);
		if (!absent.robust_safe_ko) continue;
		gTrainerBattleOpponent_A = 0;
		StandardAI_DeriveDamage(1, 0, MOVE_STRENGTH, &possible, &envelope);
		if (!possible.robust_safe_ko)
		{
			found = TRUE;
			break;
		}
	}
	assert(found);
	puts("Standard possible Badge defense cannot create a false robust KO PASS");
}

static void IronmonProductionResponseAndDispatch(void)
{
	struct IronmonPolicyObservation o, beforeReveal;
	Reset(); profile=TRAINER_AI_PROFILE_IRONMON_SMART;
	assert(IronmonAI_IsSupportedBattle());
	history.usedMoves[0][0]=MOVE_STRENGTH; /* recorded without a printed attack */
	IronmonAI_BuildObservation(1,TRUE,&o);
	assert(o.response_count==1 && o.responses[0].id==IRONMON_POLICY_UNKNOWN_RESPONSE
		&& o.responses[0].weight==1);
	beforeReveal=o;
	history.usedMoves[0][0]=MOVE_STRENGTH; newBattle.ai.ironmonMoveUseCounts[0][0]=3;
	IronmonAI_BuildObservation(1,TRUE,&o);
	assert(memcmp(&beforeReveal,&o,sizeof(o))!=0); /* legitimate public reveal */
	assert(o.response_count==2 && o.responses[0].id==MOVE_STRENGTH
		&& o.responses[0].weight==12 && o.responses[1].weight==4);
	history.usedMoves[0][1]=MOVE_TACKLE; newBattle.ai.ironmonMoveUseCounts[0][1]=1;
	IronmonAI_BuildObservation(1,TRUE,&o);
	assert(o.response_count==3 && o.responses[0].id==MOVE_TACKLE
		&& o.responses[0].weight==6 && o.responses[1].id==MOVE_STRENGTH
		&& o.responses[1].weight==12 && o.responses[2].weight==6);
	history.usedMoves[0][2]=MOVE_WATERGUN; newBattle.ai.ironmonMoveUseCounts[0][2]=1;
	history.usedMoves[0][3]=MOVE_EMBER; newBattle.ai.ironmonMoveUseCounts[0][3]=4;
	IronmonAI_BuildObservation(1,TRUE,&o);
	assert(o.response_count==4); /* All revealed: add-one weights, no UNKNOWN. */
	assert(o.responses[0].id==MOVE_TACKLE && o.responses[0].weight==2);
	assert(o.responses[1].id==MOVE_EMBER && o.responses[1].weight==5);
	assert(o.responses[2].id==MOVE_WATERGUN && o.responses[2].weight==2);
	assert(o.responses[3].id==MOVE_STRENGTH && o.responses[3].weight==4);
	profile=TRAINER_AI_PROFILE_STANDARD; assert(!IronmonAI_IsSupportedBattle());
	puts("Ironmon production response weights 100%/75%+25% and profile isolation PASS");
}

static void IronmonForcedReplacementTiming(void)
{
	struct IronmonPolicyObservation o;
	unsigned i, branch, sawVoluntaryIncoming=0, sawForced=0;
	Reset(); profile=TRAINER_AI_PROFILE_IRONMON_SMART; IronmonCertify();
	gEnemyParty[1].level=50; gEnemyParty[1].defense=100;
	gEnemyParty[1].spDefense=100; gEnemyParty[1].speed=100;
	history.usedMoves[0][0]=MOVE_STRENGTH;
	newBattle.ai.ironmonMoveUseCounts[0][0]=1;
	IronmonAI_BuildObservation(1,TRUE,&o);
	for(i=0;i<o.count;++i)
		if(o.candidates[i].floor.kind==STANDARD_POLICY_SWITCH
			&& o.candidates[i].floor.legal)
			for(branch=0;branch<o.candidates[i].response_count;++branch)
				if(o.candidates[i].responses[branch].response_id==MOVE_STRENGTH
					&& o.candidates[i].responses[branch].own_hp_fraction_lost
						> o.candidates[i].floor.own_hp_fraction_lost)
					sawVoluntaryIncoming=1;
	assert(sawVoluntaryIncoming);
	gBattleMons[1].hp=0;
	assert(IronmonAI_ChooseReplacement()==1);
	for(i=0;i<sIronmonObservation.count;++i)
		if(sIronmonObservation.candidates[i].floor.kind==STANDARD_POLICY_SWITCH
			&& sIronmonObservation.candidates[i].floor.legal)
		{
			struct IronmonPolicyCandidate* c=&sIronmonObservation.candidates[i];
			assert(c->floor.forced);
			for(branch=0;branch<c->response_count;++branch)
			{
				assert(c->responses[branch].net_faints==c->floor.net_faints);
				assert(c->responses[branch].own_hp_fraction_lost
					==c->floor.own_hp_fraction_lost);
				assert(c->responses[branch].entry_cost==c->floor.entry_cost);
			}
			sawForced=1;
		}
	assert(sawForced);
	puts("Ironmon entry timing: voluntary takes response; forced replacement does not PASS");
}

static struct IronmonPolicyCandidate* FindIronmonMove(
	struct IronmonPolicyObservation* o, u16 move)
{
	unsigned i;
	for (i = 0; i < o->count; ++i)
		if (o->candidates[i].floor.kind == STANDARD_POLICY_MOVE
			&& gBattleMons[1].moves[o->candidates[i].floor.id] == move)
			return &o->candidates[i];
	return NULL;
}

static struct IronmonPolicyBranch* FindIronmonBranch(
	struct IronmonPolicyCandidate* c, u16 response)
{
	unsigned i;
	for (i = 0; i < c->response_count; ++i)
		if (c->responses[i].response_id == response)
			return &c->responses[i];
	return NULL;
}

static void RevealIronmonResponse(u16 move)
{
	history.usedMoves[0][0] = move;
	newBattle.ai.ironmonMoveUseCounts[0][0] = 1;
}

static void IronmonProductionTurnOrderAndFaints(void)
{
	struct IronmonPolicyObservation o;
	struct IronmonPolicyCandidate* c;
	struct IronmonPolicyBranch* b;
	/* Opponent-first lethal: no outgoing trainer result survives. */
	Reset(); profile = TRAINER_AI_PROFILE_IRONMON_SMART; IronmonCertify();
	gBattleMons[1].moves[0] = MOVE_TACKLE; gBattleMons[1].hp = 10;
	gBattleMons[1].speed = 1; RevealIronmonResponse(MOVE_STRENGTH);
	IronmonAI_BuildObservation(1, TRUE, &o);
	c = FindIronmonMove(&o, MOVE_TACKLE); assert(c != NULL);
	b = FindIronmonBranch(c, MOVE_STRENGTH); assert(b != NULL);
	assert(b->net_faints == -1 && b->opponent_hp_fraction_lost == 0
		&& b->own_hp_fraction_lost == 256 && b->future_gain_undiscounted == 0);
	/* Trainer-first non-terminal action, then a certified response KO: retain
	 * the outgoing result while recording the own faint. */
	Reset(); profile = TRAINER_AI_PROFILE_IRONMON_SMART; IronmonCertify();
	gBattleMons[1].moves[0] = MOVE_TACKLE; gBattleMons[1].hp = 10;
	gBattleMons[1].speed = 200; RevealIronmonResponse(MOVE_STRENGTH);
	IronmonAI_BuildObservation(1, TRUE, &o);
	c = FindIronmonMove(&o, MOVE_TACKLE); assert(c != NULL);
	b = FindIronmonBranch(c, MOVE_STRENGTH); assert(b != NULL);
	assert(b->net_faints == -1 && b->opponent_hp_fraction_lost > 0
		&& b->own_hp_fraction_lost == 256);
	/* Trainer-first robust terminal KO: the response is not applied. */
	Reset(); profile = TRAINER_AI_PROFILE_IRONMON_SMART; IronmonCertify();
	gBattleMons[0].hp = 5; gBattleMons[1].moves[0] = MOVE_STRENGTH;
	gBattleMons[1].speed = 200; RevealIronmonResponse(MOVE_STRENGTH);
	IronmonAI_BuildObservation(1, TRUE, &o);
	c = FindIronmonMove(&o, MOVE_STRENGTH); assert(c != NULL && c->floor.robust_safe_ko);
	b = FindIronmonBranch(c, MOVE_STRENGTH); assert(b != NULL);
	assert(b->net_faints == 1 && b->opponent_hp_fraction_lost > 0
		&& b->own_hp_fraction_lost == c->floor.own_hp_fraction_lost);
	puts("Ironmon production order/faint sequencing A/B/C PASS");
}

static void IronmonProductionRecoveryRaces(void)
{
	struct IronmonPolicyObservation o;
	struct IronmonPolicyCandidate* c;
	struct IronmonPolicyBranch* b;
	/* Trainer first: pre-heal HP would be lethal, post-heal HP survives. */
	Reset(); profile = TRAINER_AI_PROFILE_IRONMON_SMART; IronmonCertify();
	gBattleMons[1].moves[0] = MOVE_RECOVER; gBattleMons[1].maxHP = 200;
	gBattleMons[1].defense = gBattleMons[1].spDefense = 500;
	gBattleMons[1].hp = 20; gBattleMons[1].speed = 200; RevealIronmonResponse(MOVE_POUND);
	IronmonAI_BuildObservation(1, TRUE, &o);
	c = FindIronmonMove(&o, MOVE_RECOVER); assert(c != NULL);
	b = FindIronmonBranch(c, MOVE_POUND); assert(b != NULL);
	assert(b->net_faints == 0 && b->own_hp_fraction_lost < 256
		&& b->future_gain_undiscounted == 40);
	/* Opponent first and lethal: recovery is never applied. */
	Reset(); profile = TRAINER_AI_PROFILE_IRONMON_SMART; IronmonCertify();
	gBattleMons[1].moves[0] = MOVE_RECOVER; gBattleMons[1].maxHP = 200;
	gBattleMons[1].defense = gBattleMons[1].spDefense = 500;
	gBattleMons[1].hp = 20; gBattleMons[1].speed = 1; RevealIronmonResponse(MOVE_POUND);
	IronmonAI_BuildObservation(1, TRUE, &o);
	c = FindIronmonMove(&o, MOVE_RECOVER); assert(c != NULL);
	b = FindIronmonBranch(c, MOVE_POUND); assert(b != NULL);
	assert(b->net_faints == -1 && b->own_hp_fraction_lost == 256
		&& b->future_gain_undiscounted == 0);
	/* Opponent first and nonlethal: heal amount/cap is derived after damage,
	 * so the net HP result differs from the stale pre-response floor amount. */
	Reset(); profile = TRAINER_AI_PROFILE_IRONMON_SMART; IronmonCertify();
	gBattleMons[1].moves[0] = MOVE_RECOVER; gBattleMons[1].maxHP = 200;
	gBattleMons[1].defense = gBattleMons[1].spDefense = 500;
	gBattleMons[1].hp = 120; gBattleMons[1].speed = 1; RevealIronmonResponse(MOVE_POUND);
	IronmonAI_BuildObservation(1, TRUE, &o);
	c = FindIronmonMove(&o, MOVE_RECOVER); assert(c != NULL);
	b = FindIronmonBranch(c, MOVE_POUND); assert(b != NULL);
	assert(b->net_faints == 0 && b->own_hp_fraction_lost > c->floor.own_hp_fraction_lost
		&& b->own_hp_fraction_lost < 0);
	puts("Ironmon production recovery order/cap/survival races PASS");
}

static void IronmonProductionVoluntaryHazardResponse(void)
{
	struct IronmonPolicyObservation o;
	struct IronmonPolicyCandidate* c;
	struct IronmonPolicyBranch* b;
	struct IronmonIncoming direct;
	Reset(); profile = TRAINER_AI_PROFILE_IRONMON_SMART; IronmonCertify();
	gSideStatuses[1] = SIDE_STATUS_SPIKES; gSideTimers[1].spikesAmount = 3;
	gEnemyParty[1].species = SPECIES_RATTATA; gEnemyParty[1].hp = gEnemyParty[1].maxHP = 40;
	gEnemyParty[1].defense = gEnemyParty[1].spDefense = 400;
	gEnemyParty[1].moves[0] = MOVE_POUND; gEnemyParty[1].pp[0] = 10;
	/* The revealed response alone survives from pre-entry HP. */
	gBattleMons[1].hp = gBattleMons[1].maxHP = 40;
	gBattleMons[1].defense = gBattleMons[1].spDefense = 400;
	IronmonAI_ProjectIncoming(1, MOVE_POUND, NULL, -128, 0xFFFF, &direct);
	assert(direct.survives);
	RevealIronmonResponse(MOVE_POUND);
	IronmonAI_BuildObservation(1, TRUE, &o);
	c = NULL;
	for (unsigned i = 0; i < o.count; ++i)
		if (o.candidates[i].floor.kind == STANDARD_POLICY_SWITCH
			&& o.candidates[i].floor.switch_to == 1)
			c = &o.candidates[i];
	assert(c != NULL && c->floor.entry_survives);
	b = FindIronmonBranch(c, MOVE_POUND); assert(b != NULL);
	assert(b->net_faints == -1 && b->own_hp_fraction_lost == 256);
	puts("Ironmon voluntary entry hazards+response KO sequencing PASS");
}

static void IronmonProductionOrderCertificates(void)
{
	struct IronmonIncoming in;
	Reset(); profile = TRAINER_AI_PROFILE_IRONMON_SMART; IronmonCertify();
	/* Ordinary field: definitely faster, then definitely slower. */
	gBattleMons[1].speed = 200;
	IronmonAI_ProjectIncoming(1, MOVE_POUND, NULL, 0, 0xFFFF, &in);
	assert(in.order_known && !in.opponent_first);
	gBattleMons[1].speed = 1;
	IronmonAI_ProjectIncoming(1, MOVE_POUND, NULL, 0, 0xFFFF, &in);
	assert(in.order_known && in.opponent_first);
	/* Badge ownership is private and irrelevant. In an ordinary public battle
	 * context, the possible 1.1x player speed boost widens the upper interval,
	 * so a previously clear comparison becomes UNKNOWN. */
	testBadgeMask = 0x0F; gBattleMons[1].speed = 140;
	IronmonAI_ProjectIncoming(1, MOVE_POUND, NULL, 0, 0xFFFF, &in);
	assert(!in.order_known);
	/* A public context where the CFRU boost cannot apply removes that possible
	 * widening without consulting the private ownership mask. */
	gTrainerBattleOpponent_A = 0x400;
	IronmonAI_ProjectIncoming(1, MOVE_POUND, NULL, 0, 0xFFFF, &in);
	assert(in.order_known && !in.opponent_first);
	gTrainerBattleOpponent_A = 0;
	/* Stable Trick Room reverses the certified comparisons. */
	newBattle.TrickRoomTimer = 3; gBattleMons[1].speed = 1;
	IronmonAI_ProjectIncoming(1, MOVE_POUND, NULL, 0, 0xFFFF, &in);
	assert(in.order_known && !in.opponent_first);
	gBattleMons[1].speed = 200;
	IronmonAI_ProjectIncoming(1, MOVE_POUND, NULL, 0, 0xFFFF, &in);
	assert(in.order_known && in.opponent_first);
	/* Ties/interval overlap and an expiring Trick Room remain UNKNOWN. */
	newBattle.TrickRoomTimer = 0; gBattleMons[1].speed = 100;
	IronmonAI_ProjectIncoming(1, MOVE_POUND, NULL, 0, 0xFFFF, &in);
	assert(!in.order_known);
	newBattle.TrickRoomTimer = 1; gBattleMons[1].speed = 200;
	IronmonAI_ProjectIncoming(1, MOVE_POUND, NULL, 0, 0xFFFF, &in);
	assert(!in.order_known);
	/* Unmodeled public speed/priority modifiers fail closed before any order
	 * claim and therefore cannot create survival/tactical future credit. */
	Reset(); profile = TRAINER_AI_PROFILE_IRONMON_SMART; IronmonCertify();
	newBattle.TailwindTimers[1] = 1; gBattleMons[1].speed = 200;
	IronmonAI_ProjectIncoming(1, MOVE_QUICKATTACK, NULL, 0, 0xFFFF, &in);
	assert(!in.modifiers_certified && !in.order_known);
	newBattle.TailwindTimers[1] = 0; gSideStatuses[0] = SIDE_STATUS_REFLECT;
	IronmonAI_ProjectIncoming(1, MOVE_POUND, NULL, 0, 0xFFFF, &in);
	assert(!in.modifiers_certified && !in.order_known);
	Reset(); profile = TRAINER_AI_PROFILE_IRONMON_SMART; IronmonCertify();
	gBattleMons[1].status2 = STATUS2_SUBSTITUTE;
	IronmonAI_ProjectIncoming(1, MOVE_POUND, NULL, 0, 0xFFFF, &in);
	assert(!in.modifiers_certified && !in.order_known);
	puts("Ironmon order/Trick Room/modifier certificates PASS");
}

static void IronmonProductionMatchingSetup(void)
{
	struct IronmonPolicyObservation o;
	struct IronmonPolicyCandidate* c;
	struct IronmonPolicyBranch* b;
	struct StandardSetupFollowup followup;
	/* Same physical follow-up owns the 3HKO -> 2HKO transition. */
	Reset(); profile = TRAINER_AI_PROFILE_IRONMON_SMART; IronmonCertify();
	gBattleMons[0].hp = gBattleMons[0].maxHP = 100;
	gBattleMons[1].hp = gBattleMons[1].maxHP = 400;
	gBattleMons[1].attack = 30; gBattleMons[1].speed = 200;
	gBattleMons[1].moves[0] = MOVE_SWORDSDANCE;
	gBattleMons[1].moves[1] = MOVE_STRENGTH; gBattleMons[1].pp[0] = gBattleMons[1].pp[1] = 10;
	{
		u16 attack;
		for (attack = 30; attack <= 300; ++attack)
		{
			gBattleMons[1].attack = attack;
			if (StandardAI_FindSetupFollowup(1, 0, STANDARD_EFFECT_ATTACK_UP, 8, &followup)
				&& followup.before_fraction * 2 < 256
				&& followup.before_fraction * 3 >= 256
				&& followup.after_fraction * 2 >= 256)
				break;
		}
		assert(attack <= 300);
	}
	assert(followup.move == MOVE_STRENGTH && followup.split == SPLIT_PHYSICAL
		&& followup.before_fraction * 2 < 256 && followup.before_fraction * 3 >= 256
		&& followup.after_fraction * 2 >= 256);
	RevealIronmonResponse(MOVE_POUND); IronmonAI_BuildObservation(1, TRUE, &o);
	c = FindIronmonMove(&o, MOVE_SWORDSDANCE); assert(c != NULL);
	b = FindIronmonBranch(c, MOVE_POUND); assert(b != NULL);
	assert(b->future_gain_undiscounted > 0);
	/* Matching special follow-up. */
	Reset(); profile = TRAINER_AI_PROFILE_IRONMON_SMART; IronmonCertify();
	gBattleMons[0].hp = gBattleMons[0].maxHP = 100;
	gBattleMons[1].hp = gBattleMons[1].maxHP = 400;
	gBattleMons[1].spAttack = 30; gBattleMons[1].speed = 200;
	gBattleMons[1].moves[0] = MOVE_NASTYPLOT;
	gBattleMons[1].moves[1] = MOVE_EMBER; gBattleMons[1].pp[0] = gBattleMons[1].pp[1] = 10;
	{
		u16 specialAttack;
		for (specialAttack = 30; specialAttack <= 300; ++specialAttack)
		{
			gBattleMons[1].spAttack = specialAttack;
			if (StandardAI_FindSetupFollowup(1, 0, STANDARD_EFFECT_SPECIAL_ATTACK_UP, 8, &followup)
				&& followup.move == MOVE_EMBER && followup.split == SPLIT_SPECIAL
				&& followup.before_fraction * 2 < 256
				&& followup.before_fraction * 3 >= 256
				&& followup.after_fraction * 2 >= 256)
				break;
		}
		assert(specialAttack <= 300);
	}
	RevealIronmonResponse(MOVE_POUND); IronmonAI_BuildObservation(1, TRUE, &o);
	c = FindIronmonMove(&o, MOVE_NASTYPLOT); assert(c != NULL);
	b = FindIronmonBranch(c, MOVE_POUND); assert(b != NULL && b->future_gain_undiscounted > 0);
	puts("Ironmon matching physical/special setup thresholds PASS");
}

static void IronmonProductionSetupMismatchAndOrder(void)
{
	struct IronmonPolicyObservation o;
	struct IronmonPolicyCandidate* c;
	struct IronmonPolicyBranch* b;
	/* Strongest current attack is special; Attack-Up has only a weak physical
	 * follow-up and therefore cannot claim a 3HKO -> 2HKO line. */
	Reset(); profile = TRAINER_AI_PROFILE_IRONMON_SMART; IronmonCertify();
	gBattleMons[0].hp = gBattleMons[0].maxHP = 100;
	gBattleMons[1].hp = gBattleMons[1].maxHP = 200; gBattleMons[1].attack = 30;
	gBattleMons[1].spAttack = 300; gBattleMons[1].speed = 200;
	gBattleMons[1].moves[0] = MOVE_SWORDSDANCE; gBattleMons[1].moves[1] = MOVE_STRENGTH;
	gBattleMons[1].moves[2] = MOVE_EMBER; gBattleMons[1].pp[0] = gBattleMons[1].pp[1]
		= gBattleMons[1].pp[2] = 10;
	RevealIronmonResponse(MOVE_POUND); IronmonAI_BuildObservation(1, TRUE, &o);
	c = FindIronmonMove(&o, MOVE_SWORDSDANCE); assert(c != NULL);
	b = FindIronmonBranch(c, MOVE_POUND); assert(b != NULL && b->future_gain_undiscounted == 0);
	/* Reverse mismatch: strongest current attack is physical; Special Attack-Up
	 * improves only a weak special follow-up. */
	Reset(); profile = TRAINER_AI_PROFILE_IRONMON_SMART; IronmonCertify();
	gBattleMons[0].hp = gBattleMons[0].maxHP = 100;
	gBattleMons[1].hp = gBattleMons[1].maxHP = 200; gBattleMons[1].attack = 300;
	gBattleMons[1].spAttack = 30; gBattleMons[1].speed = 200;
	gBattleMons[1].moves[0] = MOVE_NASTYPLOT; gBattleMons[1].moves[1] = MOVE_EMBER;
	gBattleMons[1].moves[2] = MOVE_STRENGTH; gBattleMons[1].pp[0] = gBattleMons[1].pp[1]
		= gBattleMons[1].pp[2] = 10;
	RevealIronmonResponse(MOVE_POUND); IronmonAI_BuildObservation(1, TRUE, &o);
	c = FindIronmonMove(&o, MOVE_NASTYPLOT); assert(c != NULL);
	b = FindIronmonBranch(c, MOVE_POUND); assert(b != NULL && b->future_gain_undiscounted == 0);
	/* A matching threshold is still conservative when the next action's order
	 * interval overlaps. */
	Reset(); profile = TRAINER_AI_PROFILE_IRONMON_SMART; IronmonCertify();
	gBattleMons[0].hp = gBattleMons[0].maxHP = 100;
	gBattleMons[1].hp = gBattleMons[1].maxHP = 200; gBattleMons[1].attack = 0;
	gBattleMons[1].speed = 100; gBattleMons[1].moves[0] = MOVE_SWORDSDANCE;
	gBattleMons[1].moves[1] = MOVE_STRENGTH; gBattleMons[1].pp[0] = gBattleMons[1].pp[1] = 10;
	{
		u16 attack;
		struct StandardSetupFollowup followup;
		for (attack = 30; attack <= 300; ++attack)
		{
			gBattleMons[1].attack = attack;
			if (StandardAI_FindSetupFollowup(1, 0, STANDARD_EFFECT_ATTACK_UP, 8, &followup)
				&& followup.before_fraction * 2 < 256
				&& followup.before_fraction * 3 >= 256
				&& followup.after_fraction * 2 >= 256)
				break;
		}
		assert(attack <= 300);
	}
	RevealIronmonResponse(MOVE_POUND); IronmonAI_BuildObservation(1, TRUE, &o);
	c = FindIronmonMove(&o, MOVE_SWORDSDANCE); assert(c != NULL);
	b = FindIronmonBranch(c, MOVE_POUND); assert(b != NULL && b->future_gain_undiscounted == 0);
	puts("Ironmon setup split/order mismatch rejection PASS");
}

static void IronmonProductionUnsupportedConservative(void)
{
	struct IronmonPolicyObservation o;
	struct IronmonPolicyCandidate* c;
	struct IronmonPolicyBranch* b;
	Reset(); profile = TRAINER_AI_PROFILE_IRONMON_SMART; IronmonCertify();
	gBattleMons[1].moves[0] = MOVE_PROTECT; gBattleMons[1].pp[0] = 10;
	RevealIronmonResponse(MOVE_POUND); IronmonAI_BuildObservation(1, TRUE, &o);
	c = FindIronmonMove(&o, MOVE_PROTECT); assert(c != NULL);
	b = FindIronmonBranch(c, MOVE_POUND); assert(b != NULL && b->future_gain_undiscounted == 0);
	puts("Ironmon unsupported Protect timing remains conservative PASS");
}

int main(void)
{
	Behavior(); Twins(); EnvelopeOracle(); Dispatch(); HazardsAndReplacement(); MarginalBehavior();
	ArithmeticBounds(); IronmonPublicCounts(); IronmonProductionTwins(); IronmonProductionResponseAndDispatch();
	IronmonProductionBadgeTwins();
	IronmonProductionBadgeBounds();
	StandardProductionBadgeRobustKO();
	IronmonForcedReplacementTiming(); IronmonProductionTurnOrderAndFaints();
	IronmonProductionRecoveryRaces();
	IronmonProductionVoluntaryHazardResponse();
	IronmonProductionOrderCertificates();
	IronmonProductionMatchingSetup();
	IronmonProductionSetupMismatchAndOrder();
	IronmonProductionUnsupportedConservative();
	return 0;
}
