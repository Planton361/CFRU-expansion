#pragma once

#include "../global.h"
#include "../sprite.h"
#include <stddef.h>

/* CFRU/DPE native IDs, not National Dex numbers. Stage A owns all constants. */
#define OAK_INTRO_ABI_VERSION 1
#define OAK_INTRO_ABI_SIZE 96
#define OAK_INTRO_PROFILE 1
#define OAK_INTRO_SPECIES_CAPACITY 1440
#define OAK_INTRO_DEFAULT_SPECIES 29
#define OAK_INTRO_SELECTOR_OFFSET 92
#define OAK_INTRO_SELECTOR_WIDTH 2
#define OAK_INTRO_BITMAP_BYTES 180
#define OAK_INTRO_POLICY_VERSION 1
#define OAK_INTRO_BRIDGE_SIZE 28
#define OAK_INTRO_BRIDGE_DESCRIPTOR_OFFSET 20
#define OAK_INTRO_BRIDGE_CONSUMER_OFFSET 24

struct OakIntroContractV1;
typedef void (*OakIntroEntry)(u8 taskId);
typedef void (*OakIntroConsumer)(u8 taskId,
    const volatile struct OakIntroContractV1 *intro);

/* ARM little-endian wire layout. All pointers are 32-bit; no packed fields. */
struct OakIntroContractV1
{
    u8 identity[8];                 /* 0: CFROAK01 */
    const volatile struct OakIntroContractV1 *self; /* 8 */
    u16 version;                   /* 12 */
    u16 size;                      /* 14 */
    u32 profile;                   /* 16: native CFRU/DPE Gen 1-9 */
    u16 speciesCapacity;           /* 20: includes slot zero */
    u16 defaultSpecies;            /* 22 */
    u16 selectorOffset;            /* 24 */
    u16 selectorWidth;             /* 26 */
    const u8 *eligibility;         /* 28: immutable, LSB-first */
    u16 eligibilityBytes;          /* 32 */
    u16 policyVersion;             /* 34 */
    OakIntroEntry spriteBridge;    /* 36: Thumb */
    OakIntroConsumer spriteConsumer; /* 40: Thumb */
    OakIntroEntry cryBridge;       /* 44: Thumb */
    OakIntroConsumer cryConsumer;  /* 48: Thumb */
    u32 frontTablePointerSlot;     /* 52: existing DPE repoint root */
    u32 paletteTablePointerSlot;   /* 56: normal palette repoint root */
    u16 frontRowSize;              /* 60 */
    u16 paletteRowSize;            /* 62 */
    u16 bridgeSize;                /* 64 */
    u16 bridgeDescriptorOffset;    /* 66 */
    u16 bridgeConsumerOffset;      /* 68 */
    u16 pointerWidth;              /* 70 */
    u8 reserved[20];               /* 72: zero */
    u16 selectedSpecies;           /* 92: ONLY future UPR write, native ID */
    u16 reservedTail;              /* 94: zero */
};

extern const volatile struct OakIntroContractV1 gOakIntroContract;
extern const u8 gOakIntroEligibility[OAK_INTRO_BITMAP_BYTES];

/* Existing functionrewrites names belong exclusively to assembly bridges. */
void CreateOakIntroPokemonSprite(u8 taskId);
void Task_OakSpeech_IsInhabitedFarAndWide(u8 taskId);
void OakIntroSpriteConsumer(u8 taskId, const volatile struct OakIntroContractV1 *intro);
void OakIntroCryConsumer(u8 taskId, const volatile struct OakIntroContractV1 *intro);

#if !defined(__ARMEL__)
#error "Oak Intro ABI v1 requires little-endian ARM"
#endif
#define OAK_ABI_ASSERT(name, condition) typedef char name[(condition) ? 1 : -1]
OAK_ABI_ASSERT(OakAbiWidths, sizeof(u16) == 2 && sizeof(u32) == 4
    && sizeof(void *) == 4 && sizeof(OakIntroConsumer) == 4);
OAK_ABI_ASSERT(OakAbiSize, sizeof(struct OakIntroContractV1) == OAK_INTRO_ABI_SIZE);
OAK_ABI_ASSERT(OakAbiAlignment, __alignof__(struct OakIntroContractV1) == 4);
OAK_ABI_ASSERT(OakAbiNativeRows, sizeof(struct CompressedSpriteSheet) == 8
    && offsetof(struct CompressedSpriteSheet, size) == 4
    && offsetof(struct CompressedSpriteSheet, tag) == 6
    && sizeof(struct CompressedSpritePalette) == 8
    && offsetof(struct CompressedSpritePalette, tag) == 4);
OAK_ABI_ASSERT(OakAbiSelectorWidth, sizeof(gOakIntroContract.selectedSpecies) == OAK_INTRO_SELECTOR_WIDTH);
#define OAK_ABI_OFFSET(field, offset) OAK_ABI_ASSERT(OakAbi_##field, \
    offsetof(struct OakIntroContractV1, field) == (offset))
OAK_ABI_OFFSET(identity, 0);
OAK_ABI_OFFSET(self, 8);
OAK_ABI_OFFSET(version, 12);
OAK_ABI_OFFSET(size, 14);
OAK_ABI_OFFSET(profile, 16);
OAK_ABI_OFFSET(speciesCapacity, 20);
OAK_ABI_OFFSET(defaultSpecies, 22);
OAK_ABI_OFFSET(selectorOffset, 24);
OAK_ABI_OFFSET(selectorWidth, 26);
OAK_ABI_OFFSET(eligibility, 28);
OAK_ABI_OFFSET(eligibilityBytes, 32);
OAK_ABI_OFFSET(policyVersion, 34);
OAK_ABI_OFFSET(spriteBridge, 36);
OAK_ABI_OFFSET(spriteConsumer, 40);
OAK_ABI_OFFSET(cryBridge, 44);
OAK_ABI_OFFSET(cryConsumer, 48);
OAK_ABI_OFFSET(frontTablePointerSlot, 52);
OAK_ABI_OFFSET(paletteTablePointerSlot, 56);
OAK_ABI_OFFSET(frontRowSize, 60);
OAK_ABI_OFFSET(paletteRowSize, 62);
OAK_ABI_OFFSET(bridgeSize, 64);
OAK_ABI_OFFSET(bridgeDescriptorOffset, 66);
OAK_ABI_OFFSET(bridgeConsumerOffset, 68);
OAK_ABI_OFFSET(pointerWidth, 70);
OAK_ABI_OFFSET(reserved, 72);
OAK_ABI_OFFSET(selectedSpecies, OAK_INTRO_SELECTOR_OFFSET);
OAK_ABI_OFFSET(reservedTail, 94);
#undef OAK_ABI_OFFSET
#undef OAK_ABI_ASSERT
