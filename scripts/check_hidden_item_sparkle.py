#!/usr/bin/env python3
"""M-009 source-only ownership checks and host algorithm tests; never read a ROM.

The insertion entry calls check_source_contract BEFORE accessing its input.
Run this script for the additional tracked-map census and native C unit tests.
"""
import json
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "a869c3526d7f76c54082bc71e236742564319e02"
ORDER = ["ScriptContext_RunScript", "RunTasks", "AnimateSprites", "CameraUpdate",
         "SetQuestLogEvent_Arrived", "UpdateCameraPanning", "BuildOamBuffer",
         "UpdatePaletteFade", "UpdateTilesetAnimations",
         "DoScheduledBgTilemapCopiesToVram", "TryStartVisibleHiddenItemSparkles"]
ALIASES = {"ScriptContext_RunScript": "ScriptContext2_RunScript",
           "SetQuestLogEvent_Arrived": "sub_8115798"}


def require(condition, message):
    if not condition:
        raise ValueError("M-009 fail-closed: " + message)


def git(*args, root=ROOT):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True)


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def uncomment(source):
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", source, flags=re.S)


def rows(source):
    return [line.split() for line in source.splitlines()
            if line.strip() and not line.lstrip().startswith("#")]


def body(source, name):
    start = re.search(r"\b" + re.escape(name) + r"\([^)]*\)\s*\{", source)
    require(start is not None, "missing function " + name)
    depth = 1
    pos = start.end()
    end = pos
    while depth:
        require(end < len(source), "unterminated function " + name)
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[pos:end - 1]


