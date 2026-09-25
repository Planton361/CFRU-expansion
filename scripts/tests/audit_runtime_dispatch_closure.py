#!/usr/bin/env python3
"""Source and optional linked-symbol closure for the four R1 runtime hooks.

The default mode reads source only. After build.py, pass --linked-object
build/linked.o to check the very symbol addresses consumed by insert.py.
No ROM is opened by this gate.
"""

import argparse
import importlib.util
import io
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[2]
EXPECTED = {
    "OpponentHandleChooseMove": (0x080385B0, 0, "src/battle_controller_opponent.c", r"\bvoid OpponentHandleChooseMove\(void\)"),
    "BattleSetup_StartTrainerBattle": (0x08080464, 0, "src/overworld.c", r"\bvoid BattleSetup_StartTrainerBattle\(void\)"),
    "ExpandedVarsHook": (0x0806E454, 1, "assembly/hooks/general_hooks.s", r"(?m)^ExpandedVarsHook:"),
    "BufferStringBattle": (0x080D7274, 1, "src/battle_strings.c", r"\bvoid BufferStringBattle\(u16 stringID\)"),
}
EXCLUDED = {
    "DOUBLE", "LINK", "OAK_TUTORIAL", "MULTI", "SAFARI", "ROAMER",
    "EREADER_TRAINER", "SCRIPTED_WILD_1", "SCRIPTED_WILD_2",
    "LEGENDARY_FRLG", "TRAINER_TOWER", "TWO_OPPONENTS", "INGAME_PARTNER",
    "POKE_DUDE", "OLD_MAN", "FRONTIER", "SHADOW_WARRIOR", "DYNAMAX",
    "KYOGRE_GROUDON", "REGI", "GHOST", "RING_CHALLENGE", "MOCK_BATTLE",
    "BENJAMIN_BUTTERFREE", "CAMOMONS", "MEGA_BRAWL",
}


def require(condition, message):
    if not condition:
        raise SystemExit("runtime dispatch closure failed: " + message)


