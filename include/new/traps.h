#include "../global.h"

#pragma once

#define TRAP_NONE 0

enum PassiveTraps
{
    TRAP_PASSIVE_TRAPPERS_TERRITORY = 1,
    TRAP_PASSIVE_GRAVEYARD,
    TRAP_PASSIVE_ITS_RAINING_TRAPS,
    TRAP_PASSIVE_BALLROOM_BONANZA,
    TRAP_PASSIVE_ABILITY_NULL,
    TRAP_PASSIVE_CHILLY_WINDS,
    TRAP_PASSIVE_HEALING_GROUNDS,
    TRAP_PASSIVE_BIZARRE_TEMPLE,
    TRAP_PASSIVE_MIRAGE_DOMAIN,
    TRAP_PASSIVE_HOT_LAVA,
    TRAP_PASSIVE_BOG_OF_CONFUSION,
    TRAP_PASSIVE_UNSEEN_CASINO,
    TRAP_PASSIVE_COFFEE_FIELDS,
    TRAP_PASSIVE_DISTORTED_FURY,
    TRAP_PASSIVE_NOTHING_SPECIAL,
    TRAP_PASSIVE_ZERO_GRAVITY,
    TRAP_PASSIVE_FLOOR_IS_LAVA,
    TRAP_PASSIVE_DRILLING_ZONE
};

enum ActiveTraps
{
    TRAP_ACTIVE_BACKLASH_ZONE = 1,
    TRAP_ACTIVE_TOTAL_ECLIPSE,
    TRAP_ACTIVE_JUSTICE_SECTOR,
    TRAP_ACTIVE_NO_HOLDS_BARRED,
    TRAP_ACTIVE_ENFATTEN,
    TRAP_ACTIVE_NO_INTERFERENCE,
    TRAP_ACTIVE_SHATTERED_DREAMS,
    TRAP_ACTIVE_WRONG_INTUITION,
    TRAP_ACTIVE_BLOOD_PACT,
    TRAP_ACTIVE_JACKPOT,
    TRAP_ACTIVE_BANANA_PEEL,
    TRAP_ACTIVE_DETONATION_DELUSION,
    TRAP_ACTIVE_SIN_OF_PRIDE,
    TRAP_ACTIVE_SEALED_DEMON,
    TRAP_ACTIVE_NO_MERCY,
    TRAP_ACTIVE_INSECTOPHOBIA
};

#define TRAP_PASSIVE_COUNT TRAP_PASSIVE_DRILLING_ZONE
#define TRAP_ACTIVE_COUNT TRAP_ACTIVE_INSECTOPHOBIA
#define TRAP_TOTAL_COUNT (TRAP_PASSIVE_COUNT + TRAP_ACTIVE_COUNT)
#define FLAG_SABOTAGE_BATTLE 0xA09

/*                Texts                */

extern const u8 gText_SabotageBattleStart[];

extern const u8 gText_TrappersTerritoryActivate[];
extern const u8 gText_GraveyardSpawn[];

// Passive Traps
extern const u8 gText_Trappers_Territory[];
extern const u8 gText_Graveyard[];
extern const u8 gText_Its_Raining_Traps[];
extern const u8 gText_Ballroom_Bonanza[];
extern const u8 gText_Ability_Null[];
extern const u8 gText_Chilly_Winds[];
extern const u8 gText_Healing_Grounds[];
extern const u8 gText_Bizarre_Temple[];
extern const u8 gText_Mirage_Domain[];
extern const u8 gText_Hot_Lava[];
extern const u8 gText_Bog_Of_Confusion[];
extern const u8 gText_Unseen_Casino[];
extern const u8 gText_Coffee_Fields[];
extern const u8 gText_Distorted_Fury[];
extern const u8 gText_Nothing_Special[];
extern const u8 gText_Zero_Gravity[];
extern const u8 gText_Floor_Is_Lava[];
extern const u8 gText_Drilling_Zone[];

// Active Traps
extern const u8 gText_Backlash_Zone[];
extern const u8 gText_Total_Eclipse[];
extern const u8 gText_Justice_Sector[];
extern const u8 gText_No_Holds_Barred[];
extern const u8 gText_Enfatten[];
extern const u8 gText_No_Interference[];
extern const u8 gText_Shattered_Dreams[];
extern const u8 gText_Wrong_Intuition[];
extern const u8 gText_Blood_Pact[];
extern const u8 gText_Jackpot[];
extern const u8 gText_Banana_Peel[];
extern const u8 gText_Detonation_Delusion[];
extern const u8 gText_Sin_Of_Pride[];
extern const u8 gText_Sealed_Demon[];
extern const u8 gText_No_Mercy[];
extern const u8 gText_Insectophobia[];

extern const u8 *const gTrapNames[TRAP_TOTAL_COUNT];

/*                 Battle Scripts               */

extern const u8 BattleScript_SabotageBattleStart[];
extern const u8 BattleScript_TrappersTerritoryActivate[];
extern const u8 BattleScript_GraveyardSpawn[];
extern const u8 BattleScript_TrappersTerritoryHurt[];
extern const u8 BattleScript_GraveyardAddedGhostTyping[];
extern const u8 BattleScript_BallroomBonanzaInfatuate[];

/*                   Functions                  */

extern bool8 IsSabotageBattle(void);
extern const u8* GetTrapName(u8 trapId);
extern bool8 IsTrapActive(u8 trapId);
extern u8 GetRandomPassiveTrap(void);
extern u8 GetRandomActiveTrap(void);
extern void TrySetTraps(void);
extern void HandleSabotageBattleEffects(void);
