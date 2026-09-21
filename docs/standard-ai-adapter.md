# Standard adapter — Workspace #512 repair

This document describes the supported source subset, not runtime acceptance.
The accepted policy arithmetic/RNG and existing parity vectors are preserved.
The only policy-floor extension admits explicitly unknown potentially productive
damage without assigning it positive utility. CONTROL re-review is required;
this document does not claim `CFRU_STANDARD_SOURCE_READY`.

## Observation and damage

`ai_standard.c` projects own exact trainer facts and public active-battler facts
into the pointer-free `StandardMechanicsInput`. `ai_standard_mechanics.c` derives
the candidate values used by the production policy. The production adapter test
compiles the actual `ai_standard.c` and the real CFRU move/type tables; it does
not replace the candidate builder with a host implementation.

Species comes from an eight-byte battle-local snapshot populated by the existing
sprite-position hook, after that hook has selected the identity to display.
The builder never follows Illusion into the player party or reads the underlying
active species. Missing display identity fails closed. Ability reveals come from
the existing public-message history. The snapshot follows public form/redraw
events and is zeroed with the battle allocation.

Types likewise come only from that displayed species' public base-type table,
never the opponent's internal type1/type2/type3. An unbroken Illusion therefore
cannot expose real typing. A public displayed-identity reveal can change the
model. Dynamic types are deliberately UNKNOWN: observed Conversion/Conversion2,
Camouflage, Reflect Type, Soak, Trick-or-Treat, Forest's Curse, Magic Powder,
Transform, Burn Up, Double Shock or Roost conservatively invalidate baseline
types. Public Color Change/Protean records, transformed state and Tera also
invalidate them. The move producer requires the printed attack-string marker.
Four sticky battle-local uncertainty bytes retain this invalidation through
history eviction, switches and ability replacement; they reset only on the next
battle allocation. This intentionally sacrifices precision rather than reading
hidden current types. Unknown types produce no invented damage or type immunity.

The initial direct-damage allowlist contains 33 constant-power single-hit moves:
Tackle, Pound, Scratch, Quick Attack, Vine Whip, Water Gun, Horn Attack, Peck,
Wing Attack, Swift, Aerial Ace, Dragon Claw, Dragon Pulse, Strength, Ember,
Flamethrower, Ice Beam, Thunder Shock, Thunderbolt, Bubble, Confusion, Psychic,
Bite, Crunch, Metal Claw, Rock Throw, Rock Slide, Surf, Razor Leaf, Leaf Blade,
Energy Ball, Shadow Ball and Flash Cannon. Secondary effects add no speculative
utility. Recoil, sacrifice, variable-power, multi-hit, charging and other moves
remain unsupported by this direct-damage derivation.
Legal unsupported damage, including fixed-damage zero-power table entries, is
`unknown_potentially_productive`: no expected damage, HP utility, net faint or
robust KO is invented, but it remains floor-eligible and blocks a fabricated
no-productive-stay emergency. Publicly proven immunity still rejects it. This
flag occupies former candidate padding; candidate size remains 52 bytes.

For public species/level and stages, the neutral model spans all IVs 0–31,
EV/4 0–63 and nature factors 90–110%. HP spans the corresponding legal max-HP
range. Only a 48-pixel HP ratio crosses the projection boundary; exact player
HP/max-HP does not enter the mechanics function. The ratio is expanded back to
a conservative interval. A public full bar is not treated as a privately known
exact HP stat. Shedinja's one-HP species rule is explicit.

The neutral calculation preserves the integer division order of
`damage_calc.c::CalculateBaseDamage`, ordinary STAB, public type effectiveness,
own burn, stages, accuracy/evasion and 85–100 rolls. The nominal expected-damage
field uses midpoint bounded Defense/SpD and the engine AI's deterministic 93%
representative roll, multiplied by accuracy. This is a ranking estimate, **not**
a probabilistic expectation over hidden sets. No hidden ability/item prior is
invented. HP utility uses the estimated damage clipped to estimated current HP;
uncertainty costs 20 points per estimated full bar when modifiers are unknown.

