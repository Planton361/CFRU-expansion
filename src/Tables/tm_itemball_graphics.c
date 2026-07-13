#include "../defines.h"
#include "../../include/follower_mon_sprites.h"
#include "../../include/new/tm_itemball_graphics.h"

extern const u8 TMItemBallTiles[];

static const union AnimCmd sTmItemBallAnim[] =
{
    ANIMCMD_FRAME(0, 1),
    ANIMCMD_END,
};

static const union AnimCmd *const sTmItemBallAnimTable[] =
{
    sTmItemBallAnim,
};

static const struct SpriteFrameImage sTmItemBallImages[] =
{
    overworld_frame(TMItemBallTiles, 2, 2, 0),
};

static const struct EventObjectGraphicsInfo sTmItemBallGraphicsInfo =
{
    .tileTag = 0xFFFF,
    .paletteTag1 = TM_ITEM_BALL_PALETTE_TAG,
    .paletteTag2 = EVENT_OBJ_PAL_TAG_NONE,
    .size = (16 * 16) / 2,
    .width = 16,
    .height = 16,
    .shadowSize = SHADOW_SIZE_S,
    .inanimate = TRUE,
    .disableReflectionPaletteLoad = FALSE,
    .tracks = TRACKS_NONE,
    .gender = MALE,
    .oam = gEventObjectBaseOam_16x16,
    .subspriteTables = gEventObjectSpriteOamTables_16x16,
    .anims = sTmItemBallAnimTable,
    .images = sTmItemBallImages,
    .affineAnims = gDummySpriteAffineAnimTable,
};

NPCPtr gTmItemBallOverworldTable[TM_ITEM_BALL_GRAPHICS_TABLE_COUNT] =
{
    [TM_ITEM_BALL_GRAPHICS_INDEX] = &sTmItemBallGraphicsInfo,
};
