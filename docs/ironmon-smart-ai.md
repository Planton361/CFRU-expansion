# Ironmon Smart v1 fair tactical source adapter

Issue: Workspace `#517`. This document describes CFRU source behavior only.
It is not ROM/runtime acceptance and does not claim exact NatDex patch parity.

## Architecture and profile

`TRAINER_AI_PROFILE_IRONMON_SMART` is appended after Standard, preserving every
existing numeric profile value. It is routed only for ordinary Trainer Singles
accepted by the same explicit special-mode exclusions as Standard. It never
enters legacy Smart/Hard/Expert scoring, prediction, item, or switching paths.
No menu, setting, default, save mapping, Trainer layout, Pokemon layout,
BattleMove layout, DPE ABI, or randomizer-owned table is changed.

The decision path is:

```text
CFRU battle/public history
  -> Standard common fair candidate projection
  -> Ironmon revealed-response/mechanics adapter
  -> freestanding bounded IronmonPolicyChoose()
  -> selected move or own-party replacement
```

The pure policy accepts at most nine roots and eight response branches. It has
no battle globals, recursion, heap allocation, floating point, or randomness
during scoring. It implements the accepted signed 1/256 utility, toward-zero
division, half-discounted `[-40,+40]` future, range/4 uncertainty capped at 25,
int32 final saturation, last-four repeat/loop memory, candidate-level switch
thresholds, epsilon 4, and the accepted xorshift/rejection ordering.
Forced replacement is a separate post-faint path: its entry candidates retain
public hazard cost but do not take the current-turn response applied to a
voluntary switch.

## Public response lifecycle

`NewBattleStruct.ai.ironmonMoveUseCounts[bank][slot]` is aligned with
`BATTLE_HISTORY->usedMoves`. A count changes only through the producer guarded
by `HITMARKER_ATTACKSTRING_PRINTED`; repeated printed uses increment and
saturate at `UINT16_MAX`. `ClearBattlerMoveHistory()` clears the counts in the
same identity/switch lifecycle. The state is battle-local and adds no save
bytes. A generic history slot with a zero aligned public count is excluded from
Ironmon observations, so an unprinted move attempt cannot become a response.

The response distribution is exact integer arithmetic:

- no reveal: aggregate UNKNOWN weight 1;
- partial reveal: each move gets `3 * (count + 1)`, UNKNOWN gets the sum of
  `(count + 1)` for an exact 75/25 aggregate split;
- four revealed moves: each move gets `count + 1`, with no UNKNOWN;
- opponent switch response weight is zero.

UNKNOWN never invents a move, coverage, order, damage, survival, absorber,
revenge, or tactical future. It retains only candidate value independently
projected from public state or exact own-trainer facts.

Badge ownership is private save/progression state, not a fair observation. When
the configured CFRU battle context permits a player-side Badge modifier, the
adapter bounds the public Speed and damage intervals with both unboosted and
possible 1.1x values. It never reads Badge possession to narrow a certificate;
unresolved modifiers remain conservative UNKNOWN.

## Production tactical support matrix

| Module | v1 source disposition |
|---|---|
| Common floor / robust safe KO | Supported through the unchanged Standard fair projection and Ironmon floor. |
| Revealed direct damage/order | Supported for Standard's reviewed constant-power subset using displayed species/level, public stages/types/status/field, IV/EV/nature bounds, priority, Speed bounds, paralysis, Trick Room, and exact own defenses. Unresolved modifiers/order fail conservative. |
| Two-turn damage / 2HKO | Supported only when the direct subset, two full-bar hits, response-specific survival, and order are certified. Possible/high-roll KO is never robust. |
| Two-use Speed threshold | Supported only when the actual second stage certifies the order change and two response exposures are survived. |
| Setup 3HKO to 2HKO | Supported only from a matching Standard-supported follow-up and a response-specific survival/order certificate. |
| Poison/Toxic/burn residual | Supported through effect-specific Standard residual facts; no generic status bonus. |
| Recovery | Exact own HP gain is counted once. A pre-heal lethal/post-heal surviving response is a supported survival race; post-heal lethal and UNKNOWN give no survival credit. |
| Entry hazards / immunity entry | Supported from exact own party, source-owned hazard math, exact own types/ability, and revealed attacks. Voluntary entry takes the current response; forced replacement does not. |
| Leech Seed and Yawn/pending sleep | `UNKNOWN` in production v1: CFRU timing/blocker state is not narrowed enough at this fair boundary for positive tactical utility. Duplicate public states remain rejected where the common floor represents them. |
| Field, Protect, and strategic pivot timing | `UNKNOWN` in production v1; no generic class bonus. Supported direct damage remains available independently. |
| Natural Cure / Regenerator marginal value | No positive v1 credit. In particular, Regenerator alone cannot establish loop progress. |
| Changed-public-threat loop exception | Fails conservative in production v1. Independent post-cost progress and emergency exceptions remain available; no hidden threat signature is synthesized. |

