# R1 fair-AI writable-state root cause — Workspace #532

## Revision-bound diagnosis

CONTROL classified the exact PR #56 head
`d9c226fde353741dd38b7239fa81eae7504ee666` as
`RUNTIME_FAIR_AI_DISPATCH_ROOT_CAUSE_READY` after an approved private ARM
link. Its `arm-none-eabi-objdump -h build/linked.o` and
`arm-none-eabi-nm -n -S build/linked.o` evidence was:

| Pre-fix item | VMA | Size/type |
| --- | ---: | --- |
| `.text` | `0x09000000` | ROM output |
| `ewram_data` | `0x09220278` | `0x85C`, LMA `0x09220278` |
| `sIronmonResult` | `0x09220278` | `0x130` |
| `sIronmonObservation` | `0x092203A8` | `0x72C` |
| `gOakCappedTailWhipProbeState` | `0x0921EBD1` | `0xB`, type `T` |

`EWRAM_DATA` names the input section `ewram_data`, but `linker.ld`
declares only a ROM `.text` output and never directs that input to writable
RAM. GNU ld's orphan placement put the 0x85C bytes after ROM text at 0x09.
The same linker script explicitly folds `*(.bss)` and `*(COMMON)` into
ROM `.text`; the uninitialized diagnostic global therefore became a type
`T` ROM symbol. The capped controller also declared a mutable static
`sOakProbeBoundedFallback`; the same `.bss` rule exposed it to the ROM
placement fault. The declared `ewram` MEMORY region has no output section
and does not move either input by itself. Its `4M - 4k` LENGTH also does
not prove any free physical GBA EWRAM; the writable address range for this
contract ends at `0x02040000`. `scripts/build.py` invokes
`arm-none-eabi-ld BPRE.ld -T linker.ld`, then raw
`arm-none-eabi-objcopy -O binary`; `scripts/insert.py` inserts
`build/output.bin` at its existing ROM offset. No runtime initializer copies
these objects to RAM. Ironmon observation and policy-result writes therefore
cannot be trusted in the private ROM, whereas host process globals are
writable. #529's bounded emergency chooses exact Oak Squirtle's first legal
nonzero own slot, slot 1 Tail Whip. The pre-fix Tail Whip loop and the
pre-fix capped diagnostic are **not** evidence that the fair policy admitted
a capped Tail Whip.

## Source-owned RAM inventory and allocation decision

The source does not establish an unused 0x85C-byte fixed EWRAM gap.
`BPRE.ld` assigns `gHeap = 0x02000000`, and `include/malloc.h` sets
`HEAP_SIZE = 0x1C000`: the managed heap ends at `0x0201C000`.
`include/decompress.h` places `gDecompressionBuffer` at that boundary;
`include/new/ram_locs.h` places trainer ID at `0x02020000`.
The apparent post-heap space cannot be claimed for a new static section.

The fixed source contract also includes:

| Owner | Source-backed location |
| --- | --- |
| Battle buffers, mons, struct, parties | `BPRE.ld`: `gBattleBufferA 0x02022BC4`, `gBattleBufferB 0x020233C4`, `gBattleMons 0x02023BE4`, `gBattleStruct 0x02023FE8`, `gEnemyParty 0x0202402C`, `gPlayerParty 0x02024284` |
| Frontier/temp-team and streak areas | `BPRE.ld`: Battle Sands `0x0202682C`, Tower `0x02026840`, Mine `0x02026B40`, Circus `0x02026B50`, Ring Challenge `0x02028FC0`; `src/frontier.c` allocates entered teams dynamically |
| Save/menu/bag | `gSaveDataBuffer 0x02039A38`; expanded flags `0x0203B174`, vars `0x0203B374`, and the `0x2EA4`-byte New Game clear through `0x0203E018`; bag/menu pointers and buffers span named `0x0203Bxxx`/`0x0203Cxxx` locations |
| High battle and other owners | `gNewBS` pointer slot `0x0203E038`, fixed battle helper block `0x0203E020..0x0203E034`, later high allocations including Berry Pouch `0x0203F37C`, Braille window `0x0203FFD0`, and EV/IV pointer `0x0203FFF0` |

The bounded repair uses the **already allocated battle-lifetime
`gNewBS` block**. `HandleNewBattleRamClearBeforeBattle` obtains it with
`Calloc(sizeof(struct NewBattleStruct))`; `end_battle.c` frees it after
the battle. Two policy fields now live at the tail of this structure, after
all pre-existing fields. The diagnostic-only probe state, including the
bounded-fallback flag, follows them only
when `TRAINER_AI_RUNTIME_CAPPED_TAILWHIP_PROBE` is enabled. It is cleared
by the same `Calloc`; no static mutable AI scratch remains. No fixed RAM
address, save block, BattleStruct ABI, policy algorithm, score, or fallback
rule changed.

The approved target ARM compiler produced these target sizes and offsets:

