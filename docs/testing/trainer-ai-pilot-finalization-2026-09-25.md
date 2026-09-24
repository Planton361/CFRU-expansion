# Trainer AI pilot finalization — CFRU source evidence

Workspace contract: Planton361/firered-gen9-randomizer-workspace#526, including the final CONTROL scope amendment. Component: Planton361/CFRU-expansion. This is sanitized source and host evidence for CONTROL review, not ROM/runtime acceptance.

## Revision and boundary

- Exact starting and target-base SHA: `423f96f0dcd501a64c2327d726a98f1964937ac1` (`compat/firered-gen9-randomizer`), verified locally and against the remote before branch creation.
- Final implementation/source SHA: `dfed1e3156e60aa6e869910c3a728aa96611e85a`. This SHA contains every production and test change below. The Evidence-only commit and final PR head are reported in the Workspace Issue handoff because a committed file cannot contain its own SHA.
- Head branch: `fix/r1-ai-runtime-quality`; PR base: `compat/firered-gen9-randomizer`.
- Changed implementation and tests: `include/new/ai_standard.h`, `include/new/ai_damage_engine_overrides.inc`, `src/Battle_AI/ai_standard.c`, `src/battle_strings.c`, `src/switching.c`, `src/general_bs_commands.c`, `scripts/tests/audit_ai_damage_overrides.py`, `scripts/tests/audit_standard_ai.py`, `scripts/tests/run_standard_ai_tests.py`, `scripts/tests/ai_runtime_quality_host.c`, `scripts/tests/ai_runtime_differential.py`, `scripts/tests/run_ai_runtime_quality_tests.py`, and this Evidence file.
- No Workspace Gitlink, DPE, UPR-FVX, Legacy Smart policy/dispatch, save schema, Trainer/Pokemon/BattleMove/NewBattleStruct layout, or special-mode routing change. UPSTREAM_CONTRIBUTION remains deferred.

## Root causes and falsified hypotheses

1. The old `StandardAI_IsSupportedDamage` was a small positive Move-ID list. `MOVE_ROCKTOMB` was absent although it is ordinary direct damage with a Speed-drop secondary. Source Brock/Onix is level 14 with `{TACKLE, BIND, ROCKTOMB, NONE}`. Rock Tomb is power 60, Rock, physical, accuracy 95, `EFFECT_SPEED_DOWN_HIT`. The omission was systemic; no Brock special case was added.
2. The accepted #523 Tackle/Water Gun host witness already scores Water Gun as sole near-best. New public-target witness scores Tackle damage 4 / utility 19 versus Water Gun damage 11 / utility 54, selecting Water Gun with zero selection draws. Both have PP and are legal. Water Gun gets Water STAB and 2× public Fire effectiveness. Ironmon Smart dispatch is active. UNKNOWN response does not erase this outgoing advantage. Consequently epsilon and policy RNG cannot explain Tackle **when the target species is known**.
3. Before the change, public displayed species was recorded only from a sprite-coordinate path. A deterministic first-turn state with the public species still unset makes both attacks `unknown_potentially_productive`; seed 2 then selects Tackle from two near-best actions with one draw. This is a source-backed possible production path, not proof of the user-supplied private runtime's exact hidden state. The first send-out and replacement battle text now record the same Illusion-aware public appearance before the next AI decision. No hidden actual type/species or submitted action is read by the adapter.
4. The prior policy/memory logic already hard-floored the third successful same-family pure-status move. The risk was lifecycle timing: pending success could be compared after old target stages/status were replaced or cleared. The switch-in/faint hooks now finalize against the old target before cleanup. The accepted #510 two-success rule, Standard epsilon 8, Ironmon epsilon 4, and v1/v2/v3 host digests remain unchanged. No host calibration conflict was found in the covered source states.

## Damage-class architecture and source census

Classification uses the current source move table's split, effect, power, target, priority and accuracy, then the bounded public mechanics projection uses level, displayed species/type, own offensive stat, public defensive stat interval, STAB, type effectiveness and accuracy. The generated exclusion set is an audited **negative** list of named damage-engine move overrides; it is not a positive admission list. A future named override changes the audit output and must be reviewed. Unsupported effects receive no invented tactical credit. Static-type immunity remains certifiable for fixed-damage attacks; an engine-overridden type cannot be certified from static metadata.

