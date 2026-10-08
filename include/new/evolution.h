#pragma once

#include "../global.h"

// v1 ROM data record. ARM little-endian; pointers are encoded as u32.
// Discovery also requires selfAddress and the live evolution hook's consumer.
#define EVOLUTION_FRIENDSHIP_CONTRACT_VERSION 1
#define EVOLUTION_FRIENDSHIP_CONTRACT_SIZE 32
#define EVOLUTION_FRIENDSHIP_THRESHOLD_OFFSET 28
#define EVOLUTION_FRIENDSHIP_DEFAULT 220
#define EVOLUTION_FRIENDSHIP_EASIER 160

struct EvolutionFriendshipContract
{
	u8 identity[8]; // ASCII CFRUEVO1
	u32 selfAddress;
	u32 consumer; // Thumb pointer to GetEvolutionTargetSpecies
	u16 version;
	u16 size;
	u16 thresholdOffset;
	u16 thresholdWidth;
	u16 defaultThreshold;
	u16 easierThreshold;
	u8 threshold; // Only this byte may be patched, to 220 or 160
	u8 reservedByte;
	u16 reservedHalfword;
};

// External assembly ownership + volatile prevents constant folding of reads.
extern const volatile struct EvolutionFriendshipContract gEvolutionFriendshipContract;

/**
 * \file evolution.h
 * \brief Implements new evolution methods.
 */

//Exported Functions
bool8 IsLevelUpEvolutionMethod(u8 method);
bool8 IsItemEvolutionMethod(u8 method);
bool8 IsFriendshipEvolutionMethod(u8 method);
bool8 IsOtherEvolutionMethod(u8 method);
bool8 EvolutionMethodRequiresLevelUp(u8 method);
bool8 HasHighNature(struct Pokemon* mon);
bool8 EvolvesViaScoring3Crits(struct Pokemon* mon);
u16 GetMonDevolution(struct Pokemon* mon);
u8 GetMinimumLevel(u16 species);

//Functions Hooked In
u16 GetEvolutionTargetSpecies(struct Pokemon* mon, u8 type, u16 evolutionItem);
void ItemEvolutionRemoval(pokemon_t* mon);
