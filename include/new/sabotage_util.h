#pragma once

#include "sabotage.h"

// Exported Functions
u8 GetRandomTrap(bool8 isActive); // Returns a random trap ID
u8 IsActiveTrap(u8 trapId);   // Returns whether the given trap ID is active
u8 IsPassiveTrap(u8 trapId);  // Returns whether the given trap ID is passive
const u8* GetTrapName(u8 trapId); // Returns the name of the given trap ID
const u8* GetTrapDesc(u8 trapId); // Returns the description of the given trap ID
bool8 IsPassiveTrapCounterZero(void); // Returns whether the passive trap counter is zero
bool8 IsActiveTrapCounterZero(void); // Returns whether the active trap counter is zero
void ResetSabotageCounters(void); // Resets both sabotage counters to 3
void ResetActiveTrapCounter(void); // Resets the active trap counter to 3
void ResetPassiveTrapCounter(void); // Resets the passive trap counter to 3
bool8 IsValidTrapId(u8 trapId); // Returns whether the given trap ID is valid
bool8 IsSabotageBattle(void); // Returns whether the current battle is a Sabotage battle

bool8 SabotageBattleEffects(u8 trapId); // Applies the effects of the given trap ID
u8 GetCurrentTrap(bool8 isActive); // Returns the current active trap ID