| Class | Rule | Damaging moves |
| --- | --- | ---: |
| D0 | Ordinary direct damage from bounded metadata | 49 |
| D1 | Direct damage, unmodeled secondary gets zero credit | 117 |
| D2 | Supported direct damage with priority/accuracy/always-hit variant; may also have a secondary | 110 |
| D3 | Explicitly unsupported or complex mechanic, fail closed | 445 |

Source-table census: **991** moves excluding `MOVE_NONE`; **721** damaging, **270** status. Of damaging moves, **92** fully evaluated, **184** direct-damage-only, **445** unsupported/fail-closed. D0+D1+D2 = 276 directly evaluated attacks. `Rock Tomb` is D2 because accuracy is 95; its unmodeled Speed-drop secondary does not suppress its known direct damage. The current damage-engine negative list has 131 named entries, of which 70 damaging moves reach the engine-override D3 reason after other effect checks.

| D3 reason | Count | Why fail closed |
| --- | ---: | --- |
| Non-target | 2 | Ordinary single-target projection is inapplicable. |
| Named engine override | 70 | Engine changes damage/type/power/effectiveness outside the bounded metadata formula. |
| Multi-hit | 29 | Hit count and per-hit state need an explicit model. |
| Fixed damage | 8 | Level/HP/formula-specific damage is not ordinary base-power damage. |
| Recoil | 14 | Own HP consequence is unmodeled. |
| Drain | 12 | Own HP recovery and its conditions are unmodeled. |
| Self-KO | 4 | Own faint/field timing is unmodeled. |
| Two-turn/charge | 16 | Charge and exposure timing are unmodeled. |
| Counter-like | 4 | Opponent action/damage dependence is unmodeled. |
| OHKO | 4 | Special hit/KO rules are unmodeled. |
| Other effect | 94 | Distinct scripted effect lacks an ordinary direct-damage certificate. |
| Z/Max pseudo range | 154 | Requires transformation/battle context outside ordinary move projection. |
| Recharge/lock | 20 | Future lock/recharge or variable sequence is unmodeled. |
| Conditional script | 14 | Action conditions, order, delayed hit or target state are unmodeled. |

The census is deterministic over `src/Tables/battle_moves.c`; `python3 scripts/tests/run_ai_runtime_quality_tests.py` regenerates the report and checks representative classifications. D3 has a queryable reason per move. Coverage does not claim all Gen-1–9 mechanics are tactically modeled.

## Production-adapter witnesses

- Brock/Onix against a public Fire target: Standard Tackle damage 9 / utility 17 versus Rock Tomb damage 37 / HP fraction 231/256 / utility 72; Rock Tomb sole near-best and selected with zero draws. Ironmon utilities 21 versus 90; Rock Tomb selected with zero draws. `Bind` remains D3.
- Sandshrew Accuracy: public stage 6→5, 5→4, 4→3 marginal gains **25, 15, 10**. The first and second successful uses are eligible; alternating Smokescreen and Sand Attack cannot evade normalized `ACCURACY_DOWN` memory. Both are hard-floor excluded on the third successful same-family pure-status attempt without the accepted exception; Tackle is selected. A miss with unchanged stage records failure. The pre-switch/pre-faint hook records the old target's actual public stage result. Turn progression retains memory; own replacement does not clear battle-local memory; capped Accuracy at minimum stage is nonproductive. This preserves the accepted #510 rule even when a new target appears.
- Caterpie-like String Shot: with a certified public Speed interval, the first use flips turn order and is selected; once the marginal order value disappears, Tackle is selected. Weedle-like String Shot without a certified flip loses to Poison Sting's low direct damage.
- The suite also covers ordinary STAB against weaker non-STAB, weaker super-effective against stronger neutral, resisted STAB against neutral non-STAB, reliability versus higher power/lower accuracy, priority KO versus stronger slow move, robust KO versus status, secondary-bearing direct damage versus weaker attack, all-futile legal fallback, and a true near-best pair with seeded selection of both IDs. This is deterministic source plausibility evidence, not a competitive benchmark.

