#!/usr/bin/env python3
"""Run source-owned production AI/controller handoff witnesses on the host."""

from pathlib import Path
import platform
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[2]


def run(command):
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> int:
    run(["python3", "scripts/tests/audit_ai_controller_fallback.py"])
    with tempfile.TemporaryDirectory(prefix="cfru-ai-controller-fallback-") as temporary:
        temp = Path(temporary)
        preamble = temp / "host_rom_preamble.h"
        preamble.write_text(
            '#include "src/defines.h"\n'
            '#include "src/defines_battle.h"\n'
            "#undef gBitTable\n"
            "#undef gTrainerBattleOpponent_A\n"
            "extern const u32 gBitTable[];\n"
            "extern u16 gTrainerBattleOpponent_A;\n"
        )
        learn_preamble = temp / "learn_move_host_preamble.h"
        learn_preamble.write_text(
            '#include "src/config.h"\n'
            "#undef FLAG_POKEMON_LEARNSET_RANDOMIZER\n"
        )
        strings_preamble = temp / "battle_strings_host_preamble.h"
        strings_preamble.write_text("#pragma weak EmitPrintString\n")
        common = ["cc", "-std=gnu99", "-w", "-Wno-unknown-attributes",
                  "-Iinclude", "-I.", "-ffunction-sections", "-fdata-sections"]
        host_include = ["-include", str(preamble)]
        master = temp / "ai_master.o"
        controller = temp / "battle_controller_opponent.o"
        util = temp / "util.o"
        strings = temp / "battle_strings.o"
        learn_move = temp / "learn_move.o"
        learnsets = temp / "level_up_learnsets.o"
        run(common + host_include + ["-c", "src/Battle_AI/ai_master.c", "-o", str(master)])
        run(common + host_include + ["-DCFRU_AI_TEST_TRACE", "-c",
            "src/battle_controller_opponent.c", "-o", str(controller)])
        run(common + host_include + ["-include", str(strings_preamble), "-c",
            "src/battle_strings.c", "-o", str(strings)])
        run(common + ["-include", str(learn_preamble), "-c",
            "src/learn_move.c", "-o", str(learn_move)])
        run(common + ["-c", "src/Tables/level_up_learnsets.c", "-o", str(learnsets)])
        run(common + ["-DGetTrainerAIProfile=GetTrainerAIProfileFromRaw",
            "-DMathMin=ControllerHostMathMin", "-DMathMax=ControllerHostMathMax",
            "-c", "src/util.c", "-o", str(util)])
        binary = temp / "controller_fallback_host"
        linker = ["-Wl,-dead_strip"] if platform.system() == "Darwin" else ["-Wl,--gc-sections"]
        run(common + ["scripts/tests/controller_fallback_host.c", str(master),
            str(controller), str(util), str(strings), str(learn_move), str(learnsets),
            "src/Battle_AI/ai_standard_policy.c",
            "src/Battle_AI/ai_standard_mechanics.c", "src/Battle_AI/ai_ironmon_policy.c",
            *linker, "-o", str(binary)])
        subprocess.run([str(binary)], cwd=ROOT, check=True)
    print("production controller/fallback suite: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
