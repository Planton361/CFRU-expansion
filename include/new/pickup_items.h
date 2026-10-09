#pragma once

#include "../global.h"
#include <stddef.h>

/**
 * \file pickup_items.h
 * \brief Contains data relating to the Ability Pickup.
 */

#define PU_NUM_COMMON_ITEMS     18
#define PU_NUM_RARE_ITEMS       11

#define PU_COMMON_PER_ROW   9
#define PU_RARE_PER_ROW     2

extern const item_t sPickupCommonItems[PU_NUM_COMMON_ITEMS];
extern const item_t sPickupRareItems[PU_NUM_RARE_ITEMS];

extern const u32 pickup_common_item_ceilings[PU_COMMON_PER_ROW];
extern const u32 pickup_rare_item_ceilings[PU_RARE_PER_ROW];

/* ABI v1: naturally aligned ARMv4T little-endian ROM data, never packed.
 * The E5 bridge supplies this exact object to the consumer as its argument.
 * A reader must also prove fresh-build/selected-output identity; magic alone
 * is not a locator or permission to write. See docs/testing/pickup-descriptor-abi.md.
 */
#define PU_DESCRIPTOR_MAGIC 0x31555043u /* "CPU1" */
#define PU_DESCRIPTOR_VERSION 1
#define PU_DESCRIPTOR_SIZE 64
#define PU_DESCRIPTOR_ITEM_SCHEMA 1 /* selected CFRU raw item_t IDs */
#define PU_CONFIG_UNBOUND 1u
#define PU_CONFIG_STRAIGHT_TO_BAG 2u
#define PU_CONFIG_KNOCKED_OFF 4u

struct PickupDescriptor;
void PickupItemCalculation(const volatile struct PickupDescriptor* pickup);
void atkE5_pickupitemcalculation(void);

struct PickupDescriptor
{
	u32 magic;                            /* 0 */
	u16 version;                          /* 4 */
	u16 size;                             /* 6 */
	u32 config;                           /* 8 */
	u32 itemSchema;                       /* 12 */
	const item_t* commonItems;             /* 16 */
	const item_t* rareItems;               /* 20 */
	const u32* commonCeilings;             /* 24 */
	const u32* rareCeilings;               /* 28 */
	u16 commonCount;                      /* 32 */
	u16 rareCount;                        /* 34 */
	u16 commonCeilingCount;               /* 36 */
	u16 rareCeilingCount;                 /* 38 */
	u8 pointerWidth;                      /* 40 */
	u8 itemWidth;                         /* 41 */
	u8 ceilingWidth;                      /* 42 */
	u8 levelRanges;                       /* 43 */
	u8 levelStep;                         /* 44 */
	u8 commonWindow;                      /* 45 */
	u8 rareWindow;                        /* 46 */
	u8 minLevel;                          /* 47 */
	u8 maxLevel;                          /* 48 */
	u8 reserved[3];                       /* 49 */
	u32 itemCount;                        /* 52; upper bound, NOT eligibility */
	void (*consumer)(const volatile struct PickupDescriptor*); /* 56 */
	void (*anchor)(void);                  /* 60 */
};

extern const struct PickupDescriptor gPickupDescriptor;

/* typedef assertions also work with the baseline compiler's older C dialect. */
#define PU_ABI_ASSERT(name, condition) typedef char name[(condition) ? 1 : -1]
#if !defined(__ARMEL__)
#error "Pickup descriptor ABI v1 requires little-endian ARM"
#endif
PU_ABI_ASSERT(PuAbiVersion, PU_DESCRIPTOR_VERSION == 1);
PU_ABI_ASSERT(PuAbiCounts, PU_NUM_COMMON_ITEMS == 18 && PU_NUM_RARE_ITEMS == 11
	&& PU_COMMON_PER_ROW == 9 && PU_RARE_PER_ROW == 2);
PU_ABI_ASSERT(PuAbiWidths, sizeof(item_t) == 2 && sizeof(u32) == 4
	&& sizeof(void*) == 4 && sizeof(gPickupDescriptor.consumer) == 4);
PU_ABI_ASSERT(PuAbiSize, sizeof(struct PickupDescriptor) == PU_DESCRIPTOR_SIZE);
PU_ABI_ASSERT(PuAbiAlignment, __alignof__(struct PickupDescriptor) == 4);
#define PU_ABI_OFFSET(field, offset) PU_ABI_ASSERT(PuAbi_##field, \
	offsetof(struct PickupDescriptor, field) == (offset))
PU_ABI_OFFSET(magic, 0);
PU_ABI_OFFSET(version, 4);
PU_ABI_OFFSET(size, 6);
PU_ABI_OFFSET(config, 8);
PU_ABI_OFFSET(itemSchema, 12);
PU_ABI_OFFSET(commonItems, 16);
PU_ABI_OFFSET(rareItems, 20);
PU_ABI_OFFSET(commonCeilings, 24);
PU_ABI_OFFSET(rareCeilings, 28);
PU_ABI_OFFSET(commonCount, 32);
PU_ABI_OFFSET(rareCount, 34);
PU_ABI_OFFSET(commonCeilingCount, 36);
PU_ABI_OFFSET(rareCeilingCount, 38);
PU_ABI_OFFSET(pointerWidth, 40);
PU_ABI_OFFSET(itemWidth, 41);
PU_ABI_OFFSET(ceilingWidth, 42);
PU_ABI_OFFSET(levelRanges, 43);
PU_ABI_OFFSET(levelStep, 44);
PU_ABI_OFFSET(commonWindow, 45);
PU_ABI_OFFSET(rareWindow, 46);
PU_ABI_OFFSET(minLevel, 47);
PU_ABI_OFFSET(maxLevel, 48);
PU_ABI_OFFSET(reserved, 49);
PU_ABI_OFFSET(itemCount, 52);
PU_ABI_OFFSET(consumer, 56);
PU_ABI_OFFSET(anchor, 60);
#undef PU_ABI_OFFSET
#undef PU_ABI_ASSERT
