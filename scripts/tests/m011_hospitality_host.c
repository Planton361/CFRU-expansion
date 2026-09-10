#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef uint8_t u8;
typedef uint16_t u16;
typedef int32_t s32;
typedef u8 bool8;
#define TRUE 1
#define FALSE 0
#define SPECIES_SINISTCHA 0x589
#define SPECIES_SINISTCHA_MASTERPIECE 0x58A
#define ABILITY_HOSPITALITY 0x6C
struct Mon { u16 hp, maxHP, species; u8 ability; } gBattleMons[4];
u8 gBattlersCount, gAbsentBattlerFlags, gBankTarget, gLastUsedAbility;
struct {u8 bank;} gBattleScripting;
const u8 gBitTable[4] = {1, 2, 4, 8};
const u8 BattleScript_Hospitality[] = {1};
s32 gBattleMoveDamage;
static int doubles, scheduled, hpReads;
static u8 healBlocked;
#define IS_DOUBLE_BATTLE doubles
#define PARTNER(bank) ((bank) ^ 2)
#define BATTLER_ALIVE(bank) (gBattleMons[bank].hp > 0)
#define BATTLER_MAX_HP(bank) (gBattleMons[bank].hp == gBattleMons[bank].maxHP)
#define SPECIES(bank) gBattleMons[bank].species
#define ABILITY(bank) gBattleMons[bank].ability
#define MathMax(a,b) ((a) > (b) ? (a) : (b))
#define MathMin(a,b) ((a) < (b) ? (a) : (b))
static u16 GetBaseMaxHP(u8 bank) { assert(bank < gBattlersCount); hpReads++; return gBattleMons[bank].maxHP; }
static bool8 IsHealBlocked(u8 bank) { assert(bank < gBattlersCount); return healBlocked & gBitTable[bank]; }
static void BattleScriptPushCursorAndCallback(const u8 *script) { assert(script == BattleScript_Hospitality); scheduled++; }
#include "hospitality_impl.c"
static u8 startBank, startState;
static u8 gBanksByTurnOrder[4] = {0, 1, 2, 3};
static struct { u8 switchInEffectsState; } entryState, *gNewBS = &entryState;
static u8 gActiveBattler;
#include "hospitality_entry_impl.c"
static void reset(void) {
    memset(gBattleMons, 0, sizeof(gBattleMons));
    for (int i = 0; i < 4; i++) gBattleMons[i] = (struct Mon){50, 100, SPECIES_SINISTCHA, ABILITY_HOSPITALITY};
    doubles = 1; gBattlersCount = 4; gAbsentBattlerFlags = healBlocked = scheduled = hpReads = 0;
    gBankTarget = 3; gBattleMoveDamage = 123;
}
static void apply(void) { gBattleMons[gBankTarget].hp -= gBattleMoveDamage; }
int main(void) {
    reset(); doubles = 0; gBattlersCount = 2;
    assert(!TryActivateHospitality(0) && !TryActivateHospitality(1));
    assert(hpReads == 0 && scheduled == 0 && gBattleMoveDamage == 123);
    reset(); assert(!TryActivateHospitality(4)); assert(!TryActivateHospitality(255));
    for (u8 b = 0; b < 4; b++) {
        reset(); gBattleMons[b].species = b & 1 ? SPECIES_SINISTCHA_MASTERPIECE : SPECIES_SINISTCHA;
        assert(TryActivateHospitality(b)); assert(gBankTarget == (b ^ 2));
        assert(gBattleScripting.bank == b && gBattleMoveDamage == -25);
        apply(); assert(gBattleMons[b ^ 2].hp == 75 && gBattleMons[b].hp == 50);
    }
    reset(); gBattleMons[2].hp = 100; assert(!TryActivateHospitality(0));
    reset(); gBattleMons[2].hp = 0; assert(!TryActivateHospitality(0));
    reset(); gAbsentBattlerFlags = 4; assert(!TryActivateHospitality(0));
    reset(); gBattlersCount = 2; assert(!TryActivateHospitality(0));
    reset(); gBattleMons[0].hp = 0; assert(!TryActivateHospitality(0));
    reset(); gAbsentBattlerFlags = 1; assert(!TryActivateHospitality(0));
    reset(); healBlocked = 4; assert(!TryActivateHospitality(0));
    reset(); gBattleMons[2].hp = 90; assert(TryActivateHospitality(0));
    assert(gBattleMoveDamage == -10); apply(); assert(gBattleMons[2].hp == 100);
    reset(); gBattleMons[2].maxHP = 103; assert(TryActivateHospitality(0)); assert(gBattleMoveDamage == -25);
    reset(); gBattleMons[2].hp = 1; gBattleMons[2].maxHP = 3;
    assert(TryActivateHospitality(0)); assert(gBattleMoveDamage == -1);
    reset(); gBattleMons[0].ability = 0x61; assert(!TryActivateHospitality(0)); // Heatproof
    reset(); gBattleMons[0].ability = 0; assert(!TryActivateHospitality(0)); // suppressed
    reset(); gBattleMons[0].species = 113; assert(!TryActivateHospitality(0)); // ordinary Healer
    reset(); assert(TryActivateHospitality(0)); apply(); assert(TryActivateHospitality(2)); apply();
    assert(scheduled == 2 && gBattleMons[0].hp == 75 && gBattleMons[2].hp == 75);
    reset(); gBattleMons[1].ability = gBattleMons[3].ability = 0;
    startBank = startState = 0;
    runStart(); assert(scheduled == 1); apply();
    runStart(); assert(scheduled == 2); apply();
    runStart(); runStart(); assert(scheduled == 2 && startState == 1);
    reset(); gActiveBattler = 0; entryState.switchInEffectsState = 0;
    runSwitch(); assert(scheduled == 1); apply();
    runSwitch(); runSwitch(); assert(scheduled == 1);
    entryState.switchInEffectsState = 0; // A fresh entry heals again.
    runSwitch(); assert(scheduled == 2); apply();
    assert(gBattleMons[2].hp == 100);
    puts("M-011 actual entry phases: battle start, switching, repeat entry, no repeat on resume PASS");
    puts("M-011 production helper: singles, doubles/all positions, fraction/clamp, invalid/absent/fainted, Heatproof/Healer/suppression, two users PASS");
}
