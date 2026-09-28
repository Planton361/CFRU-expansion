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
PEWTER_OVERLAY_INCLUDE_ANCHOR = '#include "include/constants/items.h"\n'
PEWTER_OVERLAY_ROW_ANCHOR = "## replace mapBank mapNum expectedCount localId oldGraphicsId"
INSERTION_PREFLIGHT = "    from check_hidden_item_sparkle import check_source_contract\n    check_source_contract()\n"
M009_SYMBOL_REJECTION = ('                        if symbol == "M009_OverworldBasic":\n'
                         '                            raise ValueError("M-009 frame replacement symbol missing; refusing partial insertion")\n')


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


def normalized_rom_linker(source):
    pattern = re.compile(
        r"(?m)^(?P<prefix>[ \t]*rom[ \t]*:[ \t]*ORIGIN[ \t]*=[ \t]*)"
        r"(?P<expression>[^,\r\n]+?)(?P<spacing>[ \t]*)"
        r"(?P<suffix>,[ \t]*LENGTH[ \t]*=[ \t]*32M[ \t]*(?:\#.*)?)"
        r"(?P<newline>\r?\n|\Z)"
    )
    matches = list(pattern.finditer(source))
    require(len(matches) == 1, "linker.ld must contain exactly one rom ORIGIN region")
    match = matches[0]
    if re.fullmatch(r"\(\s*0x08000000\s*\+\s*0[xX][0-9a-fA-F]+\s*\)",
                    match.group("expression").strip()) is None:
        raise ValueError("M-009 fail-closed: linker.ld rom ORIGIN is not the expected FireRed offset form")
    return source[:match.start("expression")] + "<M009_ROM_ORIGIN>" + source[match.end("expression"):]


def check_pewter_overlay_composition():
    before = git("show", BASE + ":mapobjectoverlays")
    current = read("mapobjectoverlays")
    require(before.count(PEWTER_OVERLAY_INCLUDE_ANCHOR) == 1,
            "M-009 overlay baseline include anchor is not unique")
    require(before.count(PEWTER_OVERLAY_ROW_ANCHOR) == 1,
            "M-009 overlay baseline row anchor is not unique")
    expected = before.replace(PEWTER_OVERLAY_INCLUDE_ANCHOR,
                              PEWTER_OVERLAY_INCLUDE_ANCHOR + PEWTER_OVERLAY_INCLUDE, 1)
    expected = expected.replace(PEWTER_OVERLAY_ROW_ANCHOR,
                                PEWTER_OVERLAY_BLOCK + "\n\n" + PEWTER_OVERLAY_ROW_ANCHOR, 1)
    require(current == expected,
            "mapobjectoverlays changed outside the exact accepted #538 Pewter extension")


