# Workspace #583 — native Early Running repair source proof

Evidence: **CONFIRMED USER DECISION + SOURCE/ARM/BUILD PASS**.
Target: `EARLY_RUNNING_NATIVE_CONFIG_REPAIR_READY`.
No runtime acceptance is claimed. The prior #577 implementation failed the
user's fresh-game B-running check; this repair does not extend that design.

## Revision basis and ownership

- Workspace main: `9138fff887c8da835597e5cfd2d367a92dc3ec4d`.
- CFRU base: `c208c4a05b2a70e3296fcbe90f061832fa4e0f8b`.
- Branch: `fix/583-native-early-running`.
- PR target: `compat/firered-gen9-randomizer`; user/CONTROL owns merge.
- UPR-FVX: `7bf79ee1e7c46c972f7a9c84942970a950be0723` (unchanged).
- DPE: `22ffa27ad09cfacbca841d90e6cbe31e6f9b7fdc` (unchanged).

Live Issue [#583](https://github.com/Planton361/firered-gen9-randomizer-workspace/issues/583)
and remote heads were checked before implementation. Workspace Gitlinks match
these exact pins. The existing local Workspace/CFRU worktree was left intact;
implementation uses a separate checkout at the exact CFRU base, one writer.

## Native Running proof established before product changes

[Base config](https://github.com/Planton361/CFRU-expansion/blob/c208c4a05b2a70e3296fcbe90f061832fa4e0f8b/src/config.h)
already documents commenting out `FLAG_RUNNING_ENABLED` as starting with
Running Shoes. This repair comments out that one definition, retaining
`FLAG_AUTO_RUN 0x914` and `CAN_RUN_IN_BUILDINGS`.

[Base overworld](https://github.com/Planton361/CFRU-expansion/blob/c208c4a05b2a70e3296fcbe90f061832fa4e0f8b/src/overworld.c):
`IsRunningDisabledByFlag()` returns `FALSE` under its existing `#else`.
`ShouldPlayerRun()` and all restriction functions are unchanged. Restrictions
(metatile, DexNav, underwater and other existing engine behavior) still win.
Indoor running uses the existing configuration, with no new indoor logic.

[Base keys](https://github.com/Planton361/CFRU-expansion/blob/c208c4a05b2a70e3296fcbe90f061832fa4e0f8b/src/read_keys.c):
`StartLButtonFunc()` wraps the progression `FlagGet` in
`#ifdef FLAG_RUNNING_ENABLED`. The compile-time removal preserves its separate
Auto-Run read/set/clear and existing button-mode, DexNav, bike/surf behavior.

`AutoRunHook 805BA30 0` remains unchanged. It passes held keys in r0 from r5
to `ShouldPlayerRun()`, selects run at `0x0805BA5A`, and walk at `0x0805BA8C`.
The B/Auto-Run truth table is tested using the actual extracted source
functions, rather than a rewritten truth-table implementation:

| Auto-Run | B | Movement, absent restrictions |
|---|---|---|
| Off | Held | Run |
| Off | Released | Walk |
| On | Released | Run |
| On | Held | Walk |

Running succeeds before any Fresh-Settings helper call. Neither these four
Vars nor the old progression flag is a movement dependency.

## Fresh settings lifecycle: source proof before selecting the hook

Public pret source:

- [new_game.c](https://github.com/pret/pokefirered/blob/037335f4c725d7c9aecdac87066f2002b4bd7e14/src/new_game.c)
- [event_data.c](https://github.com/pret/pokefirered/blob/037335f4c725d7c9aecdac87066f2002b4bd7e14/src/event_data.c)
- [load_save.c](https://github.com/pret/pokefirered/blob/037335f4c725d7c9aecdac87066f2002b4bd7e14/src/load_save.c)
- [overworld.c](https://github.com/pret/pokefirered/blob/037335f4c725d7c9aecdac87066f2002b4bd7e14/src/overworld.c)
- [ResetAllMapFlags](https://github.com/pret/pokefirered/blob/037335f4c725d7c9aecdac87066f2002b4bd7e14/data/event_scripts.s)

`NewGameInitData()` performs `ClearSav1()` then `InitEventData()`, clearing
vanilla saved flags/Vars. After PC-items initialization it still executes
`EventScript_ResetAllMapFlags` synchronously, restores the rival name and
resets Trainer Tower results before returning. The map reset script sets
hide flags and the massage cooldown; it does not own the four pilot Vars.

The existing expansion wipe hook is at the *entry* of NewGameInitData and is
too early. `Sav2_ClearSetDefault` owns vanilla SaveBlock2 options, not these
Vars. The existing M-005 `NewGameInitPCItems` replacement precedes the final
map reset, so it is not the requested late owner. Menu initialization must
preserve existing saves; field/on-frame hooks also run on existing saves.
No existing CFRU hook supplies the required stateless post-reset owner.

The selected new owner is the call site in **CB2_NewGame after NewGameInitData
returns**. Existing-save `CB2_ContinueSavedGame()` does not call
NewGameInitData or enter this call site. Whiteout and ordinary return-to-field
likewise do not enter it. CFRU's Quest Log replay of CB2_NewGameOld replays the
New Game lifecycle, not an ordinary saved-game Continue; no new global marker
or save migration is introduced.

### Exact BPRE address and replay proof

Public historical BPRE assembly, without inspecting a ROM:

- [CB2_NewGame assembly](https://github.com/pret/pokefirered/blob/9bcc82856db7e6417bb56265bbcc04dae290cbf3/asm/overworld.s)
- [NewGameInitData assembly, historical name sub_8054A60](https://github.com/pret/pokefirered/blob/b4b509f68477068ae111cc5a6094d858d396c4bb/asm/new_game.s)
- [ScriptContext1_Init assembly](https://github.com/pret/pokefirered/blob/9975ba7211cc91dc7fddec5f423ed3c42fc0d064/asm/script.s)

CB2_NewGame begins at `0x08056644`: `push {lr}` (2 bytes), then four BLs
(4 bytes each), the fourth being NewGameInitData. Its return is therefore
`0x08056656`. The next calls are ResetInitialPlayerAvatarState at `0x08056656`,
PlayTimeCounter_Start at `0x0805665A`, and ScriptContext1_Init at `0x0805665E`.
The selected CFRU symbol names the last callee `ScriptContext_Init` at
`0x08069A80 | 1`; public source/assembly identifies the same context initializer.

The existing `insert.Hook()` emits 10 bytes at a non-word-aligned site:
LDR/BX (4), alignment padding (2), destination literal (4). At `0x08056656`
it touches all three BLs, leaving the last BL's second halfword at
`0x08056660`. The hook replays **all three** calls and resumes at
`0x08056662 | 1`, before ScriptContext2_Disable. That leftover halfword is
never executed. Original CB2_NewGame's LR remains saved on its original stack;
the new hook balances no extra stack state and returns through the original
callback continuation and epilogue.

The three absolute Vanilla Thumb callees use literal loads and a local
`bx r3` trampoline, the same Thumb-1 pattern present in `assembly/main.s`.
Direct BL to absolute linker symbols produced BLX during verification, so the
final new hook explicitly avoids that ARM7-incompatible form. ARM assembly
and final linked disassembly prove the three replay calls, odd callee literals
`0x080559E5`, `0x08054839`, `0x08069A81`, and continuation `0x08056663`.

Final `ApplyFreshNewGameSettings()` owns exactly these four writes:

| Var | Raw default |
|---|---|
| VAR_GAME_DIFFICULTY | OPTIONS_VANILLA_DIFFICULTY = 4 |
| VAR_TRAINER_LEVEL_SCALING_MODE | TRAINER_LEVEL_SCALING_OFF + 1 = 1 |
| VAR_WILD_LEVEL_SCALING | 0 |
| VAR_TRAINER_AI_PROFILE | TRAINER_AI_PROFILE_STANDARD + 1 = 7 |

No FlagSet/FlagClear, running flag, Auto-Run mutation, allocation, latch,
SaveBlock field or unrelated mutation. Ironmon Smart remains a separate
preset (Trainer AI raw 8); options preserve untouched existing raw values.

## UPR-FVX and DPE evidence

At the selected UPR pin:

- [MiscTweak](https://github.com/Planton361/universal-pokemon-randomizer-fvx/blob/7bf79ee1e7c46c972f7a9c84942970a950be0723/romio/src/main/java/com/uprfvx/romio/MiscTweak.java)
  contains RUN_WITHOUT_RUNNING_SHOES.
- [GUI strings](https://github.com/Planton361/universal-pokemon-randomizer-fvx/blob/7bf79ee1e7c46c972f7a9c84942970a950be0723/random/src/main/resources/com/uprfvx/random/gui/Bundle.properties)
  name it Run Without Running Shoes and describe running before acquiring shoes.
- [Gen3RomHandler](https://github.com/Planton361/universal-pokemon-randomizer-fvx/blob/7bf79ee1e7c46c972f7a9c84942970a950be0723/romio/src/main/java/com/uprfvx/romio/romhandlers/Gen3RomHandler.java)
  routes `isCfruDpeGen9BpreProfile()` (expanded profile and BPRE) to the specialized
  patch. It finds the masked running-disallowed shape, then writes `0xE001`
  at +0x0E, bypassing the running-enabled branch.
- [Gen3RunningShoesTweakPatchTest](https://github.com/Planton361/universal-pokemon-randomizer-fvx/blob/7bf79ee1e7c46c972f7a9c84942970a950be0723/romio/src/test/java/com/uprfvx/romio/romhandlers/Gen3RunningShoesTweakPatchTest.java)
  includes `cfruDpeRunWithoutRunningShoesBypassesRunningEnabledFlagBranch` and
  unknown-shape availability rejection.

The new linked native IsRunningDisallowed is 0x26 bytes and lacks the flag
call/branch; the old 44-byte signature is absent from this function. Native
Early Running therefore makes this tweak redundant. `miscTweaksAvailable()`
only advertises it for this profile when the diagnostic signature finder is
nonnegative; availability may disappear and is not preserved artificially.
A stale request reaching applyRunWithoutRunningShoesPatch routes to the
profile-specific finder; absent signature returns -1 (<0) and no write occurs.
This is source proof, not a claim of running UPR on a private ROM. Neither
RUN_WITHOUT_RUNNING_SHOES nor the already redundant indoor tweak needs a UPR
change.

DPE's selected pinned src/include/hooks/README source inventory has no
Running-Shoes, ShouldPlayerRun, AutoRunHook or FLAG_RUNNING_ENABLED owner.
Its ownership is Pokémon/data expansion; movement belongs to CFRU.
No DPE or UPR file/Gitlink was changed.

## Removed #577 state and target-memory proof

Fully removed from product source and prototypes:
`sFreshNewGameSettingsPending`, `QueueFreshNewGameSettings`,
`ApplyQueuedFreshNewGameSettings`, queue from expansion wipe, queued apply from
on-frame scripts, and `FlagSet(FLAG_RUNNING_ENABLED)` from fresh defaults.
The now-unused settings includes in save/overworld are removed.

The old host pending-state simulation is replaced with actual source-function
movement tests. ARM comparison compiles original and final settings/save/
overworld with the existing approved compiler and source-only headers. It
rejects new mutable symbols or larger writable sections. Original settings
`.bss` size is 1; final size is 0, with no data/COMMON/EWRAM symbol. Hook object
has no data state. Final linked __bss_start__ equals __bss_end__; no removed
symbol, replacement mutable pending symbol or EWRAM orphan remains.
Unchanged functions whose names contain Pending (daycare/Standard AI) are
functions, not a replacement mutable state. The existing linked `.data`
section is retained; the audit compares changed units rather than falsely
requiring all historical CFRU data to vanish.

## Verification and invocation details

All following checks PASS:

```sh
python3 scripts/tests/run_early_running_pewter_tests.py
python3 scripts/tests/run_settings_defaults_tests.py
python3 scripts/tests/test_native_build_contract.py
python3 scripts/check_hidden_item_sparkle.py
python3 scripts/insert.py --check-map-object-overlays
python3 scripts/tests/audit_trainer_ai_storage.py
python3 scripts/tests/run_standard_ai_tests.py
CFRU_WORKSPACE_ROOT=<existing-workspace> python3 scripts/tests/run_ironmon_ai_tests.py
python3 scripts/check_coherent_learnsets.py
python3 scripts/check_premier_bonus.py
python3 scripts/check_renewable_hidden_items.py
python3 -m unittest scripts.tests.test_route10_hm05
python3 scripts/build.py
python3 scripts/tests/audit_native_early_running_arm.py --linked-object build/linked.o
python3 scripts/tests/audit_ai_writable_state.py --linked-object build/linked.o --output-bin build/output.bin
git diff --check
```

Correct disposable-checkout environment: M-009 uses sibling `references/`
public-source repositories for map census. Route10 also reads four public
pret text files materialized at `e060ab955b5dc9ac1c4904c2cd141683615cf477`.
Ironmon takes CFRU_WORKSPACE_ROOT for its existing accepted host fixtures.
Missing disposable reference files initially prevented census/Route10; adding
these public references resolved those setup errors without product changes.

Build-contract/source-identity and make.py fail-fast checks pass. M-009 has
39 negative ownership/composition mutations; the stale #577 frame requirement
is replaced by a stateless frame-entry invariant. Trainer-AI storage audit
likewise uses the new settings lifecycle; storage addresses/layout stay exact.
Route10: 6 tests PASS. Pewter script and its four overlay rows remain unchanged,
including no Shoes reward/dialog/Mom-letter flow and unchanged hide/remove.
Standard suite PASS; Ironmon 63/63 parity fixtures and 58/58 coverage tags PASS.
Learnsets, Premier and renewable items all PASS.

The full clean compile/link/objcopy completed with exit 0. It emitted 115 compiler
warnings in unchanged stock code, predominantly array bounds, plus unused
variables/parameters, pointer sizeof division, enum/int mismatch, type limits,
array comparison and indentation. Examples: attackcanceler, battle_script_util,
Battle_AI/ai_advanced and battle_anims. No changed C unit emitted a warning.
The unchanged linker layout also emits one RWX LOAD-segment warning.
The final assembly adjustment was rebuilt and linked with exit 0 (the same
linker warning). AI writable
state/re-extraction audit PASS on final output (size 0x2200D4); no insertion run.

Workspace check_git_safety.py PASS from its intended Workspace root before
writes. Running that Workspace-specific scanner directly in CFRU reports
pre-existing tracked deps binaries; none is read, edited or staged. The
component checkout is reviewed by exact changed paths and native source identity.

No ABI, SaveBlock/Pokemon/Trainer/BattleMove/NewBattleStruct layout, randomizer
format/table, repoint manifest, gameplay data, DPE/UPR or Gitlink changes.
No private ROM/build artifact, ROM inspection/hash, emulator, save or state.
Only newly generated, authorized ROM-free build objects were inspected.
`make.py` and private insertion were not run. Source/build proof does not
substitute for user runtime validation.

After CONTROL review and user merge: separate Workspace-CFRU Gitlink update;
user native DPE -> CFRU build; Fresh New Game B=run; L toggles Auto-Run;
Auto-Run on+B=walk; save/reload and Pewter cleanup regression.
