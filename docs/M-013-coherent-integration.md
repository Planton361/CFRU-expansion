# Final CFRU source integration — M-013 + coherent data

**CONFIRMED USER DECISION:** combine exactly the two accepted source candidates,
preserve both fail-closed preflight contracts, and publish a draft integration
candidate. This is source acceptance preparation, not runtime or merge acceptance.

## Exact inputs and tree relationship

| Role | Exact revision |
| --- | --- |
| Canonical baseline | `827fa1ef04bd43e5c6bad5c47f7d8690ea6823ec` |
| M-013 / CFRU #45 | `d8468e1d12dbe33f646e2778bbde51ece7010a73` |
| Coherent data / CFRU #48 | `c483410d44c1b592e8039e631556cadab2352b3a` |
| Accepted workspace helper / #493 | `ddd26b17d1ecae80a26943b76ed51b93e70e692c` |
| NEW Showdown reference | `b1156ff19204e48089e2384eb2c9c1a8004f57ce` |

Historical Showdown revision remains **UNKNOWN**. No DPE or UPR-FVX change,
component pin update, ROM/save/state/build/tool-binary access or merge occurs.
#45 and #48 remain separate and unchanged. #46, #47, M-011 Hospitality, new QoL
and new battle mechanics are excluded.

The fresh branch `integration/m013-coherent-data` starts at accepted #48 (whose
parent is the canonical baseline) and imports the **cumulative canonical-to-#45
source delta**, not just #45's final small commit. There is no merge commit.
All comparisons below are against the supplied exact SHAs, not branch tips.

| File set | Exact ownership in combined tree |
| --- | --- |
| `src/item.c` | Entire file byte-identical to #45; only the accepted purchase callback differs from canonical |
| `scripts/check_premier_bonus.py`, `scripts/tests/m013_premier_host.c`, `docs/M-013.md` | Byte-identical to #45 |
| `src/Tables/level_up_learnsets.c` | Byte-identical to #48, including all eight pointer changes |
| `scripts/check_coherent_learnsets.py`, `docs/coherent-learnset-consumers.jsonl`, `docs/coherent-learnsets-provenance.json`, `docs/coherent-learnsets-closure.md` | Byte-identical to #48, including reference/policy/source hashes |
| `scripts/check_hidden_item_sparkle.py` | Deliberate composition described below; no removed accepted assertion |
| `scripts/check_m013_coherent_integration.py`, this document | Integration-only verification and handoff additions |
| Every other tracked path | Canonical baseline; proven by exact changed-path-set comparison |

Thus the canonical diff is exactly the ten-path union of #45's five-path delta
and #48's six-path delta (one overlap), plus two integration-only files: **12
paths total**. Relative to #45 there are #48's five exclusive files, the combined
preflight and two integration files: **8 paths**. Relative to #48 there are #45's
four exclusive files, the combined preflight and two integration files: **7 paths**.
Only two runtime translation units differ from canonical: `src/item.c` and
`src/Tables/level_up_learnsets.c`; both exactly match their accepted owner.

## Fail-closed preflight composition

The insertion entry remains byte-identical to canonical. Its first action is
the existing M-009 source preflight, before protected insertion input access.
That preflight now:

1. Verifies the exact accepted file union and exact combined preflight text.
2. Executes #48's unchanged exact learnset/data/pointer/engine-layout guard.
3. Executes all existing M-009 frame/scanner/insertion/ownership checks.
4. Retains #45's exact check that no `item.c` bytes outside the accepted callback
   differ from its prior baseline.

The allowlist is the union of the two accepted lists plus the integration
checker itself. It is not a directory-wide exception. The integration guard
additionally fixes the **entire** Premier source, host suite, learnset source,
learnset guard and provenance to their accepted bytes, so an arbitrary edit
inside the allowed purchase callback is no longer sufficient to pass preflight.