def check_source_contract():
    # Preserve the independent data guard; fail before insertion accesses its input.
    from check_coherent_learnsets import check_source_contract as check_learnsets
    check_learnsets()
    bpreLinker = read("BPRE.ld")
    bindingRows = re.findall(r"^(\w+)\s*=\s*(0x[0-9a-fA-F]+)\s*\|\s*1;", bpreLinker, re.M)
    for name, expectedAddress in EXPECTED_BINDINGS.items():
        matches = [int(value, 16) for symbol, value in bindingRows if symbol == name]
        require(matches == [expectedAddress], "unexpected or duplicate BPRE binding: " + name)

    expected = ["M009_OverworldBasic", "0x08056578", "0", "0"]
    rewrites = rows(read("functionrewrites"))
    named_rows = [row for row in rewrites if row and row[0] == "M009_OverworldBasic"]
    require(named_rows == [expected], "exactly one approved M-009 rewrite row must remain")
    target_rows = [row for row in rewrites if len(row) > 1 and int(row[1], 16) == EXPECTED_BINDINGS["OverworldBasic"]]
    require(target_rows == [expected], "duplicate/missing frame owner")

    byteOwners = [row for row in rows(read("bytereplacement"))
                  if row and int(row[0], 16) == EXPECTED_BINDINGS["OverworldBasic"]]
    require(not byteOwners, "old slow-camera byte owner remains")
    activeAsm = re.sub(r"(?m)^[ \t]*@[^\n]*", "", uncomment(read("special_inserts.asm")))
    require(not re.search(r"(?m)^[ \t]*(?:M009_)?OverworldBasic\s*:", activeAsm),
            "duplicate OverworldBasic assembler owner remains")

    require(normalized_rom_linker(read("linker.ld"))
            == normalized_rom_linker(git("show", BASE + ":linker.ld")),
            "linker.ld changed outside the selected ROM offset")
    check_pewter_overlay_composition()

    for path in ("hooks", "repoints", "repointall", "free_bytereplacements",
                 "src/overworld.c", "src/field_effects.c", "src/dexnav.c", "src/read_keys.c",
                 "src/dns.c", "src/Tables/movement_action.tables.c",
                 "include/config.h", "include/constants/flags.h",
                 "scripts/clean.py", "scripts/check_renewable_hidden_items.py"):
        require(read(path) == git("show", BASE + ":" + path), "out-of-contract change: " + path)
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
    first_rom_access = min(rom_accesses)
    require(main_body.index(INSERTION_PREFLIGHT) < first_rom_access,
            "M-009 preflight runs after ROM access")

    # M-013 is an independent, bounded successor. Keep its item.c changes
    # confined to the existing purchase callback; all frame guards remain.
    item = read("src/item.c")
    old_item = git("show", BASE + ":src/item.c")
    callback = "Task_ReturnToItemListAfterItemPurchase"
    require(item.replace(body(item, callback), "") == old_item.replace(body(old_item, callback), ""),
            "item changes outside the M-013 purchase callback")
    allowed = {"src/m009_overworld_frame.c", "src/hidden_item_sparkle.c", "src/item.c",
               "scripts/check_premier_bonus.py", "scripts/tests/m013_premier_host.c",
               "include/new/hidden_item_sparkle.h", "scripts/insert.py",
               "scripts/check_hidden_item_sparkle.py", "scripts/tests/m009_sparkle_host.c",
               "scripts/make.py", "scripts/tests/test_make_assignment_updates.py",
               "src/Tables/level_up_learnsets.c", "scripts/check_coherent_learnsets.py",
               # Independent CFRU Standard AI source-only milestone.  Keep its
               # exact file set explicit so this gate still fails closed for
               # unrelated source, assembly, or data edits.
               "include/battle.h", "include/global.h", "include/new/ai_standard.h",
               "include/new/ai_standard_policy.h", "src/Battle_AI/ai_master.c",
               "src/Battle_AI/ai_standard.c", "src/Battle_AI/ai_standard_policy.c",
               "src/util.c", "scripts/tests/audit_standard_ai.py",
               "scripts/tests/run_standard_ai_tests.py",
               "scripts/tests/standard_ai_layout_host.c",
               "scripts/tests/standard_ai_policy_host.c",
               "include/new/ai_standard_mechanics.h", "src/Battle_AI/ai_standard_mechanics.c",
               "scripts/tests/standard_ai_adapter_host.c", "src/battle_controller_opponent.c",
               "src/battle_anims.c", "src/battle_util.c",
               # Independent CFRU Ironmon Smart fair-adapter milestone.
               "include/new/ai_ironmon.h", "include/new/ai_ironmon_policy.h",
               "src/Battle_AI/ai_ironmon.c", "src/Battle_AI/ai_ironmon_policy.c",
               "scripts/tests/audit_ironmon_ai.py", "scripts/tests/run_ironmon_ai_tests.py",
               "scripts/tests/ironmon_history_clear_host.c",
               # Previously accepted trainer-AI safety / settings follow-ups.
               "include/new/ai_damage_engine_overrides.inc", "include/new/ai_master.h",
               "include/new/ai_opponent_replacement.h", "include/new/battle_controller_opponent.h",
               "include/new/battle_strings.h", "include/new/settings.h", "src/battle_strings.c",
               "src/general_bs_commands.c", "src/option_menu.c", "src/switching.c",
               "scripts/tests/ai_runtime_differential.py", "scripts/tests/ai_runtime_quality_host.c",
               "scripts/tests/audit_ai_controller_fallback.py", "scripts/tests/audit_ai_damage_overrides.py",
               "scripts/tests/audit_ai_writable_state.py", "scripts/tests/audit_opponent_replacement.py",
               "scripts/tests/audit_runtime_dispatch_closure.py", "scripts/tests/audit_settings_defaults.py",
               "scripts/tests/audit_trainer_ai_storage.py", "scripts/tests/controller_fallback_host.c",
               "scripts/tests/opponent_replacement_host.c", "scripts/tests/run_ai_controller_fallback_tests.py",
               "scripts/tests/run_ai_runtime_quality_tests.py", "scripts/tests/run_replacement_safety_tests.py",
               "scripts/tests/settings_defaults_host.c",
               # Accepted #538 Fresh New Game / Pewter Aide cleanup and current build support.
               "assembly/overworld_scripts/pewter_running_shoes_cleanup.s", "scripts/build.py",
               "scripts/tests/audit_early_running_pewter.py", "scripts/tests/run_early_running_pewter_tests.py",
               "scripts/tests/run_settings_defaults_tests.py", "src/config.h", "src/save.c", "src/settings.c"}
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
    forbidden = (r"CreateSprite|DestroySprite|FieldEffectStop|FieldEffectActiveListRemove|gSprites|"
                 r"[Pp]alette|Pltt|\b(?:malloc|calloc|realloc|free|Alloc|Calloc)\s*\(|"
                 r"FlagSet|FlagClear|FlagGet\(FLAG_|VarSet|VarGet\(VAR_")
    require(not re.search(forbidden, scan), "sprite/palette/flag ownership or heap allocation added")
    require(not re.search(r"\bgSaveBlock[12](?:->|\.)[^;\n]*(?:=(?!=)|\+\+|--|\+=|-=)", scan),
            "persistent save-block mutation added")
    require(not re.search(r"0[xX][0-9a-fA-F]{7,}", scan + frame), "raw-address workaround added")
    require("static u8 s" not in scan and "EWRAM_DATA" not in scan, "ROM-backed mutable static cache")
    print("M-009 frame, scanner, preflight and accepted-composition invariants PASS")