def check_source_contract():
    linker = read("BPRE.ld")
    require(linker == git("show", BASE + ":BPRE.ld"), "linker bindings changed")
    bindings = {name: int(value, 16) for name, value in
                re.findall(r"^(\w+)\s*=\s*(0x[0-9a-fA-F]+)\s*\|\s*1;", linker, re.M)}
    require(bindings["OverworldBasic"] == 0x08056578, "unexpected named BPRE frame entry")
    require(bindings["CB2_OverworldBasic"] == 0x080565A8
            and bindings["CB2_Overworld"] == 0x080565B4, "wrapper boundary changed")
    for name in ORDER[:-1]:
        require(ALIASES.get(name, name) in bindings, "unbound frame callee " + name)

    expected = ["M009_OverworldBasic", "0x08056578", "0", "0"]
    rewrites = rows(read("functionrewrites"))
    require(rewrites == rows(git("show", BASE + ":functionrewrites")) + [expected],
            "exactly one approved rewrite must be added")
    target_rows = [row for row in rewrites if int(row[1], 16) == bindings["OverworldBasic"]]
    require(target_rows == [expected], "duplicate/missing frame owner")
    require(read("functionrewrites").count("M009_OverworldBasic") == 1,
            "conditional or duplicate frame owner")

    baseline_bytes = rows(git("show", BASE + ":bytereplacement"))
    retired = [row for row in baseline_bytes if int(row[0], 16) == bindings["OverworldBasic"]]
    require(len(retired) == 1, "old slow-camera owner not uniquely identified")
    require(rows(read("bytereplacement")) == [row for row in baseline_bytes if row not in retired],
            "old byte owner remains or unrelated byte replacements changed")
    # Active assembler must be unchanged; the historical commented listing is retired.
    asm = uncomment(read("special_inserts.asm"))
    baseline_asm = uncomment(git("show", BASE + ":special_inserts.asm"))
    strip_asm = lambda s: re.sub(r"\s+", "", re.sub(r"@[^\n]*", "", s))
    require(strip_asm(asm) == strip_asm(baseline_asm), "active assembly changed")
    require("OverworldBasic:" not in read("special_inserts.asm"), "retired listing resurrected")

    for path in ("hooks", "repoints", "repointall", "free_bytereplacements", "linker.ld",
                 "src/overworld.c", "src/field_effects.c", "src/dexnav.c", "src/read_keys.c",
                 "src/dns.c", "src/Tables/movement_action.tables.c", "mapobjectoverlays",
                 "src/config.h", "include/config.h", "include/constants/flags.h",
                 "scripts/make.py", "scripts/clean.py", "scripts/check_renewable_hidden_items.py"):
        require(read(path) == git("show", BASE + ":" + path), "out-of-contract change: " + path)
    inserted_guard = "    from check_hidden_item_sparkle import check_source_contract\n    check_source_contract()\n"
    inserter = read("scripts/insert.py")
    require(inserter.count(inserted_guard) == 1, "missing insertion preflight")
    missing_guard = '                        if symbol == "M009_OverworldBasic":\n                            raise ValueError("M-009 frame replacement symbol missing; refusing partial insertion")\n'
    require(inserter.count(missing_guard) == 1, "missing compiled-symbol rejection")
    require(inserter.replace(inserted_guard, "").replace(missing_guard, "") == git("show", BASE + ":scripts/insert.py"),
            "existing M-001 through M-008 checks or insertion behavior changed")
    main_body = inserter.split("def main():\n", 1)[1]
    require(main_body.startswith(inserted_guard),
            "ownership check runs after ROM access")

    allowed = {"src/m009_overworld_frame.c", "src/hidden_item_sparkle.c",
               "include/new/hidden_item_sparkle.h", "scripts/insert.py",
               "scripts/check_hidden_item_sparkle.py", "scripts/tests/m009_sparkle_host.c",
               "src/Tables/level_up_learnsets.c", "scripts/check_pinned_learnsets.py"}
    # Bounded data candidate: preserve the frame contract and independently
    # lock the exact learnset replacements before insertion can access an input.
    from check_pinned_learnsets import check_source_contract as check_learnsets
    check_learnsets()
    changed = set(git("diff", "--name-only", BASE, "--", "src", "include", "assembly", "scripts").splitlines())
    changed.update(git("ls-files", "--others", "--exclude-standard", "--", "src", "include", "assembly", "scripts").splitlines())
    require(changed <= allowed, "unapproved source/test change: " + str(sorted(changed - allowed)))

    frame = uncomment(read("src/m009_overworld_frame.c"))
    calls = body(frame, "M009_OverworldBasic")
    require(re.sub(r"\s+", "", calls) == "".join(name + "();" for name in ORDER),
            "frame sequence differs from canonical order")
    for canonical, legacy in ALIASES.items():
        require(re.search(canonical + r'\(void\)\s*__asm__\("' + legacy + r'"\)', frame),
                "unverified callee alias " + canonical)
    require("CB2_" not in frame and "VBlank" not in frame, "wrapper replaced")
    scan = uncomment(read("src/hidden_item_sparkle.c"))
    required = ("event->kind != BG_EVENT_HIDDEN_ITEM", "HIDDEN_ITEM_ITEM) == ITEM_NONE",
                "HIDDEN_ITEM_UNDERFOOT)", "FlagGet(itemFlag)", "GetCameraFocusCoords(&focusX, &focusY)",
                "FieldEffectStart(FLDEFF_SPARKLE)", "cache[0] != gSaveBlock1->location.mapGroup",
                "cache[1] != gSaveBlock1->location.mapNum", "memset(cache, 0, sizeof(gTasks[taskId].data))",
                "events->bgEventCount > M009_MAX_BG_EVENTS", "SetCooldown(cache, i, M009_SPARKLE_COOLDOWN)",
                "GetTaskCount() >= NUM_TASKS - 1", "gFieldEffectArguments[0] = event->x",
                "gFieldEffectArguments[1] = event->y", "gFieldEffectArguments[2] = 0")
    for fragment in required:
        require(fragment in scan, "missing scanner guard: " + fragment)
    require(re.sub(r"\s+", "", body(scan, "Task_M009SparkleCache")) == "(void)taskId;",
            "cache task must never scan/spawn")
    forbidden = r"CreateSprite|DestroySprite|FieldEffectStop|FieldEffectActiveListRemove|gSprites|[Pp]alette|Alloc\(|Calloc\(|FlagSet|FlagClear|FlagGet\(FLAG_"
    require(not re.search(forbidden, scan), "sprite/palette/flag ownership or heap allocation added")
    require(not re.search(r"0[xX][0-9a-fA-F]{7,}", scan + frame), "raw-address workaround added")
    require("static u8 s" not in scan and "EWRAM_DATA" not in scan, "ROM-backed mutable static cache")
    print("M-009 source ownership / exact frame sequence / preserved baseline checks PASS")


