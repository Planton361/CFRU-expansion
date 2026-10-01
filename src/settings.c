#include "defines.h"
#include "../include/new/settings.h"

u16 DifficultyRawToMenuSelection(u16 raw)
{
    switch (raw)
    {
        case OPTIONS_VANILLA_DIFFICULTY:
            return 0;
        case OPTIONS_EASY_DIFFICULTY:
            return 1;
        case OPTIONS_HARD_DIFFICULTY:
            return 3;
        case OPTIONS_EXPERT_DIFFICULTY:
            return 4;
        case OPTIONS_NORMAL_DIFFICULTY:
        default:
            return 2;
    }
}

u16 DifficultyMenuSelectionToRaw(u16 selection)
{
    switch (selection)
    {
        case 0:
            return OPTIONS_VANILLA_DIFFICULTY;
        case 1:
            return OPTIONS_EASY_DIFFICULTY;
        case 3:
            return OPTIONS_HARD_DIFFICULTY;
        case 4:
            return OPTIONS_EXPERT_DIFFICULTY;
        case 2:
        default:
            return OPTIONS_NORMAL_DIFFICULTY;
    }
}

u16 DifficultyRawAfterOptions(u16 originalRaw, u16 selection, bool8 dirty)
{
    if (dirty)
        return DifficultyMenuSelectionToRaw(selection);

    return originalRaw;
}

u16 WildLevelScalingRawToMenuSelection(u16 raw)
{
    if (raw <= 1)
        return raw;

    return 0;
}

u16 WildLevelScalingMenuSelectionToRaw(u16 selection)
{
    if (selection <= 1)
        return selection;

    return 0;
}

u16 WildLevelScalingRawAfterOptions(u16 originalRaw, u16 selection, bool8 dirty)
{
    if (dirty)
        return WildLevelScalingMenuSelectionToRaw(selection);

    return originalRaw;
}

u16 TrainerLevelScalingRawToMenuSelection(u16 raw)
{
    if (raw <= TRAINER_LEVEL_SCALING_EXPERT + 1)
        return raw;

    return 0;
}

u16 TrainerLevelScalingRawAfterOptions(u16 originalRaw, u16 selection, bool8 dirty)
{
    if (dirty)
    {
        if (selection <= TRAINER_LEVEL_SCALING_EXPERT + 1)
            return selection;
        return 0;
    }

    return originalRaw;
}

u16 TrainerAIProfileRawToMenuSelection(u16 raw)
{
    if (raw < TRAINER_AI_PROFILE_MENU_OPTION_COUNT)
        return raw;

    /* Keep unknown stored values in the original-raw side channel. */
    return 0;
}

u16 TrainerAIProfileMenuSelectionToRaw(u16 selection)
{
    if (selection < TRAINER_AI_PROFILE_MENU_OPTION_COUNT)
        return selection;

    return 0;
}

u16 TrainerAIProfileRawAfterOptions(u16 originalRaw, u16 selection, bool8 dirty)
{
    if (dirty)
        return TrainerAIProfileMenuSelectionToRaw(selection);

    return originalRaw;
}

void ApplyFreshNewGameSettings(void)
{
    VarSet(VAR_GAME_DIFFICULTY, OPTIONS_VANILLA_DIFFICULTY);
    VarSet(VAR_TRAINER_LEVEL_SCALING_MODE, TRAINER_LEVEL_SCALING_OFF + 1);
    VarSet(VAR_WILD_LEVEL_SCALING, 0);
    VarSet(VAR_TRAINER_AI_PROFILE, TRAINER_AI_PROFILE_STANDARD + 1);
}

void ApplyIronmonSmartSettingsPreset(void)
{
    VarSet(VAR_GAME_DIFFICULTY, OPTIONS_VANILLA_DIFFICULTY);
    VarSet(VAR_TRAINER_LEVEL_SCALING_MODE, TRAINER_LEVEL_SCALING_OFF + 1);
    VarSet(VAR_WILD_LEVEL_SCALING, 0);
    VarSet(VAR_TRAINER_AI_PROFILE, TRAINER_AI_PROFILE_IRONMON_SMART + 1);
}
