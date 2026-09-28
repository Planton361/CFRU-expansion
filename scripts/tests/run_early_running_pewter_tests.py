#!/usr/bin/env python3
"""Run the source and synthetic insertion checks for Workspace #538."""

from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    subprocess.run(["python3", "scripts/tests/audit_early_running_pewter.py"], cwd=ROOT, check=True)
    subprocess.run(["python3", "scripts/insert.py", "--check-map-object-overlays"], cwd=ROOT, check=True)
    print("Issue #538 targeted tests: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
