#!/usr/bin/env python3
"""Fail closed on #532 AI scratch ownership and optional ARM ROM extraction.

The release fix uses gNewBS's existing battle-lifetime heap allocation. There
are intentionally no linked static scratch symbols or RAM output sections.
With --linked-object, audit the real ARM link and objcopy output before ROM
insertion; the source-only mode works without the approved ARM toolchain.
"""

import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[2]
ROM_START = 0x09000000
ROM_END = 0x0A000000
HEAP_START = 0x02000000
HEAP_END = 0x0201C000
GNEWBS_PTR = 0x0203E038
FORBIDDEN_SCRATCH_SYMBOLS = {
    "sIronmonObservation", "sIronmonResult", "gOakCappedTailWhipProbeState",
    "sOakProbeBoundedFallback",
}


def require(condition, message):
    if not condition:
        raise SystemExit("AI writable-state audit failed: " + message)


def source(path):
    return (ROOT / path).read_text()


def check_source():
    linker = source("linker.ld")
    bpre = source("BPRE.ld")
    malloc = source("include/malloc.h")
    decompress = source("include/decompress.h")
    ram = source("include/new/ram_locs.h")
    battle = source("include/battle.h")
    ironmon = source("src/Battle_AI/ai_ironmon.c")
    master = source("src/Battle_AI/ai_master.c")
    master_header = source("include/new/ai_master.h")
    controller = source("src/battle_controller_opponent.c")
    start = source("src/battle_start_turn_start.c")
    end = source("src/end_battle.c")
    build = source("scripts/build.py")
    inserter = source("scripts/insert.py")

    require("*(.bss)" in linker and ">rom = 0xff" in linker
            and not re.search(r"(?m)^\s*\.(?:bss|ewram_data)\s*[^\n]*>\s*ewram", linker),
            "legacy .bss/ewram_data linker treatment changed without a RAM contract")
    require('section("ewram_data")' in source("include/gba/defines.h")
            and "*(ewram_data)" not in linker,
            "EWRAM_DATA orphan-section root cause no longer matches source")
    require("gHeap = 0x2000000;" in bpre and "#define HEAP_SIZE 0x1C000" in malloc
            and "0x201C000" in decompress,
            "managed heap or adjacent decompression-buffer boundary changed")
    require("gNewBS = 0x203E038;" in bpre
            and "gNewBS = Calloc(sizeof(struct NewBattleStruct));" in start
            and "FREE_AND_SET_NULL(gNewBS);" in end,
            "battle allocation pointer, creation, or cleanup changed")
    require("gSaveDataBuffer = 0x02039A38;" in bpre
            and "#define gExpandedFlags ((u8*) 0x0203B174)" in ram
            and "sBerryPouchListMenuItems = 0x203F37C;" in bpre
            and "sBrailleWindowId = 0x203FFD0;" in bpre
            and "gEvIv = 0x0203FFF0;" in bpre,
            "high EWRAM/save/menu inventory changed; re-audit before placement")
    require("struct IronmonPolicyObservation ironmonObservation;" in battle
            and "struct IronmonPolicyResult ironmonResult;" in battle
            and "&gNewBS->ironmonObservation" in ironmon
            and "&gNewBS->ironmonResult" in ironmon,
            "Ironmon scratch is not wholly owned by gNewBS")
    require("EWRAM_DATA" not in ironmon
            and not re.search(r"\b(?:static\s+)?struct IronmonPolicy(?:Observation|Result)\s+sIronmon", ironmon),
            "Ironmon static scratch can still be linked into ROM")
    offenders = [str(path.relative_to(ROOT)) for path in (ROOT / "src").rglob("*.c")
                 if re.search(r"\bEWRAM_DATA\b", path.read_text(errors="replace"))]
    require(not offenders,
            "EWRAM_DATA would orphan into ROM again: " + ", ".join(offenders))
    require("struct OakCappedTailWhipProbeState oakCappedTailWhipProbeState;" in battle
            and "#ifdef TRAINER_AI_RUNTIME_CAPPED_TAILWHIP_PROBE" in battle
            and "#define gOakCappedTailWhipProbeState (gNewBS->oakCappedTailWhipProbeState)" in master_header
            and "bool8 boundedFallback;" in battle
            and "#define sOakProbeBoundedFallback (gNewBS->oakCappedTailWhipProbeState.boundedFallback)" in controller
            and not re.search(r"static\s+bool8\s+sOakProbeBoundedFallback\s*;", controller)
            and not re.search(r"struct OakCappedTailWhipProbeState\s+gOakCappedTailWhipProbeState\s*;", master),
            "diagnostic mutable state can still become a ROM global")
    require("Objcopy(linked)" in build
            and "audit_ai_writable_state.py" in build
            and "OUTPUT = 'build/output.bin'" in inserter
            and inserter.index("audit_ai_writable_state.py")
                < inserter.index("shutil.copyfile(SOURCE_ROM, ROM_NAME)"),
            "post-link/pre-insertion output audit is not wired")
    print("AI ownership: gHeap 0x02000000..0x0201C000; adjacent decompression buffer, fixed battle/save/menu/high-EWRAM owners excluded: PASS")
    print("linker root cause: .bss folded into ROM .text; ewram_data orphaned into ROM; both AI scratch objects now battle-heap fields: PASS")


