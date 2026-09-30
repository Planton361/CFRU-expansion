#!/usr/bin/env python3
"""Bind the Fresh New Game flag repair to the full vanilla reset lifecycle."""

from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]
BASE_SHA = "c9a7f19f1e8aaebd33213503f32fa7bba59ce81c"
PRET_SHA = "037335f4c725d7c9aecdac87066f2002b4bd7e14"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def c_function(source: str, signature: str) -> str:
    start = source.index(signature)
    opening = source.index("{", start)
    depth = 0
    for pos in range(opening, len(source)):
        if source[pos] == "{":
            depth += 1
        elif source[pos] == "}":
            depth -= 1
            if depth == 0:
                return source[start:pos + 1]
    raise AssertionError("unterminated C function: " + signature)


def base_file(path: str) -> str:
    return subprocess.check_output(
        ["git", "show", f"{BASE_SHA}:{path}"], cwd=ROOT, text=True
    )


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit("early-running lifecycle audit failed: " + message)


def main() -> int:
    save = read("src/save.c")
    settings = read("src/settings.c")
    overworld = read("src/overworld.c")
    scripting = read("src/scripting.c")
    manifest = read("hooks")
    assembly = read("assembly/hooks/general_hooks.s")

    wipe = c_function(save, "void NewGameWipeNewSaveData(void)")
    require("QueueFreshNewGameSettings();" in wipe,
            "the genuine Fresh New Game wipe does not set the pending initializer")
    require("ApplyFreshNewGameSettings();" not in wipe and "FlagSet(FLAG_RUNNING_ENABLED);" not in wipe,
            "the running flag is written at the early save-clear hook")

    queue = c_function(settings, "void QueueFreshNewGameSettings(void)")
    apply = c_function(settings, "void ApplyFreshNewGameSettings(void)")
    pending = c_function(settings, "void ApplyQueuedFreshNewGameSettings(void)")
    require("sFreshNewGameSettingsPending = TRUE;" in queue,
            "Fresh New Game does not set the one-shot pending state")
    require("FlagSet(FLAG_RUNNING_ENABLED);" in apply,
            "the existing running flag is no longer applied")
    require("FLAG_AUTO_RUN" not in apply,
            "Fresh New Game now mutates Auto-Run")
    require(pending.index("if (!sFreshNewGameSettingsPending)")
            < pending.index("sFreshNewGameSettingsPending = FALSE;")
            < pending.index("ApplyFreshNewGameSettings();"),
            "queued Fresh New Game settings are not guarded and consumed exactly once")

    frame = c_function(overworld, "bool8 TryRunOnFrameMapScript(void)")
    require(frame.index("ApplyQueuedFreshNewGameSettings();")
            < frame.index("TryUpdateSwarm();")
            < frame.index("MapHeaderCheckScriptTable(MAP_SCRIPT_ON_FRAME_TABLE)"),
            "settings are not applied before the first post-load field input/script path")
    require("TryRunOnFrameMapScript 8069C74 0" in manifest,
            "the post-load input hook no longer binds this source function")
    require("NewGameSaveClearHook 8054A60 0" in manifest
            and "NewGameSaveClearHook:" in assembly
            and "bl NewGameWipeNewSaveData" in assembly,
            "the early New Game save-clear hook binding changed")
    require("ApplyFreshNewGameSettings();" not in scripting
            and "QueueFreshNewGameSettings();" not in scripting
            and "ApplyQueuedFreshNewGameSettings();" not in scripting,
            "ordinary existing-save load paths queue or apply Fresh New Game defaults")

    # Pret/pokefirered at PRET_SHA establishes NewGameInitData ordering:
    # ClearSav1 -> InitEventData -> explicit ResetAllMapFlags script -> return;
    # InitEventData zeroes the saved flags/vars. CB2_NewGame returns to field
    # input only after NewGameInitData, and FieldInputProcessInput tries the
    # on-frame script before processing a step. The old early write therefore
    # gets erased; the queued write is applied after that final reset.
    require(PRET_SHA == "037335f4c725d7c9aecdac87066f2002b4bd7e14",
            "the recorded public pret source witness changed")

    hook = assembly.split("@0x805BA30 with r0", 1)[1].split(".pool", 1)[0]
    require("AutoRunHook:" in hook and "bl ShouldPlayerRun" in hook
            and "ldr r0, =0x805BA5A | 1" in hook
            and "ldr r0, =0x805BA8C | 1" in hook,
            "AutoRunHook no longer replaces the vanilla run/walk gate")
    require("AutoRunHook 805BA30 0" in manifest,
            "AutoRunHook moved from the accepted BPRE gate")

    base_overworld = base_file("src/overworld.c")
    for signature in (
        "bool8 ShouldPlayerRun(u16 heldKeys)",
        "static bool8 IsRunningDisabledByFlag(void)",
        "bool8 IsRunningDisallowed(u8 tile)",
    ):
        require(c_function(overworld, signature) == c_function(base_overworld, signature),
                "running behavior/restrictions changed in " + signature)
    for path in ("src/read_keys.c", "assembly/hooks/general_hooks.s", "hooks",
                 "assembly/overworld_scripts/pewter_running_shoes_cleanup.s",
                 "mapobjectoverlays", "eventscripts"):
        require(read(path) == base_file(path), "protected #538 behavior changed: " + path)

    print("Fresh New Game full flag lifecycle ordering and negative-witness source audit: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
