#include "../../src/config.h"
#include "../../include/new/settings.h"

#include <assert.h>
#include <stdio.h>

static u16 syntheticVars[0x5200];

u16 VarGet(u16 var)
{
    return syntheticVars[var];
}

bool8 VarSet(u16 var, u16 value)
{
    syntheticVars[var] = value;
    return TRUE;
}

static void ResetSyntheticVars(u16 value)
{
    for (u32 i = 0; i < ARRAY_COUNT(syntheticVars); ++i)
        syntheticVars[i] = value;
}

static void TestRawMappingAndPreservation(void)
{
    for (u16 raw = 0; raw < TRAINER_AI_PROFILE_MENU_OPTION_COUNT; ++raw)
    {
        assert(TrainerAIProfileRawToMenuSelection(raw) == raw);
        assert(TrainerAIProfileMenuSelectionToRaw(raw) == raw);
        assert(TrainerAIProfileRawAfterOptions(raw, 0, FALSE) == raw);
    }

    assert(TrainerAIProfileRawToMenuSelection(9) == 0);
    assert(TrainerAIProfileRawToMenuSelection(0xFFFF) == 0);
    assert(TrainerAIProfileMenuSelectionToRaw(9) == 0);
    assert(TrainerAIProfileRawAfterOptions(9, 0, FALSE) == 9);
    assert(TrainerAIProfileRawAfterOptions(0xFFFF, 8, FALSE) == 0xFFFF);
    assert(TrainerAIProfileRawAfterOptions(0xFFFF, 0, TRUE) == 0);
    assert(TrainerAIProfileRawAfterOptions(0xFFFF, 8, TRUE) == 8);

    puts("Trainer AI raw 0..8 mapping, legacy Auto, and unknown untouched-raw preservation: PASS");
}

static void TestFreshDefaults(void)
{
    const u16 unrelatedVar = 0x5154;

    ResetSyntheticVars(0xBEEF);
    syntheticVars[unrelatedVar] = 0x1234;
    ApplyFreshNewGameSettings();

    assert(syntheticVars[VAR_GAME_DIFFICULTY] == OPTIONS_VANILLA_DIFFICULTY);
    assert(syntheticVars[VAR_TRAINER_LEVEL_SCALING_MODE] == TRAINER_LEVEL_SCALING_OFF + 1);
    assert(syntheticVars[VAR_WILD_LEVEL_SCALING] == 0);
    assert(syntheticVars[VAR_TRAINER_AI_PROFILE] == TRAINER_AI_PROFILE_STANDARD + 1);
    assert(syntheticVars[unrelatedVar] == 0x1234);

    puts("Fresh-default raw witness: difficulty=4 trainer-scale=1 wild-scale=0 trainer-ai=7; unrelated VARs unchanged: PASS");
}

static void TestIronmonPreset(void)
{
    const u16 hardCapVar = 0x515C;
    const u16 nuzlockeFlag = 0x1900;
    const u16 itemRestrictionsVar = 0x5190;
    const u16 battleStyleVar = 0x5191;

    ResetSyntheticVars(0xBEEF);
    syntheticVars[hardCapVar] = 2;
    syntheticVars[nuzlockeFlag] = 1;
    syntheticVars[itemRestrictionsVar] = OPTIONS_ITEM_RESTRICTIONS_AI_ONLY;
    syntheticVars[battleStyleVar] = OPTIONS_BATTLE_STYLE_SET;
    ApplyIronmonSmartSettingsPreset();

    assert(syntheticVars[VAR_GAME_DIFFICULTY] == OPTIONS_VANILLA_DIFFICULTY);
    assert(syntheticVars[VAR_TRAINER_LEVEL_SCALING_MODE] == TRAINER_LEVEL_SCALING_OFF + 1);
    assert(syntheticVars[VAR_WILD_LEVEL_SCALING] == 0);
    assert(syntheticVars[VAR_TRAINER_AI_PROFILE] == TRAINER_AI_PROFILE_IRONMON_SMART + 1);
    assert(syntheticVars[hardCapVar] == 2);
    assert(syntheticVars[nuzlockeFlag] == 1);
    assert(syntheticVars[itemRestrictionsVar] == OPTIONS_ITEM_RESTRICTIONS_AI_ONLY);
    assert(syntheticVars[battleStyleVar] == OPTIONS_BATTLE_STYLE_SET);

    puts("Ironmon preset mapping: difficulty=4 trainer-scale=1 wild-scale=0 trainer-ai=8; unrelated rules unchanged: PASS");
}

int main(void)
{
    assert(TRAINER_AI_PROFILE_MENU_OPTION_COUNT == 9);
    TestRawMappingAndPreservation();
    TestFreshDefaults();
    TestIronmonPreset();
    puts("settings/defaults source-owned host tests: PASS");
    return 0;
}
