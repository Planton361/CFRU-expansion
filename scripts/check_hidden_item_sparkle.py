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
ROUTE10_OVERLAY_ROW = ("append_object_exact 3 28 10 5 0 8 11 0x38 17 22 0 "
                       "MOVEMENT_TYPE_FACE_LEFT 0 0 0 0 EventScript_Route10HM05 FLAG_GOT_HM05 0")
ORDER = ["ScriptContext_RunScript", "RunTasks", "AnimateSprites", "CameraUpdate",
         "SetQuestLogEvent_Arrived", "UpdateCameraPanning", "BuildOamBuffer",
         "UpdatePaletteFade", "UpdateTilesetAnimations",
         "DoScheduledBgTilemapCopiesToVram", "TryStartVisibleHiddenItemSparkles"]
ALIASES = {"ScriptContext_RunScript": "ScriptContext2_RunScript",
           "SetQuestLogEvent_Arrived": "sub_8115798"}
EXPECTED_BINDINGS = {
    "OverworldBasic": 0x08056578,
    "CB2_OverworldBasic": 0x080565A8,
    "CB2_Overworld": 0x080565B4,
    "ScriptContext2_RunScript": 0x08069AA8,
    "RunTasks": 0x08077578,
    "AnimateSprites": 0x08006B5C,
    "CameraUpdate": 0x0805ABB0,
    "sub_8115798": 0x08115798,
    "UpdateCameraPanning": 0x0805AE28,
    "BuildOamBuffer": 0x08006BA8,
    "UpdatePaletteFade": 0x080704D0,
    "UpdateTilesetAnimations": 0x0806FFBC,
    "DoScheduledBgTilemapCopiesToVram": 0x080F67B8,
}
PEWTER_OVERLAY_BLOCK = """## #538: public pret Pewter City (map bank 3, map 2) has 7 objects, 7
## warps, 7 CoordEvents, and 6 BG events. Replace only the final object
## (Running-Shoes Aide; local ID 7) and the three scene-1 trigger pointers.
## Every authored field below is checked before its single pointer is written.
## replace_object_script_exact mapBank mapNum objects warps coords bg objectIndex localId graphicsId x y elevation movement rangeX rangeY trainerType trainerRange hideFlag hideFlag2 script
replace_object_script_exact 3 2 7 7 7 6 6 7 0x0037 46 20 3 MOVEMENT_TYPE_FACE_RIGHT 1 1 0 0 FLAG_HIDE_PEWTER_CITY_RUNNING_SHOES_GUY 0 EventScript_PewterRunningShoesCleanup
## replace_coord_script_exact mapBank mapNum objects warps coords bg coordIndex x y elevation sceneVar sceneValue script
replace_coord_script_exact 3 2 7 7 7 6 4 46 21 3 VAR_MAP_SCENE_PEWTER_CITY 1 EventScript_PewterRunningShoesCleanup
replace_coord_script_exact 3 2 7 7 7 6 5 46 22 3 VAR_MAP_SCENE_PEWTER_CITY 1 EventScript_PewterRunningShoesCleanup
replace_coord_script_exact 3 2 7 7 7 6 6 46 23 3 VAR_MAP_SCENE_PEWTER_CITY 1 EventScript_PewterRunningShoesCleanup"""
PEWTER_OVERLAY_INCLUDE = '#include "include/constants/vars.h"\n'
INSERTION_PREFLIGHT = "    from check_hidden_item_sparkle import check_source_contract\n    check_source_contract()\n"
M009_SYMBOL_REJECTION = ('                        if symbol == "M009_OverworldBasic":\n'
                         '                            raise ValueError("M-009 frame replacement symbol missing; refusing partial insertion")\n')
OVERLAY_ARITIES = {
    "replace_scene_scripts": 14,
    "replace_conditional_map_script": 15,
    "replace_object_script_exact": 21,
    "replace_coord_script_exact": 14,
    "append_object_exact": 20,
    "append_coord": 13,
    "append": 17,
    "replace": 29,
    "replace_graphics": (18, 31),
    "replace_script": 16,
}


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


