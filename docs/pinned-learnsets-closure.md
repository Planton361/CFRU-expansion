# Bounded pinned-reference learnset candidate

Base: canonical CFRU `827fa1ef04bd43e5c6bad5c47f7d8690ea6823ec`.
NEW reference: [Pokemon Showdown b1156ff19204e48089e2384eb2c9c1a8004f57ce](https://github.com/smogon/pokemon-showdown/tree/b1156ff19204e48089e2384eb2c9c1a8004f57ce).
The historical sync revision is UNKNOWN. This candidate does not use CFRU #46.

89 active CFRU level-up tables receive only unambiguous data updates. The
workspace's hardened planner audits all generations and every shared consumer
before writing; all 89 targets have nonempty, sorted levels 0–100, at most 50
rows and valid move IDs with a level-1 path. Its selection policy is the existing
latest generation **per move**, retaining older-generation-only moves, with
Showdown property order for equal levels. This is not a strict Scarlet/Violet
legal-moveset claim. Order-only differences remain blocked for explicit review.

The exact alias configuration SHA-256 and before/after source digests are in
`pinned-learnsets-provenance.json`. The workspace reference lock also fixes all
four Showdown source file hashes and approved Base Stats fields. No safe DPE
field differences exist, so DPE is untouched. No move effects, ability effects,
form mechanics, constants, pointer table, shops or other QoL code changes.

Post-write dry run: **0 SAFE_DATA_DIFF**. The whole candidate file also matches
an independent replay of the canonical source through the hardened planner,
byte for byte. Every blocked table and all text outside the selected bodies is
unchanged. The original inline terminator is preserved, including its suffix.

## Remaining source gates — not feature complete

Eight conflicting shared targets stay blocked: Pikachu, Pichu, Rotom, Zygarde,
Necrozma, Magearna, Zacian and Zamazenta. Missing/empty literal form data is not
treated as permission to erase a table or inherit the base form. No fallback
move or new form mapping was invented.

The five families restored historically by #46 **all differ** from the new
reference. #46 is superseded for modern-data closure, not merged or reused.
The five empty baseline tables remain blocked. Dialga still begins at level 50
because its Origin-form shared target has no resolved literal expectation;
Zygarde still begins at 80. These seven non-sentinel targets cover 38 source
species/form bindings. Sandshrew's missing level-1 moves (previously first move
at 27) and Litleo's missing level-1 moves (previously first at 5) are repaired.

There is also an unchanged missing pointer at species ID **1209,
SPECIES_ZARUDE_DADA**. Passing it to the initial-moveset function risks a null
table dereference; it must not be treated as confirmed safe to encounter.
The planner reports it as blocked form mapping, not a safe inferred alias.
These are source/data gates, not issues that can be dismissed by a runtime PASS.

Of 1,105 active table targets, 1,097 pass the structural L1 check after this
candidate; the remaining eight include the intentional NONE/EGG/reserved
sentinel. Only 915 have fully resolved literal-reference agreement. Structural
nonemptiness alone is not proof of source legality for unresolved forms.

## Validation and integration

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/check_pinned_learnsets.py
PYTHONDONTWRITEBYTECODE=1 python3 -c 'import sys; sys.path.insert(0,"scripts"); import check_hidden_item_sparkle as c; c.check_source_contract(); c.check_host_algorithm(); c.check_rejections()'
arm-none-eabi-gcc -mthumb -mno-thumb-interwork -mcpu=arm7tdmi -mtune=arm7tdmi -mno-long-calls -march=armv4t -Wall -Wextra -Os -fira-loop-pressure -fipa-pta -fsyntax-only src/Tables/level_up_learnsets.c
git diff --check
```

Passed: exact 89-table/source ownership; rejected unapproved mutations; ARM
syntax; actual `GiveBoxMonInitialMoveset` with synthetic box services for
143,900 species/level cases under address/undefined/bounds sanitizers. The host
test uses the normal pilot path, with the optional in-engine shuffle flag off.
It reports 65 bindings without L1 moves (38 species/forms plus 27 sentinel
bindings), and the one missing pointer; it does not conceal or repair them.
M-009 ownership, compiled scanner and eight negative checks passed.

`check_hidden_item_sparkle.py` gains only the narrow data/test allowlist and an
exact-source preflight call. It retains the M-001–M-009 restrictions and checks
before insertion can access input. This is a required compatibility dependency
of the existing fail-closed preflight, not a frame/scanner change.

Full clean source build is gated: native macOS `scripts/build.py` invokes
`wav2agb` and `mid2agb` by name through PATH; both are unavailable. No converter
was downloaded, installed, copied or patched around. ARM syntax/host checks are
not a linked build. No ROM/save/state or generated build was accessed.

Once approved converters exist, complete a clean/full CFRU source build, then
user runtime checks of initial moves, level progression and menus for all
changed families (particularly Sandshrew, Litleo, Raichu, Decidueye-H and Gen9
starters). Check old-only move retention, equal-level initial last-four order,
level-0 evolution moves, form displays and randomized low-level encounters.
Do not randomize unresolved families into encounters as an acceptance shortcut.

Draft only. Data work starts from canonical pilot, independently of #45.
Combining with #45 requires an explicit merge/rebase integration review of both
preflight extensions, retaining both checks, and a new full build. Do not apply
#46 on top. No merge or component pin update is performed here.
