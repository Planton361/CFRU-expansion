# Trainer AI Runtime Slot-0 Fallback — Policy/Controller Handoff Evidence

**Workspace contract:** Planton361/firered-gen9-randomizer-workspace #529\
**Component:** Planton361/CFRU-expansion\
**Branch:** fix/r1-ai-runtime-slot0-fallback\
**Base / start SHA:** fa83aae29818434cca6813be28f509b04c5dd68b\
**Target:** compat/firered-gen9-randomizer
**Final branch SHA:** the evidence-bearing tip is recorded verbatim in the #529 handoff and as the CFRU PR head after push. A commit cannot contain its own object ID.

## Disposition

**RUNTIME_SOURCE_MISMATCH_BLOCKER**

The controller/policy handoff defect described below was reproduced through the production source path and repaired. On source-owned early-trainer states, the accepted policy returns Water Gun for Rival Squirtle and Rock Tomb for Brock Onix, and both moves are emitted at their matching controller positions. Thus the accepted source witnesses do not reproduce the latest #498 runtime failure (Rival Tackle, Brock Tackle, Sandshrew Scratch, Weedle Poison Sting). The exact runtime state that produced that report was not available for an allowed source-host reproduction. This change does not claim that the runtime failure is resolved or accepted.

## Revision and boundary

- Work began at component commit fa83aae29818434cca6813be28f509b04c5dd68b, the merged CFRU pin verified by Workspace #527 from PR #54.
- The branch is based directly on that SHA. The integration base was not changed.
- Only CFRU production source, CFRU tests, and this CFRU evidence document are changed. No Workspace file or Gitlink is committed by this task; no DPE, UPR-FVX, Ironmon Tracker, or NatDexExtension content is touched.
- Exact changed paths:
  - include/new/ai_ironmon_policy.h
  - include/new/ai_standard.h
  - include/new/ai_standard_policy.h
  - include/new/battle_controller_opponent.h
  - src/Battle_AI/ai_ironmon.c
  - src/Battle_AI/ai_ironmon_policy.c
  - src/Battle_AI/ai_standard.c
  - src/Battle_AI/ai_standard_policy.c
  - src/battle_controller_opponent.c
  - scripts/tests/audit_standard_ai.py
  - scripts/tests/standard_ai_adapter_host.c
  - scripts/tests/audit_ai_controller_fallback.py
  - scripts/tests/controller_fallback_host.c
  - scripts/tests/run_ai_controller_fallback_tests.py
  - docs/testing/trainer-ai-runtime-slot0-fallback-2026-09-25.md
- The user-provided merge identity for PR #54 is accepted head f0cf999a1f7277e02870044b605a3f31045a0141 and merge fa83aae29818434cca6813be28f509b04c5dd68b. The merge is one commit above its parents and its tree is identical to the accepted head. The component start SHA is exactly the merge SHA.
- Final branch SHA, PR URL, and the exact changed-path list are included in the Workspace #529 handoff after the evidence commit is pushed.

## Root-cause hypothesis and repair

The suspected source mechanism was confirmed as a latent defect. In both adapters, the old path labelled FALLBACK_TO_ENGINE did not invoke the legacy engine: after a nonzero policy result or selected-ID lookup miss, it returned the first occupied own-move slot. On the reported early source layouts this is slot 0: Tackle for Rival/Brock, Scratch for the custom Sandshrew set, and Poison Sting for Weedle. ChooseMoveOrAction also returned literal 0 for invalid pending/non-move state. The controller then emitted the returned slot.

This proves that policy/adapter failures could be silently coerced into slot 0. It does not prove that this path caused the latest #498 runtime observations: normal policy return code 0 selects Water Gun/Rock Tomb in the reproduced source states, and the exact runtime profile, state, and controller buffer behind #498 were unavailable.

The repair exposes stable policy status values and preserves them through the adapters. Adapter failure, no admitted action, selected-ID lookup failure, invalid pending state, and non-move state now return a sentinel to the supported controller handoff. The controller uses a bounded own-move emergency choice on that error path, choosing the first legal nonzero own slot when one exists. The emergency choice uses no policy or battle RNG and reads no hidden opponent data. Rival and Brock error witnesses therefore emit slot 1 rather than slot 0. When a move slot is selected, the controller move buffer is normalized from gBattleMons before emission and the emitted move ID must equal gBattleMons[bank].moves[emittedPosition].

