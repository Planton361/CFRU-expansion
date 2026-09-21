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
u32 gStatuses3[4], gBattleTypeFlags = BATTLE_TYPE_TRAINER;
u32 gRngValue, gRng2Value;
u8 gChosenActionByBank[4];
static enum TrainerAIProfile profile = TRAINER_AI_PROFILE_STANDARD;

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
	memset(gDisableStructs, 0, sizeof(gDisableStructs));
	memset(gStatuses3, 0, sizeof(gStatuses3));
	memset(gSideStatuses, 0, sizeof(gSideStatuses));
	memset(gSideTimers, 0, sizeof(gSideTimers));
	memset(gLockedMoves, 0, sizeof(gLockedMoves));
	resources.battleHistory = (void*)&history;
	battle.battlerPreventingSwitchout = 0xFF;
	gBattleTypeFlags = BATTLE_TYPE_TRAINER;
	gBattleWeather = 0;
	for (i=0; i<2; ++i)
	{
		gBattleMons[i].species = SPECIES_RATTATA;
		newBattle.ai.standardDisplayedSpecies[i] = SPECIES_RATTATA;
		gBattleMons[i].level = 50;
		gBattleMons[i].hp = gBattleMons[i].maxHP = 100;
		gBattleMons[i].attack = gBattleMons[i].spAttack = 150;
		gBattleMons[i].type1 = gBattleMons[i].type2 = TYPE_NORMAL;
		gBattleMons[i].type3 = NUMBER_OF_MON_TYPES;
		memset(gBattleMons[i].statStages, 6, sizeof(gBattleMons[i].statStages));
		gBattlerPartyIndexes[i] = 0;
	}
	testBaseStats[SPECIES_RATTATA].baseHP = 30;
	testBaseStats[SPECIES_RATTATA].baseDefense = 35;
	testBaseStats[SPECIES_RATTATA].baseSpDefense = 35;
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
	unsigned mode,field,k,count=0;
	for (mode=0;mode<5;++mode) for(field=0;field<7;++field) for(k=1;k<=32;++k)
	{
		u32 sa=12345,sb=12345;
		Reset();
		if(mode==1) Certify();
		if(mode==2) memset(gBattleMons[1].pp,0,4);
		if(mode==3) {gSideStatuses[1]=SIDE_STATUS_SPIKES; gSideTimers[1].srAmount=1; gSideTimers[1].spikesAmount=3;}
		if(mode==4) gBattleMons[1].attack=1;
		Build(&a,&ra,&sa);
		StandardAI_DeriveDamage(1,0,MOVE_STRENGTH,&a.candidates[0],&ea);
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
		}
		Build(&b,&rb,&sb);
		StandardAI_DeriveDamage(1,0,MOVE_STRENGTH,&b.candidates[0],&eb);
		assert(memcmp(&a,&b,sizeof(a))==0);
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
	Reset(); gBattleMons[0].type1=gBattleMons[0].type2=TYPE_GHOST;
	{u32 seed=3; Build(&b,&rb,&seed);}
	assert(b.candidates[0].known_no_effect && !b.candidates[0].productive);
	Reset(); gBattleMons[0].hp=1;
	{u32 seed=3; Build(&a,&ra,&seed);}
	gBattleMons[0].hp=3; /* Same minimum one-pixel public bar. */
	{u32 seed=3; Build(&b,&rb,&seed);}
	assert(memcmp(&a,&b,sizeof(a))==0 && memcmp(&ra,&rb,sizeof(ra))==0);
	printf("production adapter twins: %u pairs, 0 mismatches; public reveal PASS\n",count);
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
	assert(newBattle.ai.standardPolicyRng[1]==(STANDARD_AI_DEFAULT_SEED^1));
	puts("production hazards/replacement: exact entry costs, entry KO, forced/singleton RNG PASS");
}

int main(void)
{
	Behavior(); Twins(); EnvelopeOracle(); Dispatch(); HazardsAndReplacement();
	return 0;
}