| Build | `sizeof(NewBattleStruct)` | Observation | Result | Diagnostic state |
| --- | ---: | ---: | ---: | ---: |
| Release | `0x143C` | `gNewBS + 0xBE0`, `0x72C` | `gNewBS + 0x130C`, `0x130` | absent |
| Capped diagnostic | `0x1448` | `gNewBS + 0xBE0`, `0x72C` | `gNewBS + 0x130C`, `0x130` | `gNewBS + 0x143C`, `0xC` |

The observation ends exactly where the result begins, and the result ends
at `0x143C`; the diagnostic state ends at `0x1448`, within `0x1448`.
All offsets are checked against the allocated object and the `0x1C000`
heap capacity. The heap allocator owns non-overlap with other live heap
allocations. Absolute object addresses vary by allocation and therefore
**cannot appear in `nm`** under this permitted managed-allocation design.
The linked-object requirement is instead: no `sIronmonObservation`,
`sIronmonResult`, `gOakCappedTailWhipProbeState`, or
`sOakProbeBoundedFallback` static symbol at
any ROM/RAM address; the fixed `gNewBS` pointer slot remains `0x0203E038`
type `A`, and ARM-compiled offsets prove all referenced bytes are inside
its writable heap block. There is no writable AI linker output section
or RAM LMA to include in the ROM payload.

## Build, insertion, and functional gates

`scripts/tests/audit_ai_writable_state.py` is now called by
`scripts/build.py` **after** linking/objcopy and by `scripts/insert.py`
**before** any ROM is copied or opened. Its linked mode requires `build/linked.o` and
`build/output.bin`; it fails if the four former static scratch symbols,
`ewram_data` bytes, or any loadable section outside the 0x09 ROM span
return. It checks `.text` VMA/LMA at `0x09000000`, `gNewBS`'s fixed
EWRAM pointer slot, and `build/output.bin` size against the exact ROM
loadable LMA span. It also re-extracts the linked object and compares the
binary bytes, rejecting stale insertion output. It compiles target ARM
layout assertions for release or
diagnostic mode based on linked symbols. This rules out a giant
`0x02`-to-`0x09` objcopy gap. The existing insertion-symbol audit
continues to check the five runtime hooks.

On this worker, the existing devkitARM toolchain compiled release and
capped-probe `ai_ironmon.c`, `ai_master.c`, and opponent-controller ARM
objects. Neither mode emitted a static AI scratch symbol or
`ewram_data`. Target ARM layout checks passed with the offsets above.
A synthetic link through the actual `BPRE.ld`/`linker.ld` and objcopy
showed `.text` size `0x10`, VMA/LMA `0x09000000`, and
`output.bin` size `0x10` exactly matching the ROM load span. This
synthetic result validates the audit machinery; **it is not a full CFRU
linked-object result**. The worker lacks `wav2agb` and `mid2agb` for
the four audio source files, so no full linked object or insertion binary
was produced here and no tool was installed. An approved private full
build must run the wired audit and provide sanitized
`objdump -h`, `nm -n -S`, and output-size evidence before a ROM test.

The complete source-owned action → pending → move host remains green:
Standard and Ironmon Smart select Water Gun on fresh revealed Oak and a
valid non-Tail-Whip Tackle at minimum Defense, without bounded fallback.
Injected Ironmon/Standard policy error, no-admitted-action, and
selected-ID lookup failures still reach #529 emergency slot 1 Tail Whip.
The original three-turn marker is unchanged. Both diagnostics remain
disabled by default and absent from release preprocessing. All seven
accepted #532 regression suites passed on this source candidate:
Standard twins `4096/0`, Ironmon twins `1024/0`, Badge twins `16/0`,
Badge oracle `663000/663000`, damage oracle `98304`, Ironmon parity
`63/63`, mandatory tags `58/58`, accepted v1/v2/v3 digests, `991`
move census, and `10/10` differential parity. Settings/raw compatibility,
Replacement Safety, Legacy Smart isolation, policy RNG isolation, save
delta zero, profile-storage audit, hook/source audit, and 131 damage
overrides also passed. The ARM source-object/layout and synthetic
linker/objcopy gates passed; the full linked-object gate still needs the
approved complete build.

## Disposition and next private gate

The source root cause and bounded writable-state repair are ready for
review. This is **not** a private runtime pass and not
`ROM_PROFILE_READY`. CONTROL first reviews the ARM full-link section,
symbol, and objcopy-size evidence from the exact PR head. A fresh
non-randomized New Game with Ironmon Smart and Charmander must then show
Oak Squirtle no longer repeatedly falling through to Tail Whip; the
accepted revealed first-turn source witness expects Water Gun. No broader
R1 work proceeds without CONTROL authorization. PR #56 stays open and
unmerged; Workspace Gitlink, DPE, UPR, Tracker, and upstream remain
untouched. `UPSTREAM_CONTRIBUTION = DEFERRED`.
