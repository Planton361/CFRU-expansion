#include <assert.h>
#include <stdio.h>

#include "../../include/battle.h"
#include "../../include/new/ai_standard_policy.h"

int main(void)
{
	assert(sizeof(struct BattlePokemon) == 0x58);
	assert(sizeof(struct BattleMove) == 0x0C);
	printf("BattlePokemon=0x%zX BattleMove=0x%zX BattleStruct=0x%zX NewBattleStruct=0x%zX StandardCandidate=0x%zX StandardObservation=0x%zX StandardResult=0x%zX\n",
		sizeof(struct BattlePokemon), sizeof(struct BattleMove),
		sizeof(struct BattleStruct), sizeof(struct NewBattleStruct),
		sizeof(struct StandardPolicyCandidate), sizeof(struct StandardPolicyObservation),
		sizeof(struct StandardPolicyResult));
	return 0;
}
