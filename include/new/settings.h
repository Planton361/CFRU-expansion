#ifndef GUARD_NEW_SETTINGS_H
#define GUARD_NEW_SETTINGS_H

#include "../global.h"

/* Raw menu values are 0 for legacy Auto and enum values plus one otherwise. */
#define TRAINER_AI_PROFILE_MENU_OPTION_COUNT (TRAINER_AI_PROFILE_IRONMON_SMART + 2)

u16 DifficultyRawToMenuSelection(u16 raw);
u16 DifficultyMenuSelectionToRaw(u16 selection);
u16 DifficultyRawAfterOptions(u16 originalRaw, u16 selection, bool8 dirty);
u16 WildLevelScalingRawToMenuSelection(u16 raw);
u16 WildLevelScalingMenuSelectionToRaw(u16 selection);
u16 WildLevelScalingRawAfterOptions(u16 originalRaw, u16 selection, bool8 dirty);
u16 TrainerLevelScalingRawToMenuSelection(u16 raw);
u16 TrainerLevelScalingRawAfterOptions(u16 originalRaw, u16 selection, bool8 dirty);
u16 TrainerAIProfileRawToMenuSelection(u16 raw);
u16 TrainerAIProfileMenuSelectionToRaw(u16 selection);
u16 TrainerAIProfileRawAfterOptions(u16 originalRaw, u16 selection, bool8 dirty);

void ApplyFreshNewGameSettings(void);
void ApplyIronmonSmartSettingsPreset(void);

#endif // GUARD_NEW_SETTINGS_H
