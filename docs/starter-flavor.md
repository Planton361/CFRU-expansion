# F02 — starter flavor removal

Contract: [Workspace #595](https://github.com/Planton361/firered-gen9-randomizer-workspace/issues/595).
**CONFIRMED USER DECISION:** omit only
`PalletTown_ProfessorOaksLab_Text_OakThisMonIsEnergetic` after starter YES.
**CONFIRMED SOURCE IMPLEMENTATION:** three explicit YES repoints to a bounded
script; runtime acceptance remains separate.

Base: `20b58bd980f55d57faf78ff29922b98874a4df22`.
Branch: `qol/595-starter-flavor`.
PR target: `compat/firered-gen9-randomizer`.
The existing persistent Workspace was clean on current main
`f3ff648b74fef1bae4725863605638d260c85f2b`; its clean CFRU checkout was at the
exact base before creating the component branch. No separate worktree was used.

## Source owner and binding

Structural reference: pret/pokefirered
`e060ab955b5dc9ac1c4904c2cd141683615cf477`,
`data/maps/PalletTown_ProfessorOaksLab/scripts.inc`.
Its ancestor `44c9109c2a04fbbf01268f53f0f4a57174563fb1` retains original BPRE
address annotations in that same source file:

| Entry / operand | BPRE address | Source derivation |
|---|---|---|
| First confirmation | `0x08169C14` | Bulbasaur prompt |
| First YES pointer | `0x08169C23` | entry + msgbox 8 + compare 5 + goto_if header 2 |
| Second confirmation | `0x08169C33` | Squirtle prompt |
| Second YES pointer | `0x08169C42` | same command widths |
| Third confirmation | `0x08169C52` | Charmander prompt |
| Third YES pointer | `0x08169C61` | same command widths |
| ChoseStarter | `0x08169C74` | explicit original source label |
| Retained restore/award tail | `0x08169C80` | entry + hide 1 + removeobject 3 + msgbox 8 |

Historical confirmation labels for Squirtle and Charmander were swapped;
their text operands identify the choices, and the pinned modern source has
corrected labels. Addresses above follow the historical source instructions,
not those misleading old names. Historical Rival movement labels have the
same naming caveat; the modern reference establishes the intended mapping.

The ancestor's `asm/macros/event.inc` proves the widths: msgbox expands to
loadword (opcode + bank + pointer = 6) and callstd (opcode + index = 2);
compare-to-value is 5; goto_if is opcode + condition + pointer = 6;
erasemonpic is 1; same-map removeobject is opcode + local-ID/variable = 3.
All three original YES branches target ChoseStarter; all three NO branches
target DeclinedStarter (`hidemonpic`, `release`, `end`) for normal retry.

At the accepted CFRU base, tracked source patch manifests have no competing
owner in the starter selection/award/nickname/Rival region. Existing M-006
map overlays replace scene-1 OnWarp/OnFrame behavior, not the starter ball
objects or their confirmation scripts. Existing Sign Lady and Parcel source
remain unchanged.

The existing `repoints` mechanism in `scripts/insert.py` writes an explicit
four-byte script pointer through `Repoint`, with no Thumb bit. The three added
rows change only YES operands. This avoids a broad pointer search or an
in-place script-opcode rewrite. `scripts/build.py` already discovers assembly
recursively; no build-system change is needed.

## Exact behavior

Old: confirmation YES → original ChoseStarter → hide picture → remove selected
ball (`VAR_LAST_TALKED`) → energetic flavor msgbox → restore previous text
color → Pokémon/Sign Lady flags → give runtime-selected species at level 5 →
copy starter number → received-Pokémon message/fanfare → nickname YES/NO →
RivalPicksStarter → Rival receives counter-starter → scene 3 / Sign Lady state.

New: confirmation YES → EventScript_ChoseStarterNoFlavor → hide picture →
remove selected ball (`LASTTALKED`, the same `0x800F` variable) → goto original
`0x08169C80` restore/award tail → exactly the same remaining flow.

Only the energetic msgbox is omitted. The original tail retains:

- `FLAG_SYS_POKEMON_GET` and `FLAG_PALLET_LADY_NOT_BLOCKING_SIGN`;
- `givemon PLAYER_STARTER_SPECIES, 5` and
  `copyvar VAR_STARTER_MON, PLAYER_STARTER_NUM`;
- species-name buffering, normal received-Pokémon acknowledgement and fanfare;
- nickname YES → existing nickname helper for party slot 0 → RivalPicksStarter;
- nickname NO → RivalPicksStarter directly;
- player slots 0/1/2 → Rival Charmander/Bulbasaur/Squirtle slot paths;
- Rival object removal, acknowledgement, scene 3 and conditional Sign Lady state.

These are existing slot relationships, not fixed species in the new award path.
The replacement never writes species/selection variables or grants a Pokémon;
the original runtime/randomizer-owned grant executes exactly once. Existing
Rival battle dispatch consumes `VAR_STARTER_MON`; battle, Lab exit and M-007
Parcel progression receive no edits. No SaveBlock, ABI or persistent layout
change occurs. ROM insertion adds script code in existing expansion space and
changes only three pointers; no new allocation/layout scheme is introduced.

## ROM-free verification

From CFRU:

```sh
python3 scripts/tests/check_starter_flavor.py --pret-root ../references/pret-pokefirered
python3 -O scripts/tests/check_starter_flavor.py --pret-root ../references/pret-pokefirered
git diff --check
git status --short
git diff --stat
```

The focused checker reads exact pinned Git source objects, proves ancestry,
address labels, command widths, all three YES/NO paths, original award/nickname
tail, Rival selection/battle mapping and scene/Sign Lady continuations. It
requires exact manifest additions and replacement commands, rejects scope
outside the four changed files, and rejects nine in-memory negative witnesses:
each YES pointer shifted or missing, continuation shifted, selected-ball
variable replaced by a fixed object, and an extra fixed-species grant. Checks
remain active under Python optimization. Existing insertion/build source and
all other component source must remain unchanged relative to the exact base.

Changed files: `assembly/overworld_scripts/starter_flavor.s`, `repoints`,
`scripts/tests/check_starter_flavor.py`, `docs/starter-flavor.md`.

**UNKNOWN:** actual presentation, all three randomized starter grants, nickname
YES/NO runtime, Rival battle win/loss, Lab exit/Parcel and save/reload until
user-owned runtime acceptance after component review and separate Workspace
integration. Source preservation does not claim runtime PASS. **CONFLICT:** none
identified. No ROM, save, emulator state, build, tool binary, private artifact
or secret is accessed. No DPE, UPR-FVX, Workspace Gitlink, F03/F04/F05, D03,
additional Oak intro or upstream contribution work. No merge.
`UPSTREAM_CONTRIBUTION = DEFERRED`.
