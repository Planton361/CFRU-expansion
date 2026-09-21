#!/usr/bin/env python3
"""Run the source-owned Standard policy and fairness checks on a host."""

from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[2]


def run(command):
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> int:
    run(["python3", "scripts/tests/audit_standard_ai.py"])
    with tempfile.TemporaryDirectory(prefix="cfru-standard-ai-") as directory:
        binary = Path(directory) / "standard_ai_policy_host"
        run([
            "cc", "-std=c99", "-Wall", "-Wextra", "-Werror", "-Iinclude",
            "scripts/tests/standard_ai_policy_host.c",
            "src/Battle_AI/ai_standard_policy.c",
            "-o", str(binary),
        ])
        subprocess.run([str(binary)], cwd=ROOT, check=True)

        layout_binary = Path(directory) / "standard_ai_layout_host"
        run([
            "cc", "-std=gnu99", "-Wno-unknown-attributes", "-Iinclude",
            "scripts/tests/standard_ai_layout_host.c", "-o", str(layout_binary),
        ])
        subprocess.run([str(layout_binary)], cwd=ROOT, check=True)
    print("standard AI source tests: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
