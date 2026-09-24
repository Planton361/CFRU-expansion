#!/usr/bin/env python3
"""Compile #526 source-table census and production-adapter plausibility gates."""

from pathlib import Path
import re
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    parties = (ROOT / "src/Tables/trainer_parties.h").read_text()
    brock = re.search(r"sParty_TrainerLeaderBrock\[\].*?\n};", parties, re.S)
    assert brock and re.search(
        r"\.species = SPECIES_ONIX,\s*\.moves = "
        r"\{MOVE_TACKLE, MOVE_BIND, MOVE_ROCKTOMB, MOVE_NONE\}",
        brock.group()), "Brock/Onix source party changed"
    subprocess.run(["python3", "scripts/tests/audit_ai_damage_overrides.py"], cwd=ROOT, check=True)
    with tempfile.TemporaryDirectory(prefix="cfru-ai-quality-") as directory:
        binary = str(Path(directory) / "ai_runtime_quality_host")
        subprocess.run([
            "cc", "-std=gnu99", "-Wall", "-Wextra", "-Werror",
            "-Wno-unknown-attributes", "-Iinclude",
            "scripts/tests/ai_runtime_quality_host.c",
            "src/Battle_AI/ai_standard_policy.c",
            "src/Battle_AI/ai_standard_mechanics.c",
            "src/Battle_AI/ai_ironmon_policy.c", "-o", binary,
        ], cwd=ROOT, check=True)
        subprocess.run([binary], cwd=ROOT, check=True)
        subprocess.run(["python3", "scripts/tests/ai_runtime_differential.py", binary],
                       cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
