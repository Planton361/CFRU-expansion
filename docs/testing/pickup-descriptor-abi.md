# Pickup descriptor ABI v1 — Workspace #719 source candidate

`CFRU_PICKUP_DESCRIPTOR_SOURCE_CANDIDATE` only. ARM compilation, linked
consumer proof, selected-output binding and gameplay tests are **NOT_RUN**.
This does not implement Pickup Random, unblock #717 or extend #498 acceptance.
References [Workspace #719](https://github.com/Planton361/firered-gen9-randomizer-workspace/issues/719).
Design basis: CFRU `e68a701aa4e68733ef8ad1e7cadb68825c0d16c2`.

## Stage A decision and source proof

The old optimized C function has no fixed literal/call layout. A descriptor
with `used` would not prove consumption. One new assembly file therefore owns
the **existing** `atkE5_pickupitemcalculation` symbol. The E5 table remains
byte-for-byte unchanged: same 256 slots, order and void(void) Thumb pointer
ABI. The 28-byte, 4-aligned bridge saves LR with an 8-byte stack frame, loads
the descriptor into r0 and C consumer into r3, calls a local `bx r3` stub,
then restores the caller through `bx`. It modifies only caller-saved registers
and restores r4/SP. Literal offsets are 20 and 24; assembly assertions reject
layout drift. Expected instruction halfwords at offsets 0..18 are:
`b510 4804 4b04 f000 f803 bc10 bc01 4700 4718 46c0`.
The last two words are linker-resolved pointers, **not fixed ROM addresses**.

`PickupItemCalculation(r0)` passes that same pointer to `ChoosePickupItem`.
The chooser reads all four pointer fields through a const volatile descriptor;
no direct table symbols or global descriptor lookup remain in the consumer.
Observable pointer loads survive chooser inlining. Separate C compilation
without LTO supplies an externally callable argument-taking consumer, so the
compiler cannot substitute an assumed singleton argument. An altered compiler,
LTO, wrapper/veneer or emitted layout requires new proof, never a heuristic.
The descriptor reciprocally names this consumer and this E5 anchor.

The header documents every naturally aligned offset and asserts widths,
offsets, counts, size and alignment at compile time. No packing, new section,
linker, dispatch table or insertion format is introduced. Little-endian fields:

| Offset | Field | Encoding |
| --- | --- | --- |
| 0 | Magic | u32 `0x31555043` (CPU1) |
| 4 / 6 | Version / byte size | u16 1 / 64 |
| 8 / 12 | Pickup config / item schema | u32 bitset / u32 1 |
| 16 / 20 / 24 / 28 | Common / rare / common ceilings / rare ceilings | four 32-bit ROM data pointers |
| 32 / 34 / 36 / 38 | Counts | u16 18 / 11 / 9 / 2 |
| 40..48 | Widths, ranges, step, windows, min/max level | u8 4,2,4,10,10,9,2,1,100 |
| 49..51 | Reserved | three zero bytes |
| 52 | CFRU ITEMS_COUNT | u32; bounds only, not item eligibility |
| 56 / 60 | C consumer / E5 bridge | 32-bit Thumb function pointers |

Config bits: 1=UNBOUND, 2=straight to bag, 4=knocked-off recovery. Selected
source is non-UNBOUND with bits 2+4 (6). Only this reviewed profile is a future
reader candidate; other bitsets, unknown bits and schemas fail closed. This
bitset identifies Pickup options, **not the complete build**. Full public
revision, headers, macros, flags and toolchain require the private receipt.
Raw item_t IDs must use the reviewed CFRU-to-UPR mapping and eligibility policy;
neither u16 fit nor ITEMS_COUNT alone certifies an item as supported.

Original tables (including both UNBOUND branches), ceilings and all gameplay
code outside the parameter/selection indirection stay unchanged. Row index is
`(level-1)/10`; each of ten ranges selects nine common then two rare slots with
one u16 draw and strict `<` ceilings. The rare tail continues after 64225.
Equal values are separate physical slots. Separate activation, Honey Gather,
straight-to-bag/held-item flow and knocked-off recovery retain their source.

## Future reader preflight — no table or magic scan

First require an accepted exact fresh-build **and selected-output** receipt.
Start at all five existing source-owned dispatch repoints from `repoints`;
they must agree on the active command table. Resolve E5, require a Thumb,
4-aligned v1 bridge and match all ten instruction halfwords. Interpret its
fixed literal loads/call, including r0 coupling, rather than searching C code.
Resolve the descriptor at bridge+20 and consumer at bridge+24. Require unique
fresh-link definitions of bridge, consumer, descriptor and all four tables;
sizes, sections and relocated positions must match that accepted receipt.

Validate all 64 descriptor bytes, reciprocal anchor/consumer pointers,
supported config/schema, widths/counts/window arithmetic and zero reserved
bytes. Require bounded, aligned, nonempty, distinct table ranges of 36,22,36,8
bytes, disjoint from one another **and** descriptor, bridge, consumer, command
table, repoint words and other protected output regions. Reject arithmetic
overflow, aliases, unknown pointers, duplicate definitions, stale identity,
unreachable/copied anchors, unsupported IDs and malformed ceilings. Validate
each item against the reviewed raw-ID mapping/allowed item data; ceilings must
match all eleven baseline constants. The first approved baseline also checks
all 29 original items. A later randomized input needs its own accepted receipt
and unchanged non-item data; baseline pattern matching cannot authenticate it.

Verify the selected output's active C consumer against the fresh compiled
consumer, including descriptor-argument data use, **not just its symbol name
or reciprocal pointer**. Copied or forged bytes cannot establish provenance.
Only after the entire preflight may a future UPR plan modify the 29 u16 item
slots atomically. No ceiling/pointer/code writes, no guard removal, no partial
mutation on failure. Vanilla/old builds without this bridge reject this ABI
and retain their separately supported vanilla handler behavior.

## Mandatory private operator gates — Stage C, never run by Codex

1. Use an isolated disposable checkout of the exact approved candidate; do not
   clean or delete anything in the existing checkout. Start with zero objects,
   generated sources, linked outputs, generated repoints or insertion outputs.
   Pin DPE input and all external assets privately. Confirm tracked cleanliness
   and selected configuration before and after compilation. Disable external
   compiler caches. Record every compilation/assembly invocation and link input
   in a local receipt with all direct/transitive headers, generated-source
   inputs, flags, linker files and actual compiler/assembler/linker/objcopy
   identities. Bind each produced object to this run and the same fresh link.
   A source-only mtime cache, clean Git status or new link timestamp cannot pass.
   Reject preexisting objects or changed headers/config/flags/toolchain even if
   their timestamps would permit reuse. `scripts/build.py` remains unchanged;
   **isolation plus the independently verified receipt is mandatory**.
2. Verify actual emitted bridge halfwords, relocations, pointer widths, layout
   assertions and consumer argument-driven four-table reads. Check optimized
   inline or non-inline chooser emission without assuming its symbol survives.
   Unknown emission is FAIL/NOT_PROVEN. Source tests do not satisfy this gate.
3. Independently reproduce/check the entire insertion sequence from the same
   fresh linked image, objcopy result and private DPE/base input. Bind all
   generated repoints, repoint_all, special inserts, free/bytereplacements,
   hooks, repoints, routine pointers, function rewrites, event scripts, map
   overlays and songs, including conditional/include inputs. Check **all**
   output bytes against the independently reconstructed expected output, then
   separately open the user's selected output and require identical identity.
   Reject unaccounted overlays/post-build writes and mismatched selected files.
   Internal absolute literals require the linker load origin to match the
   actual insertion load address; symbol-offset conversion alone is not enough.
   Confirm all five repoints, E5, bridge, consumer, descriptor and four tables
   remain active and unmodified after every transformation. An insertion log,
   operator-selected filename or copied descriptor alone cannot pass.
4. Privately witness unchanged Pickup across all ten ranges, activation and
   Honey Gather/bag/held-item/knocked-off controls on this exact output. Runtime
   outcomes and local compiler/output identity remain separate subtests.

Receipts, paths, hashes, tool output, symbols, addresses, bytes, ROMs, saves,
screenshots and manifests stay private. Return only exact **public source SHA**,
declared profile and sanitized PASS/FAIL/NOT_RUN per subtest. No user-local
verifier is delivered here; CONTROL must review the independent local proof
method before accepting results. These gates are requirements, not assertions
that the current output already satisfies them.

## ROM-free evidence and next CONTROL decision

Run `python3 -B scripts/tests/test_pickup_descriptor_abi.py`. It checks public
source coupling/layout, unchanged baseline, all ten probability partitions,
fixed-bridge instruction semantics and in-memory synthetic negative cases.
The receipt model tests rejection rules only; it has no artifact adapter and
cannot certify a compiler or output. No native object is created or opened.

CONTROL reviews the bounded CFRU source candidate and private proof protocol.
`COMPILER_LINK_PROVENANCE=NOT_RUN`, `SELECTED_OUTPUT_BINDING=NOT_RUN`,
`PICKUP_COMPILER_BINDING_PROOF=NOT_PROVEN`,
`PICKUP_CFRU_DPE_RANDOM_READY=NOT_YET`. Only user-owned evidence, user merge and
a separately approved Workspace integration/rebaseline can precede #717 work.
No merge, DPE/UPR change or Workspace Gitlink update is part of this candidate.

## Combined CFRU source candidate — Workspace #726 Stage A/B

[Workspace #726](https://github.com/Planton361/firered-gen9-randomizer-workspace/issues/726)
authorizes composition on `integration/726-cfru-pickup-evolution`, from the
same exact base above, of Pickup #75
`fc5119052cb363dac5971ff0aee0b67ef0d6a42e` and Evolution #76
`958c30ec58919ac3e13a40ddb9bd94a86651636e`. Their production source deltas
are retained exactly. Integration additions are this evidence section and six
combined regression cases in `test_evolution_runtime_compat.py`; no new file,
hook, config, linker, inserter or consumer ABI is needed.

| Boundary | Pickup owner/contract | Evolution owner/contract | Combined source finding |
|---|---|---|---|
| Live entry | Existing E5 slot; assembly alone defines `atkE5_pickupitemcalculation`; C defines `PickupItemCalculation` | Existing `GetEvolutionTargetSpecies 08042EC4 3` hook and C definition | Unique source definitions, no `BPRE.ld` alias for these owners; dispatch lists unchanged |
| Discovery data | `gPickupDescriptor`, 64B, reciprocal bridge/consumer pointers | Assembly `gEvolutionFriendshipContract`, aligned 32B `CFRUEVO1`, self/consumer pointers | Distinct names/layouts and real volatile consumer reads; both metadata contracts unchanged |
| Runtime data | 18/11 u16 items; 9/2 u32 ceilings; 28B bridge | Only record byte +28 mutable to 220/160; DPE 16x8-byte rows | 58B future item budget and one friendship byte are separate logical owners; physical separation is not established by source |
| Config/header | ARM little-endian, four-byte pointers, non-Unbound bits 6 | `EVOS_PER_MON=16`, TIME_ENABLED, SAVE_BLOCK_EXPANSION, nine-digit existing wallet | Both headers coexist in `general_bs_commands.c`; distinct ABI macros/structs; config and shared types remain base-exact |
| Semantics | All ten distributions, activation/Honey Gather/bag/held/knocked-off controls unchanged | Methods 40/41/42; no coin deduction or RNG; four friendship predicates; conservative species-only trainer synthesis | Independent regression controls retained; no shared new mutable RAM or counter |
| Assembly/build | Bridge in `.text`; descriptor/tables enter ordinary C `.rodata` | Data record in `.text`, normal assembly glob | Existing builder/linker include both; distinct object hashes also checked against existing source inputs |
| Insertion | Five E5 table repoints unchanged | Evolution/GetCoins hooks unchanged | Both enter the SAME output `.text` image including `.rodata`; source feasibility does not prove emitted bounds, relocations, capacity or absence of overlays |

Run both suites on the combined source checkout:

```sh
python3 -B scripts/tests/test_pickup_descriptor_abi.py
python3 -B scripts/tests/test_evolution_runtime_compat.py --dpe-root /path/to/exact/public/DPE -v
python3 -B scripts/tests/audit_ai_writable_state.py
```

The original 13 Pickup and 17 Evolution cases are retained. Six additional
combined cases check unique production definitions, simultaneous header/ABI
coupling, assembly/link/insertion source feasibility and object-name collisions,
base-exact dispatch/hook/config/inserter inputs, synthetic rejection of the
Evolution record overlapping every Pickup owner, and two synthetic write plans
in either order with only 29 u16 item slots and the threshold byte writable.
The last two are in-memory contract models, not a production UPR integration
or a compiled-output collision proof. Pickup's 655,360 draws and all 100 level
mappings, evolution IDs/DPE form source tables and semantic controls remain
covered by the original cases. Asset binaries are not inspected.

Disposition: `COMBINED_SOURCE_CANDIDATE_ONLY`. User-only fresh no-cache
build/link/insert/output and gameplay/save-reload gates remain **NOT_RUN**.
Fresh output ownership must establish the actual full intervals of BOTH
bridges/records/consumers/tables, raw evolution rows, repoint/hook words and
other inserted owners, including actual Thumb relocations and source origin
versus insertion address. Check non-overlap and post-insertion integrity on
the exact new combined head; independent old-PR build receipts cannot be reused.
#726's risk-proportionate protocol supersedes the retired whole-inserter/Thumb
CFG proof requirement in the historical standalone text above.

CONTROL must independently review the new CFRU head before a separate fresh
UPR Stage C session. That later session must rebind #199's strict witness SHA
from standalone #76 to the exact reviewed combined CFRU revision and validate
Pickup against the same fresh combined output. No UPR implementation, merge,
Workspace pin/Gitlink update or runtime support promotion occurs in Stage A/B.