def load_inserter():
    spec = importlib.util.spec_from_file_location("cfru_insert", ROOT / "scripts/insert.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def active_hooks(inserter):
    definitions, conditionals, found = {}, [], {}
    for line in (ROOT / "hooks").read_text().splitlines():
        if inserter.TryProcessFileInclusion(line, definitions):
            continue
        if inserter.TryProcessConditionalCompilation(line, definitions, conditionals):
            continue
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = line.split()
        require(len(parts) == 3, "unexpected hooks grammar: " + line)
        name, address, register = parts
        if name in EXPECTED:
            require(name not in found, "duplicate active hook: " + name)
            found[name] = (int(address, 16), int(register))
    return found


def check_source(inserter):
    hooks = active_hooks(inserter)
    require(set(hooks) == set(EXPECTED), "required active hook missing")
    for name, (site, register, path, pattern) in EXPECTED.items():
        require(hooks[name] == (site, register), "wrong site/register: " + name)
        require(len(re.findall(pattern, (ROOT / path).read_text())) == 1,
                "production symbol missing or duplicated: " + name)
        image = io.BytesIO(bytearray(16))
        inserter.Hook(image, 0x10000, 0, register)
        encoded = image.getvalue()
        require(encoded[:2] == bytes([0x00, 0x48 | register]),
                "Thumb LDR changed: " + name)
        require(encoded[2:4] == bytes([register << 3, 0x47]),
                "Thumb BX changed: " + name)
        require(int.from_bytes(encoded[4:8], "little") == 0x08010001,
                "Thumb target bit/ROM base changed: " + name)
    source = (ROOT / "scripts/insert.py").read_text()
    require("table = GetSymbols(GetTextSection())" in source
            and "table[entry] += OFFSET_TO_PUT" in source
            and "offset = int(address, 16) - 0x08000000" in source
            and "code = table[symbol]" in source
            and "Hook(rom, code, offset, int(register))" in source,
            "insertion symbol/site path changed")
    require(set(inserter.REQUIRED_RUNTIME_HOOKS) == set(EXPECTED)
            and "Required runtime hook symbol missing" in source,
            "required missing symbols are no longer fatal")
    print("four required hook sites, production symbols, parser and Thumb encoding: PASS")


def check_oak_flags():
    config = (ROOT / "src/config.h").read_text()
    overworld = (ROOT / "src/overworld.c").read_text()
    battle_header = (ROOT / "include/constants/battle.h").read_text()
    trainer = (ROOT / "src/Tables/trainer_data.c").read_text()
    parties = (ROOT / "src/Tables/trainer_parties.h").read_text()
    require("//#define TUTORIAL_BATTLES" in config
            and not re.search(r"(?m)^#define TUTORIAL_BATTLES\b", config),
            "Oak tutorial compile switch unexpectedly enabled")
    require("#define FLAG_ACTIVATE_TUTORIAL 0x90A" in config,
            "Oak tutorial flag changed")
    require("#define TRAINER_BATTLE_OAK_TUTORIAL                     9" in
            (ROOT / "include/battle_setup.h").read_text(), "early-rival mode changed")
    require("#define RIVAL_BATTLE_TUTORIAL    3" in battle_header,
            "early-rival end-battle helper changed")
    setup = overworld[overworld.index("void BattleSetup_StartTrainerBattle(void)"):
                      overworld.index("//Special 0x34")]
    for phrase in ("gBattleTypeFlags = (BATTLE_TYPE_TRAINER);",
                   "if (FlagGet(FLAG_ACTIVATE_TUTORIAL))",
                   "gBattleTypeFlags |= BATTLE_TYPE_OAK_TUTORIAL;",
                   "if (FlagGet(FLAG_TAG_BATTLE))",
                   "if (FlagGet(FLAG_AI_CONTROL_BATTLE))"):
        require(phrase in setup, "battle setup flag path changed: " + phrase)
    source_paths = [p for p in (ROOT / "src").rglob("*.c")]
    source_paths += [p for p in (ROOT / "assembly/overworld_scripts").rglob("*.s")]
    require(not any(re.search(r"FlagSet\(FLAG_ACTIVATE_TUTORIAL\)|(?i:setflag\s+(?:FLAG_ACTIVATE_TUTORIAL|0x90A))",
                              p.read_text(errors="ignore")) for p in source_paths),
            "current source writes the Oak tutorial flag")
    oak = trainer[trainer.index("[TRAINER_RIVAL_OAKS_LAB_SQUIRTLE] = {"):]
    oak = oak[:oak.index("[TRAINER_RIVAL_OAKS_LAB_BULBASAUR] = {")]
    require(".doubleBattle = FALSE" in oak and "sParty_TrainerRivalOaksLabSquirtle" in oak,
            "Oak trainer data no longer ordinary single/default moves")
    party = parties[parties.index("sParty_TrainerRivalOaksLabSquirtle[]"):]
    require(".lvl = 5" in party[:party.index("};")]
            and ".species = SPECIES_SQUIRTLE" in party[:party.index("};")],
            "Oak Squirtle party/level changed")
    for name, profile in (("standard", "STANDARD"), ("ironmon", "IRONMON_SMART")):
        source = (ROOT / f"src/Battle_AI/ai_{name}.c").read_text()
        predicate = source[source.index(f"bool8 {name.capitalize()}AI_IsSupportedBattle(void)"):]
        mask = predicate[predicate.index("u32 excluded ="):predicate.index(";", predicate.index("u32 excluded ="))]
        flags = set(re.findall(r"BATTLE_TYPE_([A-Z0-9_]+)", mask))
        require(flags == EXCLUDED, f"{name} support exclusion mask changed: {sorted(flags ^ EXCLUDED)}")
        for phrase in ("BATTLE_TYPE_TRAINER", "!IsRaidBattle()", "!IsInverseBattle()",
                       "!IsFrontierTrainerId(gTrainerBattleOpponent_A)",
                       f"GetTrainerAIProfile() == TRAINER_AI_PROFILE_{profile}"):
            require(phrase in predicate[:predicate.index(";", predicate.index("return "))],
                    f"{name} support condition changed: {phrase}")
    require("case BATTLE_TYPE_OAK_TUTORIAL" not in battle_header,
            "unexpected first-battle alias")
    ai_master = (ROOT / "src/Battle_AI/ai_master.c").read_text()
    require("else if (gBattleTypeFlags & BATTLE_TYPE_OAK_TUTORIAL)\n\t\tflags = AI_SCRIPT_FIRST_BATTLE;"
            in ai_master, "legacy FirstBattle route changed")
    print("Oak source battle flags: TRAINER=0x8; 26 shared exclusions absent on ordinary fresh single; tutorial flag conditional, FirstBattle only through OAK_TUTORIAL: PASS")


def check_linked_symbols(inserter, path):
    nm = subprocess.check_output([inserter.NM, str(path)], text=True)
    objdump = subprocess.check_output([inserter.OBJDUMP, "-t", str(path)], text=True)
    text_lines = [line for line in objdump.splitlines() if line.strip().endswith(".text")]
    require(text_lines, "linked object has no .text section")
    text_base = int(text_lines[0].split()[0], 16)
    names = {}
    for line in nm.splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[1].lower() in {"t", "d"}:
            names.setdefault(parts[2], []).append((int(parts[0], 16), parts[1].lower()))
    for name in EXPECTED:
        require(len(names.get(name, [])) == 1, "linked symbol missing/duplicate: " + name)
        address, kind = names[name][0]
        require(kind == "t", "required hook resolves to data, not code: " + name)
        offset = address - text_base
        require(0 <= offset < 0x1000000 and offset % 2 == 0,
                "linked symbol outside inserted Thumb text: " + name)
        target = inserter.OFFSET_TO_PUT + offset + 0x08000001
        require(0x09000001 <= target < 0x0A000001 and target & 1,
                "invalid inserted hook pointer: " + name)
        print(f"  {name}: linked=0x{address:08X} inserted=0x{target:08X}")
    print("linked insertion-symbol closure: PASS")


def check_diagnostic_preprocessing():
    config = (ROOT / "src/config.h").read_text()
    controller = (ROOT / "src/battle_controller_opponent.c").read_text()
    require("//#define TRAINER_AI_RUNTIME_DISPATCH_TRACE" in config
            and not re.search(r"(?m)^#define TRAINER_AI_RUNTIME_DISPATCH_TRACE\b", config),
            "temporary marker enabled in the default configuration")
    require("CheckMoveLimitations(bank, 0, 0xFF)" in controller,
            "marker no longer checks all normal move restrictions")
    command = ["cc", "-E", "-P", "-Iinclude", "-I.",
               "src/battle_controller_opponent.c"]
    normal = subprocess.check_output(command, cwd=ROOT, text=True)
    diagnostic = subprocess.check_output(command[:1] +
        ["-DTRAINER_AI_RUNTIME_DISPATCH_TRACE"] + command[1:], cwd=ROOT, text=True)
    require("OpponentHandleOakDispatchMarker" not in normal,
            "marker is present in release preprocessed source")
    require("OpponentHandleOakDispatchMarker" in diagnostic,
            "marker absent from diagnostic preprocessed source")
    print("diagnostic switch: disabled by default; release preprocessing omits marker; diagnostic preprocessing includes marker: PASS")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--linked-object", type=Path,
                        help="optional local build/linked.o from the approved toolchain")
    args = parser.parse_args()
    inserter = load_inserter()
    check_source(inserter)
    check_oak_flags()
    check_diagnostic_preprocessing()
    if args.linked_object is not None:
        check_linked_symbols(inserter, args.linked_object)
    else:
        print("linked insertion-symbol closure: NOT RUN (no approved linked object)")


if __name__ == "__main__":
    main()
