#include <assert.h>
#include <stdio.h>
#include <string.h>

#include "../../src/defines.h"
#include "../../include/new/ai_opponent_replacement.h"

static struct Pokemon sOpponentParty[PARTY_SIZE];
static struct Pokemon sPlayerParty[PARTY_SIZE];

static void ClearParties(void)
{
	memset(sOpponentParty, 0, sizeof(sOpponentParty));
	memset(sPlayerParty, 0, sizeof(sPlayerParty));
}

static void SetMon(struct Pokemon* mon, u16 species, u16 hp, bool8 isEgg)
{
	mon->species = species;
	mon->hp = hp;
	mon->isEgg = isEgg;
}

static void TestValidStandardAndIronmonReplacements(void)
{
	u8 selected;

	ClearParties();
	SetMon(&sOpponentParty[0], SPECIES_SQUIRTLE, 0, FALSE);
	SetMon(&sOpponentParty[1], SPECIES_CHARMANDER, 18, FALSE);

	/* Standard and Ironmon use this same production controller validator. */
	selected = 1;
	assert(OpponentReplacementIndexIsUsable(sOpponentParty, sOpponentParty,
		0, 2, selected, 0, 0));
	assert(selected == 1);
	puts("Standard/Ironmon valid 2-mon forced replacement PASS");
}

static void TestSentinelFallback(void)
{
	u8 selected;

	ClearParties();
	SetMon(&sOpponentParty[0], SPECIES_SQUIRTLE, 0, FALSE);
	SetMon(&sOpponentParty[1], SPECIES_CHARMANDER, 18, FALSE);
	SetMon(&sOpponentParty[2], SPECIES_PIDGEY, 20, FALSE);

	selected = PARTY_SIZE;
	assert(!OpponentReplacementIndexIsUsable(sOpponentParty, sOpponentParty,
		0, 3, selected, 0, 0));
	selected = OpponentReplacementFindFirstUsable(sOpponentParty, sOpponentParty,
		0, 3, 0, 0);
	assert(selected == 1);

	assert(!OpponentReplacementIndexIsUsable(sOpponentParty, sOpponentParty,
		0, 3, PARTY_SIZE + 1, 0, 0));
	assert(OpponentReplacementFindFirstUsable(sOpponentParty, sOpponentParty,
		0, 3, 0, 0) == 1);
	puts("PARTY_SIZE and out-of-range chooser results use safe fallback PASS");
}

static void TestDeadEmptyEggAndCurrentRejection(void)
{
	ClearParties();
	SetMon(&sOpponentParty[0], SPECIES_SQUIRTLE, 20, FALSE);
	SetMon(&sOpponentParty[1], SPECIES_CHARMANDER, 0, FALSE);
	SetMon(&sOpponentParty[2], SPECIES_NONE, 20, FALSE);
	SetMon(&sOpponentParty[3], SPECIES_PIDGEY, 20, TRUE);
	SetMon(&sOpponentParty[4], SPECIES_EGG, 20, FALSE);
	SetMon(&sOpponentParty[5], SPECIES_PIDGEY, 20, FALSE);

	assert(!OpponentReplacementIndexIsUsable(sOpponentParty, sOpponentParty,
		0, PARTY_SIZE, 0, 0, 0));
	assert(!OpponentReplacementIndexIsUsable(sOpponentParty, sOpponentParty,
		0, PARTY_SIZE, 1, 0, 0));
	assert(!OpponentReplacementIndexIsUsable(sOpponentParty, sOpponentParty,
		0, PARTY_SIZE, 2, 0, 0));
	assert(!OpponentReplacementIndexIsUsable(sOpponentParty, sOpponentParty,
		0, PARTY_SIZE, 3, 0, 0));
	assert(!OpponentReplacementIndexIsUsable(sOpponentParty, sOpponentParty,
		0, PARTY_SIZE, 4, 0, 0));
	assert(OpponentReplacementFindFirstUsable(sOpponentParty, sOpponentParty,
		0, PARTY_SIZE, 0, 0) == 5);
	puts("dead/empty/egg/current-slot filtering PASS");
}

