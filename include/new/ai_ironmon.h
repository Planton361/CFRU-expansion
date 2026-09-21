#pragma once

#include "../global.h"

bool8 IronmonAI_IsSupportedBattle(void);
void IronmonAI_SetupAIData(void);
u8 IronmonAI_ChooseMoveOrAction(void);
void IronmonAI_TrySwitchOrUseItem(void);
u8 IronmonAI_ChooseReplacement(void);

/* Called only by the public attack-string history producer. */
void IronmonAI_ObservePublicMove(u8 bank, u16 move);
void IronmonAI_ClearPublicMoveCounts(u8 bank);
