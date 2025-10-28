#pragma once

#include "../global.h"

/*
    New type of battle. 
    * At the start of turn, and every three subsquent turns, one random active trap
      and one random passive trap is activated.

    * Passive traps are applied throughout the field and have no activation condition.
      They are announced at the start of their activation turn.

      Examples: Graveyard (All Pokemon gain Ghost-type), Trapper's Territory (All Pokemon
      can't switch out), Bizzare Temple (All Pokemon have a 50% chance to switch moves with
      their opponent), Sin of Pride (All Dragon-type moves turn Dark-type)

    * Active traps are hidden to the player and have an activation condition.
      They are only announced when they are activated. They last for 3 turns, except when their
      effect ends, then the next turn a new trap is set.

      Examples: No Interference (Using an item cancels the effect and ends the turn),
      Shattered Dreams (If the trainer attempts to Mega Evolve, use a Z-Move, Dynamax
      or Terastallize, and other gimmicks, the action fails and the turn ends),
      Jackpot! (25% for the ability to pop-up and guarantee a crit)
*/

// Passive Traps

#define TRAP_NONE 0

enum PassiveTraps
{
    TRAP_TRAPPERS_TERRITORY = 1, // All Pokemon cannot switch out
    TRAP_GRAVEYARD,              // All Pokemon gain Ghost-type (Can have upto 3 types)
    TRAP_ITS_RAINING_HAZARDS,    // Random entry hazards are set at the start of each turn
    TRAP_BALLROOM_BONANZA,       // All Pokemon are infatuated, provided there are both genders on field
    TRAP_ABILITY_NULL,           // All abilities are nullified
    TRAP_CHILLY_WINDS,           // All moves deal additional Ice-type damage
    TRAP_HEALING_GROUNDS,        // All Recovery moves heal double the amount
    TRAP_BIZZARE_TEMPLE,         // All Pokemon have a 50% chance to switch moves with their opponent
    TRAP_HOT_LAVA,               // All Pokemon are burned, except Fire-types
    TRAP_STAT_ROULETTE,          // All Pokemon gain a random 2-stage stat boost
    TRAP_COFFEE_FIELDS,          // All Pokemon can't sleep, have their speed either halved or doubled
    TRAP_DISTORTED_FURY,         // Physical moves become Special and vice versa
    TRAP_WRONG_INTUITION,        // Pokemon will use a different move than intended
    TRAP_PASSIVE_COUNT
};

enum ActiveTraps
{
    TRAP_NO_INTERFERENCE = TRAP_PASSIVE_COUNT, // Using an item cancels the effect and ends the turn
    TRAP_SHATTERED_DREAMS,                     // Mega Evolution, Z-Move, Dynamax, Terastallize fail and turn ends
    TRAP_JACKPOT,                              // 25% chance to guarantee a critical hit
    TRAP_BANANA_PEEL,                          // Using a Grass-type move causes the user to switch out
    TRAP_NO_HOLDS_BARRED,                      // Fighting-type moves deal double damage, but have their accuracy halved
    TRAP_SEALED_DEMON,                         // For that turn, all moves have double power
    TRAP_BLOOD_PACT,                           // If a Pokemon KOs another, it loses half its health
    TRAP_SIN_OF_PRIDE,                         // All Dragon-type moves become Dark-type
    TRAP_DETONATION_DELUSION,                  // All moves have a 25% chance to turn into Explosion
    TRAP_NOTHING_SPECIAL,                      // Normal-type moves become a random-type
};

#define TRAP_TOTAL_COUNT (TRAP_NOTHING_SPECIAL + 1)
#define TRAP_ACTIVE_COUNT (TRAP_TOTAL_COUNT - TRAP_PASSIVE_COUNT)

// Structure for holding trap data
struct TrapData
{
    // Basic Info
    u8 *name;
    u8 *desc;

    // Identifier: 1 = Active Trap, 0 = Passive Trap
    bool8 isActive;
};

extern struct TrapData gTrapData[TRAP_TOTAL_COUNT];

// Flavor Text
extern u8 sText_Name_TrappersTerritory[];
extern u8 sText_Name_Graveyard[];
extern u8 sText_Name_ItsRainingHazards[];
extern u8 sText_Name_BallroomBonanza[];
extern u8 sText_Name_AbilityNull[];
extern u8 sText_Name_ChillyWinds[];
extern u8 sText_Name_HealingGrounds[];
extern u8 sText_Name_BizzareTemple[];
extern u8 sText_Name_HotLava[];
extern u8 sText_Name_StatRoulette[];
extern u8 sText_Name_CoffeeFields[];
extern u8 sText_Name_DistortedFury[];
extern u8 sText_Name_WrongIntuition[];

extern u8 sText_Name_NoInterference[];
extern u8 sText_Name_ShatteredDreams[];
extern u8 sText_Name_Jackpot[];
extern u8 sText_Name_BananaPeel[];
extern u8 sText_Name_NoHoldsBarred[];
extern u8 sText_Name_SealedDemon[];
extern u8 sText_Name_BloodPact[];
extern u8 sText_Name_SinOfPride[];
extern u8 sText_Name_DetonationDelusion[];
extern u8 sText_Name_NothingSpecial[];


extern u8 sText_Desc_TrappersTerritory[];
extern u8 sText_Desc_Graveyard[];
extern u8 sText_Desc_ItsRainingHazards[];
extern u8 sText_Desc_BallroomBonanza[];
extern u8 sText_Desc_AbilityNull[];
extern u8 sText_Desc_ChillyWinds[];
extern u8 sText_Desc_HealingGrounds[];
extern u8 sText_Desc_BizzareTemple[];
extern u8 sText_Desc_HotLava[];
extern u8 sText_Desc_StatRoulette[];
extern u8 sText_Desc_CoffeeFields[];
extern u8 sText_Desc_DistortedFury[];
extern u8 sText_Desc_WrongIntuition[];

extern u8 sText_Desc_NoInterference[];
extern u8 sText_Desc_ShatteredDreams[];
extern u8 sText_Desc_Jackpot[];
extern u8 sText_Desc_BananaPeel[];
extern u8 sText_Desc_NoHoldsBarred[];
extern u8 sText_Desc_SealedDemon[];
extern u8 sText_Desc_BloodPact[];
extern u8 sText_Desc_SinOfPride[];
extern u8 sText_Desc_DetonationDelusion[];
extern u8 sText_Desc_NothingSpecial[];
