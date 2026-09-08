#include "../include/global.h"
#include "../include/item.h"

// Replaces BPRE NewGameInitPCItems at 0x080EB658.  The vanilla function
// clears PC storage before adding the starter Potion; M-005 retains only the
// clearing step so New Game cannot retain stale PC items.
void NewGameInitPCItems(void)
{
	ClearItemSlots(gSaveBlock1->pcItems, PC_ITEMS_COUNT);
}
