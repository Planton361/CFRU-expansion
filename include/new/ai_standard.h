#pragma once

#include "../global.h"
#include "ai_standard_policy.h"

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

/* Shared fair-adapter surface used by the distinct Ironmon profile. */
void StandardAI_BuildObservation(u8 bank, bool8 includeSwitches,
	struct StandardPolicyObservation* observation);
void StandardAI_LoadMemory(u8 bank, struct StandardPolicyMemory* memory);
void StandardAI_StageLastAction(u8 bank,
	const struct StandardPolicyCandidate* candidate);
bool8 StandardAI_GetPublicTypes(u8 bank, u8 types[3]);
u8 StandardAI_PublicTypeMultiplier(u8 attackType, u8 defenseType);
bool8 StandardAI_IsSupportedDamage(u16 move);