def tool(name):
    found = shutil.which(name)
    if found:
        return found
    devkit = os.environ.get("DEVKITARM")
    candidate = Path(devkit) / "bin" / name if devkit else None
    require(candidate is not None and candidate.is_file(),
            "approved ARM tool unavailable: " + name)
    return str(candidate)


def parse_sections(output):
    lines = output.splitlines()
    sections = []
    pattern = re.compile(
        r"^\s*\d+\s+(\S+)\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+"
        r"([0-9a-fA-F]+)\s+[0-9a-fA-F]+\s+2\*\*\d+")
    for index, line in enumerate(lines):
        match = pattern.match(line)
        if match:
            name, size, vma, lma = match.groups()
            flags = lines[index + 1].strip() if index + 1 < len(lines) else ""
            sections.append((name, int(size, 16), int(vma, 16),
                             int(lma, 16), flags))
    require(sections, "objdump returned no section headers")
    return sections


def parse_symbols(output):
    symbols = {}
    for line in output.splitlines():
        parts = line.split()
        if len(parts) >= 3 and re.fullmatch(r"[0-9a-fA-F]+", parts[0]):
            symbols[parts[-1]] = (int(parts[0], 16), parts[-2])
    return symbols


def check_arm_layout(diagnostic):
    code = r'''
#include <stddef.h>
#include "include/battle.h"
#include "include/malloc.h"
_Static_assert(sizeof(struct IronmonPolicyObservation) == 0x72C, "observation size");
_Static_assert(sizeof(struct IronmonPolicyResult) == 0x130, "result size");
_Static_assert(offsetof(struct NewBattleStruct, ironmonObservation) % 4 == 0, "observation alignment");
_Static_assert(offsetof(struct NewBattleStruct, ironmonResult) % 4 == 0, "result alignment");
_Static_assert(offsetof(struct NewBattleStruct, ironmonResult) ==
    offsetof(struct NewBattleStruct, ironmonObservation)
    + sizeof(struct IronmonPolicyObservation), "scratch overlap/padding");
_Static_assert(offsetof(struct NewBattleStruct, ironmonResult)
    + sizeof(struct IronmonPolicyResult) <= sizeof(struct NewBattleStruct), "allocation bound");
_Static_assert(sizeof(struct NewBattleStruct) < 0x2000
    && sizeof(struct NewBattleStruct) < HEAP_SIZE, "heap capacity bound");
#ifdef TRAINER_AI_RUNTIME_CAPPED_TAILWHIP_PROBE
_Static_assert(offsetof(struct NewBattleStruct, oakCappedTailWhipProbeState) >=
    offsetof(struct NewBattleStruct, ironmonResult)
    + sizeof(struct IronmonPolicyResult), "diagnostic overlap");
_Static_assert(offsetof(struct NewBattleStruct, oakCappedTailWhipProbeState)
    + sizeof(struct OakCappedTailWhipProbeState) <= sizeof(struct NewBattleStruct),
    "diagnostic allocation bound");
#endif
/* nm -S reports these target-compiled array sizes as allocation offsets. */
const unsigned char ai_layout_allocation[sizeof(struct NewBattleStruct)] = {0};
const unsigned char ai_layout_observation_offset[
    offsetof(struct NewBattleStruct, ironmonObservation)] = {0};
const unsigned char ai_layout_result_offset[
    offsetof(struct NewBattleStruct, ironmonResult)] = {0};
#ifdef TRAINER_AI_RUNTIME_CAPPED_TAILWHIP_PROBE
const unsigned char ai_layout_diagnostic_offset[
    offsetof(struct NewBattleStruct, oakCappedTailWhipProbeState)] = {0};
#endif
'''
    with tempfile.TemporaryDirectory(prefix="cfru-ai-arm-layout-") as temp:
        cfile = Path(temp) / "layout.c"
        obj = Path(temp) / "layout.o"
        cfile.write_text(code)
        command = [tool("arm-none-eabi-gcc"), "-std=gnu99", "-mthumb",
                   "-mcpu=arm7tdmi", "-I.", "-c", str(cfile),
                   "-o", str(obj)]
        if diagnostic:
            command.insert(1, "-DTRAINER_AI_RUNTIME_CAPPED_TAILWHIP_PROBE")
        subprocess.run(command, cwd=ROOT, check=True)
        symbols = subprocess.check_output(
            [tool("arm-none-eabi-nm"), "-n", "-S", str(obj)], text=True)
        sizes = {}
        for line in symbols.splitlines():
            parts = line.split()
            if len(parts) == 4 and parts[-1].startswith("ai_layout_"):
                sizes[parts[-1]] = int(parts[1], 16)
    total = sizes["ai_layout_allocation"]
    observation = sizes["ai_layout_observation_offset"]
    result = sizes["ai_layout_result_offset"]
    require(observation % 4 == 0 and result % 4 == 0
            and observation + 0x72C == result
            and result + 0x130 <= total
            and total < 0x2000 and total < HEAP_END - HEAP_START,
            "target ARM scratch offsets exceed the battle heap allocation")
    if diagnostic:
        probe = sizes["ai_layout_diagnostic_offset"]
        require(probe >= result + 0x130 and probe + 12 <= total,
                "target ARM diagnostic field overlaps or exceeds allocation")
    else:
        require("ai_layout_diagnostic_offset" not in sizes,
                "release target layout retained diagnostic state")
    print(f"target ARM battle allocation=0x{total:X}, observation=+0x{observation:X}/0x72C, "
          f"result=+0x{result:X}/0x130" +
          (f", diagnostic=+0x{probe:X}/0xC: PASS" if diagnostic else
           ", diagnostic absent: PASS"))


