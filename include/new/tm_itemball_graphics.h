#pragma once

#include "../constants/map_objects.h"
#include "character_customization.h"

#define TM_ITEM_BALL_GRAPHICS_TABLE_ID 6
#define TM_ITEM_BALL_GRAPHICS_INDEX 92
#define TM_ITEM_BALL_GRAPHICS_TABLE_COUNT (TM_ITEM_BALL_GRAPHICS_INDEX + 1)
#define TM_ITEM_BALL_PALETTE_TAG 0x1106

#if MAP_OBJ_GFX_GOLD_TM_ITEM_BALL != ((TM_ITEM_BALL_GRAPHICS_TABLE_ID << 8) | TM_ITEM_BALL_GRAPHICS_INDEX)
#error "Gold TM itemball graphics id must remain exactly 0x065C"
#endif

extern NPCPtr gTmItemBallOverworldTable[TM_ITEM_BALL_GRAPHICS_TABLE_COUNT];
