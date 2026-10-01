#!/usr/bin/env python3
"""Reject tracked source edits at the native build entry; ignore build inputs."""

from pathlib import Path
import argparse
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def check_source_identity(root: Path = ROOT) -> None:
    """Require tracked-clean source and reject unignored extras without reading them."""
    result = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(
            "Native build could not verify tracked source identity (git status failed)."
        )
    changes = []
    for entry in result.stdout.splitlines():
        state, path = entry[:2], entry[3:]
        if state == "??" and path == "BPRE0.gba":
            continue
        changes.append(entry)
    if changes:
        raise SystemExit(
            "Native build requires clean tracked source; commit or discard source changes "
            "and remove unexpected untracked files first."
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    args = parser.parse_args()
    check_source_identity(args.root.resolve())
    print("Native build tracked-source identity: PASS")


if __name__ == "__main__":
    main()