def check_arm_source_objects():
    flags = ["-mthumb", "-mno-thumb-interwork", "-mcpu=arm7tdmi",
             "-mtune=arm7tdmi", "-mno-long-calls", "-march=armv4t",
             "-Os", "-fira-loop-pressure", "-fipa-pta"]
    units = [
        ("src/Battle_AI/ai_ironmon.c", False),
        ("src/Battle_AI/ai_master.c", False),
        ("src/battle_controller_opponent.c", False),
        ("src/Battle_AI/ai_master.c", True),
        ("src/battle_controller_opponent.c", True),
    ]
    with tempfile.TemporaryDirectory(prefix="cfru-ai-arm-sources-") as temp:
        for index, (unit, diagnostic) in enumerate(units):
            obj = Path(temp) / f"unit-{index}.o"
            command = [tool("arm-none-eabi-gcc"), *flags]
            if diagnostic:
                command.append("-DTRAINER_AI_RUNTIME_CAPPED_TAILWHIP_PROBE")
            command += ["-c", unit, "-o", str(obj)]
            subprocess.run(command, cwd=ROOT, check=True, capture_output=True)
            symbols = parse_symbols(subprocess.check_output(
                [tool("arm-none-eabi-nm"), "-n", "-S", str(obj)], text=True))
            sections = parse_sections(subprocess.check_output(
                [tool("arm-none-eabi-objdump"), "-h", str(obj)], text=True))
            for name in FORBIDDEN_SCRATCH_SYMBOLS:
                require(name not in symbols, f"{unit} still emits static {name}")
            require(not any(name in ("ewram_data", ".ewram_data") and size
                            for name, size, _, _, _ in sections),
                    f"{unit} still emits writable orphan section")
    print("approved ARM source objects: release and capped-probe AI/controller compile without static scratch symbols or ewram_data: PASS")