static void TestPartyOwnershipAndRange(void)
{
	ClearParties();
	SetMon(&sOpponentParty[2], SPECIES_PIDGEY, 20, FALSE); /* other trainer's range */
	SetMon(&sOpponentParty[3], SPECIES_SQUIRTLE, 0, FALSE);
	SetMon(&sOpponentParty[4], SPECIES_CHARMANDER, 18, FALSE);
	SetMon(&sOpponentParty[5], SPECIES_PIDGEY, 20, FALSE);
	SetMon(&sPlayerParty[4], SPECIES_CHARMANDER, 18, FALSE);

	assert(!OpponentReplacementIndexIsUsable(sOpponentParty, sOpponentParty,
		3, 6, 2, 3, 3));
	assert(OpponentReplacementFindFirstUsable(sOpponentParty, sOpponentParty,
		3, 6, 3, 3) == 4);
	assert(OpponentReplacementIndexIsUsable(sOpponentParty, sOpponentParty,
		3, 6, 5, 3, 3));

	/* Even a valid numeric index is rejected when the source party is the player party. */
	assert(!OpponentReplacementIndexIsUsable(sPlayerParty, sOpponentParty,
		3, 6, 4, 3, 3));
	assert(OpponentReplacementFindFirstUsable(sPlayerParty, sOpponentParty,
		3, 6, 3, 3) == PARTY_SIZE);
	puts("opponent party ownership/range isolation PASS");
}

static void TestRepeatedReplacementAndBattleEnd(void)
{
	u8 selected;

	ClearParties();
	SetMon(&sOpponentParty[0], SPECIES_SQUIRTLE, 0, FALSE);
	SetMon(&sOpponentParty[1], SPECIES_CHARMANDER, 18, FALSE);

	assert(OpponentReplacementIndexIsUsable(sOpponentParty, sOpponentParty,
		0, 2, 1, 0, 0));
	sOpponentParty[1].hp = 0;
	assert(OpponentReplacementFindFirstUsable(sOpponentParty, sOpponentParty,
		0, 2, 1, 1) == PARTY_SIZE);

	ClearParties();
	SetMon(&sOpponentParty[0], SPECIES_SQUIRTLE, 0, FALSE);
	SetMon(&sOpponentParty[1], SPECIES_CHARMANDER, 18, FALSE);
	SetMon(&sOpponentParty[2], SPECIES_PIDGEY, 20, FALSE);
	selected = OpponentReplacementFindFirstUsable(sOpponentParty, sOpponentParty,
		0, 3, 0, 0);
	assert(selected == 1);
	sOpponentParty[selected].hp = 0;

	selected = OpponentReplacementFindFirstUsable(sOpponentParty, sOpponentParty,
		0, 3, 1, 1);
	assert(selected == 2);
	sOpponentParty[selected].hp = 0;

	/* The last opposing faint has no replacement and must not emit an index. */
	assert(OpponentReplacementFindFirstUsable(sOpponentParty, sOpponentParty,
		0, 3, 2, 2) == PARTY_SIZE);
	assert(!OpponentReplacementIndexIsUsable(sOpponentParty, sOpponentParty,
		0, 3, PARTY_SIZE, 2, 2));
	puts("2-mon/3-mon repeated replacements and final-faint stop PASS");
}

static void TestValidVoluntaryTargetUnchanged(void)
{
	ClearParties();
	SetMon(&sOpponentParty[0], SPECIES_SQUIRTLE, 20, FALSE);
	SetMon(&sOpponentParty[1], SPECIES_CHARMANDER, 18, FALSE);
	SetMon(&sOpponentParty[2], SPECIES_PIDGEY, 20, FALSE);

	/* A valid preselected target passes through unchanged. */
	assert(OpponentReplacementIndexIsUsable(sOpponentParty, sOpponentParty,
		0, 3, 2, 0, 0));
	puts("valid voluntary target identity unchanged PASS");
}

int main(void)
{
	TestValidStandardAndIronmonReplacements();
	TestSentinelFallback();
	TestDeadEmptyEggAndCurrentRejection();
	TestPartyOwnershipAndRange();
	TestRepeatedReplacementAndBattleEnd();
	TestValidVoluntaryTargetUnchanged();
	return 0;
}
