#!/usr/bin/env python3
"""Source-owned lifecycle and scene contract checks for Workspace #538/#577."""

from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]
START_SHA = "c9a7f19f1e8aaebd33213503f32fa7bba59ce81c"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit("early-running/Pewter audit failed: " + message)


def main() -> int:
    settings = read("src/settings.c")
    save = read("src/save.c")
    hooks = read("assembly/hooks/general_hooks.s")
    scripting = read("src/scripting.c")
    config = read("src/config.h")
    overworld = read("src/overworld.c")
    read_keys = read("src/read_keys.c")
    overlays = read("mapobjectoverlays")
    cleanup = read("assembly/overworld_scripts/pewter_running_shoes_cleanup.s")

    fresh_settings = settings[settings.index("void ApplyFreshNewGameSettings(void)"):]
    fresh_settings = fresh_settings.split("void ApplyIronmonSmartSettingsPreset(void)", 1)[0]
    require(fresh_settings.count("FlagSet(FLAG_RUNNING_ENABLED);") == 1,
            "fresh initialization does not set the existing running-enabled flag exactly once")
    require("FLAG_AUTO_RUN" not in fresh_settings,
            "fresh initialization implicitly sets or clears Auto-Run")
    require("#define FLAG_RUNNING_ENABLED 0x82F" in config,
            "FLAG_RUNNING_ENABLED is no longer defined at its existing ID")
    require("#define FLAG_AUTO_RUN 0x914" in config,
            "FLAG_AUTO_RUN is no longer defined independently")

    wipe = save[save.index("void NewGameWipeNewSaveData(void)"):]
    require("QueueFreshNewGameSettings();" in wipe, "Fresh New Game does not queue its settings initializer")
    require(wipe.index("QueueFreshNewGameSettings();") > wipe.index("#endif"),
            "Fresh New Game settings are not queued after both wipe branches finish")
    require("ApplyFreshNewGameSettings();" not in wipe,
            "Fresh New Game settings are applied before the later vanilla event reset")
    require("NewGameSaveClearHook:" in hooks and "bl NewGameWipeNewSaveData" in hooks,
            "the existing New Game hook no longer owns the wipe lifecycle")
    require("ApplyFreshNewGameSettings();" not in scripting and "QueueFreshNewGameSettings();" not in scripting,
            "ordinary save loading invokes fresh initialization")
    frame_script = overworld[overworld.index("bool8 TryRunOnFrameMapScript(void)"):]
    frame_script = frame_script.split("// Whiteout Hack", 1)[0]
    require(frame_script.index("ApplyQueuedFreshNewGameSettings();")
            < frame_script.index("TryUpdateSwarm();"),
            "queued settings are not applied before post-load field input/scripts")

    should_run = overworld[overworld.index("bool8 ShouldPlayerRun(u16 heldKeys)"):]
    should_run = should_run.split("static bool8 IsRunningDisabledByFlag(void)", 1)[0]
    require("IsRunningDisallowed(gEventObjects[gPlayerAvatar->eventObjectId].currentMetatileBehavior)" in should_run,
            "normal running no longer checks the current metatile")
    require("IsDexNavHudActive()" in should_run, "DexNav running restriction was removed")
    require("FlagGet(FLAG_AUTO_RUN)" in should_run and "if (heldKeys & B_BUTTON)" in should_run,
            "Auto-Run or B-button behavior changed")
    disallowed = overworld[overworld.index("bool8 IsRunningDisallowed(u8 tile)"):]
    disallowed = disallowed.split("bool8 IsRunningDisallowedByMetatile", 1)[0]
    require("IsRunningDisabledByFlag()" in disallowed and "IsRunningDisallowedByMetatile(tile)" in disallowed,
            "running-enabled or metatile restriction was removed")
    require("gMapHeader.mapType == MAP_TYPE_UNDERWATER" in disallowed,
            "underwater running restriction was removed")
    require("GetCurrentMapType() == MAP_TYPE_INDOOR" in disallowed,
            "existing indoor-running restriction was removed")
    l_toggle = read_keys[read_keys.index("if (FlagGet(FLAG_RUNNING_ENABLED))"):]
    l_toggle = l_toggle.split("return TRUE;", 1)[0]
    require("FlagGet(FLAG_AUTO_RUN)" in l_toggle and "FlagSet(FLAG_AUTO_RUN)" in l_toggle
            and "FlagClear(FLAG_AUTO_RUN)" in l_toggle,
            "L Auto-Run no longer remains gated by running availability")

    required_script = (
        ".global EventScript_PewterRunningShoesCleanup",
        "lockall",
        "setvar VAR_MAP_SCENE_PEWTER_CITY 2",
        "setflag FLAG_HIDE_PEWTER_CITY_RUNNING_SHOES_GUY",
        "removeobject LOCALID_PEWTER_RUNNING_SHOES_AIDE",
        "releaseall",
        "end",
    )
    for fragment in required_script:
        require(fragment in cleanup, "cleanup script is missing " + fragment)
    commandOrder = [cleanup.index(fragment) for fragment in required_script[1:]]
    require(commandOrder == sorted(commandOrder), "cleanup control release/order changed")
    for forbidden in (
        "clearflag", "FLAG_RUNNING_ENABLED", "FLAG_AUTO_RUN", "msgbox", "msgbox", "letter",
        "Mom", "applymovement", "waitmovement", "faceplayer", "RunningShoesAideTrigger",
    ):
        require(forbidden.lower() not in cleanup.lower(), "cleanup script contains obsolete content: " + forbidden)

    pewterRows = [line.split() for line in overlays.splitlines()
                  if line.strip().startswith(("replace_object_script_exact 3 2", "replace_coord_script_exact 3 2"))]
    require(len(pewterRows) == 4, "Pewter must have exactly one Aide and three coordinate pointer replacements")
    require(all(row[1:3] == ["3", "2"] for row in pewterRows),
            "Pewter cleanup targets a map other than public Pewter City")
    require(not any("Brock" in row[-1] or "Brock" in " ".join(row) for row in pewterRows),
            "Pewter cleanup unexpectedly replaces Brock reward flow")
    require(all(row[-1] == "EventScript_PewterRunningShoesCleanup" for row in pewterRows),
            "all four Aide paths do not share the fast cleanup script")

    # The accepted Pewter and control path remain byte-identical to the exact
    # repair base; this scope only changes Fresh New Game initialization.
    unchanged = subprocess.run(
        ["git", "diff", "--quiet", START_SHA, "--", "eventscripts", "mapobjectoverlays",
         "assembly/overworld_scripts/pewter_running_shoes_cleanup.s", "assembly/hooks/general_hooks.s",
         "hooks", "src/read_keys.c"],
        cwd=ROOT,
        check=False,
    )
    require(unchanged.returncode == 0,
            "Pewter cleanup, object/coord overlays, movement hook or L-toggle changed from exact start")

    print("Fresh running lifecycle and Pewter Aide cleanup source audit: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