def check_linked(linked, output_bin):
    require(linked.is_file() and output_bin.is_file(),
            "linked object or objcopy output does not exist")
    sections = parse_sections(subprocess.check_output(
        [tool("arm-none-eabi-objdump"), "-h", str(linked)], text=True))
    symbols = parse_symbols(subprocess.check_output(
        [tool("arm-none-eabi-nm"), "-n", "-S", str(linked)], text=True))
    text_sections = [section for section in sections if section[0] == ".text"]
    require(len(text_sections) == 1, "expected one ROM .text output section")
    _, text_size, text_vma, text_lma, text_flags = text_sections[0]
    require(text_vma == ROM_START and text_lma == ROM_START
            and "ALLOC" in text_flags and "LOAD" in text_flags,
            ".text is not loadable at the CFRU ROM insertion origin")
    require(symbols.get("gNewBS") == (GNEWBS_PTR, "A"),
            "gNewBS pointer slot is not the fixed EWRAM owner")
    for name in FORBIDDEN_SCRATCH_SYMBOLS:
        require(name not in symbols, "ROM-backed static AI symbol remains: " + name)
    require(not any(name in ("ewram_data", ".ewram_data") and size
                    for name, size, _, _, _ in sections),
            "orphaned ewram_data still contributes bytes to the link")
    loaded = [(name, size, vma, lma) for name, size, vma, lma, flags in sections
              if size and all(flag in flags for flag in ("CONTENTS", "ALLOC", "LOAD"))]
    require(loaded, "no loadable ROM sections")
    for name, size, vma, lma in loaded:
        require(ROM_START <= vma < vma + size <= ROM_END
                and ROM_START <= lma < lma + size <= ROM_END,
                "objcopy would include non-ROM section or a giant gap: " + name)
    low = min(lma for _, _, _, lma in loaded)
    high = max(lma + size for _, size, _, lma in loaded)
    require(low == ROM_START and output_bin.stat().st_size == high - low,
            "objcopy output size differs from ROM-only load span")
    with tempfile.TemporaryDirectory(prefix="cfru-ai-objcopy-check-") as temp:
        fresh = Path(temp) / "output.bin"
        subprocess.run([tool("arm-none-eabi-objcopy"), "-O", "binary",
                        str(linked), str(fresh)], cwd=ROOT, check=True)
        require(fresh.read_bytes() == output_bin.read_bytes(),
                "insertion binary is stale or differs from this ARM linked object")
    diagnostic = "AI_OakCappedTailWhipProbeExactBattle" in symbols
    check_arm_layout(diagnostic)
    print(f"ARM .text size=0x{text_size:X} VMA=0x{text_vma:08X} LMA=0x{text_lma:08X} flags={text_flags}: PASS")
    print(f"managed AI fields: no static linked scratch symbols; gNewBS pointer slot=0x{GNEWBS_PTR:08X} (EWRAM): PASS")
    print(f"objcopy output size=0x{output_bin.stat().st_size:X}; ROM-only load span=0x{low:08X}..0x{high:08X}; exact re-extraction matches: PASS")


def check_arm_linker_self_test():
    with tempfile.TemporaryDirectory(prefix="cfru-ai-arm-linker-") as temp:
        cases = (
            ("clean", "", None),
            ("orphan", '__attribute__((section("ewram_data"))) unsigned char badOrphan[0x85C];\n',
             "orphaned ewram_data"),
            ("bss", "unsigned char gOakCappedTailWhipProbeState[11];\n",
             "ROM-backed static AI symbol"),
        )
        for name, code, expected_failure in cases:
            cfile = Path(temp) / f"{name}.c"
            obj = Path(temp) / f"{name}.o"
            linked = Path(temp) / f"{name}.linked.o"
            binary = Path(temp) / f"{name}.output.bin"
            cfile.write_text("int AiLinkerProbe(void) { return 1; }\n" + code)
            subprocess.run([tool("arm-none-eabi-gcc"), "-mthumb", "-mcpu=arm7tdmi",
                            "-c", str(cfile), "-o", str(obj)], cwd=ROOT, check=True)
            subprocess.run([tool("arm-none-eabi-ld"), "BPRE.ld", "-T", "linker.ld",
                            "-o", str(linked), str(obj)], cwd=ROOT, check=True,
                           capture_output=True)
            subprocess.run([tool("arm-none-eabi-objcopy"), "-O", "binary",
                            str(linked), str(binary)], cwd=ROOT, check=True)
            try:
                check_linked(linked, binary)
            except SystemExit as error:
                require(expected_failure is not None
                        and expected_failure in str(error),
                        f"unexpected {name} linker audit failure: {error}")
            else:
                require(expected_failure is None,
                        f"{name} bad writable section escaped the ARM audit")
    print("synthetic ARM linker/objcopy positive and orphan/BSS rejection: PASS (not a full CFRU build)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--linked-object", type=Path)
    parser.add_argument("--output-bin", type=Path)
    parser.add_argument("--arm-layout", action="store_true",
                        help="compile both release and capped-probe layouts with approved ARM GCC")
    parser.add_argument("--arm-source-objects", action="store_true",
                        help="compile AI/controller release and diagnostic ARM objects")
    parser.add_argument("--arm-linker-self-test", action="store_true",
                        help="exercise the ROM-only linker/objcopy audit without a full build")
    args = parser.parse_args()
    require(bool(args.linked_object) == bool(args.output_bin),
            "pass both --linked-object and --output-bin for ARM closure")
    check_source()
    if args.arm_layout:
        check_arm_layout(False)
        check_arm_layout(True)
    if args.arm_source_objects:
        check_arm_source_objects()
    if args.arm_linker_self_test:
        check_arm_linker_self_test()
    if args.linked_object:
        check_linked(args.linked_object, args.output_bin)
    else:
        print("ARM linked-object/objcopy closure: NOT RUN (pass approved build paths)")


if __name__ == "__main__":
    main()