def parse_overlay_rows(source):
    parsed = []
    for line_number, line in enumerate(source.splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        fields = stripped.split()
        command = fields[0].lower()
        require(command in OVERLAY_ARITIES,
                "unknown mapobjectoverlays command at line " + str(line_number))
        expected = OVERLAY_ARITIES[command]
        allowed = expected if isinstance(expected, tuple) else (expected,)
        require(len(fields) in allowed,
                "malformed mapobjectoverlays command at line " + str(line_number))
        parsed.append((line_number, fields))
    return parsed


def check_pewter_overlay_composition():
    current = read("mapobjectoverlays")
    parsed = parse_overlay_rows(current)
    expected_rows = [fields for _, fields in parse_overlay_rows(PEWTER_OVERLAY_BLOCK)]
    owned_commands = {"replace_object_script_exact", "replace_coord_script_exact"}
    pewter_rows = [
        (line_number, fields) for line_number, fields in parsed
        if fields[0].lower() in owned_commands
        and fields[1:3] == ["3", "2"]
        and ((fields[0].lower() == "replace_object_script_exact"
              and fields[7:9] == ["6", "7"])
             or (fields[0].lower() == "replace_coord_script_exact"
                 and fields[7] in {"4", "5", "6"}))
    ]
    expected_owned = [fields for fields in expected_rows
                      if fields[0] in owned_commands and fields[1:3] == ["3", "2"]]
    object_rows = [fields for _, fields in pewter_rows if fields[0].lower() == "replace_object_script_exact"]
    coord_rows = [fields for _, fields in pewter_rows if fields[0].lower() == "replace_coord_script_exact"]
    expected_objects = [fields for fields in expected_owned if fields[0] == "replace_object_script_exact"]
    expected_coords = [fields for fields in expected_owned if fields[0] == "replace_coord_script_exact"]
    require(object_rows == expected_objects and len(object_rows) == 1,
            "#538 Pewter object replacement differs from its exact owned contract")
    require(coord_rows == expected_coords and len(coord_rows) == 3,
            "#538 Pewter CoordEvent replacements differ from their exact owned contract")

    vars_includes = [(line_number, line.strip()) for line_number, line in enumerate(current.splitlines(), 1)
                     if line.strip() == PEWTER_OVERLAY_INCLUDE.strip()]
    require(len(vars_includes) == 1, "#538 Pewter VAR constants include must exist exactly once")
    require(vars_includes[0][0] < min(line_number for line_number, _ in pewter_rows),
            "#538 Pewter VAR constants include must precede its owned rows")
    owned_symbols = ("VAR_MAP_SCENE_PEWTER_CITY", "FLAG_HIDE_PEWTER_CITY_RUNNING_SHOES_GUY",
                     "MOVEMENT_TYPE_FACE_RIGHT")
    for symbol in owned_symbols:
        require(re.search(r"(?m)^\s*#\s*define\s+" + re.escape(symbol) + r"\b", current) is None,
                "#538 Pewter constants must remain owned by their canonical includes: " + symbol)


def check_route10_overlay_composition():
    parsed = parse_overlay_rows(read("mapobjectoverlays"))
    route10_rows = [fields for _, fields in parsed
                    if fields[0].lower() == "append_object_exact"
                    and fields[1:3] == ["3", "28"]
                    and fields[7] == "11"]
    require(route10_rows == [ROUTE10_OVERLAY_ROW.split()],
            "#557 Route 10 HM05 object row differs from its exact owned contract")


def check_linker_insert_contract(linker, inserter):
    offset_assignments = re.findall(
        r"(?m)^OFFSET_TO_PUT\s*=\s*(0[xX][0-9a-fA-F]+|[0-9]+)\s*$", inserter)
    require(len(offset_assignments) == 1, "insert.py must have one insertion offset")
    offset = int(offset_assignments[0], 0)
    pattern = re.compile(
        r"(?m)^\s*rom\s*:\s*ORIGIN\s*=\s*\(\s*0x08000000\s*\+\s*(0[xX][0-9a-fA-F]+)\s*\)"
        r"\s*,\s*LENGTH\s*=\s*32M\s*$"
    )
    rom_regions = list(pattern.finditer(linker))
    require(len(rom_regions) == 1 and int(rom_regions[0].group(1), 16) == offset,
            "linker ROM origin must match insert.py's selected offset and preserve the 32M region")
    require(len(re.findall(r"(?m)^\s*ewram\s*:\s*ORIGIN\s*=\s*0x02000000\s*,\s*LENGTH\s*=\s*4M\s*-\s*4k\s*$",
                           linker)) == 1,
            "linker EWRAM region differs from its required ABI boundary")
    required_layout = (
        r"FILL\s*\(0xABCD\)", r"__text_start\s*=", r"\*\(\.init\)", r"\*\(\.text\)",
        r"\*\(\.ctors\)", r"\*\(\.dtors\)", r"\*\(\.rodata\)", r"\*\(\.fini\)",
        r"\*\(COMMON\)", r"__text_end\s*=", r"__bss_start__\s*=", r"\*\(\.bss\)",
        r"__bss_end__\s*=", r"_end\s*=\s*__bss_end__", r"__end__\s*=\s*__bss_end__",
        r"\}\s*>rom\s*=\s*0xff",
    )
    positions = []
    for token in required_layout:
        matches = list(re.finditer(token, linker))
        require(len(matches) == 1, "linker insertion layout is missing or duplicates " + token)
        positions.append(matches[0].start())
    require(positions == sorted(positions), "linker text/BSS insertion layout order changed")


def check_stateless_frame_entry():
    # #583 removes #577's ROM-backed queue. Keep the frame entry free of
    # deferred settings work; settings belong to CB2_NewGame, not M-009.
    current_frame = body(read("src/overworld.c"), "TryRunOnFrameMapScript")
    require(current_frame.lstrip().startswith("TryUpdateSwarm();")
            and current_frame.count("TryUpdateSwarm();") == 1,
            "frame-script entry must retain one swarm update")
    require(not re.search(r"FreshNewGame|SettingsPending", current_frame),
            "Fresh New Game state must not be deferred to the frame path")


def check_m009_feature_contract():
    # This function owns M-009 and #538 Pewter rows only. Other manifest
    # owners compose independently; check_source_contract aggregates them.
    bpre_linker = read("BPRE.ld")
    binding_rows = re.findall(r"^(\w+)\s*=\s*(0x[0-9a-fA-F]+)\s*\|\s*1;", bpre_linker, re.M)
    for name, expected_address in EXPECTED_BINDINGS.items():
        matches = [int(value, 16) for symbol, value in binding_rows if symbol == name]
        require(matches == [expected_address], "unexpected or duplicate BPRE binding: " + name)

    expected = ["M009_OverworldBasic", "0x08056578", "0", "0"]
    rewrites = rows(read("functionrewrites"))
    named_rows = [row for row in rewrites if row and row[0] == "M009_OverworldBasic"]
    require(named_rows == [expected], "exactly one approved M-009 rewrite row must remain")
    target_rows = [row for row in rewrites
                   if len(row) > 1 and int(row[1], 16) == EXPECTED_BINDINGS["OverworldBasic"]]
    require(target_rows == [expected], "duplicate/missing frame owner")

    byte_owners = [row for row in rows(read("bytereplacement"))
                   if row and int(row[0], 16) == EXPECTED_BINDINGS["OverworldBasic"]]
    require(not byte_owners, "old slow-camera byte owner remains")
    active_asm = re.sub(r"(?m)^[ \t]*@[^\n]*", "", uncomment(read("special_inserts.asm")))
    require(not re.search(r"(?m)^[ \t]*(?:M009_)?OverworldBasic\s*:", active_asm),
            "duplicate OverworldBasic assembler owner remains")

    hook_rows = rows(read("hooks"))
    for name, address in (("TryRunOnFrameMapScript", 0x08069C74),
                          ("AutoRunHook", 0x0805BA30),
                          ("FieldGetPlayerInputLButtonHook", 0x0806C9AC)):
        owned = [row for row in hook_rows if row[0] == name]
        targets = [row for row in hook_rows
                   if len(row) > 1 and int(row[1], 16) == address]
        require(len(owned) == 1 and int(owned[0][1], 16) == address
                and owned[0][2:] == ["0"] and targets == [owned[0]],
                "unexpected or duplicate hook owner: " + name)

    check_linker_insert_contract(read("linker.ld"), read("scripts/insert.py"))
    check_pewter_overlay_composition()
    check_stateless_frame_entry()

    inserter = read("scripts/insert.py")
    require(inserter.count(INSERTION_PREFLIGHT) == 1, "M-009 insertion preflight must exist exactly once")
    require(inserter.count(M009_SYMBOL_REJECTION) == 1,
            "M-009 compiled-symbol rejection must exist exactly once")
    require(inserter.count("def main():\n") == 1, "insertion main entry must exist exactly once")
    main_body = inserter.split("def main():\n", 1)[1]
    require(main_body.startswith(INSERTION_PREFLIGHT), "M-009 preflight does not run first in insertion main")
    rom_accesses = [index for index in (
        main_body.find("shutil.copyfile(SOURCE_ROM"),
        main_body.find("open(SOURCE_ROM"),
        main_body.find("open(ROM_NAME"),
    ) if index >= 0]
    require(bool(rom_accesses), "insertion main has no recognizable ROM access boundary")
    require(main_body.index(INSERTION_PREFLIGHT) < min(rom_accesses),
            "M-009 preflight runs after ROM access")

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
    forbidden = (r"CreateSprite|DestroySprite|FieldEffectStop|FieldEffectActiveListRemove|gSprites|"
                 r"[Pp]alette|Pltt|\b(?:malloc|calloc|realloc|free|Alloc|Calloc)\s*\(|"
                 r"FlagSet|FlagClear|FlagGet\(FLAG_|VarSet|VarGet\(VAR_")
    require(not re.search(forbidden, scan), "sprite/palette/flag ownership or heap allocation added")
    require(not re.search(r"\bgSaveBlock[12](?:->|\.)[^;\n]*(?:=(?!=)|\+\+|--|\+=|-=)", scan),
            "persistent save-block mutation added")
    require(not re.search(r"0[xX][0-9a-fA-F]{7,}", scan + frame), "raw-address workaround added")
    require("static u8 s" not in scan and "EWRAM_DATA" not in scan, "ROM-backed mutable static cache")
    require("#define M009_MAX_BG_EVENTS 36" in read("include/new/hidden_item_sparkle.h"),
            "M-009 scanner capacity no longer matches the source-backed BG-event bound")
    print("M-009 frame, scanner, Pewter owner, stateless frame entry, and insertion invariants PASS")


def check_source_contract():
    # Data and insertion safety are feature-owned; historical change lists are
    # intentionally not consulted here.
    from check_coherent_learnsets import check_source_contract as check_learnsets
    check_learnsets()
    check_m009_feature_contract()
    check_route10_overlay_composition()
    parse_overlay_rows(read("mapobjectoverlays"))


def check_composition_variants():
    # Owner checks compose: M-009/#538 Pewter does not take ownership of
    # Route 10, and unrelated accepted source in shared files does not inherit
    # historical whole-file locks.
    global read
    original = read
    offset = "0x1234560"
    linker = original("linker.ld").replace("(0x08000000 + 0x1000000)",
                                           "(0x08000000 + " + offset + ")", 1)
    inserter = original("scripts/insert.py").replace(
        "OFFSET_TO_PUT = 0x1000000", "OFFSET_TO_PUT = " + offset, 1)
    require(linker != original("linker.ld") and inserter != original("scripts/insert.py"),
            "dynamic insertion-offset fixture did not change both files")
    route10_row = ROUTE10_OVERLAY_ROW
    current_overlay = original("mapobjectoverlays")
    require(current_overlay.splitlines().count(route10_row) == 1,
            "accepted #557 Route 10 fixture row is not unique")
    pewter_only_overlay = current_overlay.replace(route10_row + "\n", "", 1)
    require(pewter_only_overlay != current_overlay, "could not form the #538-only overlay fixture")
    adjacent_pewter_owner = (
        "replace_object_script_exact 3 2 7 7 7 6 5 6 0x0037 45 20 3 "
        "MOVEMENT_TYPE_FACE_RIGHT 1 1 0 0 FLAG_HIDE_PEWTER_CITY_RUNNING_SHOES_GUY "
        "0 EventScript_PewterRunningShoesCleanup"
    )
    adjacent_route10_owner = (
        "append_object_exact 3 28 11 5 0 8 12 0x38 18 22 0 "
        "MOVEMENT_TYPE_FACE_LEFT 0 0 0 0 EventScript_Route10HM05 0 0"
    )
    composed_overlay = current_overlay + adjacent_pewter_owner + "\n" + adjacent_route10_owner + "\n"
    try:
        read = lambda path: (linker if path == "linker.ld" else
                             inserter if path == "scripts/insert.py" else
                             pewter_only_overlay if path == "mapobjectoverlays" else original(path))
        check_m009_feature_contract()
        read = lambda path: (linker if path == "linker.ld" else
                             inserter if path == "scripts/insert.py" else
                             composed_overlay if path == "mapobjectoverlays" else
                             original(path) + "\n/* unrelated accepted source */\n"
                             if path == "src/overworld.c" else original(path))
        check_source_contract()
    finally:
        read = original
    print("M-009/Pewter/Route 10 owner composition and unrelated-source witness PASS")


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
    # The compositional parser and row owners prevent these operations from
    # changing BG-event counts or pointers; no overlay command appends BG rows.


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
    rewrite_path = "functionrewrites"
    insert_path = "scripts/insert.py"
    overlay_path = "mapobjectoverlays"
    overworld_path = "src/overworld.c"
    rewrite_row = "M009_OverworldBasic 0x08056578 0 0\n"
    cases = [
        ("duplicate rewrite", rewrite_path, original(rewrite_path) + "\n" + rewrite_row),
        ("missing rewrite", rewrite_path, original(rewrite_path).replace(rewrite_row, "", 1)),
        ("mutated rewrite target", rewrite_path,
         original(rewrite_path).replace("M009_OverworldBasic 0x08056578", "M009_OverworldBasic 0x080565A8", 1)),
        ("retired owner", "bytereplacement", git("show", BASE + ":bytereplacement")),
        ("missing arrival", frame_path, original(frame_path).replace("    SetQuestLogEvent_Arrived();", "")),
        ("wrong OAM order", frame_path, original(frame_path).replace("    BuildOamBuffer();\n", "").replace("    UpdatePaletteFade();", "    UpdatePaletteFade();\n    BuildOamBuffer();")),
        ("early scanner", frame_path, original(frame_path).replace("    TryStartVisibleHiddenItemSparkles();\n", "").replace("    CameraUpdate();", "    TryStartVisibleHiddenItemSparkles();\n    CameraUpdate();")),
        ("missing flag check", scan_path, original(scan_path).replace("FlagGet(itemFlag)", "FALSE")),
        ("task spawn", scan_path, original(scan_path).replace("(void)taskId;", "(void)taskId; TryStartVisibleHiddenItemSparkles();")),
        ("heap allocation", scan_path,
         original(scan_path).replace("FieldEffectStart(FLDEFF_SPARKLE)", "malloc(1); FieldEffectStart(FLDEFF_SPARKLE)", 1)),
        ("palette ownership", scan_path,
         original(scan_path).replace("FieldEffectStart(FLDEFF_SPARKLE)", "gPlttBufferUnfaded[0] = 0; FieldEffectStart(FLDEFF_SPARKLE)", 1)),
        ("persistent save mutation", scan_path,
         original(scan_path).replace("FieldEffectStart(FLDEFF_SPARKLE)",
                                     "gSaveBlock1->location.mapGroup = 0; FieldEffectStart(FLDEFF_SPARKLE)", 1)),
        ("missing insertion preflight", insert_path,
         original(insert_path).replace(INSERTION_PREFLIGHT, "", 1)),
        ("duplicate insertion preflight", insert_path,
         original(insert_path).replace(INSERTION_PREFLIGHT, INSERTION_PREFLIGHT * 2, 1)),
        ("mutated insertion preflight", insert_path,
         original(insert_path).replace("check_source_contract()", "check_host()", 1)),
        ("missing compiled-symbol rejection", insert_path,
         original(insert_path).replace(M009_SYMBOL_REJECTION, "", 1)),
        ("duplicate compiled-symbol rejection", insert_path,
         original(insert_path).replace(M009_SYMBOL_REJECTION, M009_SYMBOL_REJECTION * 2, 1)),
        ("mutated compiled-symbol rejection", insert_path,
         original(insert_path).replace("M-009 frame replacement symbol missing; refusing partial insertion",
                                       "M-009 frame replacement symbol missing", 1)),
        ("unrelated linker drift", "linker.ld",
         original("linker.ld").replace("ewram   : ORIGIN = 0x02000000", "ewram   : ORIGIN = 0x02001000", 1)),
        ("deferred settings frame work", overworld_path,
         original(overworld_path).replace("TryUpdateSwarm();",
                                          "ApplyFreshNewGameSettings();\n\tTryUpdateSwarm();", 1)),
        ("duplicate frame swarm update", overworld_path,
         original(overworld_path).replace("TryUpdateSwarm();",
                                          "TryUpdateSwarm();\n\tTryUpdateSwarm();", 1)),
    ]
    overlay_source = original(overlay_path)
    pewter_rows = [line for line in PEWTER_OVERLAY_BLOCK.splitlines()
                   if line.startswith(("replace_object_script_exact 3 2 ",
                                       "replace_coord_script_exact 3 2 "))]
    require(len(pewter_rows) == 4, "expected #538 owned row fixture is incomplete")
    for index, row in enumerate(pewter_rows):
        label = "Pewter object" if index == 0 else "Pewter CoordEvent " + str(index)
        cases.extend((
            ("missing " + label, overlay_path, overlay_source.replace(row + "\n", "", 1)),
            ("mutated " + label, overlay_path,
             overlay_source.replace(row, row.replace("EventScript_PewterRunningShoesCleanup",
                                                     "EventScript_Unapproved", 1), 1)),
            ("duplicated " + label, overlay_path, overlay_source + row + "\n"),
        ))
    cases.extend((
        ("missing Pewter constants include", overlay_path,
         overlay_source.replace(PEWTER_OVERLAY_INCLUDE, "", 1)),
        ("duplicate Pewter constants include", overlay_path,
         overlay_source + PEWTER_OVERLAY_INCLUDE),
        ("mutated Route 10 owned row", overlay_path,
         overlay_source.replace(ROUTE10_OVERLAY_ROW,
                                ROUTE10_OVERLAY_ROW.replace("EventScript_Route10HM05",
                                                             "EventScript_Unapproved"), 1)),
        ("duplicate Route 10 owned row", overlay_path,
         overlay_source + ROUTE10_OVERLAY_ROW + "\n"),
        ("malformed Route 10 overlay row", overlay_path,
         overlay_source.replace("FLAG_GOT_HM05 0\n", "FLAG_GOT_HM05\n", 1)),
        ("unknown overlay command", overlay_path,
         overlay_source + "append_unreviewed 3 28\n"),
    ))
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
    print(f"M-009 {len(cases)} in-memory ownership/preflight/composition mutations rejected PASS")


if __name__ == "__main__":
    check_source_contract()
    check_composition_variants()
    check_rejections()
    check_map_census()
    check_host_algorithm()