No policy balance or ranking rule changed. Standard epsilon remains 8; Ironmon epsilon remains 4. Status and Accuracy rules and accepted v1/v2/v3 identities are unchanged.

## Failure-mode separation

| Case | Exact test evidence | Result |
|---|---|---|
| Correct policy selection | Standard and Ironmon source witnesses return rc 0; selected ID resolves to the source candidate and emitted slot | Water Gun/Rock Tomb source routes preserve the selected slot and move ID |
| Policy validation/error | Standard rc -1 and Ironmon rc -1 injected separately | Bounded own-move fallback; Rival/Brock do not emit slot 0 |
| No admitted action | Standard rc -2 injected | Distinct status retained; Brock emits its first legal nonzero own slot |
| Invalid candidate code | StandardPolicyChoose rc -3 asserted by the exact-code host test | Not folded into the generic nonzero-success path |
| Selected-ID lookup failure | rc 0 with selected ID 254 injected | Recorded as lookup failure; Rival emits slot 1 |
| Pending-state failure | Invalid pending position 255 injected | Recorded as pending-state failure; Sandshrew emits slot 1 |
| Unsupported battle / Legacy routing | Normal trainer flags pass the support gates; profile-dispatch audit retains Legacy Smart routing | Legacy graph is unchanged and remains isolated |
| Controller buffer mismatch | Stale selected-slot and permuted-slot buffers injected | Buffer restored from gBattleMons before emission; parity passes |
| Literal slot-0 coercion | Source audit verifies sentinel returns and absence of adapter slot-0 coercion | No Rival/Brock injected adapter failure emits slot 0 |

IronmonPolicyChoose returns 0, -1, or -2 for the tested success, validation-error, and no-admitted-action cases. Its bounded response builder reports -3 for an invalid/duplicate response candidate; the test names this separately rather than attributing it to IronmonPolicyChoose.

## Source-owned trainer states and production handoff

The host suite calls the actual supported outer OpponentHandleChooseMove route, then BattleAI_SetupAIData, the dispatched Standard/Ironmon ChooseMoveOrAction adapter, and EmitMoveChosen. Trainer party, profile mapping, early move order, controller flow, and level-up defaults are source-derived. The witness stat inputs use trainer-class IVs from source tables (Rival 25, Leader 31, Camper 5, Bug Catcher 1), zero EVs, neutral nature inputs, and the existing source stat formula. This is a deterministic source witness, not a claim that it recreates the user’s randomized runtime stats.

Every witness uses ordinary trainer Singles flags 00000008 (BATTLE_TYPE_TRAINER); Raid, Inverse, and Frontier flags are false. The actual standard and Ironmon support predicates return true for their respective profiles. Their guards also reject the excluded battle-type set and frontier trainer IDs, so these early trainer IDs do not fall through due to those gates.

The exact source move arrays and accepted policy-to-controller results are:

| Source trainer | gBattleMons slots 0..3 = controller slots 0..3 | Profile dispatch | Accepted selection and emission |
|---|---|---|---|
| Cerulean Rival Squirtle, level 18 | Tackle, Tail Whip, Withdraw, Water Gun | raw 7 → Standard enum 6; Standard supported=1, Ironmon=0 | policy rc=0, selected ID/slot 3; pending consumed; returned 3, emitted 3, final move ID 55 (Water Gun) |
| Brock Onix, level 14 | Tackle, Bind, Rock Tomb, None | raw 7 → Standard enum 6; Standard supported=1, Ironmon=0 | policy rc=0, selected ID/slot 2; pending consumed; returned 2, emitted 2, final move ID 317 (Rock Tomb) |
| Camper Liam Sandshrew, level 11 | Scratch, Defense Curl, Sand Attack, None | raw 7 → Standard enum 6; Standard supported=1, Ironmon=0 | rc=0, selected/returned/emitted slot 0, Scratch ID 10; Scratch and Sand Attack are both Standard near-best candidates |
| Bug Catcher Rick Weedle, level 6 | Poison Sting, String Shot, None, None | raw 7 → Standard enum 6; Standard supported=1, Ironmon=0 | rc=0, selected/returned/emitted slot 0, Poison Sting ID 40; String Shot is not admitted/productive |
| Same four source states under Ironmon Smart | Same source arrays as above | raw 8 → Ironmon Smart enum 7; Standard=0, Ironmon supported=1 | rc=0 for all; Rival slot 3/Water Gun, Brock slot 2/Rock Tomb, Sandshrew slot 0/Scratch, Weedle slot 0/Poison Sting |

