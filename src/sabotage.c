#include "../include/battle.h"
#include "../include/global.h"
#include "../include/pokemon.h"

#include "../include/new/battle_util.h"
#include "../include/new/sabotage_util.h"

/*
   Various functions for the Sabotage battle type.
   Main logic for various traps will be widespread throughout the repo.
*/

// List of all traps
struct TrapData gTrapData[] = 
{
    // Passive Traps
    [TRAP_TRAPPERS_TERRITORY] = 
    {
        .name = sText_Name_TrappersTerritory,
        .desc = sText_Desc_TrappersTerritory,
        .isActive = FALSE
    },
    [TRAP_GRAVEYARD] = 
    {
        .name = sText_Name_Graveyard,
        .desc = sText_Desc_Graveyard,
        .isActive = FALSE
    },
    [TRAP_ITS_RAINING_HAZARDS] = 
    {
        .name = sText_Name_ItsRainingHazards,
        .desc = sText_Desc_ItsRainingHazards,
        .isActive = FALSE
    },
    [TRAP_BALLROOM_BONANZA] = 
    {
        .name = sText_Name_BallroomBonanza,
        .desc = sText_Desc_BallroomBonanza,
        .isActive = FALSE
    },
    [TRAP_ABILITY_NULL] = 
    {
        .name = sText_Name_AbilityNull,
        .desc = sText_Desc_AbilityNull,
        .isActive = FALSE
    },
    [TRAP_CHILLY_WINDS] = 
    {
        .name = sText_Name_ChillyWinds,
        .desc = sText_Desc_ChillyWinds,
        .isActive = FALSE
    },
    [TRAP_HEALING_GROUNDS] =
    {
        .name = sText_Name_HealingGrounds,
        .desc = sText_Desc_HealingGrounds,
        .isActive = FALSE
    },
    [TRAP_BIZZARE_TEMPLE] =
    {
        .name = sText_Name_BizzareTemple,
        .desc = sText_Desc_BizzareTemple,
        .isActive = FALSE
    },
    [TRAP_HOT_LAVA] =
    {
        .name = sText_Name_HotLava,
        .desc = sText_Desc_HotLava,
        .isActive = FALSE
    },
    [TRAP_STAT_ROULETTE] =
    {
        .name = sText_Name_StatRoulette,
        .desc = sText_Desc_StatRoulette,
        .isActive = FALSE
    },
    [TRAP_COFFEE_FIELDS] =
    {
        .name = sText_Name_CoffeeFields,
        .desc = sText_Desc_CoffeeFields,
        .isActive = FALSE
    },
    [TRAP_DISTORTED_FURY] =
    {
        .name = sText_Name_DistortedFury,
        .desc = sText_Desc_DistortedFury,
        .isActive = FALSE
    },
    [TRAP_WRONG_INTUITION] =
    {
        .name = sText_Name_WrongIntuition,
        .desc = sText_Desc_WrongIntuition,
        .isActive = FALSE
    },

    // Active Traps
    [TRAP_NO_INTERFERENCE] =
    {
        .name = sText_Name_NoInterference,
        .desc = sText_Desc_NoInterference,
        .isActive = TRUE
    },
    [TRAP_SHATTERED_DREAMS] =
    {
        .name = sText_Name_ShatteredDreams,
        .desc = sText_Desc_ShatteredDreams,
        .isActive = TRUE
    },
    [TRAP_JACKPOT] =
    {
        .name = sText_Name_Jackpot,
        .desc = sText_Desc_Jackpot,
        .isActive = TRUE
    },
    [TRAP_BANANA_PEEL] =
    {
        .name = sText_Name_BananaPeel,
        .desc = sText_Desc_BananaPeel,
        .isActive = TRUE
    },
    [TRAP_NO_HOLDS_BARRED] =
    {
        .name = sText_Name_NoHoldsBarred,
        .desc = sText_Desc_NoHoldsBarred,
        .isActive = TRUE
    },
    [TRAP_SEALED_DEMON] =
    {
        .name = sText_Name_SealedDemon,
        .desc = sText_Desc_SealedDemon,
        .isActive = TRUE
    },
    [TRAP_BLOOD_PACT] =
    {
        .name = sText_Name_BloodPact,
        .desc = sText_Desc_BloodPact,
        .isActive = TRUE
    },
    [TRAP_SIN_OF_PRIDE] =
    {
        .name = sText_Name_SinOfPride,
        .desc = sText_Desc_SinOfPride,
        .isActive = TRUE
    },
    [TRAP_DETONATION_DELUSION] =
    {
        .name = sText_Name_DetonationDelusion,
        .desc = sText_Desc_DetonationDelusion,
        .isActive = TRUE
    },
    [TRAP_NOTHING_SPECIAL] =
    {
        .name = sText_Name_NothingSpecial,
        .desc = sText_Desc_NothingSpecial,
        .isActive = TRUE
    },
};


u8 GetRandomTrap(bool8 isActive)
{
    u8 start = isActive ? TRAP_PASSIVE_COUNT : 0;
    u8 end = isActive ? TRAP_TOTAL_COUNT : TRAP_PASSIVE_COUNT;
    u8 random;

    /*
    do
    {
        random = start + (Random() % (end - start));
    }
    while (!IsValidTrapId(random));
    */
    // Commented for debugging

    random = isActive ? TRAP_SIN_OF_PRIDE : TRAP_TRAPPERS_TERRITORY; // For debugging, easiest to code
    return random;
}

u8 IsActiveTrap(u8 trapId)
{
    return gTrapData[trapId].isActive;
}

u8 IsPassiveTrap(u8 trapId)
{
    return !(gTrapData[trapId].isActive);
}

const u8* GetTrapName(u8 trapId)
{
    return gTrapData[trapId].name;
}

const u8* GetTrapDesc(u8 trapId)
{
    return gTrapData[trapId].desc;
}

bool8 IsPassiveTrapCounterZero(void)
{
    return (gNewBS->sabotage.passiveTrapCounter == 0);
}

bool8 IsActiveTrapCounterZero(void)
{
    return (gNewBS->sabotage.activeTrapCounter == 0);
}

void ResetSabotageCounters(void)
{
    gNewBS->sabotage.passiveTrapCounter = 3;
    gNewBS->sabotage.activeTrapCounter = 3;
}

void ResetActiveTrapCounter(void)
{
    gNewBS->sabotage.activeTrapCounter = 3;
}

void ResetPassiveTrapCounter(void)
{
    gNewBS->sabotage.passiveTrapCounter = 3;
}

bool8 IsValidTrapId(u8 trapId)
{
    return (trapId > 0 && trapId < TRAP_TOTAL_COUNT);
}

bool8 IsSabotageBattle(void)
{
    return (gBattleTypeFlags & BATTLE_TYPE_SABOTAGE);
}

u8 GetCurrentTrap(bool8 isActive)
{
    return isActive ? gNewBS->sabotage.activeTrapId : gNewBS->sabotage.passiveTrapId;
}

bool8 SabotageBattleEffects(u8 trapId)
{
    switch (trapId)
    {
        case TRAP_GRAVEYARD:
            // All Pokemon gain tertiary Ghost-typing
            for (u8 i = 0; i < gBattlersCount; i++)
            {
                if (IsOfType(i, TYPE_GHOST))
                    continue;
                else
                    gBattleMons[i].type3 = TYPE_GHOST;
            }
            return TRUE;

        default:
            // For Debugging
            return TRUE;
    }

    return FALSE;
}