The complete envelope is [0, 65535] when ability, item or other modifier
uncertainty is unresolved. Its lower bound is also zero if accuracy permits a
miss. Unknown immunity never becomes known no-effect. Public type immunity or a
recorded absorber ability can mark a move no-effect. Ability suppression is
public; no hidden ability slot is consulted. The sparse type table's NO_DATA=0
means neutral and NO_EFFECT=1 means immunity, and is explicitly decoded.

The **certified** envelope is intentionally narrow: both abilities must be
publicly suppressed, Magic Room must have more than one turn remaining, the
target must be publicly recharging, and weather, terrain, screens, Aurora Veil,
type-changing timers, other status2/status3 effects and Terastallization must be
absent as checked in `StandardAI_DeriveDamage`. Terapagos is not certified.
The lower bound covers the highest permitted defense, lowest ordinary roll and
HP display uncertainty. The upper bound also admits critical hits, ignoring
unfavorable offensive and favorable defensive stages. Robust KO additionally
requires own survival/action certainty and minimum damage >= maximum current HP.
Only robust KO gets `net_faints=1`; a possible/high-roll KO never does.

Thus ordinary unknown-item battles receive useful damage ranking, but do not
claim robust KO through a potentially unrevealed Focus Band/Sash or immunity.
Opponent speed/order is not guessed from submitted moves or hidden stats.
Illusion/Transform and other identity-changing effects are not certified damage
contexts; their displayed identity can inform a nominal estimate only. Full
item/move/bench reveal tracking remains a limitation of this initial adapter.
No full engine damage parity is claimed outside this subset.

## Marginal utility and switching

Accuracy utility measures a single hypothetical 100-accuracy exposure: the
100->75->60->50... hit-rate curve gives decreasing marginal value per stage.
The one-HP-bar exposure is an upper bound, with half the gain charged as
uncertainty because the opponent's unobserved move is unknown. Capped drops are
unproductive. Sand Attack and Smokescreen still share the policy's effect family.

Speed uses exact own Speed and public displayed-species/level/stage bounds over
all legal IV/EV/nature values. Badge-boost uncertainty widens the upper bound.
Public paralysis divisors and Trick Room order inversion are explicit. A credit
requires a strict definitely-behind to definitely-ahead flip across the entire
interval after one application, plus a supported ordinary-priority follow-up.
Already faster, overlapping intervals and ties receive zero. Both abilities must
be publicly suppressed and Magic Room must survive the horizon; weather,
terrain, Tailwind/Swamp and unmodeled optional speed rules preclude certification.
The credited value is the supported follow-up HP value (at most 40), not a fixed
Speed bonus or a prediction of the submitted move. String Shot retains its
Speed-down family normalization.

Attack/SpA boosts and Defense/SpD drops compare supported follow-up damage before
and after one stage change. The best single improvement in public HP terms is
valued at 100 points/bar, capped at 40; damage already capped by remaining HP
cannot gain a setup bonus. Defense/SpD boosts and Attack/SpA drops instead use
only supported moves in the public revealed-move history. Their nominal incoming
attack is derived from displayed-species legal-stat bounds and public stages;
own defensive stats/HP are exact. No revealed supported threat means zero.
Unmodeled own ability/item, status2, weather, terrain and defensive-side effects
also suppress this threat estimate rather than inventing a reduction.
The before/after reduction of one incoming HP exposure supplies value. No hidden
move or private offensive stat is read. Half of nominal marginal value is charged
as uncertainty; no claim is made that the opponent will choose that threat.

Major status has no class bonus. Poison values one 1/8-bar residual; Toxic values
its first 1/16-bar residual; burn values 1/16 (or configured legacy 1/8). Residuals
are clipped by public remaining HP and scaled by move accuracy, then priced for
unknown blockers. No speculative burn Attack reduction is added. Paralysis earns
only certified Speed-flip follow-up value; unmodeled action-loss value is zero.
Sleep duration/action-loss remains unsupported and receives zero. Known public
type immunity and redundant status reject status; unrevealed abilities/items
are not inspected or assumed absent.
Recorded Immunity/Water Veil/Limber/Insomnia block their relevant effects;
recorded Magic Guard/Poison Heal suppress unsupported positive residual value.

