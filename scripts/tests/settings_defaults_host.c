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

static void TestDifficultyMappingAndPreservation(void)
{
    static const u16 knownRaw[] = {0, 1, 2, 3, 4};
    static const u16 knownSelections[] = {2, 1, 3, 4, 0};

    for (u32 i = 0; i < ARRAY_COUNT(knownRaw); ++i)
    {
        assert(DifficultyRawToMenuSelection(knownRaw[i]) == knownSelections[i]);
        assert(DifficultyMenuSelectionToRaw(knownSelections[i]) == knownRaw[i]);
        assert(DifficultyRawAfterOptions(knownRaw[i], 0, FALSE) == knownRaw[i]);
    }

    assert(DifficultyRawToMenuSelection(5) == 2);
    assert(DifficultyRawToMenuSelection(0xFFFF) == 2);
    assert(DifficultyRawToMenuSelection(5) < 5);
    assert(DifficultyRawToMenuSelection(0xFFFF) < 5);
    assert(DifficultyMenuSelectionToRaw(5) == OPTIONS_NORMAL_DIFFICULTY);
    assert(DifficultyRawAfterOptions(5, 0, FALSE) == 5);
    assert(DifficultyRawAfterOptions(0xFFFF, 2, FALSE) == 0xFFFF);
    assert(DifficultyRawAfterOptions(5, 3, TRUE) == OPTIONS_HARD_DIFFICULTY);
    assert(DifficultyRawAfterOptions(0xFFFF, 0, TRUE) == OPTIONS_VANILLA_DIFFICULTY);

    puts("Difficulty raw 0..4 mapping, unknown 5/0xFFFF safe display, and preservation: PASS");
}

static void TestWildLevelScalingMappingAndPreservation(void)
{
    assert(WildLevelScalingRawToMenuSelection(0) == 0);
    assert(WildLevelScalingRawToMenuSelection(1) == 1);
    assert(WildLevelScalingMenuSelectionToRaw(0) == 0);
    assert(WildLevelScalingMenuSelectionToRaw(1) == 1);
    assert(WildLevelScalingRawAfterOptions(0, 1, FALSE) == 0);
    assert(WildLevelScalingRawAfterOptions(1, 0, FALSE) == 1);

    assert(WildLevelScalingRawToMenuSelection(2) == 0);
    assert(WildLevelScalingRawToMenuSelection(0xFFFF) == 0);
    assert(WildLevelScalingRawToMenuSelection(2) < 2);
    assert(WildLevelScalingRawToMenuSelection(0xFFFF) < 2);
    assert(WildLevelScalingMenuSelectionToRaw(2) == 0);
    assert(WildLevelScalingRawAfterOptions(2, 1, FALSE) == 2);
    assert(WildLevelScalingRawAfterOptions(0xFFFF, 0, FALSE) == 0xFFFF);
    assert(WildLevelScalingRawAfterOptions(2, 1, TRUE) == 1);
    assert(WildLevelScalingRawAfterOptions(0xFFFF, 0, TRUE) == 0);

    puts("Wild Scaling raw 0/1 mapping, unknown 2/0xFFFF safe display, and preservation: PASS");
}

static void TestTrainerLevelScalingPreservation(void)
{
    for (u16 raw = 0; raw <= TRAINER_LEVEL_SCALING_EXPERT + 1; ++raw)
    {
        assert(TrainerLevelScalingRawToMenuSelection(raw) == raw);
        assert(TrainerLevelScalingRawAfterOptions(raw, 0, FALSE) == raw);
    }

    assert(TrainerLevelScalingRawToMenuSelection(6) == 0);
    assert(TrainerLevelScalingRawToMenuSelection(0xFFFF) == 0);
    assert(TrainerLevelScalingRawAfterOptions(6, 0, FALSE) == 6);
    assert(TrainerLevelScalingRawAfterOptions(0xFFFF, 1, FALSE) == 0xFFFF);
    assert(TrainerLevelScalingRawAfterOptions(6, 1, TRUE) == 1);

    puts("Trainer Level Scaling known/unknown raw preservation: PASS");
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

static void TestFullStateOpenClosePreservation(void)
{
    struct SyntheticOptionState
    {
        u16 difficulty;
        u16 trainerScaling;
        u16 wildScaling;
        u16 trainerAI;
    } state = {5, 0xFFFF, 2, 0xFFFF};
    u16 difficultySelection = DifficultyRawToMenuSelection(state.difficulty);
    u16 trainerScalingSelection = TrainerLevelScalingRawToMenuSelection(state.trainerScaling);
    u16 wildScalingSelection = WildLevelScalingRawToMenuSelection(state.wildScaling);
    u16 trainerAISelection = TrainerAIProfileRawToMenuSelection(state.trainerAI);

    assert(difficultySelection < 5);
    assert(trainerScalingSelection <= TRAINER_LEVEL_SCALING_EXPERT + 1);
    assert(wildScalingSelection < 2);
    assert(trainerAISelection < TRAINER_AI_PROFILE_MENU_OPTION_COUNT);

    /* Simulate editing an unrelated setting while all four are untouched. */
    state.difficulty = DifficultyRawAfterOptions(state.difficulty, difficultySelection, FALSE);
    state.trainerScaling = TrainerLevelScalingRawAfterOptions(state.trainerScaling, trainerScalingSelection, FALSE);
    state.wildScaling = WildLevelScalingRawAfterOptions(state.wildScaling, wildScalingSelection, FALSE);
    state.trainerAI = TrainerAIProfileRawAfterOptions(state.trainerAI, trainerAISelection, FALSE);

    assert(state.difficulty == 5);
    assert(state.trainerScaling == 0xFFFF);
    assert(state.wildScaling == 2);
    assert(state.trainerAI == 0xFFFF);

    /* Explicit edits replace only the selected setting with a supported raw. */
    state.difficulty = DifficultyRawAfterOptions(state.difficulty, 4, TRUE);
    state.trainerScaling = TrainerLevelScalingRawAfterOptions(state.trainerScaling, 1, TRUE);
    state.wildScaling = WildLevelScalingRawAfterOptions(state.wildScaling, 1, TRUE);
    state.trainerAI = TrainerAIProfileRawAfterOptions(state.trainerAI, 8, TRUE);

    assert(state.difficulty == OPTIONS_EXPERT_DIFFICULTY);
    assert(state.trainerScaling == TRAINER_LEVEL_SCALING_OFF + 1);
    assert(state.wildScaling == 1);
    assert(state.trainerAI == 8);

    puts("Combined unknown Difficulty/Trainer Scaling/Wild Scaling/Trainer AI open-close preservation: PASS");
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
    TestDifficultyMappingAndPreservation();
    TestWildLevelScalingMappingAndPreservation();
    TestTrainerLevelScalingPreservation();
    TestRawMappingAndPreservation();
    TestFullStateOpenClosePreservation();
    TestFreshDefaults();
    TestIronmonPreset();
    puts("settings/defaults source-owned host tests: PASS");
    return 0;
}
