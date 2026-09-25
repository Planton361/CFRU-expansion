# R1 runtime fair-AI dispatch trace — Workspace #532

## Revision and disposition

- **CONFIRMED USER-SUPPLIED RUNTIME FAIL:** active Workspace `30f776cec15dd69eb542d25bf97e2d05998aa378`, CFRU `b8e58508f2474db1702c5fa0429a24dc076f1abc`, DPE `22ffa27ad09cfacbca841d90e6cbe31e6f9b7fdc`; fresh non-randomized New Game. Oak's-Lab Squirtle had Water Gun but repeatedly used Tail Whip, even with player Defense at minimum.
- CFRU branch starts exactly at `b8e58508f2474db1702c5fa0429a24dc076f1abc`. The final immutable SHA is recorded in the PR body and GitHub PR head; a commit cannot contain its own hash in this file.
- **Disposition: `RUNTIME_DIAGNOSTIC_REQUIRED`.** The source and production-equivalent host still enter the fair adapter for an ordinary Oak Trainer Single. The private runtime's raw profile, battle flags, hook execution, and public state have not been observed. No product scoring or Oak battle rule was changed.
- Workspace Gitlink and all other components are unchanged. No ROM, save, emulator state, build artifact, or private data was read or requested. `UPSTREAM_CONTRIBUTION = DEFERRED`.

## Why capped Tail Whip is incompatible with the accepted fair policy

The Oak party is one level-5 Squirtle with production-derived slots `Tackle (33) / Tail Whip (39) / Water Gun (55) / None (0)`. With the player public Charmander revealed and ordinary flags, both adapters return policy rc `0`, select slot 2, and emit Water Gun. With reveal deliberately omitted, Tackle and Water Gun are UNKNOWN-potential ties; Tail Whip is below the productive floor. With player Defense at stage `0`, both production adapters mark Tail Whip as a capped stat change and select/emit slot 0 Tackle in the host witness. Thus the repeated private Tail Whip at cap cannot be attributed to a legal Standard or Ironmon fair selection.

## Profile storage closure

`NewGameSaveClearHook` at `0x08054A60` calls `NewGameWipeNewSaveData`; that function clears the parasite (`0x0203B174`, `0x2EA4` bytes) before `ApplyFreshNewGameSettings` writes `VAR_TRAINER_AI_PROFILE = 0x515B` as Standard raw `7`. The Ironmon preset writes raw `8`. Options load the original raw through `VarGet`, display menu index `7` or `8`, set a dirty bit only on an edit, write the chosen raw through `VarSet` on close, and reopen through the same read helper. `GetTrainerAIProfile` decodes raw `7` to enum Standard `6` and raw `8` to enum Ironmon Smart `7`; raw `0` retains the legacy resolver.

