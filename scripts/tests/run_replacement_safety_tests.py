#!/usr/bin/env python3
"""Run source/host regressions for safe opponent replacement selection."""

from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[2]


def run(command: list[str]) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> int:
    run(["python3", "scripts/tests/audit_opponent_replacement.py"])
    with tempfile.TemporaryDirectory(prefix="cfru-opponent-replacement-") as directory:
        binary = Path(directory) / "opponent_replacement_host"
        run([
            "cc", "-std=gnu99", "-Wall", "-Wextra", "-Werror",
            "-Wno-unknown-attributes", "-Iinclude",
            "scripts/tests/opponent_replacement_host.c", "-o", str(binary),
        ])
        subprocess.run([str(binary)], cwd=ROOT, check=True)
    print("opponent replacement source/host regressions: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
