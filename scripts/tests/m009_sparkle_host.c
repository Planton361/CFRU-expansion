// Host-only engine doubles. The checker inserts the actual scanner below.
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef uint8_t u8;
typedef uint16_t u16;
typedef uint32_t u32;
typedef int16_t s16;
typedef u8 bool8;
#define FALSE 0
#define TRUE 1
#define NUM_TASKS 16
#define ITEM_NONE 0
#define FLAG_HIDDEN_ITEMS_START 1000
#define FLDEFF_SPARKLE 54
typedef void (*TaskFunc)(u8);
struct Task { TaskFunc func; bool8 isActive; u8 prev, next, priority; s16 data[16]; };
struct Task gTasks[NUM_TASKS];
struct BgEvent { u16 x, y; u8 elevation, kind; union { u32 hiddenItem; } bgUnion; };
struct MapEvents { u8 bgEventCount; struct BgEvent *bgEvents; };
struct MapHeader { const struct MapEvents *events; } gMapHeader;
struct SaveBlock1 { struct { s16 x, y; } pos; struct { u8 mapGroup, mapNum; } location; } save;
struct SaveBlock1 *gSaveBlock1 = &save;
u32 gFieldEffectArguments[8];
static bool8 flags[256];
static unsigned spawns, spawnX[512], spawnY[512];

static bool8 FlagGet(u16 flag)
{
    assert(flag >= 1000 && flag < 1256);
    return flags[flag - 1000];
}
static u8 FindTaskIdByFunc(TaskFunc func)
{
    for (u8 i = 0; i < NUM_TASKS; ++i)
        if (gTasks[i].isActive && gTasks[i].func == func) return i;
    return 0xFF;
}
static u8 GetTaskCount(void)
{
    u8 count = 0;
    for (u8 i = 0; i < NUM_TASKS; ++i) count += gTasks[i].isActive != 0;
    return count;
}
static void DestroyTask(u8 taskId)
{
    assert(taskId < NUM_TASKS && gTasks[taskId].isActive);
    gTasks[taskId].isActive = FALSE;
}
static u8 CreateTask(TaskFunc func, u8 priority)
{
    for (u8 i = 0; i < NUM_TASKS; ++i)
        if (!gTasks[i].isActive)
        {
            memset(&gTasks[i], 0, sizeof(gTasks[i]));
            gTasks[i].func = func;
            gTasks[i].priority = priority;
            gTasks[i].isActive = TRUE;
            return i;
        }
    assert(!"scanner called CreateTask with no available slot");
    return 0;
}
static u8 FieldEffectStart(u8 effect)
{
    assert(effect == FLDEFF_SPARKLE);
    assert(gFieldEffectArguments[2] == 0);
    assert(spawns < 512);
    spawnX[spawns] = gFieldEffectArguments[0];
    spawnY[spawns++] = gFieldEffectArguments[1];
    return 0; // Deliberately not a sprite handle.
}

/* SCANNER_SOURCE */

static struct BgEvent events[37];
static struct MapEvents map;
static void reset(void)
{
    memset(gTasks, 0, sizeof(gTasks));
    memset(&save, 0, sizeof(save));
    memset(flags, 0, sizeof(flags));
    memset(events, 0, sizeof(events));
    map.bgEventCount = 1;
    map.bgEvents = events;
    gMapHeader.events = &map;
    spawns = 0;
    events[0].kind = BG_EVENT_HIDDEN_ITEM;
    events[0].bgUnion.hiddenItem = 1 | (1u << 24);
}
static void frames(unsigned count)
{
    for (unsigned i = 0; i < count; ++i) TryStartVisibleHiddenItemSparkles();
}
static void unrelated(u8 id) { (void)id; }

