# R1 Oak capped Tail Whip probe — Workspace #532 extension

**Later root-cause finding:** The approved private ARM link at head
`d9c226fde353741dd38b7239fa81eae7504ee666` put this probe's mutable
state in 0x09 ROM. Its capped Tail Whip result cannot classify the policy.
The repair and ARM gate are recorded in
[trainer-ai-runtime-writable-state-2026-09-26.md](trainer-ai-runtime-writable-state-2026-09-26.md).

**2026-09-26 correction:** The first capped private result was Tail Whip, but
the interpretation below was confounded by action-phase pending/last-action
staging before this probe's move-phase interception. The corrected full-lifecycle
contract and evidence are in
[trainer-ai-runtime-full-lifecycle-2026-09-26.md](trainer-ai-runtime-full-lifecycle-2026-09-26.md).
The original three-turn marker and its evidence remain unchanged.

## Runtime fact and disposition

The user supplied a private result for the original three-turn marker on PR #56 head `936fd1dce2c3ad830ca8b3f47fd164aacd5bf7d6`: menu profile **Ironmon Smart**, then **Water Gun / Water Gun / Water Gun**. Under the unchanged marker contract, this confirms `IronmonAI_IsSupportedBattle() == TRUE`, `GetTrainerAIProfile() == TRAINER_AI_PROFILE_IRONMON_SMART`, and public player species Charmander for those decisions. Three forced Water Guns KO Charmander, so that experiment cannot reach a fourth decision. This supersedes the earlier evidence file's statement that these private values were unobserved; the earlier file and its marker remain unchanged.

**Disposition: `RUNTIME_DIAGNOSTIC_REQUIRED`.** The new experiment isolates the first normal policy decision after the player Defense stage actually reaches `STAT_STAGE_MIN`. No source root cause or release runtime fix has been proven. `ROM_PROFILE_READY` is unclaimed. PR #56 stays open and unmerged; `UPSTREAM_CONTRIBUTION = DEFERRED`.

## Second diagnostic switch

`TRAINER_AI_RUNTIME_CAPPED_TAILWHIP_PROBE` is commented out in `src/config.h`. Enable this switch alone for a private diagnostic build; the original `TRAINER_AI_RUNTIME_DISPATCH_TRACE` remains disabled and unchanged. The two diagnostic switches are mutually exclusive at compile time. Both probe functions are absent from ordinary release preprocessing.

The probe is reached only from the outer `OpponentHandleChooseMove` hook. It requires trainer ID `TRAINER_RIVAL_OAKS_LAB_SQUIRTLE` (`326`), an opponent-bank Squirtle whose four live slots are exactly `Tackle / Tail Whip / Water Gun / None`, non-null expanded battle state, and **exactly** `BATTLE_TYPE_TRAINER` (`0x8`). This retains the original marker's Oak/trainer/opponent/moves checks and narrows its mode check to the ordinary single battle: Oak Tutorial, Double, Link, Multi, Two Opponents, Mock, and every other extra battle-type bit cannot trigger the setup. It never acts in another trainer encounter or moveset.

On each eligible opponent decision, the probe reads the **actual target battle Defense stage** at `gBattleMons[FOE(bank)].statStages[STAT_STAGE_DEF - 1]`. If it is above `STAT_STAGE_MIN`, and Tail Whip has PP and passes `CheckMoveLimitations`, it normalizes the controller move view from Squirtle's own live moves, writes the authoritative chosen slot/move/target, and emits legal slot 1 Tail Whip through the normal controller buffer. It does not call either fair policy or consume battle or policy RNG. A miss or unchanged stage simply leads to another setup attempt at the next decision. There is no turn-count threshold. If Tail Whip has no PP or is restricted, the probe returns to normal dispatch without emitting a marker move.

At `STAT_STAGE_MIN`, the function returns **before** move-limit checks, normalization, buffer writes, policy calls, or controller emission. That same opponent decision proceeds into `OpponentHandleSupportedAIMoveChoice` and its normal Ironmon/Standard profile route. The first such decision is the witness. Neither diagnostic changes policy weights, epsilon, damage, status utility, Tail Whip scoring, or Legacy Smart behavior.

## Historical reading rule — superseded by the full-lifecycle probe

The setup phase should show Tail Whip only while the player's displayed Defense stage can still fall. Do not infer the cap from a fixed number of turns; wait until the game shows further Defense reduction is impossible. Then record **the first opponent move after the stage is already at minimum at decision entry**:

| First normal decision at minimum Defense | Interpretation |
| --- | --- |
| Tail Whip | **No longer a valid policy conclusion.** Stale action-phase pending state or bounded emergency slot 1 can also emit Tail Whip. |
| Tackle or Water Gun | The old probe did not control action-phase staging, so this observation alone would also be incomplete. |

The user's original **Water Gun / Water Gun / Water Gun** result belongs to the first marker and does not predict the second probe's capped decision. A new diagnostic build and runtime observation are still required; the host witness does not substitute for them.

## Source and host gates

`scripts/tests/run_ai_controller_fallback_tests.py` builds and runs the ordinary controller host, the unchanged three-turn marker's 18-state matrix, and a separate capped-probe host. For both Standard raw `7` and Ironmon Smart raw `8`, the capped host uses source-derived level-5 Oak Squirtle moves and level-5 Charmander, the production public reveal lifecycle, and exact ordinary Trainer flags. Its stages are `6, 5, 5, 1, 0`: the repeated stage `5` simulates a missed or ineffective setup turn, and the fourth forced Tail Whip proves there is no three-turn limit. Every forced emission is Squirtle's legal own slot 1, agrees with the controller buffer and chosen-move state, and leaves battle RNG plus both fair policy RNG states unchanged. At stage `0`, the adapter is normal Standard (`1`) or Ironmon (`2`), policy rc is `0`, and both select/emit Tackle, never Tail Whip. Already-capped first decisions behave the same. Exhausted PP, a move restriction, wrong trainer, wrong move slot, Oak Tutorial, and Mock Battle do not invoke the probe.

`scripts/tests/audit_runtime_dispatch_closure.py` checks the stage-before-legality fallthrough, no fixed turn count, own-move/controller emission, no policy/RNG calls in the probe, ordinary Trainer-only gate, and both compile-time switches. Preprocessed release source contains neither diagnostic path; each single-switch diagnostic source contains only its own path. The existing hook parser, Thumb encoding, and source symbol checks still pass. Linked insertion-symbol closure was not run because no approved ARM linked object/toolchain is available here; no tool was installed and no ROM or private artifact was read or requested.

All seven required #532 regression commands passed again with the read-only Workspace path supplied through `CFRU_WORKSPACE_ROOT` for the existing cross-repository host scripts. The profile-storage and runtime-dispatch closure audits also passed. Preserved results include Standard twins `4096/0`, Ironmon twins `1024/0`, Badge twins `16/0`, Badge oracle `663000/663000`, damage oracle `98304`, Ironmon parity `63/63`, tags `58/58`, accepted v1/v2/v3 digests, `991` move census, differential `10/10`, settings/raw compatibility, replacement safety, save delta `0`, Legacy Smart isolation, and policy RNG isolation. `git diff --check` passed. The original three-turn marker and its evidence file were not modified. Workspace Gitlink and other components remain unchanged.
