# Issue #523: R1 trainer replacement safety evidence

Date: 2026-09-24
CFRU repository: `Planton361/CFRU-expansion`
Branch: `fix/r1-trainer-replacement-safety`
Requested base branch: `compat/firered-gen9-randomizer`
Start/base SHA: `3c2f38140ed07991a04ae63ff1108ff2f25547a6`

## Finding and repair

The Standard and Ironmon controller branches emitted the profile chooser's index immediately and returned. That bypassed the existing CFRU replacement route's ownership, trainer-party range, active-slot, and viable-mon checks. A `PARTY_SIZE` sentinel or an unusable result could therefore reach `EmitChosenMonReturnValue`. The source path matches the runtime-defect hypothesis reported under #498; the exact runtime event was not replayed.

The controller now sends both profile results and preselected profile targets through one opponent-party/range/state validator before emission. Invalid results fall through to CFRU's existing pivot/best-mon selection, with candidate validation and a first-usable-in-range fallback. The non-profile legacy selection statements remain on their prior path. A valid preselected voluntary target retains its index. The profile path has a final guard that completes without emitting a replacement index if no live candidate exists.

The reusable validator rejects a wrong party pointer, invalid or foreign trainer range, `PARTY_SIZE` and out-of-range indices, either active slot, empty species, eggs, and fainted Pokémon.

## Regression evidence

Commands run on the branch:

- `python3 scripts/tests/run_replacement_safety_tests.py` — PASS. Controller routing audit and host regressions cover Standard/Ironmon valid 2-mon replacement, `PARTY_SIZE` and out-of-range fallback, dead/empty/egg/current-slot filtering, opponent party ownership and trainer-range isolation, repeated 2-mon/3-mon replacements, last-faint/no-candidate behavior, and a valid voluntary target.
- `python3 scripts/tests/run_standard_ai_tests.py` — PASS. Existing fairness, adapter parity (4,096 pairs), mechanics envelope (98,304 cases), dispatch and excluded-mode gates pass. Production Standard forced replacement selects the valid second mon; existing Ironmon replacement timing and chooser regressions pass.
- `python3 scripts/tests/run_ironmon_ai_tests.py` — PASS. Existing fairness and source audits pass; 63/63 parity fixtures and all 58 mandatory coverage tags pass. Accepted host digests are unchanged: Standard `227ecebc2b937671cc4f2fbab1694abf1b7c186f7e455ed7daf22014b62d0a85`; Ironmon Smart `0a637d0bc42cb2e37701bbfa33677ae95c878b1f9a67ec55a60e15a4fbdb85d7`.
- `python3 scripts/tests/run_settings_defaults_tests.py` — PASS. Defaults, all existing settings mappings, raw unknown-value preservation, and the Ironmon preset pass.
- Native source syntax check: `cc -std=gnu99 -Wno-unknown-attributes -Iinclude -fsyntax-only src/battle_controller_opponent.c` — PASS with three existing pointer-cast warnings in unchanged lines 672, 742, and 749.
- `git diff --check` — PASS.

## Tackle / Water Gun policy witness

The deterministic production-adapter host fixture in `scripts/tests/standard_ai_adapter_host.c` uses a level-5 Charmander against a level-5 Squirtle with Tackle and Water Gun. Both are legal. Results:

| Move | Expected damage | Damage envelope | Opponent HP fraction lost | Utility | Eligible | Near-best |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| Tackle | 3 | 3–18 | 38 | 14 | yes | no |
| Water Gun | 11 | 10–42 | 140 | 54 | yes | yes |

Water Gun is the sole near-best candidate and is selected. Pool size is 1, selection draws are 0, and policy RNG is unchanged (`1A0B5156 -> 1A0B5156`). This fixture does not supply the incident's exact private runtime levels, stats, or configuration, so it is a source/host witness rather than a reproduction of that runtime observation. The disposition for the reported Tackle choice is RUNTIME_STATE_INSUFFICIENT_FOR_POLICY_VERDICT; preserve the observation for a targeted user rerun. The witness itself selects Water Gun under the accepted policy, so no move-scoring policy change was made.

## ARM, object, ABI, save, and layout boundary

No structure declarations, assembly hooks, ABI definitions, save fields, settings, or submodule Gitlinks were changed. The source diff introduces no persistent state. The Standard host harness reports target ARM `BattleStruct=0x200` and `save delta=0`; the `0x208` value printed alongside it is explicitly the host harness representation. These are source/host layout assertions, not a newly generated target object.

`arm-none-eabi-gcc` is unavailable in this environment. No target ARM compile, object comparison, or ROM build was performed, so target code-generation/object equivalence cannot be independently confirmed here. No ROM, save, emulator state, or build artifact was read or modified, and no runtime was launched.

## Limits

The controller's complete battle script was not run in an emulator or target build, as required by the contract. The host tests exercise the production chooser adapters and the shared production validator; a source audit verifies the controller's gate-before-emission and fallback routing. The final-faint case proves that the guarded profile path emits no invalid replacement index when there is no live candidate; normal battle-end routing remains owned by the engine.
