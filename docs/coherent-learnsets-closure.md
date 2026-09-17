# Coherent current learnset data candidate

Draft, not integration acceptance. Supersedes CFRU #47
`d6b0e8eb14cc66e7dc75c1738fbe16b99623f843` and the #46 historical-restoration
approach for modern-data closure. Neither old candidate is an input.

Canonical CFRU baseline: `827fa1ef04bd43e5c6bad5c47f7d8690ea6823ec`.
NEW Pokemon Showdown reference: `b1156ff19204e48089e2384eb2c9c1a8004f57ce`.
Historical Showdown revision: **UNKNOWN**.

## Bounded change

- Replace 820 existing active learnset table bodies; add two form tables.
- Rebind six existing Pikachu-Cosplay family IDs to their Gen-6 table and
  Spiky-eared Pichu's existing ID to its Gen-4 table.
- Bind existing ID 1209 / Zarude-Dada to Zarude's table: its own exact Gen-9
  dataset matches Zarude, and pinned DPE already uses that shared binding.
- No species IDs, struct layouts, engine routines, configuration, battle
  mechanics, DPE tables, shops, QoL behavior or component pins change.
- Narrow M-009 preflight extension verifies the exact data source before
  insertion input access. Existing frame/scanner checks remain active.

## Selected-generation policy

Choose **one** generation for the exact species/form: Gen 9 when it has literal
Gen-9 level-up sources, otherwise its newest earlier coherent level-up dataset.
Older-only moves never survive merely because they were once level-up moves.
Own older-generation form data takes precedence over a newer base dataset.

Missing literal form data may follow explicit `changesFrom` / `battleOnly`, or
the pinned source's missing-literal `forme` / `baseSpecies` path. All possible
explicit battle parents must agree. Never combine pre-evolution, event,
restricted (`R`), machine or tutor sources into a level-up dataset. Reviewed
local ownership exceptions are enumerated and locked separately; no prefix
guessing. These are learnset representations, not transformation implementation.

Showdown's `nLlevel` strings do not encode order within a level. Preserve
canonical relative order of surviving exact level/move pairs and append new
same-level pairs in source property order. This minimizes initial-move changes
without retaining any older-only move.

`coherent-learnsets-provenance.json` locks reference files, both alias policies,
canonical inputs and all 822 approved table-body hashes. Every one of the 1,440
pointer slots is accounted for in `coherent-learnset-consumers.jsonl`, including
selected generation, exact local target, source ancestry and profile disposition.

## Final whole-pilot inventory

| Class | Count | Unit / disposition |
| --- | ---: | --- |
| SAFE_DATA_DIFF | 0 | No remaining approved data or pointer diff |
| NO_DIFF | 2381 | 1293 comparable approved base rows + 1088 tables, including sentinel |
| SHARED_TABLE_CONFLICT | 0 | Both distinct-data families safely split |
| FORM_MAPPING_BLOCK | 88 | 87 general source mappings + Shadow Warrior local table |
| MOVE_BEHAVIOR_BLOCK | 18 | Ally Switch has no approved existing move mapping; tables unchanged |
| ABILITY_BEHAVIOR_BLOCK | 44 | Existing unsupported/blocked assignment slots unchanged |
| NO_L1_PATH | 0 | Non-sentinel active targets; structural initial-move path |
| UNBOUND_POINTER | 0 | All 1440 source array slots bound |

These are typed inventory rows, not species counts. 1,106 non-sentinel targets
have a structural L1 path; 1,087 have fully reconciled coherent source legality.
The 18 move-blocked tables and Shadow Warrior retain legacy data: do not claim
they are current-data certified. The 27 NONE/EGG/reserved sentinel bindings must
not be random encounter selections. Custom pre-evolution markers, Surfing/Flying
Pikachu and Zygarde Cell/Core have explicit excluded-form dispositions; their
existing shared ownership does not establish mainline form/battle support.

## Verification completed

- 27 synthetic helper regressions: one-generation selection, older exact forms,
  source inheritance/cycles/multiple parents, rejected aliases/abilities/moves,
  shared conflicts, explicit split/binding rendering, bounds and no-write failures.
- Exact deterministic whole-file replay from canonical source, including the
  eight pointer changes; every other source byte preserved.
- ARM syntax using repository CFLAGS.
- Actual `GiveBoxMonInitialMoveset` at every level 1–100 for every ID: **144,000
  cases**, address/undefined/bounds sanitizers; zero null pointers and zero
  non-sentinel no-L1 paths. This covers all low levels and both sides of every
  in-range level boundary, including level-0/start entries at level 1.
- Exact data ownership guard plus five negative mutations; M-009 source/frame
  ownership, compiled scanner and eight negative preflight cases; diff checks.

Run source-only regressions from the CFRU root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_coherent_learnsets.py
PYTHONDONTWRITEBYTECODE=1 python3 -c 'import sys; sys.path.insert(0,"scripts"); import check_hidden_item_sparkle as c; c.check_source_contract(); c.check_host_algorithm(); c.check_rejections()'
arm-none-eabi-gcc -mthumb -mno-thumb-interwork -mcpu=arm7tdmi -mtune=arm7tdmi -mno-long-calls -march=armv4t -Wall -Wextra -Os -fira-loop-pressure -fipa-pta -fsyntax-only src/Tables/level_up_learnsets.c
git diff --check
```

## Remaining gates

Full clean source/link build: **BLOCKED**, not passed. Native macOS
`scripts/build.py` invokes `wav2agb` and `mid2agb` by executable name through
PATH; neither is available in the session. No converter download, install,
copy, environment workaround, or missing-mechanic patch was performed. Once
the approved toolchain exists, use a fresh complete isolated source checkout:

```sh
for tool in arm-none-eabi-gcc arm-none-eabi-as arm-none-eabi-ld arm-none-eabi-objcopy grit wav2agb mid2agb; do
  command -v "$tool" || exit 1
done
python3 scripts/build.py
```

Do not run the ROM insertion wrapper as part of this source-only preflight.
Do not submit build/ROM/save/state files: a sanitized command/result record is
sufficient evidence.

User runtime acceptance remains required: fresh low-level encounters/starters,
all eight resolved families, Dialga/Origin, Sandshrew, Litleo, Zarude/Dada,
boundary level-ups and Move Reminder, transformed-form display/crash sanity,
save/reload and randomized-output smoke with unsupported profiles excluded.
Source memory safety is not full random-selection, battle-mechanic, playthrough
or ROM-freeze certification.

Independent canonical baseline from CFRU #45. Combining #45 with this candidate
requires a separately reviewed integration that retains **both** exact preflight
guards, then a fresh build and runtime matrix. Do not merge #46 or old #47 into
this data candidate. No merge or pin update was performed.
