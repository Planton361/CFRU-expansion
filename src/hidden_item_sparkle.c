#include "../include/global.h"
#include "../include/task.h"
#include "../include/event_data.h"
#include "../include/field_effect.h"
#include "../include/constants/items.h"
#include "../include/constants/flags.h"
#include "../include/new/hidden_item_sparkle.h"

// Source contracts from pret e060ab95 and Cyan natdex 16b8b9ff:
// constants/event_bg.h, global.fieldmap.h, fieldmap.c, field_specials.c.
#define BG_EVENT_HIDDEN_ITEM 7
#define MAP_OFFSET 7
enum { HIDDEN_ITEM_ITEM, HIDDEN_ITEM_FLAG, HIDDEN_ITEM_QUANTITY, HIDDEN_ITEM_UNDERFOOT };
extern struct MapHeader gMapHeader;

// CFRU does not export these two APIs. Keep the tiny source implementations
// local rather than inventing linker addresses or using player destinations.
static void GetCameraFocusCoords(u16 *x, u16 *y)
{
    *x = gSaveBlock1->pos.x + MAP_OFFSET;
    *y = gSaveBlock1->pos.y + MAP_OFFSET;
}

static u16 GetHiddenItemAttr(u32 hiddenItem, u8 attr)
{
    switch (attr)
    {
    case HIDDEN_ITEM_ITEM: return hiddenItem & 0xFFFF;
    case HIDDEN_ITEM_FLAG: return ((hiddenItem >> 16) & 0xFF) + FLAG_HIDDEN_ITEMS_START;
    case HIDDEN_ITEM_QUANTITY: return (hiddenItem >> 24) & 0x7F;
    case HIDDEN_ITEM_UNDERFOOT: return hiddenItem >> 31;
    default: return 1;
    }
}

// This linker puts ordinary .bss in ROM. Use existing task data as transient
// RAM: map group/number followed by 36 five-bit counters (25 bytes total).
// The task never scans/spawns; ONLY the canonical frame tail does that work.
// ResetTasks destroys the cache on warp/menu reload without heap allocations,
// saved state, new RAM addresses, or retained task/sprite pointers.
#define COOLDOWN_BITS 5
#define COOLDOWN_MASK 31
_Static_assert(2 + (M009_MAX_BG_EVENTS * COOLDOWN_BITS + 7) / 8 + 1 <= sizeof(gTasks[0].data), "cache exceeds task data");
_Static_assert(M009_SPARKLE_COOLDOWN <= COOLDOWN_MASK, "cooldown exceeds packed counter");

static void Task_M009SparkleCache(u8 taskId)
{
    (void)taskId;
}

static u8 GetCooldown(const u8 *cache, u16 event)
{
    u16 bit = event * COOLDOWN_BITS;
    u16 byte = 2 + bit / 8;
    u16 packed = cache[byte] | (cache[byte + 1] << 8);
    return (packed >> (bit % 8)) & COOLDOWN_MASK;
}

static void SetCooldown(u8 *cache, u16 event, u8 value)
{
    u16 bit = event * COOLDOWN_BITS;
    u16 byte = 2 + bit / 8;
    u16 shift = bit % 8;
    u16 packed = cache[byte] | (cache[byte + 1] << 8);
    packed = (packed & ~(COOLDOWN_MASK << shift)) | (value << shift);
    cache[byte] = packed;
    cache[byte + 1] = packed >> 8;
}

void TryStartVisibleHiddenItemSparkles(void)
{
    const struct MapEvents *events = gMapHeader.events;
    u16 focusX, focusY;
    s16 left, right, top, bottom;
    u16 i;
    u8 taskId;
    u8 *cache;
    bool8 fresh = FALSE;

    taskId = FindTaskIdByFunc(Task_M009SparkleCache);
    if (events == NULL || events->bgEvents == NULL || events->bgEventCount == 0
     || events->bgEventCount > M009_MAX_BG_EVENTS)
    {
        // A connected map with no BG events must invalidate the previous map
        // too, even if we return to that same map without ResetTasks.
        if (taskId != 0xFF)
            DestroyTask(taskId);
        return;
    }

    if (taskId == 0xFF)
    {
        // Vanilla CreateTask returns slot 0 on exhaustion: check BEFORE use.
        // Leave a spare task slot for normal overworld interactions.
        if (GetTaskCount() >= NUM_TASKS - 1)
            return;
        taskId = CreateTask(Task_M009SparkleCache, 0xFF);
        fresh = TRUE;
    }
    cache = (u8 *)gTasks[taskId].data;
    if (fresh || cache[0] != gSaveBlock1->location.mapGroup
              || cache[1] != gSaveBlock1->location.mapNum)
    {
        memset(cache, 0, sizeof(gTasks[taskId].data));
        cache[0] = gSaveBlock1->location.mapGroup;
        cache[1] = gSaveBlock1->location.mapNum;
    }

    GetCameraFocusCoords(&focusX, &focusY);
    left = focusX - 7;
    right = focusX + 7;
    top = focusY - 5;
    bottom = focusY + 5;
    for (i = 0; i < events->bgEventCount; i++)
    {
        const struct BgEvent *event = &events->bgEvents[i];
        u16 itemFlag;
        s16 itemX, itemY;
        u8 cooldown;

        if (event->kind != BG_EVENT_HIDDEN_ITEM)
            continue;
        if (GetHiddenItemAttr(event->bgUnion.hiddenItem, HIDDEN_ITEM_ITEM) == ITEM_NONE)
            continue;
        if (GetHiddenItemAttr(event->bgUnion.hiddenItem, HIDDEN_ITEM_UNDERFOOT))
            continue;
        itemFlag = GetHiddenItemAttr(event->bgUnion.hiddenItem, HIDDEN_ITEM_FLAG);
        if (FlagGet(itemFlag))
            continue;

        itemX = event->x + MAP_OFFSET;
        itemY = event->y + MAP_OFFSET;
        if (itemX < left || itemX > right || itemY < top || itemY > bottom)
            continue;
        cooldown = GetCooldown(cache, i);
        if (cooldown > 0)
        {
            SetCooldown(cache, i, cooldown - 1);
            continue;
        }

        gFieldEffectArguments[0] = event->x;
        gFieldEffectArguments[1] = event->y;
        gFieldEffectArguments[2] = 0;
        FieldEffectStart(FLDEFF_SPARKLE);
        SetCooldown(cache, i, M009_SPARKLE_COOLDOWN);
    }
}
