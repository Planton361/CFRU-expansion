#!/usr/bin/env python3
"""ROM-free source contract for the M-007 National Dex handoff (#549)."""

from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[2]
START_SHA = "ec4e1b7410a65b23e081010c580ecb8c078a64a1"
HANDOFF = "assembly/overworld_scripts/shortened_oak_parcel_flow.s"
ALLOWED_CHANGED_PATHS = {
    HANDOFF,
    "scripts/insert.py",
    "scripts/tests/audit_m007_national_dex_handoff.py",
}


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit("M-007 National Dex handoff audit failed: " + message)


def without_assembly_comments(source: str) -> str:
    return "\n".join(line.split("@", 1)[0] for line in source.splitlines())


def changed_paths() -> set[str]:
    committed_or_modified = subprocess.check_output(
        ["git", "diff", "--name-only", START_SHA, "--"], cwd=ROOT, text=True
    )
    untracked = subprocess.check_output(
        ["git", "ls-files", "--others", "--exclude-standard"], cwd=ROOT, text=True
    )
    return set(committed_or_modified.splitlines()) | set(untracked.splitlines())


def main() -> int:
    source = read(HANDOFF)
    code = without_assembly_comments(source)
    handoff = code.split("EventScript_M007PalletOakHandoff:", 1)[1].split(
        "Movement_M007Route1ClerkApproach10:", 1
    )[0]

    constants = re.findall(
        r"(?m)^\s*\.equ\s+SPECIAL_ENABLE_NATIONAL_POKEDEX\s*,\s*(0x[0-9A-Fa-f]+)\s*$",
        code,
    )
    require(len(constants) == 1 and int(constants[0], 16) == 0x016F,
            "the named National Dex special must bind exactly once to BPRE index 0x016F")
    calls = re.findall(r"(?mi)^\s*special\s+SPECIAL_ENABLE_NATIONAL_POKEDEX\s*$", code)
    require(len(calls) == 1, "the full National Dex special must be invoked exactly once")
    require(code.count("0x016F") == 1, "0x016F must appear only in its named binding")
    require(handoff.count("special SPECIAL_ENABLE_NATIONAL_POKEDEX") == 1,
            "the National Dex special is outside or duplicated in the Oak handoff")

    ordering = (
        "removeitem ITEM_OAKS_PARCEL 1",
        "setflag FLAG_SYS_POKEDEX_GET",
        "special SPECIAL_SET_UNLOCKED_POKEDEX_FLAGS",
        "special SPECIAL_ENABLE_NATIONAL_POKEDEX",
        "obtainitem ITEM_POKE_BALL 5",
        "setvar VAR_MAP_SCENE_POKEMON_CENTER_TEALA 1",
        "compare VAR_TEMP_1 0",
        "if equal _call EventScript_M007PalletOakLeave12",
        "compare VAR_TEMP_1 1",
        "if equal _call EventScript_M007PalletOakLeave13",
        "setvar VAR_MAP_SCENE_PALLET_TOWN_PROFESSOR_OAKS_LAB 6",
        "setvar VAR_MAP_SCENE_VIRIDIAN_CITY_MART 2",
        "setvar VAR_MAP_SCENE_VIRIDIAN_CITY_OLD_MAN 2",
        "setvar VAR_MAP_SCENE_PALLET_TOWN_RIVALS_HOUSE 1",
        "setvar VAR_MAP_SCENE_ROUTE22 1",
        "setflag FLAG_HIDE_OAK_PALLET_TOWN_BALL_CUTSCENE",
        "releaseall",
        "end",
    )
    positions = [handoff.index(fragment) for fragment in ordering]
    require(positions == sorted(positions),
            "Parcel, Pokédex flags/specials, five balls, and existing handoff transitions changed order")
    require(".equ SPECIAL_SET_UNLOCKED_POKEDEX_FLAGS, 0x181" in code,
            "the existing unlocked-Pokédex special no longer binds to 0x0181")

    for forbidden in (
        "EnableNationalPokedex", "nationalMagic", "VAR_NATIONAL_DEX",
        "FLAG_SYS_NATIONAL_DEX", "0x6258", "0x00B9", "special 0x016F",
    ):
        require(forbidden not in handoff,
                "raw or partial National Dex setter workaround found: " + forbidden)
    require(not re.search(r"(?mi)^\s*(?:callasm|callnative|bl)\b", handoff),
            "a direct function/address call was introduced instead of the proven BPRE special")

    fresh_new_game_paths = (
        "src/save.c",
        "src/settings.c",
        "src/new_game_pc_items.c",
        "assembly/hooks/general_hooks.s",
    )
    for path in fresh_new_game_paths:
        fresh_source = read(path)
        for forbidden in (
            "SPECIAL_ENABLE_NATIONAL_POKEDEX", "EnableNationalPokedex", "FLAG_SYS_NATIONAL_DEX",
            "VAR_NATIONAL_DEX", "nationalMagic", "0x6258", "0x00B9",
        ):
            require(forbidden not in fresh_source,
                    "National Dex activation leaked into Fresh New Game source "
                    + path + ": " + forbidden)
        require(not re.search(r"\b0x016[Ff]\b", fresh_source),
                "BPRE National Dex special index leaked into Fresh New Game source: " + path)

    changed = changed_paths()
    require(changed == ALLOWED_CHANGED_PATHS,
            "change scope includes an unexpected path (including save/ABI/layout files): "
            + ", ".join(sorted(changed ^ ALLOWED_CHANGED_PATHS)))

    print("M-007 National Dex handoff ROM-free source audit: PASS")
    print("Fresh New Game, save/ABI/layout, and M-007 flow scope: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