`combined_preflight()` independently reconstructs the overlap from the two
accepted Git blobs: keep #48's guard and original assertions, splice #45's exact
callback-boundary block/allowlist entries, then add the integration guard entry.
The complete resulting preflight must match. No guard is disabled, swallowed,
or moved after insertion input access. Missing accepted Git objects fail closed;
an isolated source checkout used for verification must retain those histories.

The M-001–M-008 insertion contracts remain canonical and are checked for exact
preservation by M-009. All map/overlay/frame/scanner/configuration owners are
unchanged. Runtime acceptance remains separately gated.

## Source-only verification

Results are recorded after execution on this combined tree. No prior candidate's
runtime or full-build result transfers automatically.

| Check | Result |
| --- | --- |
| Exact source union and 13 rejection mutations | PASS |
| M-013 actual callback, 11,110 ball cases + controls | PASS, UBSan/bounds |
| Accepted coherent helper's 27 synthetic tests | PASS |
| Deterministic full-file learnset replay and two identical inventories | PASS, exact #48 inventory equality |
| Actual initial movesets: 144,000 ID/level cases, ASan/UBSan/bounds | PASS |
| Unchanged coherent guard plus five negative mutations | PASS |
| M-009 source/frame/scanner and eight negative cases | PASS |
| M-004 renewable hidden-item source-table check | PASS |
| ARM syntax for both affected translation units | PASS; unchanged M-009 frame/scanner units also checked |
| Diff checks / workspace git safety before and after | PASS; existing checkouts and pins preserved |

Reproduce from the integration CFRU root. `WORKSPACE_SOURCE` denotes an isolated
read-only workspace checkout at the exact helper revision above, containing
canonical DPE source; `SHOWDOWN_DATA` denotes the pinned public source `data/`
directory. Neither is a ROM, build or private fixture path.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_premier_bonus.py
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s "$WORKSPACE_SOURCE/07_scripts/data_audit" -p 'test_showdown_pinned_closure.py' -v
PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_m013_coherent_integration.py --workspace "$WORKSPACE_SOURCE" --showdown-data-dir "$SHOWDOWN_DATA"
PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_coherent_learnsets.py
PYTHONDONTWRITEBYTECODE=1 python3 -c 'import sys; sys.path.insert(0,"scripts"); import check_hidden_item_sparkle as c; c.check_source_contract(); c.check_host_algorithm(); c.check_rejections()'
arm-none-eabi-gcc -mthumb -mno-thumb-interwork -mcpu=arm7tdmi -mtune=arm7tdmi -mno-long-calls -march=armv4t -Wall -Wextra -Os -fira-loop-pressure -fipa-pta -fsyntax-only src/item.c src/Tables/level_up_learnsets.c
git diff --check
```

The wrapper does not edit the accepted helper, DPE, UPR-FVX or any candidate
checkout: its in-process CFRU table/engine read paths point at the integration
tree. The accepted constants parser uses workspace-relative component labels,
so its existing CFRU header inputs are retained only after byte-for-byte equality
with the integration headers is verified. No parser/policy bypass is used.
Both full inventories exactly match #48's accepted tracked inventory.

The retained data counts are SAFE_DATA_DIFF 0, NO_DIFF 2381,
SHARED_TABLE_CONFLICT 0, FORM_MAPPING_BLOCK 88, MOVE_BEHAVIOR_BLOCK 18,
ABILITY_BEHAVIOR_BLOCK 44, NO_L1_PATH 0 and UNBOUND_POINTER 0. These are scoped
inventory rows, not unrestricted species-support certification. The 18 legacy
Ally Switch-blocked tables, unresolved/custom form exclusions, 44 blocked ability
slots and 27 reserved sentinel consumers keep #48's exact disposition.

## Full build gate

**BUILD_BLOCKED_TOOLCHAIN:** executable-name lookup confirms `wav2agb` and
`mid2agb` are both unavailable. The full build was not retried against missing
converters or partial sparse inputs. Full clean/link build is not claimed by
ARM syntax or host compilation. Native POSIX `scripts/build.py` requires executable
names `wav2agb` and `mid2agb` on PATH. Do not install, download, copy, patch around
or silently skip absent converters. `clean.py`, the ROM insertion wrapper and
protected artifacts are not used by this session.

Once the approved toolchain exists, the user can run this preflight followed by
a clean full source build in a fresh **complete** isolated source checkout:

```sh
for tool in arm-none-eabi-gcc arm-none-eabi-as arm-none-eabi-ld arm-none-eabi-objcopy grit wav2agb mid2agb; do
  command -v "$tool" || exit 1