int main(void)
{
    // Packed cache: all 36 positions and all legal values, no adjacent damage.
    u8 packed[32] = {0};
    packed[0] = 11; packed[1] = 22; packed[31] = 99;
    for (u8 value = 0; value <= 16; ++value)
    {
        for (u16 i = 0; i < 36; ++i) SetCooldown(packed, i, value);
        for (u16 i = 0; i < 36; ++i) assert(GetCooldown(packed, i) == value);
        SetCooldown(packed, 17, 16 - value);
        for (u16 i = 0; i < 36; ++i)
            assert(GetCooldown(packed, i) == (i == 17 ? 16 - value : value));
        assert(packed[0] == 11 && packed[1] == 22 && packed[31] == 99);
    }
    assert(GetHiddenItemAttr(0xFFFFFFFF, HIDDEN_ITEM_FLAG) == 1255);
    assert(GetHiddenItemAttr(0xFFFFFFFF, HIDDEN_ITEM_ITEM) == 65535);
    assert(GetHiddenItemAttr(0xFFFFFFFF, HIDDEN_ITEM_QUANTITY) == 127);
    assert(GetHiddenItemAttr(0xFFFFFFFF, HIDDEN_ITEM_UNDERFOOT) == 1);
    assert(GetHiddenItemAttr(0, 99) == 1);

    // No events / malformed tables / future map capacity: no task or effect.
    reset(); gMapHeader.events = NULL; frames(1); assert(!spawns && !GetTaskCount());
    reset(); map.bgEvents = NULL; frames(1); assert(!spawns && !GetTaskCount());
    reset(); map.bgEventCount = 0; frames(1); assert(!spawns && !GetTaskCount());
    reset(); map.bgEventCount = 37; frames(1); assert(!spawns && !GetTaskCount());

    // All exclusions plus two independent visible events in one frame.
    reset(); map.bgEventCount = 6;
    for (u8 i = 0; i < 6; ++i) { events[i] = events[0]; events[i].bgUnion.hiddenItem |= (u32)i << 16; }
    events[0].kind = 0;
    events[1].bgUnion.hiddenItem &= 0xFFFF0000;
    events[2].bgUnion.hiddenItem |= 1u << 31;
    flags[3] = TRUE;
    events[4].x = 1; events[5].x = 2;
    frames(1); assert(spawns == 2 && spawnX[0] == 1 && spawnX[1] == 2);
    frames(16); assert(spawns == 2);
    frames(1); assert(spawns == 4); // Cyan's 16 decrementing frames then next spawn.
    unsigned before = spawns;
    gTasks[FindTaskIdByFunc(Task_M009SparkleCache)].func(0);
    assert(spawns == before); // No scan or effect from the storage task.

    // Every inclusive viewport edge and one tile outside each edge.
    reset(); save.pos.x = 10; save.pos.y = 10; map.bgEventCount = 8;
    const u16 xs[] = {3, 17, 10, 10, 2, 18, 10, 10};
    const u16 ys[] = {10, 10, 5, 15, 10, 10, 4, 16};
    for (u8 i = 0; i < 8; ++i) { events[i] = events[0]; events[i].x = xs[i]; events[i].y = ys[i]; }
    frames(1); assert(spawns == 4);
    for (u8 i = 0; i < 4; ++i) assert(spawnX[i] == xs[i] && spawnY[i] == ys[i]);

    // Move the second Forest item into range, then out. No global cooldown starvation.
    reset(); map.bgEventCount = 2; events[1] = events[0];
    events[0].x = 3; events[0].y = 22; events[1].x = 28; events[1].y = 57;
    save.pos.x = 3; save.pos.y = 22; frames(1); assert(spawns == 1 && spawnY[0] == 22);
    save.pos.x = 28; save.pos.y = 57; frames(1); assert(spawns == 2 && spawnY[1] == 57);
    save.pos.x = 100; save.pos.y = 100; frames(40); assert(spawns == 2);

    // Pickup suppresses future effects; bag-full (no flag) retains them; renewal clears flag.
    reset(); frames(1); flags[0] = TRUE; frames(40); assert(spawns == 1);
    flags[0] = FALSE; frames(17); assert(spawns == 2);
    frames(17); assert(spawns == 3);

    // Connected transitions (tasks retained) reset by BOTH map identifiers.
    reset(); frames(1); save.location.mapNum++; frames(1); assert(spawns == 2);
    save.location.mapGroup++; frames(1); assert(spawns == 3 && GetTaskCount() == 1);
    // Warp / party or bag return / same-map reload: ResetTasks invalidates RAM.
    memset(gTasks, 0, sizeof(gTasks)); frames(1); assert(spawns == 4 && GetTaskCount() == 1);
    flags[0] = TRUE; memset(gTasks, 0, sizeof(gTasks)); frames(1); assert(spawns == 4);

    // A -> empty connected B -> A must not retain A's old cooldown.
    reset(); frames(1); map.bgEventCount = 0; save.location.mapNum = 1;
    frames(1); assert(GetTaskCount() == 0);
    map.bgEventCount = 1; save.location.mapNum = 0; frames(1); assert(spawns == 2);

    // All 36 events including the last packed counter, after a retained start-menu frame loop.
    reset(); map.bgEventCount = 36;
    for (u8 i = 0; i < 36; ++i) { events[i] = events[0]; events[i].bgUnion.hiddenItem |= (u32)i << 16; }
    frames(1); assert(spawns == 36);
    frames(16); assert(spawns == 36);
    frames(1); assert(spawns == 72);

    // Task pressure must not alias/overwrite slot zero; preserve a spare slot.
    reset();
    for (u8 i = 0; i < 15; ++i) { gTasks[i].isActive = TRUE; gTasks[i].func = unrelated; gTasks[i].data[0] = 123; }
    frames(1); assert(spawns == 0 && GetTaskCount() == 15 && gTasks[0].data[0] == 123);
    gTasks[14].isActive = FALSE; frames(1); assert(spawns == 1 && GetTaskCount() == 15);
    puts("M-009 compiled scanner: filters, camera edges, 36 packed counters, independent cooldowns, map/reset lifecycle, pickup/renewal and task pressure PASS");
    return 0;
}