The Weedle default order is derived from its level-up learnset: Poison Sting then String Shot, both learned at level 1. Trainer party data has no explicit Weedle move array; the source initial-moveset stack preserves learnset order.

The per-candidate trace below gives candidate ID/slot, legality, expected damage, utility, floor-reason mask, admission-reason mask, and near-best. For Ironmon, the final field also gives admitted status. Candidate IDs are own move slots. The normal-route traces report policy rc=0, selected ID, consumed pending state, returned position, emitted position, and final move ID as shown above.

| Profile / trainer | Candidate traces: ID/slot, legal, damage, utility, floor, admission, near-best [Ironmon: admitted] |
|---|---|
| Standard / Rival | 0 Tackle: 1,7,13,0,1,0; 1 Tail Whip: 1,0,6,0,1,0; 2 Withdraw: 1,0,0,128,128,0; 3 Water Gun: 1,22,40,0,1,1 |
| Standard / Brock | 0 Tackle: 1,5,9,0,1,0; 1 Bind: 1,0,0,0,1,0; 2 Rock Tomb: 1,20,37,0,1,1; 3 None: 0,0,0,1,1,0 |
| Standard / Sandshrew | 0 Scratch: 1,4,7,0,1,1; 1 Defense Curl: 1,0,0,128,128,0; 2 Sand Attack: 1,0,13,0,1,1; 3 None: 0,0,0,1,1,0 |
| Standard / Weedle | 0 Poison Sting: 1,2,4,0,1,1; 1 String Shot: 1,0,0,128,128,0; 2 None: 0,0,0,1,1,0; 3 None: 0,0,0,1,1,0 |
| Ironmon Smart / Rival | 0 Tackle: 1,7,16,0,0,0 [1]; 1 Tail Whip: 1,0,0,0,0,0 [1]; 2 Withdraw: 1,0,0,128,128,0 [0]; 3 Water Gun: 1,22,50,0,0,1 [1] |
| Ironmon Smart / Brock | 0 Tackle: 1,5,11,0,0,0 [1]; 1 Bind: 1,0,0,0,0,0 [1]; 2 Rock Tomb: 1,20,46,0,0,1 [1]; 3 None: 0,0,0,1,1,0 [0] |
| Ironmon Smart / Sandshrew | 0 Scratch: 1,4,8,0,0,1 [1]; 1 Defense Curl: 1,0,0,128,128,0 [0]; 2 Sand Attack: 1,0,0,0,0,0 [1]; 3 None: 0,0,0,1,1,0 [0] |
| Ironmon Smart / Weedle | 0 Poison Sting: 1,2,4,0,0,1 [1]; 1 String Shot: 1,0,0,128,128,0 [0]; 2 None: 0,0,0,1,1,0 [0]; 3 None: 0,0,0,1,1,0 [0] |

For Standard rows, tuple order is legal, expected damage, utility, floor mask, admission mask, near-best. For Ironmon, the same tuple is followed by admitted in brackets. In the normal accepted witnesses, pending state was consumed before emission. Separate injected invalid-pending witnesses report the pending-state failure and bounded emergency result.

## Regression gates

All listed commands passed on this component revision:

- python3 scripts/tests/run_standard_ai_tests.py
- python3 scripts/tests/run_ironmon_ai_tests.py
- python3 scripts/tests/run_settings_defaults_tests.py
- python3 scripts/tests/run_replacement_safety_tests.py
- python3 scripts/tests/run_ai_runtime_quality_tests.py
- python3 scripts/tests/run_ai_controller_fallback_tests.py
- python3 scripts/tests/audit_ai_damage_overrides.py