def check_map_census():
    for repo, revision, count in (
        ("cyansmp64-pokefirered-natdex", "16b8b9ffd77607debe7ce332cd50d3615f47e125", 426),
        ("pret-pokefirered", "e060ab955b5dc9ac1c4904c2cd141683615cf477", 425),
    ):
        root = ROOT.parent / "references" / repo
        paths = git("ls-tree", "-r", "--name-only", revision, "data/maps", root=root).splitlines()
        paths = [p for p in paths if p.endswith("/map.json")]
        require(len(paths) == count, "unexpected reference map inventory")
        census = [(len(json.loads(git("show", revision + ":" + p, root=root)).get("bg_events", [])), p)
                  for p in paths]
        require(max(census) == (36, "data/maps/CeladonCity_GameCorner/map.json"), "BG capacity changed")
        print(f"M-009 {repo}: {count} tracked maps; maximum BG events = 36 PASS")
    require("#define M009_MAX_BG_EVENTS 36" in read("include/new/hidden_item_sparkle.h"), "cache capacity mismatch")
    # The existing overlay program/manifests are baseline-locked above. Their
    # source operations preserve BG pointers/counts; no BG append operation exists.


def check_host_algorithm():
    # Compile actual scanner body with mocked engine services, not a Python
    # reimplementation. Only platform includes are substituted; target ABI,
    # graphics, and timing still require the ARM build and runtime acceptance.
    scan = re.sub(r'^#include[^\n]*\n', '', read("src/hidden_item_sparkle.c"), flags=re.M)
    header = re.sub(r'^#pragma once\n', '', read("include/new/hidden_item_sparkle.h"), flags=re.M)
    harness = read("scripts/tests/m009_sparkle_host.c")
    require(harness.count("/* SCANNER_SOURCE */") == 1, "host harness source boundary")
    with tempfile.TemporaryDirectory(prefix="m009-host-") as tmp:
        source = Path(tmp) / "scanner.c"
        binary = Path(tmp) / "scanner-test"
        source.write_text(harness.replace("/* SCANNER_SOURCE */", header + scan), encoding="utf-8")
        subprocess.run(["cc", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror",
                        "-fsanitize=undefined,bounds", str(source), "-o", str(binary)], check=True)
        subprocess.run([str(binary)], check=True)


def check_rejections():
    # Mutate read results in memory only: each invalid candidate must be rejected.
    global read
    original = read
    frame_path = "src/m009_overworld_frame.c"
    scan_path = "src/hidden_item_sparkle.c"
    cases = [
        ("duplicate rewrite", "functionrewrites", original("functionrewrites") + "\nM009_OverworldBasic 0x08056578 0 0\n"),
        ("retired owner", "bytereplacement", git("show", BASE + ":bytereplacement")),
        ("missing arrival", frame_path, original(frame_path).replace("    SetQuestLogEvent_Arrived();", "")),
        ("wrong OAM order", frame_path, original(frame_path).replace("    BuildOamBuffer();\n", "").replace("    UpdatePaletteFade();", "    UpdatePaletteFade();\n    BuildOamBuffer();")),
        ("early scanner", frame_path, original(frame_path).replace("    TryStartVisibleHiddenItemSparkles();\n", "").replace("    CameraUpdate();", "    TryStartVisibleHiddenItemSparkles();\n    CameraUpdate();")),
        ("missing flag check", scan_path, original(scan_path).replace("FlagGet(itemFlag)", "FALSE")),
        ("task spawn", scan_path, original(scan_path).replace("(void)taskId;", "(void)taskId; TryStartVisibleHiddenItemSparkles();")),
        ("wrong target", "functionrewrites", original("functionrewrites").replace("M009_OverworldBasic 0x08056578", "M009_OverworldBasic 0x080565A8")),
    ]
    try:
        for label, path, replacement in cases:
            read = lambda p: replacement if p == path else original(p)
            try:
                check_source_contract()
            except ValueError:
                continue
            raise AssertionError("invalid candidate was accepted: " + label)
    finally:
        read = original
    print(f"M-009 {len(cases)} in-memory invalid ownership/order/scanner candidates rejected PASS")


if __name__ == "__main__":
    check_source_contract()
    check_rejections()
    check_map_census()
    check_host_algorithm()
