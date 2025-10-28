#include "../include/global.h"
#include "../include/battle.h"
#include "../include/event_data.h"
#include "../include/new/traps.h"

const u8 *const gTrapNames[TRAP_TOTAL_COUNT] = {
    gText_Trappers_Territory,
    gText_Graveyard,
    gText_Its_Raining_Traps,
    gText_Ballroom_Bonanza,
    gText_Ability_Null,
    gText_Chilly_Winds,
    gText_Healing_Grounds,
    gText_Bizarre_Temple,
    gText_Mirage_Domain,
    gText_Hot_Lava,
    gText_Bog_Of_Confusion,
    gText_Unseen_Casino,
    gText_Coffee_Fields,
    gText_Distorted_Fury,
    gText_Nothing_Special,
    gText_Zero_Gravity,
    gText_Floor_Is_Lava,
    gText_Drilling_Zone,

    gText_Backlash_Zone,
    gText_Total_Eclipse,
    gText_Justice_Sector,
    gText_No_Holds_Barred,
    gText_Enfatten,
    gText_No_Interference,
    gText_Shattered_Dreams,
    gText_Wrong_Intuition,
    gText_Blood_Pact,
    gText_Jackpot,
    gText_Banana_Peel,
    gText_Detonation_Delusion,
    gText_Sin_Of_Pride,
    gText_Sealed_Demon,
    gText_No_Mercy,
    gText_Insectophobia,
};

// Returns TRUE if player in a Sabotage Battle
bool8 IsSabotageBattle(void)
{
	return FlagGet(FLAG_SABOTAGE_BATTLE);
}

// Gets the name of the trap based on its ID
const u8* GetTrapName(u8 trapId)
{
    if (trapId < TRAP_TOTAL_COUNT)
        return gTrapNames[trapId];
    return NULL; // Fallback
}


// Checks if a trap is currently active (One Active and One Passive)
bool8 IsTrapActive(u8 trapId)
{
    if (trapId < TRAP_PASSIVE_COUNT)
    {
        // Check if the trap is a passive trap
        return gNewBS->trapData.passiveTrapId == trapId;
    }
    else if (trapId < TRAP_TOTAL_COUNT)
    {
        // Check if the trap is an active trap
        return gNewBS->trapData.activeTrapId == (trapId - TRAP_ACTIVE_BACKLASH_ZONE);
    }
    return FALSE;  // Not active
}

// Generates a random Passive Trap
u8 GetRandomPassiveTrap(void)
{
    u8 trapId = TRAP_PASSIVE_GRAVEYARD; // Random() % TRAP_PASSIVE_COUNT;
    gNewBS->trapData.passiveTrapId = trapId;
    return trapId;
}

// Generates a random Active Trap
u8 GetRandomActiveTrap(void)
{
    u8 trapId = TRAP_ACTIVE_BACKLASH_ZONE/*+ (Random() % TRAP_ACTIVE_COUNT)*/;
    gNewBS->trapData.activeTrapId = trapId;
    return trapId;
}

// Set Traps (At start and at the end of turn)
void TrySetTraps(void)
{
	u8 activeTrap = GetRandomActiveTrap();
	u8 passiveTrap = GetRandomPassiveTrap();

	gNewBS->trapData.activeTrapId = activeTrap;
	gNewBS->trapData.passiveTrapId = passiveTrap;	
}

/*
					// Adds a random hazard to both sides (Use Random())- Stealth Rock, Spikes, Toxic Spikes, or Sticky Web
					case TRAP_PASSIVE_ITS_RAINING_TRAPS:
						if (gSideTimers[SIDE(gActiveBattler)].srAmount == 0
						&& gSideTimers[SIDE(gActiveBattler)].spikesAmount == 0
						&& gSideTimers[SIDE(gActiveBattler)].tspikesAmount == 0
						&& gSideTimers[SIDE(gActiveBattler)].stickyWeb == 0)
						{
							u8 hazard = Random() % 4;

							switch (hazard)
							{
								case TrapState_StealthRock:
									BattleScriptPushCursor();
									gBattlescriptCurrInstr = BattleScript_MaxMoveSetStealthRock;
									break;
								case TrapState_Spikes:
									gSideTimers[SIDE(gActiveBattler)].spikesAmount = 1;
									BattleScriptPushCursor();
									gBattlescriptCurrInstr = BattleScript_SpikesSet;
									break;
								case TrapState_StickyWeb:
									gSideTimers[SIDE(gActiveBattler)].stickyWeb = TRUE;
									BattleScriptPushCursor();
									gBattlescriptCurrInstr = BattleScript_StickyWebSet;
									break;
								case TrapState_ToxicSpikes:
									gSideTimers[SIDE(gActiveBattler)].tspikesAmount = 1;
									BattleScriptPushCursor();
									gBattlescriptCurrInstr = BattleScript_ToxicSpikesSet;
									break;
							}
						}
						return;*/