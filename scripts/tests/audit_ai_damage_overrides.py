#!/usr/bin/env python3
"""Audit the fail-closed damage-engine override boundary against live source."""

from pathlib import Path
import argparse
import re


ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT / "src/damage_calc.c"
OUTPUT = ROOT / "include/new/ai_damage_engine_overrides.inc"


def source_moves() -> list[str]:
    source = ENGINE.read_text()
    # A named damage-engine move special case may alter type, power, stats,
    # accuracy or effectiveness. Err on the side of excluding all of them.
    names = set(re.findall(r"\bcase\s+(MOVE_[A-Z0-9_]+)\s*:", source))
    names.update(re.findall(
        r"\b(?:[A-Za-z_][A-Za-z_0-9]*)?[Mm]ove\s*[!=]=\s*(MOVE_[A-Z0-9_]+)",
        source))
    return sorted(names - {"MOVE_NONE"})


def content() -> str:
    return ("/* Generated from named move cases/comparisons in src/damage_calc.c.\n"
            " * Run scripts/tests/audit_ai_damage_overrides.py --write after reviewing\n"
            " * a changed engine. All listed moves fail closed as D3. */\n"
            + "".join(f"\tcase {name}:\n" for name in source_moves()))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    expected = content()
    if args.write:
        OUTPUT.write_text(expected)
    else:
        assert OUTPUT.read_text() == expected, "engine override list has drifted"
    print(f"damage-engine named move overrides: {len(source_moves())} audited")


if __name__ == "__main__":
    main()