Recovery counts actual supported healing once, through negative own HP loss.
Ordinary recovery is capped at half max HP (Life Dew at a quarter), then missing
HP, using engine integer rounding. Rest can restore the missing bar; no separate
survival/action-loss bonus is invented. Full HP and Heal Block are nonproductive.
Purify/Jungle Healing/Lunar Blessing prerequisites remain unmodeled. Recovery's
future term is zero: at 60/100 HP Recover scores the host HP term 39; at 10/100 it
heals 50 and scores 50, with no duplicate missing-HP bonus or 50%-HP threshold.

Low HP is no longer an emergency condition. Any legal productive stay prevents
voluntary switching, as does unknown potentially productive damage. A switch needs no productive stay, a usable supported
non-immune own-party attack, legal switching and survival of entry hazards.
The existing policy owns the A->B->A guard. Forced replacement/pivot selection
is a separate controller path and records a forced memory edge.

Entry hazard damage uses only own party data and public side counters. Spikes
use divisors 8/6/4; Rock/Steel use the public type factors and the engine's 1-HP
minimum. Own Magic Guard, Boots, grounding and Magic Room are handled through
own-data helpers. No active player stat participates. Special-rule battles
(including Inverse) do not dispatch Standard.

## Transitive boundary review

- `GetRecordedAbility` was removed: the adapter uses only the public message
  history and public suppression, without guessing from an actual hidden slot.
- `GetRecordedItemEffect` is forbidden: it compares against the current hidden
  item through `ITEM_EFFECT` before returning its history value.
- `GetMonEntryHazardDamage`/`WillFaintFromEntryHazards` are forbidden. Their
  Rock/Steel path calls `TypeDamageModificationPartyMon -> ModulateDmgByType`,
  which reads active-bank HP/max-HP/species even with a party-mon argument.
- The remaining own-data graph is `GetMonAbility -> GetMonData / public species
  ability tables`, `GetMonItemEffect -> GetMonAbility / IsMagicRoomActive /
  ItemId_GetHoldEffect`, and `CheckGrounding(own bank) -> own status/item/ability
  and public field checks`. No opposing bank is passed into that graph.
- `LoadPartyRange` receives only the trainer bank in supported ordinary singles.
  `GetTrainerAIProfile`, `IsRaidBattle`, `IsInverseBattle` and
  `IsFrontierTrainerId` supply dispatch metadata. Value arithmetic uses only
  `MathMin`, `MathMax` and `Memset`. `SIDE` resolves a battler position, not a
  selected player action.
- Controller early returns prevent a Standard move from entering legacy
  Z/Mega/Dynamax/Tera prediction and prevent replacement from entering legacy
  matchup selection. Unsupported gimmicks are not selected by Standard.
- The static audit covers policy, mechanics, projection and controller guards;
  executable production twins provide the noninterference evidence.

## Verification and memory

```
python3 scripts/tests/run_standard_ai_tests.py
python3 scripts/tests/run_standard_ai_tests.py --arm-cc PATH_TO_APPROVED_ARM_GCC
```

The latter records HEAD, dirty state, compiler version and each checked C file.
Use its clean, final-commit output for revision-bound ARM evidence. It compiles
all changed C files against the contract base, including host harness sources,
using syntax-only ARM7TDMI/Thumb checks with the production relative includes.

Production twins cover 8 hidden-input categories x 32 mutations x 16 contexts:
4096 pairs, including the original 1120 cases. Hidden real species/all three
types are the added category (512 pairs); public identity remains fixed. Added
contexts exercise Speed, setup, revealed incoming threats, major status, healing,
unknown damage and dynamic-type uncertainty. They compare the entire
candidate observation, damage envelope, policy diagnostics, RNG state/draws and
selected action. The independent damage oracle covers 98,304 IV/EV/nature/roll
combinations. Behavior witnesses cover both Accuracy moves versus KO, useful and
diminishing Accuracy, cap, meaningful/weak damage, possible-only KO, reveal,
switch admission, entry-KO, loop guard, forced replacement and singleton RNG.
Additional production witnesses cover Speed flip/no-benefit/uncertainty/Trick
Room; useful/saturated/capped setup; revealed versus absent/ineffective threats;
residual/redundant status; recovery host-utility parity; eligible unknown damage
without invented facts or emergency switching; and public type reveal/invalidation.

