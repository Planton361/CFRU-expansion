# #727 CFRU Oak Intro ABI v1 — Stage A source candidate

Authority: [Workspace #727, Stage A authorization](https://github.com/Planton361/firered-gen9-randomizer-workspace/issues/727#issuecomment-6318621103).
Base: CFRU Draft #77 `e27e2113e4d59dc76cf5da8d4c43b067addae348`,
branch `integration/726-cfru-pickup-evolution`. Implementation branch:
`fix/727-cfru-oak-intro-abi-v1`. Exactly five authorized source/test/doc files.
No DPE/UPR implementation, hook, linker, inserter, Pickup/Evolution or Gitlink
change. Never merge this candidate from an agent.

Safety-repair authority: [CONTROL same-contract repair](https://github.com/Planton361/firered-gen9-randomizer-workspace/issues/727#issuecomment-6319777043).
Repair base is `fda64ec5068f5adcad7685001854854d14e1d509` on the same branch.
Only the selector helper in `src/scripting.c`, its existing ABI test file and
this document change in the repair. Header, 96-byte record, selector write
budget, bitmap, both bridges, both actual consumers and intro flow remain
source-identical to that repair base.

**CONFIRMED CURRENT STATE — source only:** one assembly-owned descriptor, one
immutable bitmap, two real bridges, two distinct C consumers. Tests below
exercise public text and constructed memory. **UNKNOWN:** emitted instruction
bytes, relocation, selected insertion ranges, output provenance, runtime.
`ABI_PROVENANCE_BLOCKED`; no support/runtime or original private-failure claim.

## Wire record

`include/new/oak_intro.h` defines `struct OakIntroContractV1`.
`assembly/data/oak_intro_contract.s` owns `gOakIntroContract`, an ARM
little-endian, 4-aligned 96-byte object in the existing `.text` image.
The header asserts every field offset, total size, alignment, pointer/scalar
widths and native row layouts; assembly asserts record/bridge/bitmap sizes.
A `const volatile` external declaration prevents folding the selected u16.

| Byte | Width | Field / v1 value |
| --- | --- | --- |
| 0 | 8 | `identity`: ASCII `CFROAK01` |
| 8 | 4 | `self`: `gOakIntroContract` |
| 12 | 2 | `version`: 1 |
| 14 | 2 | `size`: 96 |
| 16 | 4 | `profile`: 1, selected native CFRU/DPE Gen 1–9 source profile |
| 20 | 2 | `speciesCapacity`: 1440, including reserved slot zero |
| 22 | 2 | `defaultSpecies`: 29, native Nidoran♀ |
| 24 | 2 | `selectorOffset`: 92 |
| 26 | 2 | `selectorWidth`: 2 |
| 28 | 4 | `eligibility`: `gOakIntroEligibility` |
| 32 | 2 | `eligibilityBytes`: 180 |
| 34 | 2 | `policyVersion`: 1 |
| 36 | 4 | `spriteBridge`: Thumb `CreateOakIntroPokemonSprite` |
| 40 | 4 | `spriteConsumer`: Thumb `OakIntroSpriteConsumer` |
| 44 | 4 | `cryBridge`: Thumb `Task_OakSpeech_IsInhabitedFarAndWide` |
| 48 | 4 | `cryConsumer`: Thumb `OakIntroCryConsumer` |
| 52 | 4 | `frontTablePointerSlot`: existing public DPE root `0x08000128` |
| 56 | 4 | `paletteTablePointerSlot`: existing normal-palette root `0x08000130` |
| 60 | 2 | `frontRowSize`: 8 (pointer, u16 decompressed size, u16 tag) |
| 62 | 2 | `paletteRowSize`: 8 (pointer, u16 tag, padding/unused u16) |
| 64 | 2 | `bridgeSize`: 28 |
| 66 | 2 | `bridgeDescriptorOffset`: 20 |
| 68 | 2 | `bridgeConsumerOffset`: 24 |
| 70 | 2 | `pointerWidth`: 4 |
| 72 | 20 | `reserved`: all zero |
| 92 | 2 | `selectedSpecies`: native ID, initially 29; only future write budget |
| 94 | 2 | `reservedTail`: zero |

These roots identify existing public pointer slots, **not new descriptor or
asset locations**. Tables must still be resolved from the actual selected
output, validated and protected by the later independent witness.

Only `[92,94)` may be changed by a separately authorized future UPR integration.
Everything else, including the entire 180-byte bitmap, bridges, C consumers,
loaded table rows/assets and template infrastructure, is immutable to that
writer. This is a source ownership contract, not hardware write protection.
Version/profile/magic alone never authorize discovery or a write. A copied
record, duplicate definition, stale consumer, bad Thumb bit, wrong root,
changed constant, owner alias or interval overlap must fail external preflight.
No Stage B production locator/writer is implemented here.

## Actual symbol and argument paths

Unchanged `functionrewrites` entries:

- `CreateOakIntroPokemonSprite 0x08130f2c 0 1`
- `Task_OakSpeech_IsInhabitedFarAndWide 0x0812fa78 0 1`

Their former C definitions in `src/scripting.c` are renamed to the distinct
`OakIntroSpriteConsumer` and `OakIntroCryConsumer`. Only assembly defines the
public entry symbols. Each bridge calls its matching C consumer as
`void consumer(u8 taskId, const volatile struct OakIntroContractV1 *intro)`:
`r0` retains the task ID; `r1` receives the same `gOakIntroContract`; `r3`
receives that bridge's C function address. Both C functions pass `intro` to
`OakIntroSelectedSpecies`; neither uses a private selection or a replacement
Nidoran♀ row. The repaired helper establishes `intro == &gOakIntroContract`
before any record dereference. A foreign, null, copied or unaligned address
returns the **compiled** default 29 without reading the supplied record.

At the known record, runtime C checks all immutable metadata against compiled
expectations: all eight identity bytes; self pointer; ABI version, size,
profile and native capacity; default species; selector offset/width;
eligibility pointer, byte count and policy version; both bridge and both
consumer addresses; both table-pointer-slot numbers; native row sizes; bridge
size/literal offsets; pointer width; every reserved byte and reserved tail.
The loops use compiled `sizeof` bounds, never a size read from the record.
Pointer fields are compared with known symbols only: **no stored pointer is
dereferenced or called**, even after comparison. The public table-slot numbers
are compared as integers; this does not validate their installed contents.

Any mismatch returns `OAK_INTRO_DEFAULT_SPECIES`, not `intro->defaultSpecies`,
before reading `selectedSpecies` or the bitmap. Only a valid immutable header
allows the volatile u16 selector read. The fixed compiled 1440 bound is checked
before indexing the source-owned `gOakIntroEligibility` directly; the helper
never follows `intro->eligibility`. Invalid selections also return 29. This
repair does not rehash bitmap payloads or prove installed asset/table contents;
the source-owned bitmap is unchanged and full link/output ownership remains
a separate external preflight/witness requirement.

Each bridge is 4-aligned and declares `.thumb_func` / `%function`:

| Relative byte | Instruction / modeled Thumb halfword |
| --- | --- |
| 0 | `push {r4,lr}` / `b510` |
| 2 | `ldr r1,[pc,#16]` / `4904`, descriptor literal at +20 |
| 4 | `ldr r3,[pc,#16]` / `4b04`, consumer literal at +24 |
| 6 | local `bl` to +16 / `f000 f803` |
| 10 | `pop {r4}` / `bc10` |
| 12 | `pop {r0}` / `bc01`, saved caller LR; void return |
| 14 | `bx r0` / `4700` |
| 16 | `bx r3` / `4718` |
| 18 | `nop` / `46c0` |
| 20 | descriptor pointer relocation |
| 24 | matching Thumb C consumer relocation |

The local BL gives the C callee a Thumb return at +10. BX permits the
indirect Thumb-1 call without ARMv5 BLX. The 8-byte push preserves alignment
and original LR even when C clobbers r0–r3/r12/LR; r4 is preserved. Returning
through the saved LR retains its instruction-set bit. `.word consumer`
relies on the actual toolchain supplying Thumb function relocations; these
source words are **not** measured machine code.

The existing `scripts/insert.py::FunctionWrap` for the unchanged `0 1` rows
pushes r4/LR (8 bytes), loads its target into r4 and calls through BX r4;
it does not overwrite r0. It returns via saved LR in r1. The nested new bridge
adds another 8 bytes. The legacy wrapper's returning flag remains untouched;
these actual C consumers remain void. No emitted wrapper or hook bytes were
read. Missing symbols are especially significant because the existing
inserter can print and continue for these legacy entries; source regressions
therefore require unique definitions and both connections explicitly.

`scripts/build.py` already recursively collects `assembly/**/*.s` and C,
uses Thumb/ARMv4T C flags, and `linker.ld` includes `.text`. The new basename
is unique. No build infrastructure change is required by the source graph.
Actual symbol resolution, reachability and placement remain unproved.

## Sprite, palette and lifecycle

`OakIntroSpriteConsumer` reads the current complete native front-sheet row
and normal-palette row for the selected ID. `LoadCompressedSpriteSheetUsingHeap`
consumes the row's data, size and tag; no 2048-byte frame size is invented in
the consumer. `LoadCompressedSpritePaletteUsingHeap` receives the typed normal
row. Existing `SetMultiuseSpriteTemplateToPokemon` supplies the original
OAM, animations and affine setup. Its existing long-lived RAM
`gMultiuseSpriteTemplate` gets the actual sheet tag, the **palette row's tag**,
and `images = NULL` for the tagged-sheet path. No stack template or additional
persistent writable global is introduced. In particular native Unown B–?
front tags remain their native IDs, while their normal palette tag is the
shared base `SPECIES_UNOWN=201`.

The single `CreateSprite(...,96,96,1)`, dummy callback, priority, invisible
flag and task data[4] assignment remain source-identical. The existing minimal
exposition destroys that hidden sprite exactly once, and still bypasses its
visible release/cry/return sequence. Tagged sheet tiles now live until the
scene's existing `ResetSpriteData` (including naming-screen return); palette
lifetime remains the existing scene's `FreeAllSpritePalettes`. This resource
change is explicit: unlike the old per-sprite image path, `DestroySprite`
alone does not release a tagged sheet. No extra cleanup hook was added.
Allocation/resource-pressure behavior and lifetime through actual character
creation require later user-only runtime controls; the inherited assumptions
that sprite/palette allocation succeeds have not been expanded into a new
failure-recovery flow.

`OakIntroCryConsumer` preserves the existing message, timer and task transition
and changes only the species argument to `PlayCry1` to the same shared
selection. The shortened flow does not invoke it visibly. `CRY_SPECIES` and
`SetTitleScreenScene_Cry` remain separate and source-identical. The legacy
`OAK_INTRO_SPECIES` definition remains unchanged but no longer selects either
Oak consumer: the descriptor is the single v1 owner, default native ID 29.
Shared Poke Ball/Trade handling in `src/catching.c` remains untouched.

Public structural reference for loader/template/reset/destroy semantics:
[pret FireRed source at e060ab9](https://github.com/pret/pokefirered/tree/e060ab955b5dc9ac1c4904c2cd141683615cf477/src),
`decompress.c`, `pokemon.c`, `sprite.c`, `oak_speech.c`. This reference explains
source behavior; it does not prove the selected output implementation.

## Immutable eligibility policy v1

Derivation uses exact public DPE
[`d887185de1f6ae6a78e85c4311bbadde17041d00`](https://github.com/Planton361/Dynamic-Pokemon-Expansion-Gen-9/tree/d887185de1f6ae6a78e85c4311bbadde17041d00):
`include/species.h`, `include/sprite_data.h`, `src/Front_Pic_Table.c`,
`src/Palette_Table.c`, `src/Species_To_Pokdex_Table.c`, both native cry tables, and **only tree names**
under `graphics/frontspr`. No PNG content or generated graphics are read.
The native pilot category policy is independently extracted in tests from
[`SpecialFormPredicates.cfruDpePoolCategory` at UPR #218](https://github.com/Planton361/universal-pokemon-randomizer-fvx/blob/e1127cfde58af359e458f8d6a19339f3db3c8589/romio/src/main/java/com/uprfvx/romio/services/SpecialFormPredicates.java).
No UPR behavior is changed by this CFRU policy. All eligible IDs also have
explicit `.wav` source entries in both DPE cry tables; those declarations do
not prove decoded cry contents or runtime sound.

The 180 bytes cover exactly slots 0..1439, LSB first: bit `id & 7` in byte
`id >> 3`. **1250 eligible IDs**, not a contiguous range. An ID is eligible
only when all these source premises hold:

1. Native positive ID <=1439; not 252..276 legacy placeholders or 412 Egg/
   Bad Egg sentinel. The source declares `NUM_SPECIES=1440` including slot 0.
2. Pilot category is ordinary, regional or persistent alternate. Reject
   missing-source rows, Mega, Primal, G-Max, Eternamax, Tera transformations,
   temporary battle/ability forms, and item/move/time/PC-dependent forms.
3. Explicit front and normal-palette table rows, declared asset symbols,
   native-to-Dex mapping and corresponding tracked public front asset names
   exist. Front tag must equal its native ID; palette tag comes from its row.
   The selected public rows declare `(64*64)/2`; consumers nevertheless use
   the row metadata rather than substitute a hardcoded frame size.
4. Intro-specific exclusions: Deoxys native 410, Attack 1040, Defense 1041,
   Speed 1042 remain unsupported by v1. Vanilla Deoxys tile duplication and
   selected compressed-frame/runtime semantics are not established. The
   complete-sheet path does not silently assume these four forms work.
   Castform native 385 has declared rows but no matching tracked
   `gFrontSprite385Castform` asset in this exact DPE tree: no provable asset
   owner, so excluded. Generated/local graphics do not supply source evidence.

All native Unown forms 413..439 are included with their shared normal palette
tag. Native IDs above 255 (e.g. Treecko 277, Pecharunt 1439) are preserved.
Normal/regional/persistent form selection stays broad; unsafe categories are
explicitly excluded. Invalid selected fields fall back to Nidoran♀ in both
consumers; future UPR must reject an invalid requested selection before any
write. The bitmap is public source evidence, **not validation of decoded asset
contents, compressed lengths, cries, actual installed tables or gameplay**.
No canonical Nidoran♀ front/palette row is written or redirected by Stage A.

## ROM-free verification

From this branch's source-only worktree:

```sh
python3 -B scripts/tests/test_oak_intro_abi.py \
  --dpe-root ../02_external/Dynamic-Pokemon-Expansion-Gen-9 \
  --upr-root ../upr-fvx-pr218
python3 -B scripts/tests/test_pickup_descriptor_abi.py
python3 -B scripts/tests/test_evolution_runtime_compat.py \
  --dpe-root ../02_external/Dynamic-Pokemon-Expansion-Gen-9
git diff --check
```

Only public text sources and synthetic buffers are used. There is no
private-input mode. Tests require Python plus the already available public
`pycparser` package (installed version in this repair run: 3.11). No package
was installed or changed. The parser reads the actual selector helper and
header/native-row declarations without a C preprocessor or compiler. A bounded
interpreter executes that C AST's branches, loops, comparisons, field reads,
array accesses and returns over synthetic ARM-width objects; unsupported nodes
fail closed. It records reads and rejects any foreign-record dereference or
attempt to follow a stored pointer. This is source interpretation, not compiled
C/ARM execution, ROM discovery, an inserter run or physical ownership proof.
The tests include the actual public `FunctionWrap` function executed only
against `BytesIO`, followed by a bounded model of nested wrapper/bridge calls
with scratch-register clobbering, 8-byte stack alignment and LR state controls.
This still is not emitted hook execution. The model's 64-byte consumer
intervals are arbitrary synthetic fixtures, not asserted native code sizes.
The original external-preflight model remains separate. The repair's runtime
regressions do not use `validate_record`: they execute the parsed production C
helper, using a valid non-default species so a missing fallback is observable.
They cover all 65,536 u16 selections; 94 immutable descriptor bytes x 8 bit
changes = 752 bad-header cases; null/foreign/unaligned record addresses; forged
self/bitmap/bridge/consumer/root fields; compiled fallback despite a corrupted
default; and no bitmap read for out-of-capacity IDs even with every bitmap bit
set. Read traces require header validation before selector/bitmap access.

Mutation controls execute the actual pre-repair helper, which wrongly accepts
species 277 with a bad version, and variants with version/consumer/bitmap-owner
checks removed. These reproduce the safety defect and demonstrate that the new
assertions detect it. Removing the foreign-pointer guard or introducing a
stored-pointer dereference is rejected by the interpreter. Descriptor, bitmap,
bridges, consumers and the read-only Evolution test are checked against the
exact repair base; only the selector helper may change in `scripting.c`.

The Workspace safety helper passes at the Workspace root. A component-local
run still rejects inherited tracked `deps/*.exe`/`deps/*.dll` names; this is
an existing baseline limitation, **not a component safety PASS**. Source-only
sparse checkout omits these protected blobs; they are not read or changed.
The isolated worktree starts clean at #77; allowed diff, modes, ancestry and
no-Gitlink checks are separate. Existing Workspace submodule/Gitlink/document
mismatches remain `CONFLICT/NOT_RECONCILED`, unchanged by this candidate.

### Recorded local source results

- Repaired ABI/source suite, command above: **25/25 PASS**, exit 0,
  no failures/errors/skips. Original Stage-A result was 19/19 at `fda64ec5...`;
  that historical result did not establish immutable-header runtime fallback.
- Existing Pickup suite: **13/13 PASS**, exit 0, no skips.
- Existing full Evolution/combined suite: **21/23 PASS, 2 FAIL**, exit 1,
  no errors/skips. This invocation is **not a full-suite PASS**. Its
  `test_dispatch_hooks_config_and_insertion_inputs_are_base_exact` requires
  byte-identical `src/scripting.c`, incompatible with this authorized consumer
  change. `test_exact_dpe_enum_and_existing_abi` requires local DPE HEAD
  `d887185...`; the untouched local checkout remains `22ffa27...` as already
  documented by CONTROL. Other tests in that legacy invocation read that
  local public checkout and are not promoted to exact-pinned DPE evidence.
- The new suite separately verifies every unchanged hook/build/config owner,
  the exact allowed regions of `scripting.c`, and the exact pinned public DPE
  enum/16x8 evolution-row contract via Git objects. No legacy test file or
  DPE checkout was changed to make its incompatible prerequisite pass.
- `git diff --check`: **PASS**, exit 0. Repair three-file subset of the
  unchanged five-file allowlist; no Gitlink or mode changes; exact `fda64ec5...`
  repair ancestry and clean initial target-worktree checks: PASS.
- Workspace-root `python3 -B 07_scripts/bootstrap/check_git_safety.py`:
  **PASS**, exit 0. Component-root
  `python3 -B ../07_scripts/bootstrap/check_git_safety.py`: **FAIL**, exit 1,
  only the inherited tracked `deps` binary names described above. Those blobs
  remain omitted and untouched; no component-wide safety PASS is claimed.
- Native C/ARM compilation, full CFRU/DPE build, link, insert, binary/map/ROM
  inspection, emulator/gameplay and selected-output ownership: **NOT_RUN**
  (outside this authorization; no exit code). No private artifacts accessed.

These are source/synthetic results only. The legacy suite's two failures and
the component safety helper's inherited binary-name rejection remain explicit
CONTROL review caveats; neither is represented as PASS.

## Required later independent evidence — NOT_RUN

- Exact fresh source/config build, unique link symbols, emitted descriptor and
  bitmap layout/alignment, Thumb relocations and instruction bytes; both live
  wrapper → bridge → r1 descriptor → real C consumer paths.
- Source-to-selected-output identity, full inserted code/data extents/capacity,
  selector provenance and reservation. The complete Intro record/bitmap/
  bridges/consumers must be disjoint from native rows/assets, palette owners,
  learnset repoints/allocator/rollback, Pickup E5+descriptor+tables+consumer,
  Evolution descriptor+table+consumer, and every other active hook/owner.
- Independent `OWNERSHIP_WITNESS_V1` for the exact combined selected output;
  no magic-only scanning, guessed free space, `0xFF` ownership or inherited
  witness from #77 alone. #726 Stage-D gates remain in force.
- Separately authorized UPR Stage B, bound to the reviewed CFRU revision:
  selector-only writes, full immutable/connection/interval rejection, canonical
  Nidoran♀ preservation, GFX-001/003 × Intro OFF/ON, separate GFX-002/004 controls,
  pointer-last/rollback, reopen, fixed-seed replay and non-CFRU controls.
- User-only graphical/cry, native >255/Unown, hidden-sprite single destruction,
  character creation, allocation pressure, naming/retry, save/reload and
  title-screen/Poke Ball/Trade smoke. Excluded Deoxys support requires its own
  source/runtime evidence and explicit policy revision, not a flipped bit.

No private build, linker map, binary, ROM, save, emulator state, secret or
private pathname is required or accepted as an input to these tests/report.
Return the exact candidate HEAD/test results for CONTROL source review, then
STOP. `UPR_STAGE_B=NOT_AUTHORIZED`; `RUNTIME_ACCEPTED=NO`; `MERGE/GITLINK=NO`.
