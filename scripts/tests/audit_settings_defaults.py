#!/usr/bin/env python3
"""Static/source-owned checks for Issue #520 settings compatibility."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit("settings/defaults audit failed: " + message)


def main() -> int:
    option_menu = read("src/option_menu.c")
    save = read("src/save.c")
    hooks = read("assembly/hooks/general_hooks.s")
    scripting = read("src/scripting.c")
    settings = read("src/settings.c")
    util = read("src/util.c")
    strings = read("strings/option_menu.string")
    header = read("include/new/settings.h")

    require("gText_StandardOption" in strings, "Standard menu label is missing")
    require("gText_IronmonSmartOption" in strings, "Ironmon Smart menu label is missing")
    require("Standard\n" in strings, "Standard label text is missing")
    require("Ironmon Smart\n" in strings, "Ironmon Smart label text is missing")
    require(
        "[TRAINER_AI_PROFILE_MENU_OPTION_COUNT]" in option_menu,
        "Trainer AI option table is not count-bounded",
    )
    require(
        "TRAINER_AI_PROFILE_MENU_OPTION_COUNT, 3" in option_menu,
        "Trainer AI cycling count does not include both new profiles",
    )
    require(
        "gText_SmartOption,\n    gText_StandardOption,\n    gText_IronmonSmartOption," in option_menu,
        "legacy Smart plus appended Standard/Ironmon Smart menu order is missing",
    )
    require(
        "TrainerAIProfileRawToMenuSelection(sOptionMenuPtr->trainerAIProfileOriginalRaw)"
        in option_menu,
        "options entry does not use the raw mapping helper",
    )
    require(
        "TrainerAIProfileRawAfterOptions" in option_menu,
        "options close does not use the original-raw/dirty preservation helper",
    )
    require(
        "static u16 TrainerAIProfileRawToMenuSelection" not in option_menu,
        "Trainer AI raw mapping was duplicated in the menu",
    )

    wipe = save[save.index("void NewGameWipeNewSaveData(void)"):]
    require("ApplyFreshNewGameSettings();" in wipe, "fresh defaults are not called by the wipe hook")
    require(
        wipe.index("ApplyFreshNewGameSettings();") > wipe.index("#endif"),
        "fresh defaults are not written after both wipe branches",
    )
    require("ApplyFreshNewGameSettings();" not in option_menu, "options entry applies fresh defaults")
    require(
        "NewGameSaveClearHook:" in hooks and "bl NewGameWipeNewSaveData" in hooks,
        "the selected CFRU new-game clear hook does not call the wipe lifecycle",
    )
    require("ApplyFreshNewGameSettings();" not in scripting, "ordinary save-load code applies fresh defaults")

    require("VAR_GAME_DIFFICULTY, OPTIONS_VANILLA_DIFFICULTY" in settings, "fresh/preset Vanilla write missing")
    require(
        "VAR_TRAINER_LEVEL_SCALING_MODE, TRAINER_LEVEL_SCALING_OFF + 1" in settings,
        "fresh/preset trainer scaling Off write missing",
    )
    require("VAR_WILD_LEVEL_SCALING, 0" in settings, "fresh/preset wild scaling Off write missing")
    require(
        "VAR_TRAINER_AI_PROFILE, TRAINER_AI_PROFILE_STANDARD + 1" in settings,
        "fresh Standard raw write missing",
    )
    require(
        "VAR_TRAINER_AI_PROFILE, TRAINER_AI_PROFILE_IRONMON_SMART + 1" in settings,
        "Ironmon Smart raw write missing",
    )
    require(settings.count("VarSet(") == 8, "fresh/preset helpers write an unexpected number of Vars")
    for forbidden in ("FlagSet(", "FlagClear(", "gSaveBlock", "SaveBlock"):
        require(forbidden not in settings, f"preset helper mutates unrelated state: {forbidden}")
    require(
        "TRAINER_AI_PROFILE_MENU_OPTION_COUNT (TRAINER_AI_PROFILE_IRONMON_SMART + 2)" in header,
        "menu count is not derived from the appended profile",
    )
    for raw_case in (
        "TRAINER_AI_PROFILE_VANILLA + 1",
        "TRAINER_AI_PROFILE_EASY + 1",
        "TRAINER_AI_PROFILE_NORMAL + 1",
        "TRAINER_AI_PROFILE_HARD + 1",
        "TRAINER_AI_PROFILE_EXPERT + 1",
        "TRAINER_AI_PROFILE_SMART_AI + 1",
        "TRAINER_AI_PROFILE_STANDARD + 1",
        "TRAINER_AI_PROFILE_IRONMON_SMART + 1",
    ):
        require(f"case {raw_case}:" in util, f"raw mapping case is missing: {raw_case}")
    get_profile = util[util.index("enum TrainerAIProfile GetTrainerAIProfile(void)"):]
    require(
        "case 0:" in get_profile and "return GetLegacyTrainerAIProfile();" in get_profile,
        "raw 0 legacy Trainer AI fallback is missing",
    )
    require("TRAINER_AI_PROFILE_EXPERT + 1" not in settings, "settings helper reuses legacy Expert raw")
    require("TRAINER_AI_PROFILE_SMART_AI + 1" not in settings, "settings helper reuses legacy Smart raw")

    print("settings/defaults source wiring and lifecycle audit: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
