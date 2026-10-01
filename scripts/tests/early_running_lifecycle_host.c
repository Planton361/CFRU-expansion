/* #583: actual source functions are extracted by the runner into
 * early_running_functions.inc. Only engine dependencies are synthetic. */
#include "../../src/config.h"
#include "global.h"
#include "constants/map_types.h"
#include "new/settings.h"
#include <assert.h>
#include <stdio.h>

#ifdef FLAG_RUNNING_ENABLED
#error Native early running must have no progression gate
#endif
#ifndef FLAG_AUTO_RUN
#error Auto-Run must remain enabled
#endif
#ifndef CAN_RUN_IN_BUILDINGS
#error Indoor running must remain enabled
#endif

/* Minimal field dependencies; SaveBlocks and constants use actual headers. */
struct MapHeader gMapHeader;
struct EventObject gEventObjects[NUM_FIELD_OBJECTS];
static struct PlayerAvatar playerAvatar;
static const void *lastScript;
#define gPlayerAvatar (&playerAvatar)
#define ITEM_NONE 0
static struct SaveBlock1 save1;
static struct SaveBlock2 save2;
struct SaveBlock1 *gSaveBlock1 = &save1;
struct SaveBlock2 *gSaveBlock2 = &save2;
static u16 vars[0x5200];
static u8 flags[0x1000];
static u8 dexNav, tileBlocked, avatarFlags;
static unsigned writes;
static const u8 EventScript_SecondBagItemCanBeRegisteredToL[] = {1};
static const u8 SystemScript_EnableAutoRun[] = {2};
static const u8 SystemScript_DisableAutoRun[] = {3};
static const u8 SystemScript_EnableBikeTurboBoost[] = {4};
static const u8 SystemScript_DisableBikeTurboBoost[] = {5};
static const u8 SystemScript_EnableSurfTurboBoost[] = {6};
static const u8 SystemScript_DisableSurfTurboBoost[] = {7};

bool8 FlagGet(u16 flag) { assert(flag != 0x82F); return flags[flag]; }
u8 FlagSet(u16 flag) { assert(flag != 0x82F); flags[flag] = TRUE; return TRUE; }
u8 FlagClear(u16 flag) { assert(flag != 0x82F); flags[flag] = FALSE; return FALSE; }
bool8 VarSet(u16 var, u16 value) { vars[var] = value; ++writes; return TRUE; }
static bool8 IsDexNavHudActive(void) { return dexNav; }
static bool8 MetatileBehavior_IsRunningDisallowed(u8 tile) { (void)tile; return tileBlocked; }
static bool8 TestPlayerAvatarFlags(u8 mask) { return !!(avatarFlags & mask); }
static bool8 CheckBagHasItem(u16 item, u16 count) { (void)item; (void)count; return FALSE; }
static void UseRegisteredItem(u16 item) { (void)item; }
static void RemoveRegisteredItem(u16 item) { (void)item; }
static void ScriptContext1_SetupScript(const u8 *script) { lastScript = script; }
static void ScriptContext2_Enable(void) {}
static void DismissMapNamePopup(void) {}
static bool8 IsRunningDisallowed(u8 tile);
static bool8 IsRunningDisallowedByMetatile(u8 tile);
#include "early_running_functions.inc"

int main(void)
{
    /* Running works before any settings/flag initialization, including when
     * legacy progression flag 0x82F is unset. */
    gMapHeader.mapType = MAP_TYPE_INDOOR;
    for (unsigned autoRun = 0; autoRun < 2; ++autoRun)
    {
        flags[FLAG_AUTO_RUN] = autoRun;
        for (unsigned b = 0; b < 2; ++b)
        {
            u16 keys = b ? B_BUTTON : 0;
            assert(ShouldPlayerRun(keys) == (autoRun != b));
            dexNav = TRUE;
            assert(!ShouldPlayerRun(keys));
            dexNav = FALSE;
            tileBlocked = TRUE;
            assert(!ShouldPlayerRun(keys));
            tileBlocked = FALSE;
            gMapHeader.mapType = MAP_TYPE_UNDERWATER;
            assert(!ShouldPlayerRun(keys));
            gMapHeader.mapType = MAP_TYPE_INDOOR;
        }
    }
    flags[FLAG_AUTO_RUN] = FALSE;
    assert(StartLButtonFunc());
    assert(flags[FLAG_AUTO_RUN] && lastScript == SystemScript_EnableAutoRun);
    assert(!ShouldPlayerRun(B_BUTTON));
    assert(ShouldPlayerRun(0));
    assert(StartLButtonFunc());
    assert(!flags[FLAG_AUTO_RUN] && lastScript == SystemScript_DisableAutoRun);
    dexNav = TRUE;
    assert(!StartLButtonFunc());
    dexNav = FALSE;
    save2.optionsButtonMode = OPTIONS_BUTTON_MODE_L_EQUALS_A;
    assert(!StartLButtonFunc());
    save2.optionsButtonMode = OPTIONS_BUTTON_MODE_AUTO_RUN;
    puts("Actual native B/Auto-Run truth table, L toggle, indoor and restrictions: PASS");

    /* Public lifecycle proof binds this call to AFTER all resets. The
     * negative witness models InitEventData erasing premature defaults. */
    ApplyFreshNewGameSettings();
    memset(vars, 0, sizeof(vars));
    assert(vars[VAR_GAME_DIFFICULTY] != OPTIONS_VANILLA_DIFFICULTY);
    writes = 0;
    ApplyFreshNewGameSettings();
    assert(writes == 4);
    assert(vars[VAR_GAME_DIFFICULTY] == OPTIONS_VANILLA_DIFFICULTY);
    assert(vars[VAR_TRAINER_LEVEL_SCALING_MODE] == TRAINER_LEVEL_SCALING_OFF + 1);
    assert(vars[VAR_WILD_LEVEL_SCALING] == 0);
    assert(vars[VAR_TRAINER_AI_PROFILE] == TRAINER_AI_PROFILE_STANDARD + 1);
    assert(!flags[FLAG_AUTO_RUN]);
    /* Existing saved values remain untouched by field movement and L input.
     * Existing-save lifecycle exclusion is source-proven, not a fake latch. */
    vars[VAR_GAME_DIFFICULTY] = 0xBEEF;
    vars[VAR_TRAINER_LEVEL_SCALING_MODE] = 5;
    vars[VAR_WILD_LEVEL_SCALING] = 2;
    vars[VAR_TRAINER_AI_PROFILE] = 0xFFFF;
    assert(StartLButtonFunc());
    assert(ShouldPlayerRun(0));
    assert(writes == 4);
    assert(vars[VAR_GAME_DIFFICULTY] == 0xBEEF);
    assert(vars[VAR_TRAINER_LEVEL_SCALING_MODE] == 5);
    assert(vars[VAR_WILD_LEVEL_SCALING] == 2);
    assert(vars[VAR_TRAINER_AI_PROFILE] == 0xFFFF);
    ApplyIronmonSmartSettingsPreset();
    assert(vars[VAR_TRAINER_AI_PROFILE] == TRAINER_AI_PROFILE_IRONMON_SMART + 1);
    assert(flags[FLAG_AUTO_RUN]);
    puts("Four fresh Vars, reset witness, existing field preservation, separate preset: PASS");
    return 0;
}
