#include "defines.h"
#include "../include/new/settings.h"

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
