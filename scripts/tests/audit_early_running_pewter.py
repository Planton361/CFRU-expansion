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
    from audit_early_running_lifecycle import check_source_contract
    check_source_contract()
    overlays = read("mapobjectoverlays")
    cleanup = read("assembly/overworld_scripts/pewter_running_shoes_cleanup.s")

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
         "assembly/overworld_scripts/pewter_running_shoes_cleanup.s", "src/read_keys.c"],
        cwd=ROOT,
        check=False,
    )
    require(unchanged.returncode == 0,
            "Pewter cleanup, object/coord overlays, movement hook or L-toggle changed from exact start")

    print("Native running and Pewter Aide cleanup source audit: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
