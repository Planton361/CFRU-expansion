#include "defines.h"
#include "../include/constants/battle.h"

void ViridianForest_IsPoisonInParty(void)
{
    u8 partyIndex;

    gSpecialVar_LastResult = FALSE;
    for (partyIndex = 0; partyIndex < PARTY_SIZE; partyIndex++)
    {
        if (GetMonData(&gPlayerParty[partyIndex], MON_DATA_STATUS, NULL) & STATUS1_PSN_ANY)
        {
            gSpecialVar_LastResult = TRUE;
            return;
        }
    }
}
