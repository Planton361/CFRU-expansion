# R1 Oak fair-AI full-lifecycle probe — Workspace #532

**Later root-cause finding:** The approved private ARM link at PR head
`d9c226fde353741dd38b7239fa81eae7504ee666` placed the Ironmon policy's
mutable observation/result in 0x09 ROM and this probe's mutable state in ROM
`.text`. The pre-fix capped Tail Whip is therefore invalid as a policy
classifier even with the corrected lifecycle. See
[trainer-ai-runtime-writable-state-2026-09-26.md](trainer-ai-runtime-writable-state-2026-09-26.md)
for the same-branch source repair and its remaining ARM/private gate. The
original three-turn marker and its evidence remain unchanged.

## Revision-bound finding

The private run of `TRAINER_AI_RUNTIME_CAPPED_TAILWHIP_PROBE` at CFRU PR #56 head `8e6ce4c3bfd93a858f06a1eaf74c6386ae399920` used Ironmon Smart and forced Tail Whip until target Defense was at `STAT_STAGE_MIN`. The first visible move with Defense already at minimum was **Tail Whip**. [CONTROL review 5323296547](https://github.com/Planton361/CFRU-expansion/pull/56#pullrequestreview-5323296547) and [Workspace #532 comment 5840541870](https://github.com/Planton361/firered-gen9-randomizer-workspace/issues/532#issuecomment-5840541870) classify this as **diagnostic-confounded**. It does not prove that the capped Ironmon policy selected Tail Whip.

The previous probe intercepted only `OpponentHandleChooseMove`. The earlier `AI_TrySwitchOrUseItem` action phase can call `IronmonAI_Choose(TRUE)` or `StandardAI_Choose(TRUE)`, set `standardPendingValid` / `standardPendingKind` / `standardPendingAction`, and stage `standardLast*`. Forcing a move without consuming that pending choice can carry state into the first capped turn. Independently, #529's bounded emergency route selects Oak Squirtle's first legal nonzero slot, slot 1 Tail Whip. The private Tail Whip could therefore reflect stale pending state, a current valid slot-1 result, or emergency fallback. No release-path root cause is established.

**Disposition: `RUNTIME_DIAGNOSTIC_REQUIRED`.** PR #56 remains open and unmerged. The original three-turn marker and its evidence were not changed; the earlier capped-probe evidence is now marked superseded for interpretation. No policy scoring, epsilon, damage/status utility, Tail Whip scoring, Legacy Smart behavior, save layout, or product Oak special-case changed. `UPSTREAM_CONTRIBUTION = DEFERRED`.

## Corrected action and move path

The second switch remains commented out in `src/config.h`, mutually exclusive with `TRAINER_AI_RUNTIME_DISPATCH_TRACE`, and absent from ordinary release preprocessing. Its exact battle gate requires Oak Rival Squirtle trainer ID `326`, opponent-bank Squirtle, live moves `Tackle / Tail Whip / Water Gun / None`, non-null expanded battle state, and exactly ordinary Trainer Single flag `0x8`. The source hook for the real earlier action phase is `AI_TrySwitchOrUseItem` at `0x08039C84`; its symbol is now a required insertion symbol alongside the four original #532 hooks.

While actual target Defense is above `STAT_STAGE_MIN`, Tail Whip has PP, and `CheckMoveLimitations` permits it, the action-phase hook emits `ACTION_USE_MOVE` **before** either fair action selector runs. It leaves pending and staged last-action fields untouched and does not consume battle or policy RNG. The corresponding move phase consumes that action-phase probe authorization, normalizes the controller buffer from Squirtle's live moves, and emits legal own Tail Whip. It does not use a turn count; a miss or unchanged Defense repeats setup. If the setup move is restricted or lacks PP, both phases use the normal route. No post-policy clearing is used.

On a decision beginning with Defense at minimum, the probe does not intercept the action phase. It records whether `standardPendingValid` and `standardLastValid` were clear at entry, then the ordinary Standard/Ironmon action selector stages its current-state result. The move phase consumes the pending choice or runs the ordinary adapter. Only **after** the raw slot and #529 resolver outcome are known does a diagnostic-only marker replace the emitted move for the first capped decision. All markers require legal PP and `CheckMoveLimitations` success and use Squirtle's own slots; if a marker is illegal, the diagnostic code leaves the resolved move unchanged and that observation has no marker interpretation.

| First capped marker | Required observed category |
| --- | --- |
| **Water Gun** (slot 2) | Clean action entry, valid fresh raw slot 0 or 2, matching current move-kind pending/last state, no controller-buffer mismatch and no bounded fallback. |
| **Tail Whip** (slot 1) | Clean action entry, valid fresh raw slot 1 from current policy/pending, no bounded fallback. This is the current slot-1 selection discriminant. |
| **Tackle** (slot 0) | Invalid/stale action entry, non-move last-action state, controller-buffer mismatch, invalid raw or pending/lookup result, or bounded emergency. In Oak's exact moveset the ordinary #529 emergency would emit slot 1 Tail Whip; Tackle separates that failure class from a valid current slot-1 choice. |