done
python3 scripts/build.py
```

Do not promote a sparse checkout's skipped asset inputs or a cached build into
a clean/full-build PASS. Supply sanitized command/result evidence, not generated
build artifacts. No insertion or runtime step is run by the agent.

## Exact remaining manual runtime matrix

All rows are **PENDING for the integration SHA**. Start with a successful clean
full build of this exact combined tree and the declared supported profile. Use
known initial money, inventory, species/form, level and story state. Rows requiring
unavailable legitimate setup are BLOCKED, not PASS. #45's detailed P01–P10 matrix
in [M-013.md](M-013.md) remains unchanged and mandatory.

| ID | Action | Required PASS result |
| --- | --- | --- |
| P01 | Each of Poke/Great/Ultra/another normally sold ball: buy 9, 10, 19, 20, 21 with space | Premier deltas 0/1/1/2/2, no custom Dusk/Luxury substitution; correct money and purchased items |
| P02 | Separate 9+9 and 10+10 purchases | Bonuses 0+0 and 1+1; no cross-transaction carry |
| P03 | Buy 20 with exactly one then zero Premier capacity | Bonus 1 then 0; original purchase remains correct |
| P04 | Full ball pocket with existing Premier stack room, full Premier stack, then no Premier slot | Existing-stack room used only; no overflow/new-slot corruption or hang |
| P05 | Purchase fills last slot; repeat with purchased Premier Balls if legitimately stocked | Capacity evaluated after purchase; bonus based on purchased count only |
| P06 | A/B confirmation and repeated/held/mashing input through award/return | One award, correct singular/plural count, normal callback/menu progression |
| P07 | Cancel quantity/confirmation, insufficient funds, purchased item cannot fit | No bonus, no unintended money/item change |
| P08 | 5/10 Potions, 3 Antidotes, 5 Repels; unlisted non-ball item and sales | Existing custom rewards unchanged; no Premier bonus on non-balls or sales |
| P09 | Leave/re-enter and change Mart; save/reload after purchase | Correct persisted inventory/money, no repeated award or script lock |
| P10 | Randomized shop with valid ball and non-ball controls | Same pocket-based rule, independent of the original shop slot |
| L01 | Fresh starters/ordinary encounters at levels 1–5 | Non-sentinel initial moves match the last four eligible rows in the coherent source, with existing duplicate handling; usable moves, no crash |
| L02 | Pikachu/base/caps and each of the six Cosplay-family IDs at L1 and representative level boundaries | Base/caps Gen9; Cosplay/Libre/Pop/Rock/Belle/PhD Gen6; no shared-table regression; no invented costume `R` moves |
| L03 | Pichu and Spiky-eared Pichu at L1, then through their first level-up boundaries | Gen9 versus Gen4 respectively; Spiky L1 Charm/Thunder Shock; no accidental re-sharing |
| L04 | Rotom plus five appliances; Necrozma/base/Dusk/Dawn/Ultra display/initial moves | Coherent Gen9 shared tables; no empty moves/crash or automatic import of restricted-only signature entries |
| L05 | Magearna/Original, Zacian/base/Crowned, Zamazenta/base/Crowned | Shared Gen9 data retained, no wrong IDs/moves or new mechanic claim |
| L06 | Zygarde/base/10%/Complete at L1 and subsequent boundaries | Coherent Gen8 start/level rows, usable initial moves; Cell/Core not ordinary selections |
| L07 | Dialga/Origin, Sandshrew and Litleo at L1 and first level-up boundary | Metal Claw/Scary Face; Defense Curl/Scratch; Leer/Tackle start paths respectively; correct subsequent rows |
| L08 | Zarude and existing ID1209 Zarude-Dada at L1, level-up, party/summary and battle entry | Both bind the same Gen9 table; Bind/Scratch at L1; no null-table path or form-ID corruption |
| L09 | Representative changed species immediately below, at and above listed learn levels; Move Reminder and save/reload | Exact selected-generation rows; no removed older-only move returns; no list overflow, persistence or menu corruption |
| X01 | Buy a bonus-triggering ball quantity, open Bag/Party/PC/Start, enter battle with a corrected low-level species, return and warp | Correct single bonus persists; moves remain intact; camera/OAM/palettes/scripts return normally |
| R01 / M-001 | Representative visible TM/HM ball, ordinary item ball and randomized visible TM/HM | Gold visible TM/HM semantics and pickup remain correct; no ordinary-item reclassification |
| R02 / M-002 | Forest Nurse, including poisoned-party refusal | Prior healing/refusal/dialogue behavior preserved |
| R03 / M-003 | Kanto/Sevii instant Centers; Trainer Tower control, Name Rater and PC | Prior fast path and Tower exception, restoration, menus and warps preserved |
| R04 / M-004 | Underground/Sevii renewable representatives after cycle; Mt. Moon control | Guaranteed approved regeneration, vanilla/random Mt. Moon; one-time hidden items and Itemfinder intact |
| R05 / M-005 | Fresh game PC and Lab Potion, pickup then reload | No initial PC Potion; one Lab Potion with persistent pickup state |
| R06 / M-006 | Attempt pre-Mom exit, talk to Mom, starter/Rival transition, post-rival Mom | Exit guard and mandatory handoff; normal starter/Rival and healing behavior |
| R07 / M-007 | Route1/Pallet parcel flow, Pokedex + five Balls, Viridian Mart, Old Man, Daisy/Map, Route22 | Single parcel/reward, no Mart duplicate, tutorial skip and correct subsequent story state |
| R08 / M-008 | Post-Blaine scene; Center Bill NO/save/reload then YES/Sevii/return | No mandatory outdoor Bill interruption; optional existing flow preserved |
| R09 / M-009 | Camera/OAM during walking/auto-run, menus/options, warps/connections and battle-to-field | Correct global-frame order; no offset sprites, palette loss, stale frame or menu corruption |
| R10 / M-009 | Hidden sparkles, pickup, Itemfinder, renewal; busy field effects and cutscenes/scripts; Quest Log where practical | Existing filtering/cooldowns and lifecycle reset; no stray effects, sprite/palette leaks or script locks |
| R11 | Randomized-output smoke under exact declared settings/profile, including expanded species/forms | No unsupported/reserved ordinary selections, no null/invalid moves or writer regressions; existing block/exclusion caveats explicit |

No row certifies missing battle mechanics. Full story/playthrough acceptance
remains a later product gate; targeted source/host PASS is not ROM FEATURE
COMPLETE or ROM FROZEN.

Evidence format: integration SHA, preserved component pins, settings/profile
label, row ID, sanitized initial conditions, action, expected versus actual,
PASS/FAIL/BLOCKED, severity. Do not provide ROM/save/state/build files or private
paths. STOP/S1 for crash/freeze, progression lock, duplicate reward, invalid
move/pointer, inventory/money/state corruption, or wrong reward quantity/type.
Readability-only text issues are S2/S3 unless they obscure acceptance.

Next user action: review the exact integration diff, supply the approved local
toolchain, complete clean build, then execute this matrix on the exact integration
revision. Do not replace or merge #45/#48 during this source-only handoff.