def check_composition_variants():
    # make.py changes only this offset before building and the preflight runs.
    global read
    original = read
    offset = "0x1234560"
    linker = original("linker.ld").replace("(0x08000000 + 0x1000000)",
                                           "(0x08000000 + " + offset + ")", 1)
    inserter = original("scripts/insert.py").replace(
        "OFFSET_TO_PUT = 0x1000000", "OFFSET_TO_PUT = " + offset, 1)
    require(linker != original("linker.ld") and inserter != original("scripts/insert.py"),
            "dynamic insertion-offset fixture did not change both files")
    try:
        read = lambda path: linker if path == "linker.ld" else inserter if path == "scripts/insert.py" else original(path)
        check_source_contract()
    finally:
        read = original
    print("M-009 composition with the semantic make.py linker/insert offset update PASS")


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
    rewrite_path = "functionrewrites"
    insert_path = "scripts/insert.py"
    overlay_path = "mapobjectoverlays"
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
        ("missing accepted Pewter overlay row", overlay_path,
         original(overlay_path).replace(PEWTER_OVERLAY_BLOCK.splitlines()[-1] + "\n", "", 1)),
        ("mutated accepted Pewter overlay row", overlay_path,
         original(overlay_path).replace("EventScript_PewterRunningShoesCleanup",
                                        "EventScript_Unapproved", 1)),
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
    print(f"M-009 {len(cases)} in-memory ownership/preflight/composition mutations rejected PASS")


if __name__ == "__main__":
    check_source_contract()
    check_composition_variants()
    check_rejections()
    check_map_census()
    check_host_algorithm()