Key retained identities and counters:

- Standard production twins: 4096 pairs / 0 mismatches.
- Ironmon production twins: 1024 pairs / 0 mismatches.
- Badge twins: 16 pairs / 0 mismatches; Badge oracle: 663000 / 663000.
- Damage envelope oracle: 98304 cases.
- Ironmon parity: 63 / 63; mandatory coverage tags: 58 / 58.
- Accepted digests unchanged:
  - uniform_legal: 71fc84c8fd3e219c4e364ecd506127303ac8524a73d47a39999be384efbc95a7
  - standard: 227ecebc2b937671cc4f2fbab1694abf1b7c186f7e455ed7daf22014b62d0a85
  - ironmon_smart: 0a637d0bc42cb2e37701bbfa33677ae95c878b1f9a67ec55a60e15a4fbdb85d7
- 991-move census unchanged: 991 total = 721 damaging + 270 status; D0=49, D1=117, D2=110, D3=445; full=92, direct-only=184, unsupported=445.
- Production-vs-Workspace-host differential: 10/10 states passed, 0 mismatches.
- Runtime quality counters: illegal/no-effect choice with productive alternative=0; missed robust KO=0; third harmful same-family repeat=0; below-epsilon selection=0; unsupported selection below clearly superior supported alternative=0. The sole policy fallback remains NO_PRODUCTIVE_ACTION in the all-futile case.
- Accuracy first/marginal/repeat/lifecycle checks passed. Caterpie String Shot marginality and subsequent attack passed. Weedle Poison Sting remained the direct-damage choice.
- Settings/raw compatibility and unknown raw-value preservation passed. Replacement Safety passed. Legacy Smart isolation passed.
- Existing policy-RNG isolation suites passed. The bounded emergency helper does not call a policy or battle RNG.
- Damage override audit: 131 named overrides audited.

The runtime-quality census reported no behavior or digest changes. The new controller suite additionally verifies the exact policy return codes, profile dispatch, stale/permuted controller buffers, policy error/no-action/lookup/pending failure classes, source party bindings, and normal supported outer-handler emission.

## ABI, layout, build, and environment

- Save delta remains 0. No save fields or production AI state layouts were added or reordered.
- Existing layout witnesses pass: host harness BattlePokemon=0x58, BattleMove=0xC, BattleStruct=0x208 (host-only); target BattleStruct ABI witness=0x200; NewBattleStruct=0xC08 with aligned Standard delta 4 and Ironmon aligned delta 56. These remain the suite's existing host/static layout witnesses, not a substitute for the unavailable fresh ARM object pass.
- ARM syntax/object/runtime-helper and ABI object recheck: ARM_RECHECK_UNAVAILABLE_ENVIRONMENT. The approved devkitARM tools arm-none-eabi-gcc, arm-none-eabi-as, arm-none-eabi-ld, arm-none-eabi-nm, arm-none-eabi-objcopy, and arm-none-eabi-size were not available. No tools were installed or downloaded.
- Full source build: FULL_SOURCE_BUILD_NOT_RUN_TOOLCHAIN_UNAVAILABLE. python3 scripts/build.py was not run because wav2agb and mid2agb were unavailable. scripts/make.py was not used.
- git diff --check passed before commit. Final clean component status and the final commit SHA are recorded in the #529 handoff.

## Protected boundary and limitations

The work stayed inside the CFRU repository and the bounded feature branch. It read no ROM, save, emulator state, generated build input, screenshot, compiler/tool binary, .env, token, key, or secret. It changed no Workspace Gitlink or other component repository. No Legacy Smart redesign, Expert/Omniscient mode, new Gen-9 mechanic, M-011/Hospitality, R2, BizHawk, Tracker, merge, upstream PR, or history rewrite was performed. UPSTREAM_CONTRIBUTION remains DEFERRED.

The production-source host witnesses establish the policy/controller contract for deterministic source-derived early trainer states. They do not identify which adapter, profile, runtime data, or controller buffer was active in the reported #498 run. No new runtime correction is claimed; the targeted real-runtime witnesses remain necessary before #498 can resume its broader R1 run, and ROM_PROFILE_READY remains unclaimed.
