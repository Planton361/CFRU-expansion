#pragma once

#include "../global.h"

/*
 * Standard dispatch is intentionally narrower than the legacy AI dispatch.
 * The implementation owns the observation boundary and calls only the pure
 * policy entry point after it has projected fair candidate facts.
 */
bool8 StandardAI_IsSupportedBattle(void);
void StandardAI_SetupAIData(void);
u8 StandardAI_ChooseMoveOrAction(void);
void StandardAI_TrySwitchOrUseItem(void);
u8 StandardAI_ChooseReplacement(void);
void StandardAI_ObservePublicMove(u16 move);
void StandardAI_ObservePublicAbility(u8 bank, u8 ability);