The host trace keeps policy rc, selected ID, adapter failure reason (`NONE`, `POLICY_ERROR`, `NO_ADMITTED_ACTION`, `SELECTED_ID_LOOKUP`, `PENDING_STATE`, `NON_MOVE_STATE` remain distinct), pending validity/kind/action, staged last validity, raw pre-resolve slot, controller buffer mismatch, bounded fallback, pre-marker resolved slot, final emitted slot/move, support predicates, Defense stage, and battle/Standard/Ironmon RNG. A Tackle marker reports the failure class; the host fields identify its exact member. No emulator log, ROM, save, or binary artifact is needed from the private run.

## Source-owned lifecycle witnesses

The host now invokes the production `AI_TrySwitchOrUseItem` before the production `OpponentHandleChooseMove` for each relevant Oak decision. Its `CFRU_AI_TEST_TRACE` guard removes only unrelated legacy item/switch engine dependencies from the host translation unit; ordinary release preprocessing retains the complete action function. On the exact revealed level-5 Oak battle with ordinary Trainer flags and **no diagnostic macro**:

| Profile | Defense at action entry | Action selected ID / pending slot | Move raw / resolved / emitted | Fallback |
| --- | ---: | ---: | --- | ---: |
| Standard raw `7` | `6` | `2 / 2` | `2 / 2 / Water Gun` | no |
| Ironmon Smart raw `8` | `6` | `2 / 2` | `2 / 2 / Water Gun` | no |
| Standard raw `7` | `0` | `0 / 0` | `0 / 0 / Tackle` | no |
| Ironmon Smart raw `8` | `0` | `0 / 0` | `0 / 0 / Tackle` | no |

All four action policies return rc `0`, stage a move and `standardLastValid`, then the move phase consumes exactly the pending slot without controller mismatch or bounded fallback. The capped Tail Whip is floor-rejected. The complete ordinary source host does **not** reproduce the private release loop; release AI remains unchanged.

The #529 Oak release witness sets exact moves and Defense minimum, then injects policy error, no-admitted-action, or selected-ID lookup failure for both profiles. Each action/move lifecycle returns a raw sentinel, `StandardAI_ChooseEmergencyMoveSlot(1) == 1`, resolver flag true, and emitted Tail Whip slot 1. This confirms the visible emergency signature without changing the bounded algorithm.

With the corrected diagnostic enabled, the host drives stages `6, 5, 5, 1, 0`. Four setup decisions, including repeated stage `5`, emit Tail Whip with `standardPendingValid == FALSE` and `standardLastValid == FALSE` after both action and move phases. Battle RNG and both policy RNG states remain unchanged. At stage `0`, entry is clean; the normal action phase stages current selected ID `0`, pending move slot `0`, and last-action state. The move phase consumes raw/resolved slot `0` without fallback, then emits Water Gun as the **healthy-current** marker for both profiles. An already capped first decision behaves the same. Separate diagnostic host injections prove valid fresh slot `1` maps to Tail Whip, while policy-error, no-admitted-action, selected-ID lookup, pending-invalid, stale prior-turn slot-1 state, and controller-buffer mismatch map to Tackle; the first four retain distinct adapter failure codes. PP/restriction and wrong trainer/moves/modes do not force setup.

## Gates and remaining boundary

All seven required #532 regression commands passed again with `CFRU_WORKSPACE_ROOT` pointing to the read-only active Workspace for cross-repository host parity. Standard twins `4096/0`, Ironmon twins `1024/0`, Badge twins `16/0`, Badge oracle `663000/663000`, damage oracle `98304`, Ironmon parity `63/63`, tags `58/58`, accepted v1/v2/v3 digests, `991` move census, differential `10/10`, settings/raw compatibility, replacement safety, Legacy Smart isolation, policy RNG isolation, save delta `0`, and host layout/ABI evidence remain passing. The original 18-state marker gate, expanded-var storage audit, full-lifecycle controller/fallback suite, and release/diagnostic preprocessing audit pass. The hook parser, symbol source and Thumb encoding checks now cover the earlier action hook in addition to the original four.

An approved ARM linked object/toolchain is unavailable in this worker; the post-build linked-symbol check remains for the private build, and no tool was installed. No ROM, save, emulator state, build artifact, secret, or other component was read or requested. The Workspace Gitlink is unchanged. The next private discriminant is **one capped opponent decision** on the corrected PR head, reporting only the marked move name. CONTROL decides its interpretation and acceptance; no merge or `ROM_PROFILE_READY` claim follows here.
