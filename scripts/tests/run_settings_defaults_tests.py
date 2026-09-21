#!/usr/bin/env python3
"""Run the source-owned settings/defaults compatibility checks on a host."""

from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[2]


def run(command: list[str]) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> int:
    run(["python3", "scripts/tests/audit_settings_defaults.py"])
    with tempfile.TemporaryDirectory(prefix="cfru-settings-defaults-") as directory:
        binary = Path(directory) / "settings_defaults_host"
        run([
            "cc", "-std=c99", "-Wall", "-Wextra", "-Werror",
            "-Wno-unknown-attributes", "-Iinclude",
            "scripts/tests/settings_defaults_host.c", "src/settings.c", "-o", str(binary),
        ])
        subprocess.run([str(binary)], cwd=ROOT, check=True)
    print("settings/defaults temporary host objects: deleted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
