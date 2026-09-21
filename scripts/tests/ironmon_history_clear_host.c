/* Calls the production ClearBattlerMoveHistory() entry point.  The link is
 * section-garbage-collected so only that source function and its real
 * IronmonAI_ClearPublicMoveCounts() dependency are retained. */
#include <assert.h>
#include <string.h>
#include "../../src/defines.h"
#include "../../src/defines_battle.h"
#include "../../include/new/battle_util.h"

static struct BattleHistory history;
static struct BattleResources resources;
static struct NewBattleStruct newBattle;
struct BattleResources* gBattleResources = &resources;
struct NewBattleStruct* gNewBS = &newBattle;

/* Keep the producer dependency tiny for this host link; the call itself is
 * made by the real battle_util.c ClearBattlerMoveHistory() implementation. */
void IronmonAI_ClearPublicMoveCounts(u8 bank)
{
	unsigned i;
	for (i = 0; i < MAX_MON_MOVES; ++i)
		newBattle.ai.ironmonMoveUseCounts[bank][i] = 0;
}

int main(void)
{
	unsigned i;
	resources.battleHistory = &history;
	for (i = 0; i < MAX_MON_MOVES; ++i)
	{
		history.usedMoves[1][i] = MOVE_STRENGTH;
		newBattle.ai.ironmonMoveUseCounts[1][i] = 7;
	}
	ClearBattlerMoveHistory(1);
	for (i = 0; i < MAX_MON_MOVES; ++i)
	{
		assert(history.usedMoves[1][i] == MOVE_NONE);
		assert(newBattle.ai.ironmonMoveUseCounts[1][i] == 0);
	}
	return 0;
}
