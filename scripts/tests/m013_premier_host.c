#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "include/constants/items.h"
typedef uint8_t u8;
typedef uint16_t u16;
typedef int16_t s16;
#define MULTIPLE_PREMIER_BALLS_AT_ONCE
#define ENABLE_MULTIPLE_PURCHASE_REWARDS
#define ARRAY_COUNT(a) (sizeof(a) / sizeof((a)[0]))
#define A_BUTTON 1
#define B_BUTTON 2
#define SE_SELECT 5
#define STR_CONV_MODE_LEFT_ALIGN 0
struct Task { s16 data[16]; void (*func)(u8); } gTasks[1];
struct { u16 newKeys; } gMain;
u8 gStringVar1[32], gStringVar2[32];
const u8 gText_ReceivedBonusItem[] = "custom";
const u8 gText_ThrowInOnePremierBall[] = "one";
const u8 gText_ThrowInPremierBalls[] = "many";
static u16 capacity, awardedItem, awardedQty, displayedQty;
static unsigned additions, returns, messages, sounds;
static int failAdd;
static const u8 *message;
static void Idle(u8 task) { (void)task; }
static void BuyMenuReturnToItemList(u8 task) { ++returns; gTasks[task].func = Idle; }
static void BuyMenuDisplayMessage(u8 task, const u8 *text, void (*next)(u8))
{ ++messages; message = text; gTasks[task].func = next; }
static void PlaySE(u16 sound) { assert(sound == SE_SELECT); ++sounds; }
static u8 GetPocketByItemId(u16 item)
{ return item <= ITEM_PREMIER_BALL || item == ITEM_DUSK_BALL ? POCKET_POKE_BALLS : 1; }
static int CheckBagHasSpace(u16 item, u16 count)
{ assert(item == ITEM_PREMIER_BALL && count > 0); return count <= capacity; }
static int AddBagItem(u16 item, u16 count)
{
    ++additions;
    if (failAdd || count > capacity) return 0;
    capacity -= count; awardedItem = item; awardedQty += count; return 1;
}
static void VarSet(u16 var, u16 value) { (void)var; (void)value; }
static void ConvertIntToDecimalStringN(u8 *dst, u16 n, int mode, int digits)
{ (void)dst; (void)mode; (void)digits; displayedQty = n; }
static const u8 *ItemId_GetName(u16 item) { (void)item; return (const u8 *)"Premier Ball"; }
static void StringCopy(u8 *dst, const u8 *src) { strcpy((char *)dst, (const char *)src); }
static void CopyItemName(u16 item, u8 *dst) { StringCopy(dst, ItemId_GetName(item)); }
/* PURCHASE_SOURCE */
static void Setup(u16 item, u16 qty, u16 room, u16 keys)
{
    memset(gTasks, 0, sizeof(gTasks));
    gTasks[0].data[1] = qty; gTasks[0].data[5] = item;
    gTasks[0].func = Task_ReturnToItemListAfterItemPurchase;
    gMain.newKeys = keys; capacity = room;
    awardedItem = awardedQty = displayedQty = 0;
    additions = returns = messages = sounds = 0; failAdd = 0; message = NULL;
}
int main(void)
{
    const u16 balls[] = {ITEM_POKE_BALL, ITEM_GREAT_BALL, ITEM_ULTRA_BALL,
                         ITEM_PREMIER_BALL, ITEM_DUSK_BALL};
    const u16 quantities[] = {0, 1, 9, 10, 19, 20, 21, 99, 255, 256, 999};
    unsigned cases = 0;
    for (unsigned b = 0; b < ARRAY_COUNT(balls); ++b)
    for (unsigned q = 0; q < ARRAY_COUNT(quantities); ++q)
    for (u16 room = 0; room <= 100; ++room)
    for (u16 key = A_BUTTON; key <= B_BUTTON; ++key)
    {
        u16 expected = quantities[q] / 10;
        if (expected > room) expected = room;
        Setup(balls[b], quantities[q], room, key);
        gTasks[0].func(0);
        assert(awardedQty == expected && sounds == 1);
        assert(additions == (expected > 0) && messages == (expected > 0));
        if (expected)
        {
            assert(awardedItem == ITEM_PREMIER_BALL && displayedQty == expected);
            assert(message == (expected == 1 ? gText_ThrowInOnePremierBall : gText_ThrowInPremierBalls));
        }
        /* Repeated input advances the new callback; it must not award twice. */
        gTasks[0].func(0); gTasks[0].func(0);
        assert(awardedQty == expected && additions == (expected > 0));
        ++cases;
    }
    Setup(ITEM_GREAT_BALL, 20, 9, 0); gTasks[0].func(0);
    assert(additions == 0 && sounds == 0 && returns == 0);
    Setup(ITEM_GREAT_BALL, 20, 9, A_BUTTON); failAdd = 1; gTasks[0].func(0);
    assert(additions == 1 && awardedQty == 0 && messages == 0 && returns == 1);
    /* Separate 9-ball purchases never accumulate into a bonus. */
    for (int i = 0; i < 2; ++i)
    { Setup(ITEM_POKE_BALL, 9, 9, A_BUTTON); gTasks[0].func(0); assert(awardedQty == 0); }
    /* Every non-ball reward retains its original threshold, item and quantity. */
    for (unsigned i = 0; i < ARRAY_COUNT(sPurchaseRewards); ++i)
    {
        const PurchaseReward *r = &sPurchaseRewards[i];
        if (GetPocketByItemId(r->purchasedItem) == POCKET_POKE_BALLS) continue;
        Setup(r->purchasedItem, r->requiredAmount - 1, 99, A_BUTTON);
        gTasks[0].func(0); assert(awardedQty == 0);
        Setup(r->purchasedItem, r->requiredAmount * 2, 99, B_BUTTON);
        gTasks[0].func(0);
        assert(awardedItem == r->rewardItem && awardedQty == r->rewardQty * 2);
        assert(message == gText_ReceivedBonusItem);
        /* Large non-ball purchases retain the pinned callback's u8 semantics;
         * only the Premier calculation is widened by this milestone. */
        for (unsigned q = 0; q < ARRAY_COUNT(quantities); ++q)
        {
            u8 legacyQty = (u8)quantities[q];
            u8 expected = legacyQty >= r->requiredAmount
                ? (u8)((legacyQty / r->requiredAmount) * r->rewardQty) : 0;
            Setup(r->purchasedItem, quantities[q], 1000, A_BUTTON);
            gTasks[0].func(0);
            assert(awardedQty == expected);
            if (expected) assert(awardedItem == r->rewardItem);
        }
    }
    puts("M-013 real callback: thresholds, every capacity 0..100, A/B, 16-bit quantities,");
    printf("%u ball cases, single reward, failure/no-input and all non-ball controls PASS\n", cases);
    return 0;
}
