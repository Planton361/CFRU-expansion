#!/usr/bin/env python3
"""Source-owned lifecycle and scene contract checks for Workspace #538."""

from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]
START_SHA = "d851256f2bb897042fbe865b4533e55fc7586ba9"


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
    require("ApplyFreshNewGameSettings();" in wipe, "Fresh New Game does not call the settings initializer")
    require(wipe.index("ApplyFreshNewGameSettings();") > wipe.index("#endif"),
            "Fresh New Game settings run before the relevant wipe branches finish")
    require("NewGameSaveClearHook:" in hooks and "bl NewGameWipeNewSaveData" in hooks,
            "the existing New Game hook no longer owns the wipe lifecycle")
    require("ApplyFreshNewGameSettings();" not in scripting,
            "ordinary save loading invokes fresh initialization")

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

    # The Brock trainer/reward script is not source-owned by this component;
    # ensure this repair leaves the existing event-script manifest byte-identical.
    unchanged = subprocess.run(
        ["git", "diff", "--quiet", START_SHA, "--", "eventscripts"],
        cwd=ROOT,
        check=False,
    )
    require(unchanged.returncode == 0, "Brock/event-script overrides changed from the exact start revision")

    print("Fresh running lifecycle and Pewter Aide cleanup source audit: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