The configured `SAVE_BLOCK_EXPANSION` makes `GetExpandedVarPointer(0x515B)` return `&gExpandedVars[0x15B]`. `gExpandedVars` begins at `0x0203B374`; the two-byte slot is `0x0203B62A..0x0203B62B`, inside the saved `0xEC4`-byte parasite and outside the preceding expanded flags. The source-owned pointer function was compiled and executed on a host with `0x5000`, `0x515B`, `0x51FF`, and `0x5200` boundary cases; writes/readback of raw `7` and `8` used exactly index `0x15B`. The `ExpandedVarsHook` at `0x0806E454` zero-extends the 16-bit ID, calls `GetExpandedVarPointer`, returns its pointer, and falls back to the base routine for other IDs. `BPRE.ld` places `GetVarPointer` at this hook site and `VarGet`/`VarSet` at `0x0806E568`/`0x0806E584`. The [pinned pret source](https://github.com/pret/pokefirered/blob/e060ab955b5dc9ac1c4904c2cd141683615cf477/src/event_data.c#L235-L249) shows that both base APIs call `GetVarPointer`.

The tracked CFRU C/header/script/data scan found no write to `0x515B`, decimal `20827`, or the backing address outside the settings/option owners. A literal `0x515B` in `assembly/followingmon_normal_pals.s` is palette data. The only broad clear covering the slot in the inspected source is the New Game parasite wipe before the default write. No later CFRU clear or alias to this slot was found. **Expected raw immediately before Oak setup is `7` after untouched fresh settings, or `8` after choosing Ironmon Smart.** The private runtime raw value remains unobserved.

## Oak battle flags and First Battle

The [pinned pret Oak script](https://github.com/pret/pokefirered/blob/e060ab955b5dc9ac1c4904c2cd141683615cf477/data/maps/PalletTown_ProfessorOaksLab/scripts.inc#L332-L334) uses `trainerbattle_earlyrival TRAINER_RIVAL_OAKS_LAB_SQUIRTLE, RIVAL_BATTLE_TUTORIAL`; the [macro](https://github.com/pret/pokefirered/blob/e060ab955b5dc9ac1c4904c2cd141683615cf477/asm/macros/event.inc#L776-L779) expands to early-rival mode `9` with helper value `3`. In CFRU, mode `9` uses `sContinueLostBattleParams` while `TUTORIAL_BATTLES` is compile-disabled. `RIVAL_BATTLE_TUTORIAL` is an end-battle/helper value, not a battle-type bit. The trainer table binds ID `326` to level-5 Squirtle, a one-mon non-double party and legacy smart flags. Legacy `AI_SCRIPT_FIRST_BATTLE` is selected only if `BATTLE_TYPE_OAK_TUTORIAL` is present; it is not an independent support exclusion.

The ordinary `BattleSetup_StartTrainerBattle` arm assigns `BATTLE_TYPE_TRAINER = 0x8`. Double/two-opponent, partner, Frontier, mock, special mode, and Dynamax bits require their respective flags or modes. `BATTLE_TYPE_OAK_TUTORIAL = 0x10` is set only by the disabled `TUTORIAL_BATTLES` block or `FLAG_ACTIVATE_TUTORIAL = 0x90A`; no current tracked CFRU C or overworld script sets that flag. A fresh New Game clears event flags in the base source. For the exact non-randomized ordinary Oak encounter, the source-expected flags are `0x00000008` and the exclusion-bit intersection is zero. `IsRaidBattle` rejects trainer battles; `IsInverseBattle` is false without its flag/Circus mode; Oak ID `326` is not one of `IsFrontierTrainerId`'s special IDs. These remain source expectations, not private runtime measurements.

Both fair support predicates require `TRAINER`, the matching resolved profile, no Raid/Inverse/Frontier trainer ID, and no bits in the same 26-entry mask: `DOUBLE`, `LINK`, `OAK_TUTORIAL`, `MULTI`, `SAFARI`, `ROAMER`, `EREADER_TRAINER`, `SCRIPTED_WILD_1`, `SCRIPTED_WILD_2`, `LEGENDARY_FRLG`, `TRAINER_TOWER`, `TWO_OPPONENTS`, `INGAME_PARTNER`, `POKE_DUDE`, `OLD_MAN`, `FRONTIER` (Tower/Sands/Circus), `SHADOW_WARRIOR`, `DYNAMAX`, `KYOGRE_GROUDON`, `REGI`, `GHOST`, `RING_CHALLENGE`, `MOCK_BATTLE`, `BENJAMIN_BUTTERFREE`, `CAMOMONS`, `MEGA_BRAWL`. The source gate checks the full mask in both predicates.

## Hook and insertion closure

| Production hook | Site | Register | Owner |
| --- | ---: | ---: | --- |
| `OpponentHandleChooseMove` | `0x080385B0` | `r0` | outer opponent controller |
| `BattleSetup_StartTrainerBattle` | `0x08080464` | `r0` | trainer flags |
| `ExpandedVarsHook` | `0x0806E454` | `r1` | expanded variable pointer |
| `BufferStringBattle` | `0x080D7274` | `r1` | public send-out reveal |

The source gate invokes the actual `scripts/insert.py` hook parser, checks the active `hooks` entries once each, checks production definitions, and executes `Hook` against an in-memory stream to verify its Thumb `LDR/BX` sequence and odd target pointer. The inserter reads `build/linked.o` via `nm`/`objdump`, subtracts its `.text` base, adds insertion offset `0x01000000`, and writes a `0x08000001`-based Thumb pointer at each declared site. Missing any of these four symbols is now fatal to insertion rather than silently skipped. `python3 scripts/tests/audit_runtime_dispatch_closure.py --linked-object build/linked.o` is the post-build symbol-map gate and reads no ROM. It was **not run** here because the approved ARM toolchain and linked object are unavailable; actual private insertion execution is still unproven.

## Outer dispatch host witness

The test-only capture runs as the first action in `OpponentHandleChooseMove`, before the diagnostic marker or normal policy route. It records raw/profile, trainer ID, all battle/exclusion bits, Raid/Inverse/Frontier conditions, both support predicates, active/attacker/target banks, both public displayed species, player Defense stage, own four slots, selected adapter, policy rc, selected slot/move, and emitted slot/move. This capture is behind `CFRU_AI_TEST_TRACE` and absent from release preprocessing.

| Witness | Raw/profile | Flags/support S/I | Public player/opponent | Defense | Adapter, rc | Selected/emitted |
| --- | --- | --- | --- | ---: | --- | --- |
| Revealed Standard | `7/6` | `0x8`, `1/0` | `4/7` | `6` | Standard, `0` | `2/55` Water Gun |
| Omitted reveal Standard | `7/6` | `0x8`, `1/0` | `0/0` | `6` | Standard, `0` | `0/33` Tackle |
| Capped Standard | `7/6` | `0x8`, `1/0` | `4/7` | `0` | Standard, `0` | `0/33` Tackle |
| Revealed Ironmon | `8/7` | `0x8`, `0/1` | `4/7` | `6` | Ironmon, `0` | `2/55` Water Gun |
| Omitted reveal Ironmon | `8/7` | `0x8`, `0/1` | `0/0` | `6` | Ironmon, `0` | `0/33` Tackle |
| Capped Ironmon | `8/7` | `0x8`, `0/1` | `4/7` | `0` | Ironmon, `0` | `0/33` Tackle |

Every row has trainer ID `326`, banks `1/1/0`, moves `33/39/55/0`, zero exclusion bits, and selected/emitted slot and move parity. The capped state changes relative damage, so Tackle may become best; the required invariant is that Tail Whip is excluded. The production public send-out helper is exercised for the positive/capped rows. The omitted-reveal rows are diagnostic invalid-opening states.

## Private diagnostic marker

One line in `src/config.h` enables `TRAINER_AI_RUNTIME_DISPATCH_TRACE` by removing the leading `//`. It is disabled in the submitted source. Only trainer ID `326`, opponent Squirtle with exactly `Tackle / Tail Whip / Water Gun / None`, a Trainer Single with no Double/Link/Multi/Two-Opponents bit, and first three opponent decisions are eligible. The marker runs before normal AI. It checks PP and all `CheckMoveLimitations` restrictions and emits only the chosen legal own slot; if a marker cannot be legally used, normal dispatch proceeds. No policy RNG is consumed. Normal preprocessing contains no marker function.

| Opponent decision | Water Gun | Tackle | Tail Whip |
| --- | --- | --- | --- |
| 1, support route | Ironmon support true | Standard support true | both support false |
| 2, resolved profile | Ironmon Smart | Standard | any other profile |
| 3, player public identity | expected Charmander shown | `SPECIES_NONE` | any other/invalid identity |

The complete three-turn signatures for a stable profile, support state, and public identity are below. In each cell the third move is respectively **Water Gun / Tackle / Tail Whip** for expected Charmander / unknown / unexpected identity. The compiled diagnostic host exercised all 18 profile × exclusion × identity states and asserted unchanged battle and both policy RNG states on every marker decision; Normal's two exclusion states intentionally have the same signature.

| Stable route | Expected identity | Unknown identity | Unexpected identity |
| --- | --- | --- | --- |
| Ironmon supported | Water Gun / Water Gun / Water Gun | Water Gun / Water Gun / Tackle | Water Gun / Water Gun / Tail Whip |
| Ironmon excluded | Tail Whip / Water Gun / Water Gun | Tail Whip / Water Gun / Tackle | Tail Whip / Water Gun / Tail Whip |
| Standard supported | Tackle / Tackle / Water Gun | Tackle / Tackle / Tackle | Tackle / Tackle / Tail Whip |
| Standard excluded | Tail Whip / Tackle / Water Gun | Tail Whip / Tackle / Tackle | Tail Whip / Tackle / Tail Whip |
| Other profile | Tail Whip / Tail Whip / Water Gun | Tail Whip / Tail Whip / Tackle | Tail Whip / Tail Whip / Tail Whip |

`Water Gun / Water Gun / Water Gun` proves the outer hook ran, Ironmon support was true, Ironmon Smart resolved, and public Charmander was known. `Tail Whip / Water Gun / Water Gun` means the hook ran, Ironmon Smart and public Charmander were present, but support was rejected; inspect exclusion flags. `Tail Whip / Tail Whip / Water Gun` means fair support false and a non-Standard/non-Ironmon profile resolved; inspect raw storage. A stable three-move sequence outside the table, with all three legal marker moves and three completed decisions, is strong evidence that this outer hook is not the executing move route. If profile, flags, or public identity changes between turns, apply each row's per-turn mapping directly; a KO, move limitation, or missing turn invalidates the three-move signature.

## Gates and remaining boundary

All seven requested CFRU commands passed after setting `CFRU_WORKSPACE_ROOT` to the active read-only Workspace path for the two existing host-parity scripts. That environment override is needed only because this isolated CFRU worktree is not physically nested under the Workspace; the scripts retain their original default. Standard twins `4096/0`, Ironmon twins `1024/0`, Badge twins `16/0`, Badge oracle `663000`, damage oracle `98304`, Ironmon parity `63/63`, mandatory tags `58/58`, accepted v1/v2/v3 digests, `991` move census, differential `10/10`, Settings raw compatibility, Replacement Safety, Legacy Smart isolation, policy RNG isolation, save delta `0`, and accepted host layout checks all passed. Runtime quality counters remain zero; the only fallback is `NO_PRODUCTIVE_ACTION` in the all-futile case. The separate damage override audit covers 131 named moves. The new profile storage, 26-flag, hook-source, release/diagnostic preprocessing, capped-Tail-Whip, and 18-state marker gates passed.

`ARM_RECHECK_UNAVAILABLE_ENVIRONMENT` and `FULL_SOURCE_BUILD_NOT_RUN_TOOLCHAIN_UNAVAILABLE`: `arm-none-eabi-as`, `arm-none-eabi-gcc`, `arm-none-eabi-ld`, `arm-none-eabi-objcopy`, `arm-none-eabi-nm`, `arm-none-eabi-objdump`, `wav2agb`, and `mid2agb` are absent here. No tool was installed; no full source build or ARM object check was run. The private user's reported completed build remains revision-bound to the old CFRU pin and cannot certify this candidate.

The Workspace `check_git_safety.py` was run before edits. On Workspace `main` it correctly refused writes; when run from this CFRU branch it reported CFRU's pre-existing tracked `deps/*.exe` and `deps/*.dll` paths under the Workspace-specific forbidden-extension rule. None was read, changed, staged, or committed. `git diff --check` and the CFRU changed-path/status review passed; the Workspace worktree and Gitlink remain clean.

The remaining discriminant is a fresh private diagnostic run at this PR head, reporting only the first three move names, the menu-selected profile, and whether all three turns completed with the listed moves available. CONTROL, not this branch, determines the next runtime acceptance step. `#529` and `#498` remain blocked; `ROM_PROFILE_READY` is unclaimed.
