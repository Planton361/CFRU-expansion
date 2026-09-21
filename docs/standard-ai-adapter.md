# Standard adapter — Workspace #512 repair

This document describes the supported source subset, not runtime acceptance.
The pure policy and its existing parity vectors are unchanged by this repair.

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

The initial direct-damage allowlist contains 33 constant-power single-hit moves:
Tackle, Pound, Scratch, Quick Attack, Vine Whip, Water Gun, Horn Attack, Peck,
Wing Attack, Swift, Aerial Ace, Dragon Claw, Dragon Pulse, Strength, Ember,
Flamethrower, Ice Beam, Thunder Shock, Thunderbolt, Bubble, Confusion, Psychic,
Bite, Crunch, Metal Claw, Rock Throw, Rock Slide, Surf, Razor Leaf, Leaf Blade,
Energy Ball, Shadow Ball and Flash Cannon. Secondary effects add no speculative
utility. Recoil, sacrifice, variable-power, multi-hit, charging and other moves
remain unsupported by this direct-damage derivation.

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

## Accuracy and switching

Accuracy utility measures a single hypothetical 100-accuracy exposure: the
100->75->60->50... hit-rate curve gives decreasing marginal value per stage.
The one-HP-bar exposure is an upper bound, with half the gain charged as
uncertainty because the opponent's unobserved move is unknown. Capped drops are
unproductive. Sand Attack and Smokescreen still share the policy's effect family.

Low HP is no longer an emergency condition. Any legal productive stay prevents
voluntary switching. A switch needs no productive stay, a usable supported
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

Production twins cover 7 hidden-input categories x 32 mutations x 5 contexts
(ordinary, certified KO, emergency switch, hazards and near-best ties): 1120 pairs. They compare the entire
candidate observation, damage envelope, policy diagnostics, RNG state/draws and
selected action. The independent damage oracle covers 98,304 IV/EV/nature/roll
combinations. Behavior witnesses cover both Accuracy moves versus KO, useful and
diminishing Accuracy, cap, meaningful/weak damage, possible-only KO, reveal,
switch admission, entry-KO, loop guard, forced replacement and singleton RNG.

Repair delta: 8 battle-local EWRAM bytes for displayed species; zero IWRAM or
save/persistent bytes. Existing Standard state is 0xE4 bytes plus this 8-byte
snapshot (0xEC total), checked by compile-time assertions. ARM asserts
BattlePokemon=0x58, BattleMove=0x0C and BattleStruct=0x200. No Trainer/Pokemon,
DPE, ROM table/repoint or randomizer layout changes. Battle allocation/zeroing
still resets Standard memory/RNG.

Scratch additions: mechanics input 26 bytes, envelope 16 bytes, and a 26-byte
critical-bound copy plus scalar locals. The replacement path has bounded local
observation/result/memory objects (472/192/33 bytes); it does not recurse or add
dynamic allocation. Exact optimized call-chain stack/cycle cost is not certified
by syntax checks and remains part of later target build/runtime measurement.

Full build is conditional on the complete already-approved source toolchain.
The repair environment has devkitARM GCC 16.1.0 but lacks `wav2agb`/`mid2agb`;
no tools are installed or downloaded. No ROM/emulator operation is authorized.
