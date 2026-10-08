# Evolution runtime compatibility v1 — Workspace #722

Contract: [Workspace #722](https://github.com/Planton361/firered-gen9-randomizer-workspace/issues/722).
Dependency: [blocked UPR #721](https://github.com/Planton361/firered-gen9-randomizer-workspace/issues/721).
This is a CFRU source candidate, not output/gameplay acceptance or UPR support.

## Exact source basis and Stage A findings

- CFRU base: `e68a701aa4e68733ef8ad1e7cadb68825c0d16c2`, tree
  `ee1272f41ccc6f30d3fb5ed36d54d1df0db5fd1c`.
- DPE: `d887185de1f6ae6a78e85c4311bbadde17041d00`.
- Selected UPR: `4670a5413104ec02bc08c09ff584470a8a6cb7bd`; unchanged.
- Workspace: `9411c39f472d1d08555be988d2f7ab9482902580`; unchanged.

**CONFIRMED CURRENT STATE, public source:** CFRU/DPE method names at IDs 0–39
are identical. DPE appends exactly 40/41/42. Its actual four slots are:

| Source ID | Method | param | Target ID | unknown |
|---|---|---|---|---|
| `0x574` Gimmighoul | 40 | 2999 | `0x576` Gholdengo | 0 |
| `0x575` Gimmighoul Roaming | 40 | 2999 | `0x576` Gholdengo | 0 |
| `0x521` Tandemaus | 41 | 25 | `0x522` Maushold (three) | 0 |
| `0x521` Tandemaus | 42 | 25 | `0x523` Maushold Four | 0 |

These numeric species definitions match CFRU. DPE's Base Stats, Front/Back Pic
and Icon *source tables* contain both Maushold forms and Gholdengo. No asset
binary or rendered form has been inspected; appearance remains user-owned.

`GetCoins()` is defined in `src/scripting.c` and hooked at `0x080D0554`.
With selected `SAVE_BLOCK_EXPANSION` and `MAX_COINS_DIGITS=9`, it reads the
existing u32 `gPlayerCoins` at `0x0203B814`, with normal wallet maximum
999999999. `scrB3_CheckCoins` uses the same getter. The existing save parasite
starts at `0x0203B174` and covers that counter. Without expansion the getter
reads the existing u16 `gSaveBlock1->coins`, with normal maximum 9999.
Neither the old u16 field nor the command's saturated u16 export is used by
evolution. No new counter, item inventory, save field, deduction or clamping
is introduced. Raw extreme counter values retain the getter's read semantics.

The existing hook is `GetEvolutionTargetSpecies 08042EC4 3`. Inserter `Hook`
writes `00 4B 18 47` followed by the selected consumer's Thumb pointer at ROM
offset `0x42EC8`. Ordinary assembly `**/*.s` discovery, linker `*(.text)` and
binary insertion already retain the new external data record. There is no
wrapper, dispatch change, new fixed-ROM repoint, or linker/inserter edit.
External assembly ownership plus a `const volatile` C declaration prevents
the live threshold read being folded into a source constant. This is source
feasibility evidence; ARM relocation/output ownership is not yet verified.

## Runtime and helper semantics

Only `EVO_MODE_NORMAL` evaluates the new methods. Existing Everstone handling,
trade/item checks, item-removal flags, Silvally adjustment and slot iteration
remain intact. Normal mode is called for level-up, Rare Candy checks and,
if separately configured, the existing mid-battle level-up path. It is not
a new overworld poll or a battle-end-without-level-up trigger.

- 40: `GetCoins() >= param`, without changing coins, items or personality.
- 41: `level >= param && personality % 100 == 0`.
- 42: `level >= param && personality % 100 != 0`.

The latter predicates use the existing complete u32 personality, not its
upper half and not RNG. They are exclusive for the two DPE slots, so their
order does not affect the selected form. Targets always come from the row;
UPR's separately owned target-only plans and auxiliary fields remain intact.

`EvolutionMethodRequiresLevelUp` includes all three. `GetMinimumLevel`
explicitly classifies 41/42 as having a param level threshold.
40 is excluded from that threshold path: its 2999 must never become a u8
minimum level. Thus `GetMinimumLevel`
retains its ordinary ancestry rule: the two Maushold forms require 25;
Gholdengo requires one level-up beyond Gimmighoul's minimum (2 for these rows).
Existing method groups and split evolutions are unchanged.

`IsLevelUpEvolutionMethod` retains its existing grouping. The existing
`src/util.c` helpers are approximate metadata consumers:
`CouldHaveEvolvedViaLevelUp` tests level thresholds for EXP policy, while
`EvolveSpeciesByLevel` synthesizes a species by selecting the first eligible
row without a personality/coin input. As with its legacy Silcoon/Cascoon
branches, it is not the identity-aware normal evolution evaluator. Adding
41/42 to that generic grouping would incorrectly force the first Maushold form
in selected trainer scaling (`SCALED_TRAINERS`). Therefore all three new methods
are kept outside the generic level/other/item/friendship groups. Species-only
trainer synthesis and that EXP heuristic retain their baseline handling of
these rows. Identity-aware normal evolution and the distinct minimum-level
classification support the new methods. Personality-aware forced trainer
synthesis would require a separate contract; none is claimed here.

## Consumer-owned friendship data contract

The sole source owner is `assembly/data/evolution_friendship_anchor.s`;
the sole runtime reader is the accessor in `src/evolution.c`, called once
in normal mode. All four predicates (1/2/3 and friendship-required 17) use
that same read. Day/Night gates, known move type and the row's `unknown`
friendship-required flag are unchanged, including non-time builds.

The aligned 32-byte record is ARM little-endian:

| Offset | Width | Required value |
|---|---|---|
| 0 | 8 | ASCII `CFRUEVO1` |
| 8 | 4 | record's own absolute GBA ROM address |
| 12 | 4 | live `GetEvolutionTargetSpecies` Thumb pointer |
| 16 | 2 | version 1 |
| 18 | 2 | record size 32 |
| 20 | 2 | threshold offset 28 |
| 22 | 2 | threshold width 1 |
| 24 | 2 | default 220 |
| 26 | 2 | optional value 160 |
| 28 | 1 | live threshold, initially 220 |
| 29 | 1 | reserved zero |
| 30 | 2 | reserved zero |

The only authorized future write is byte 28 to 160 or 220. The engine falls
back to 220 for any other byte value. This fallback is not permission for a
future writer to accept corrupt records. Header fields are discovery metadata;
the engine does not perform output identity/preflight checks.

**INTENDED FUTURE STATE, separate UPR #721 contract:** locate only within the
independently accepted CFRU insertion extent for an accepted candidate build.
Require exactly one record identity; verify alignment, whole-record bounds,
all immutable fields/reserved zeros, exact self address, and consumer equality
with the live hook at `0x42EC4`. Require an in-range Thumb consumer in the
accepted code-owner interval. Independently reject overlap of the record with
consumer code, evolution rows, another descriptor, Pickup data and any other
owned code/data range. Verify the current byte is 220 or 160 before planning
the one-byte write, then read it back and preserve every other byte.

Signature matching by itself is never sufficient. A consumer pointer alone
does not certify that arbitrary code reads the record: the reviewed source
candidate and fresh local build/output witness establish the source-to-output
binding. Unknown revisions/layouts, missing/duplicate records, unrelated or
broken hooks, wrong pointers and incomplete ownership evidence must fail before
any write. This requires no general Thumb CFG or whole-inserter oracle.
No production UPR locator/patcher is delivered here.

## ROM-free verification and remaining evidence

Run from this source-only CFRU checkout with the exact public DPE source:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/tests/test_evolution_runtime_compat.py --dpe-root /path/to/public/DPE -v
```

17 unittest cases pass. They execute extracted C predicates in a bounded
Python model and synthetic data/hook fixtures, including coins 2998/2999,
full-width and mismatched counters, Tandemaus 24/25 and personalities
0/1/99/100 plus extremes, repetition/ordering, all four friendship consumers
at 159/160/219/220 and both thresholds, Fairy move/unknown/time controls,
invalid threshold fallback, classifier/minimum-level rules, and negative
descriptor/hook/bounds/collision/overlap/atomicity cases. Original enum/row
identity and original C function bodies are compared with the exact base.
The Hook fixture executes only the existing Python function on fresh BytesIO.

Classification: **source/model evidence**, not compiled-C execution, ARM
build/link evidence, output randomization, or gameplay. No ROM, build, ELF,
object or tool binary is created/read by this suite. The tests do not execute
every legacy C method, rendering, save persistence or the native inserter.

All private build/output/runtime gates are **NOT_RUN**. Later user-owned
acceptance must bind exact CFRU head/tree, DPE/config/toolchain and selected
UPR/output revisions; verify fresh relocation, one live record and its code/data
ownership without overlap; compare default and patched output bytes; witness
friendship/Day/Night/Sylveon controls, both Gimmighoul rows at 2998/2999 with
unchanged balance, both Tandemaus forms at 24/25 and deterministic personality
selection; test repeated evaluation/cancel, Everstone, Rare Candy, normal
level-up, trainer scaling controls, save/reload and representative legacy
split/item/trade evolutions. Report only sanitized revision-bound results.

`CFRU_EVOLUTION_RUNTIME_COMPAT=NOT_YET` and
`EVOLUTION_EASIER_RANDOM_READY=NOT_YET` remain the acceptance statuses.
Pickup #75/#198, product pins/Gitlinks and all other repositories are unchanged.
No merge or integration is authorized by this document.
