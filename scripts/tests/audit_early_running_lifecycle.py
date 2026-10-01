#!/usr/bin/env python3
"""#583 native running and stateless, post-reset settings owner contract.

Public source witnesses and exact BPRE instruction/return reasoning are in
scripts/tests/early_running_583_source_proof.md. No ROM is used by this audit.
"""
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BASE_SHA = "c208c4a05b2a70e3296fcbe90f061832fa4e0f8b"
REMOVED = ("sFreshNewGameSettingsPending", "QueueFreshNewGameSettings",
           "ApplyQueuedFreshNewGameSettings")


def read(path):
    return (ROOT / path).read_text()


def c_function(source, signature):
    match = re.search(re.escape(signature) + r"\s*\{", source)
    require(match is not None, "missing definition: " + signature)
    start = match.start()
    opening = source.index("{", start)
    depth = 0
    for pos in range(opening, len(source)):
        if source[pos] == "{":
            depth += 1
        elif source[pos] == "}":
            depth -= 1
            if depth == 0:
                return source[start:pos + 1]
    raise AssertionError("unterminated function: " + signature)


def require(condition, message):
    if not condition:
        raise AssertionError("#583 contract: " + message)


def active(source):
    return re.sub(r"//[^\n]*|/\*.*?\*/|^\s*@[^\n]*", "", source, flags=re.S | re.M)


def check_source_contract():
    config = active(read("src/config.h"))
    require(not re.search(r"(?m)^\s*#\s*define\s+FLAG_RUNNING_ENABLED\b", config),
            "native running progression gate is enabled")
    require(re.search(r"(?m)^#define FLAG_AUTO_RUN 0x914\b", config), "Auto-Run flag changed")
    require(re.search(r"(?m)^#define CAN_RUN_IN_BUILDINGS\b", config), "indoor running disabled")
    settings = active(read("src/settings.c"))
    helper = c_function(settings, "void ApplyFreshNewGameSettings(void)")
    expected = '''void ApplyFreshNewGameSettings(void)
{
    VarSet(VAR_GAME_DIFFICULTY, OPTIONS_VANILLA_DIFFICULTY);
    VarSet(VAR_TRAINER_LEVEL_SCALING_MODE, TRAINER_LEVEL_SCALING_OFF + 1);
    VarSet(VAR_WILD_LEVEL_SCALING, 0);
    VarSet(VAR_TRAINER_AI_PROFILE, TRAINER_AI_PROFILE_STANDARD + 1);
}'''
    require(re.sub(r"\s+", "", helper) == re.sub(r"\s+", "", expected),
            "fresh helper must own exactly four VarSet calls")
    # No replacement latch, linked static, heap or SaveBlock ownership can fit
    # between these independently checked, complete function definitions.
    signatures = re.findall(r"(?m)^(?:u16|void) \w+\([^\n]*\)", settings)
    remainder = settings
    for signature in signatures:
        remainder = remainder.replace(c_function(settings, signature), "", 1)
    remainder = re.sub(r"(?m)^#include[^\n]*", "", remainder)
    require(not remainder.strip(), "settings translation unit acquired file-scope state")
    require("FlagSet(" not in settings and "FlagClear(" not in settings
            and "EWRAM_DATA" not in settings and "gSaveBlock" not in settings,
            "settings acquired flag/RAM/SaveBlock ownership")
    for directory in ("src", "include", "assembly"):
        for path in (ROOT / directory).rglob("*"):
            if path.suffix in (".c", ".h", ".s"):
                source = path.read_text(errors="replace")
                require(not any(name in source for name in REMOVED),
                        "obsolete pending mechanism in " + str(path.relative_to(ROOT)))
    call_sites = []
    for path in (ROOT / "src").rglob("*.c"):
        if "ApplyFreshNewGameSettings();" in active(path.read_text(errors="replace")):
            call_sites.append(str(path.relative_to(ROOT)))
    require(not call_sites, "fresh helper called outside New Game assembly owner")
    hooks = active(read("assembly/hooks/general_hooks.s"))
    hook = hooks.split("FreshNewGameSettingsHook:", 1)[1].split(".pool", 1)[0]
    expected_hook = '''bl ApplyFreshNewGameSettings
ldr r3, =ResetInitialPlayerAvatarState
bl FreshNewGameSettingsCallR3
ldr r3, =PlayTimeCounter_Start
bl FreshNewGameSettingsCallR3
ldr r3, =ScriptContext_Init
bl FreshNewGameSettingsCallR3
ldr r0, =0x8056662 | 1
bx r0
FreshNewGameSettingsCallR3:
bx r3'''
    require(re.sub(r"\s+", "", hook) == re.sub(r"\s+", "", expected_hook),
            "settings hook changed replay/continuation or acquired state")
    require(hooks.count("bl ApplyFreshNewGameSettings") == 1, "duplicate fresh owner")
    rows = [line.split() for line in read("hooks").splitlines()
            if line.strip() and not line.lstrip().startswith("#")]
    require([row for row in rows if row[0] == "FreshNewGameSettingsHook"]
            == [["FreshNewGameSettingsHook", "8056656", "0"]], "fresh hook binding changed")
    require([row for row in rows if int(row[1], 16) in range(0x8056652, 0x8056662)]
            == [["FreshNewGameSettingsHook", "8056656", "0"]], "overlapping late hook")
    require("AutoRunHook 805BA30 0" in read("hooks"), "movement hook binding changed")
    running_hook = hooks.split("AutoRunHook:", 1)[1].split(".pool", 1)[0]
    require("bl ShouldPlayerRun" in running_hook
            and "0x805BA5A | 1" in running_hook and "0x805BA8C | 1" in running_hook,
            "native movement dispatch changed")
    # Existing semantics/restrictions and L behavior are implementation-owned;
    # #583 changes their preprocessing configuration only.
    for path, signatures in {
        "src/overworld.c": ("bool8 ShouldPlayerRun(u16 heldKeys)",
                            "static bool8 IsRunningDisabledByFlag(void)",
                            "bool8 IsRunningDisallowed(u8 tile)",
                            "bool8 IsRunningDisallowedByMetatile(u8 tile)"),
        "src/read_keys.c": ("bool8 StartLButtonFunc(void)",),
    }.items():
        base = subprocess.check_output(["git", "show", f"{BASE_SHA}:{path}"], cwd=ROOT, text=True)
        for signature in signatures:
            require(c_function(read(path), signature) == c_function(base, signature),
                    "movement implementation changed: " + signature)
    print("#583 native config, four-Var helper, stateless late owner, removed queue: PASS")


if __name__ == "__main__":
    check_source_contract()
