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
u32 StandardAI_GetSwitchEntryDamage(u8 bank, const struct Pokemon* mon);
enum StandardAIBadgeBoostKind
{
	STANDARD_AI_BADGE_SPEED = 0,
	STANDARD_AI_BADGE_ATTACK,
	STANDARD_AI_BADGE_DEFENSE,
	STANDARD_AI_BADGE_SPECIAL_ATTACK,
	STANDARD_AI_BADGE_SPECIAL_DEFENSE,
};
/* Returns whether a player-side Badge boost is possible from public
 * compile/battle context. It never reads private Badge ownership. */
bool8 StandardAI_PublicBadgeBoost(u8 bank, u8 kind);
void StandardAI_DeriveDamageWithCertificate(u8 bank, u8 foe, u16 move,
	struct StandardPolicyCandidate* candidate, bool8 certified);

/* One concrete, source-owned setup follow-up.  The Ironmon adapter uses this
 * rather than combining the strongest current move with a marginal gain from
 * a different move.  Fractions use the shared 1/256 HP scale. */
struct StandardSetupFollowup
{
	bool8 found;
	u8 slot;
	u8 split;
	s8 priority;
	u16 move;
	u16 before_fraction;
	u16 after_fraction;
};

bool8 StandardAI_FindSetupFollowup(u8 bank, u8 foe, u8 family, u8 afterStage,
	struct StandardSetupFollowup* out);