## Switching and trace values

The pure result exposes each candidate utility and switch advantage, individual
threshold eligibility, best stay/switch, threshold class, admission pre/post
state and draw count, admitted pool, epsilon near-best pool, selection draw
count, total draws, final RNG state, and selected stable ID. Emergency candidates
individually must dominate the best defensible stay. Non-emergency candidates
individually need `advantage >= 12`; a class admission can never restore a
below-threshold candidate.

Production derives a response emergency only when all revealed slots are known,
every defensible stay is certified lethal, and that particular entry survives
every response. With aggregate UNKNOWN present, this extra emergency proof is
unavailable and the ordinary candidate-level threshold path remains.

## Production sequencing repair

The adapter applies certified engine order before copying an outgoing result.
An opponent-first lethal branch records the own faint and has zero outgoing
damage/future; a trainer-first non-terminal action retains its result before a
response KO; and a trainer-first robust terminal KO suppresses the response
entirely. Recovery is evaluated at the HP present at each point in that
sequence, including the post-hit cap for an opponent-first response. Voluntary
replacement evaluates entry hazards before the revealed current-turn response;
forced post-faint replacement remains hazard-only.

Order certificates use public Speed intervals, priority, paralysis, and stable
Trick Room comparisons. Tailwind, Swamp, weather, terrain, screens, dynamic
types, unresolved status/side modifiers, expiring Trick Room, and selected
species exceptions fail closed. The same modifier certificate gates incoming
damage survival and tactical future credit. A concrete Standard-owned setup
follow-up carries its move/slot, physical-or-special split, before/after HP
fractions, priority, and the next-turn order/survival check; a different move
cannot supply the threshold gain.

## Memory and source gates

The Ironmon additions inside `NewBattleStruct.ai` are 52 bytes: 4 seed flags,
16 policy-RNG bytes, and 32 public move-count bytes. Host alignment increases
`NewBattleStruct` by 56 bytes. The existing 240-byte Standard fair memory block
is reused as the common last-four/pending foundation without changing its
layout or Standard sequences.

The production adapter uses one non-reentrant EWRAM scratch observation and
result (2,140 bytes total) so the 9x8 value objects are not placed on the battle
callback stack. It adds zero IWRAM and zero persistent/save bytes. Exact target
object sizes, static stack estimates, undefined symbols, helper bindings, and
direct relocatable-link closure are emitted by
`scripts/tests/run_standard_ai_tests.py --arm-cc <approved compiler>`.

At the source candidate gate, exact production-CFLAGS temporary ARM objects
reported: Ironmon policy text 4,352 bytes / BSS 0 / maximum per-function static
stack estimate 232 bytes; Ironmon adapter text 4,612 / BSS 2,140 / maximum
static estimate 728 bytes. The related unchanged-semantics objects reported
Standard policy 1,668 / 0 / 152, mechanics 1,264 / 0 / 96, and Standard adapter
7,955 / 0 / 728. Thus the modeled Ironmon EWRAM delta is 2,196 bytes (2,140
scratch plus the aligned 56-byte `NewBattleStruct` increase), and IWRAM/save
deltas are zero. These compiler estimates are source evidence only, not a
runtime frame-budget or two-frame timing claim.

`scripts/tests/run_ironmon_ai_tests.py` validates the three accepted Workspace
digests, generates a temporary C harness from the accepted 63-fixture v3
corpus, compares replicate-0 policy results/diagnostics, and reproduces the
1,024-seed switch and epsilon sequences. Temporary sources/objects are deleted.
