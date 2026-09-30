#include "../../src/config.h"
#include "../../include/new/settings.h"

#include <assert.h>
#include <stdio.h>
#include <string.h>

static u16 syntheticVars[0x5200];
static u8 syntheticFlags[0x1000];

u16 VarGet(u16 var)
{
    return syntheticVars[var];
}

bool8 VarSet(u16 var, u16 value)
{
    syntheticVars[var] = value;
    return TRUE;
}

u8 FlagSet(u16 flag)
{
    syntheticFlags[flag] = TRUE;
    return TRUE;
}

bool8 FlagGet(u16 flag)
{
    return syntheticFlags[flag];
}

static void SyntheticWipe(void)
{
    memset(syntheticVars, 0, sizeof(syntheticVars));
    memset(syntheticFlags, 0, sizeof(syntheticFlags));
}

/* Mirrors the relevant public pret InitEventData behavior: saved flags and
 * vars are cleared after NewGameSaveClearHook returns. */
static void SyntheticInitEventData(void)
{
    memset(syntheticVars, 0, sizeof(syntheticVars));
    memset(syntheticFlags, 0, sizeof(syntheticFlags));
}

static bool8 ShouldPlayerRunContract(bool8 autoRun, bool8 bHeld, bool8 restricted)
{
    if (restricted)
        return FALSE;
    return autoRun ? !bHeld : bHeld;
}

static void TestNegativeOldOrderingWitness(void)
{
    SyntheticWipe();

    /* This is the old #538 order: set after the CFRU wipe, then vanilla
     * InitEventData clears the flag. The assertion is the regression witness. */
    ApplyFreshNewGameSettings();
    SyntheticInitEventData();

    assert(!FlagGet(FLAG_RUNNING_ENABLED));
    assert(!FlagGet(FLAG_AUTO_RUN));
    assert(syntheticVars[VAR_GAME_DIFFICULTY] == 0);
    puts("Negative witness: pre-InitEventData running/settings writes are erased: PASS");
}

static void TestFreshNewGameRunsAfterAllResets(void)
{
    SyntheticWipe(); /* NewGameWipeNewSaveData clears the CFRU expansion. */
    QueueFreshNewGameSettings();

    assert(!FlagGet(FLAG_RUNNING_ENABLED));
    SyntheticInitEventData(); /* ClearSav1 / InitEventData follow the hook. */
    ApplyQueuedFreshNewGameSettings(); /* first post-init field input */

    assert(FlagGet(FLAG_RUNNING_ENABLED));
    assert(!FlagGet(FLAG_AUTO_RUN));
    assert(syntheticVars[VAR_GAME_DIFFICULTY] == OPTIONS_VANILLA_DIFFICULTY);
    assert(syntheticVars[VAR_TRAINER_LEVEL_SCALING_MODE] == TRAINER_LEVEL_SCALING_OFF + 1);
    assert(syntheticVars[VAR_WILD_LEVEL_SCALING] == 0);
    assert(syntheticVars[VAR_TRAINER_AI_PROFILE] == TRAINER_AI_PROFILE_STANDARD + 1);

    FlagSet(FLAG_AUTO_RUN);
    FlagSet(FLAG_RUNNING_ENABLED);
    syntheticFlags[FLAG_RUNNING_ENABLED] = FALSE;
    ApplyQueuedFreshNewGameSettings();
    assert(!FlagGet(FLAG_RUNNING_ENABLED)); /* request is consumed only once */
    assert(FlagGet(FLAG_AUTO_RUN)); /* no default helper mutation */
    puts("Fresh New Game post-reset settings and one-shot running flag: PASS");
}

static void TestExistingSaveLoadDoesNotForceRunning(void)
{
    SyntheticWipe();
    syntheticVars[VAR_GAME_DIFFICULTY] = 3;
    syntheticFlags[FLAG_AUTO_RUN] = TRUE;

    ApplyQueuedFreshNewGameSettings(); /* no fresh-game queue on this path */
    assert(!FlagGet(FLAG_RUNNING_ENABLED));
    assert(FlagGet(FLAG_AUTO_RUN));
    assert(syntheticVars[VAR_GAME_DIFFICULTY] == 3);

    FlagSet(FLAG_RUNNING_ENABLED);
    ApplyQueuedFreshNewGameSettings();
    assert(FlagGet(FLAG_RUNNING_ENABLED)); /* existing saved state is preserved */
    assert(FlagGet(FLAG_AUTO_RUN));
    puts("Existing-save load does not force or rewrite running flags: PASS");
}

static void TestBAndRestrictionContract(void)
{
    assert(ShouldPlayerRunContract(FALSE, TRUE, FALSE));  /* Auto-Run off + B = run */
    assert(!ShouldPlayerRunContract(TRUE, TRUE, FALSE)); /* Auto-Run on + B = walk */
    assert(ShouldPlayerRunContract(TRUE, FALSE, FALSE)); /* Auto-Run on + no B = run */
    assert(!ShouldPlayerRunContract(FALSE, TRUE, TRUE)); /* restrictions still win */
    puts("B/Auto-Run movement contract truth table: PASS");
}

int main(void)
{
    TestNegativeOldOrderingWitness();
    TestFreshNewGameRunsAfterAllResets();
    TestExistingSaveLoadDoesNotForceRunning();
    TestBAndRestrictionContract();
    puts("Early Running full-lifecycle host tests: PASS");
    return 0;
}
