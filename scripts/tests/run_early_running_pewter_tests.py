#!/usr/bin/env python3
"""Run the source and synthetic insertion checks for Workspace #538."""

from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    subprocess.run(["python3", "scripts/tests/audit_early_running_pewter.py"], cwd=ROOT, check=True)
    subprocess.run(["python3", "scripts/tests/audit_early_running_lifecycle.py"], cwd=ROOT, check=True)
    with tempfile.TemporaryDirectory(prefix="cfru-early-running-lifecycle-") as directory:
        binary = Path(directory) / "early_running_lifecycle_host"
        subprocess.run([
            "cc", "-std=c99", "-Wall", "-Wextra", "-Werror",
            "-Wno-unknown-attributes", "-Iinclude",
            "scripts/tests/early_running_lifecycle_host.c", "src/settings.c", "-o", str(binary),
        ], cwd=ROOT, check=True)
        subprocess.run([str(binary)], cwd=ROOT, check=True)
    subprocess.run(["python3", "scripts/insert.py", "--check-map-object-overlays"], cwd=ROOT, check=True)
    print("Issues #538/#577 targeted tests: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