Round-2 delta: 4 battle-local EWRAM bytes for sticky type uncertainty; zero IWRAM
or save/persistent bytes. Total Standard state is 0xE4 original bytes plus the
8-byte displayed-species snapshot and these 4 bytes (0xF0 total), checked by
compile-time assertions. ARM asserts
BattlePokemon=0x58, BattleMove=0x0C and BattleStruct=0x200. No Trainer/Pokemon,
DPE, ROM table/repoint or randomizer layout changes. Battle allocation/zeroing
still resets Standard memory/RNG.

Scratch: mechanics input grows from 26 to 32 bytes for exact OWN target stats in
the revealed-threat model; envelope remains 16. Before/after evaluators use two
32-byte inputs, two 52-byte candidates and one envelope, plus scalar locals;
the damage evaluator has a 32-byte critical-bound copy. Candidate and observation
layouts stay 52/472 bytes. The replacement path has bounded local
observation/result/memory objects (472/192/33 bytes); it does not recurse or add
dynamic allocation. Exact optimized call-chain stack/cycle cost is not certified
by syntax checks and remains part of later target build/runtime measurement.

Full build is conditional on the complete already-approved source toolchain.
The repair environment has devkitARM GCC 16.1.0 but lacks `wav2agb`/`mid2agb`;
no tools are installed or downloaded. No ROM/emulator operation is authorized.

## ARM object/runtime-helper gate

The ARM runner also parses the literal production CFLAGS from `scripts/build.py`
(without importing/executing that build script), compiles the three Standard
production objects in a temporary directory, and inspects `arm-none-eabi-nm -u`.
It assembles the existing `thumb_compiler_helper.s`, verifies its dependencies
against `BPRE.ld`, and performs a direct `ld -r` runtime-symbol closure check.
Temporary objects are deleted; none are retained or submitted. This is not a
full engine link or runtime test.

The reviewed head emitted unbound `__aeabi_lmul` and `__aeabi_uldivmod`. The narrow
repair removes production 64-bit arithmetic. Damage explicitly bounds level to
1..100, power to 1..150, raw attack to 0..2048, stages to 0..12, base HP/Defense
to 0..255, accuracy to 0..100 and type factors to at most 20. Outside that domain
it returns UNKNOWN with no invented damage/KO. These bounds include the accepted
subset. At staged attack 8192 the initial product is at most 51,609,600; after
division, STAB and three 2x factors, the largest roll numerator is 1,238,632,800.
Every intermediate fits uint32 and the original division order is preserved.

Validated policy HP numerator is -25600..51200; signed 32-bit division preserves
toward-zero semantics. The non-cost prefix is -340..440. Nonnegative costs can
only lower it, so sequential lower-saturating subtraction is mathematically
equivalent to clamping the final exact utility sum. The epsilon threshold also
avoids underflow at INT32_MIN without changing mathematical near-best membership.
A host-only 64-bit oracle checks 17,496 boundary/cost combinations, in addition
to the existing policy vectors and damage oracle. No RNG sequence changes.

Remaining emitted runtime names are only existing 32-bit wrappers:
`__aeabi_uidivmod` in policy, `__aeabi_idiv`/`__aeabi_uidiv` in mechanics and adapter.
These resolve through the existing assembly to BPRE's `__umodsi3`, `__divsi3`,
and `__udivsi3`; memcpy/memset also use existing wrappers/BPRE bindings. No
libgcc, runtime dependency, linker binding, ABI/layout or battle-memory change
is introduced by this arithmetic repair. Final readiness remains CONTROL's decision.