## Production versus accepted Workspace host

`ai_runtime_differential.py` feeds ten source-table/production-adapter public observations to the accepted Workspace Standard/Ironmon host floor and policies. Cases: Rival, equal near-best, Accuracy first/second/third, unsupported fixed damage, known immunity, all-futile fallback, secondary direct damage, and revealed-response priority KO. It compares legality, source mechanics class/reason, expected direct damage, HP fraction, no-effect, marginal gain, repeat state, utility, admission, near-best, selected action, RNG draws and RNG post-state. The source mechanics projection is the producer of candidate facts; the differential verifies transfer and policy parity, while the existing 98,304-case damage-envelope oracle independently bounds its arithmetic. All **10/10** states match; **0** field/decision/RNG mismatches. D3 unknown is explicitly reasoned (`fixed_damage` in the differential), not silently scored as weak direct damage.

Covered-suite counts: illegal/no-effect selections with productive legal alternative **0**; missed robust KO **0**; third harmful same-family repeat **0**; below-epsilon selection **0**; selected unsupported damage with a clearly superior supported alternative **0**. Fallback invocation **1**, solely `NO_PRODUCTIVE_ACTION` in the all-futile case. The host's older `productive` input represents the adapter's explicit unknown-potentially-productive admission in that one boundary case; no host digest was changed.

## Regressions, ARM and build

| Gate | Result |
| --- | --- |
| `python3 scripts/tests/run_standard_ai_tests.py` | PASS; Standard production twins 4096/0, Ironmon production twins 1024/0, Badge twins 16/0, Badge oracle 663000/663000, damage oracle 98304; hidden state, submitted action, future RNG, dispatch, RNG isolation and save/layout witnesses pass. |
| `python3 scripts/tests/run_ironmon_ai_tests.py` | PASS; C/host parity 63/63, mandatory tags 58/58, v1/v2/v3 accepted digests unchanged. |
| `python3 scripts/tests/run_settings_defaults_tests.py` | PASS; defaults, raw mappings, Legacy Smart raw meaning preserved. |
| `python3 scripts/tests/run_replacement_safety_tests.py` | PASS; replacement identity and boundary checks. |
| `python3 scripts/tests/run_ai_runtime_quality_tests.py` | PASS; census, fourteen plausibility families, ten differential states and runtime quality counters. |
| Standard suite with already-installed devkitARM `--arm-cc` | PASS; ARM syntax for 16 applicable source files, eight policy/adapter/lifecycle objects under literal production CFLAGS, undefined-symbol audit and relocatable `ld -r` closure. Existing helper assembly resolves emitted runtime helpers; unsupported compiler helpers **none**. Remaining engine/BPRE symbols are expected without a full link. |

The layout witness reports no new `BattlePokemon`, `BattleMove`, `BattleStruct`, `NewBattleStruct` or save delta in this branch; save delta is **0**. Battle-local state uses only previously accepted fields. Full `python3 scripts/build.py` was **not run** because the complete approved toolchain is unavailable (`wav2agb` and `mid2agb` absent). No tool was installed or downloaded. No ROM, save, emulator state or generated/private build was inspected or produced.

## Architecture references and limitations

The accepted #506 reference lessons were applied as architecture only: pret/Cyan/Ironmon's separate viability and offensive competence; pokeemerald-expansion's modular policy boundaries and broad effect review; Shin/PokeRed Canonical's small battle-local memory; Elite Redux's explicit coverage discipline; PokAImon Emerald's source-aligned damage plus differential validation. Metamon/Showdown remains an evaluation-method reference. No omniscient preset, learned weight, foreign balance value, foreign engine mechanic or submitted-action access was copied.

The private R1 report was not replayed with a ROM here. The public-species timing path explains how Tackle was possible in source but does not establish the exact unseen runtime cause. D3 remains conservative; weather, dynamic type, hidden ability/item and unsupported special mechanics can widen uncertainty. CONTROL must review the source PR, then the separate integration/rerun process in #526 applies. Workspace #498 remains Blocked.

TRAINER_AI_PILOT_FINAL_SOURCE_READY
