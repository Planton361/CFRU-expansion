#include <assert.h>
#include <stdio.h>
#include <stddef.h>

#include "../../include/battle.h"
#include "../../include/new/ai_standard_policy.h"
#include "../../include/new/ai_standard_mechanics.h"
#include "../../include/new/ai_ironmon_policy.h"

_Static_assert(offsetof(struct NewBattleStruct, ai.standardMemoryStageAfter)
	+ sizeof(((struct NewBattleStruct*)0)->ai.standardMemoryStageAfter)
	- offsetof(struct NewBattleStruct, ai.standardPolicySeeded) == 0xE4,
	"Standard battle-local allocation changed");
_Static_assert(sizeof(((struct NewBattleStruct*)0)->ai.standardDisplayedSpecies) == 8,
	"public display snapshot must add exactly 8 bytes");
_Static_assert(sizeof(((struct NewBattleStruct*)0)->ai.standardTypeUncertain) == 4,
	"sticky public type uncertainty must add exactly 4 bytes");
_Static_assert(offsetof(struct NewBattleStruct, ai.standardTypeUncertain)
	+ sizeof(((struct NewBattleStruct*)0)->ai.standardTypeUncertain)
	- offsetof(struct NewBattleStruct, ai.standardPolicySeeded) == 240,
	"total Standard battle-local state must be 240 bytes");
_Static_assert(offsetof(struct NewBattleStruct, ai.ironmonPolicySeeded)
	== offsetof(struct NewBattleStruct, ai.standardTypeUncertain)
	+ sizeof(((struct NewBattleStruct*)0)->ai.standardTypeUncertain),
	"Ironmon state must append without changing Standard layout");
_Static_assert(offsetof(struct NewBattleStruct, ai.ironmonMoveUseCounts)
	+ sizeof(((struct NewBattleStruct*)0)->ai.ironmonMoveUseCounts)
	- offsetof(struct NewBattleStruct, ai.ironmonPolicySeeded) == 52,
	"Ironmon battle-local allocation must remain 52 bytes");
_Static_assert(sizeof(struct StandardPolicyCandidate) == 52, "UNKNOWN flag uses existing padding");
_Static_assert(sizeof(struct StandardMechanicsInput) == 34,
	"possible Badge defense flag must remain source-owned mechanics state");
_Static_assert(sizeof(struct BattlePokemon) == 0x58, "BattlePokemon ABI");
_Static_assert(sizeof(struct BattleMove) == 0xC, "BattleMove ABI");
#ifdef __arm__
_Static_assert(sizeof(struct BattleStruct) == 0x200, "ARM BattleStruct ABI");
#endif

int main(void)
{
	assert(sizeof(struct BattlePokemon) == 0x58);
	assert(sizeof(struct BattleMove) == 0x0C);
	printf("BattlePokemon=0x%zX BattleMove=0x%zX BattleStruct=0x%zX (HOST HARNESS SIZE ONLY; target ARM ABI=0x200) NewBattleStruct=0x%zX StandardCandidate=0x%zX StandardObservation=0x%zX StandardResult=0x%zX\n",
		sizeof(struct BattlePokemon), sizeof(struct BattleMove),
		sizeof(struct BattleStruct), sizeof(struct NewBattleStruct),
		sizeof(struct StandardPolicyCandidate), sizeof(struct StandardPolicyObservation),
		sizeof(struct StandardPolicyResult));
	printf("StandardMechanicsInput=%zu DamageEnvelope=%zu; round-2 battle-local EWRAM delta=4; total Standard state=240; save delta=0\n",
		sizeof(struct StandardMechanicsInput), sizeof(struct StandardDamageEnvelope));
	printf("IronmonCandidate=%zu IronmonObservation=%zu IronmonResult=%zu IronmonResponse=%zu IronmonBranch=%zu; Ironmon ai fields=52; NewBattleStruct aligned delta=56; save delta=0\n",
		sizeof(struct IronmonPolicyCandidate), sizeof(struct IronmonPolicyObservation),
		sizeof(struct IronmonPolicyResult), sizeof(struct IronmonPolicyResponse),
		sizeof(struct IronmonPolicyBranch));
	return 0;
}
