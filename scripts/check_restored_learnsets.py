#!/usr/bin/env python3
"""Verify the five restored tables against tracked source, never a ROM."""
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIN = "827fa1ef04bd43e5c6bad5c47f7d8690ea6823ec"
REFERENCE = "53273184bab06f91cdc3ad6e0e5af4a8ba41591a"
PATH = "src/Tables/level_up_learnsets.c"
TARGETS = ("Pikachu", "Rotom", "Necrozma", "Zacian", "Zamazenta")


def git(revision):
    return subprocess.check_output(["git", "-C", str(ROOT), "show", revision+":"+PATH], text=True)


def get(text, name):
    found = re.findall(r"static const struct LevelUpMove s"+name+r"LevelUpLearnset\[\] = \{.*?\n\};", text, re.S)
    if len(found) != 1: raise ValueError("Expected unique table: " + name)
    return found[0]


def check_source_contract():
    actual = (ROOT / PATH).read_text()
    baseline, reference = git(PIN), git(REFERENCE)
    expected = baseline
    for name in TARGETS:
        empty, restored = get(baseline,name), get(reference,name)
        if "LEVEL_UP_MOVE" in empty or "LEVEL_UP_MOVE" not in restored:
            raise ValueError("Unexpected restoration baseline: " + name)
        expected = expected.replace(empty,restored)
        if get(actual,name) != restored:
            raise ValueError("Restoration differs from tracked source: " + name)
    if actual != expected:
        raise ValueError("Unrelated learnset/pointer change outside five restored tables")
    # Do not allow a future shared-form sync to silently empty any named table.
    empty = re.findall(r"static const struct LevelUpMove (\w+)\[\] = \{\s*LEVEL_UP_END,?\s*\};",actual)
    if empty != ["sEmptyMoveset"]:
        raise ValueError("Unexpected empty active learnset: " + str(empty))
    moves = set(re.findall(r"^#define\s+(MOVE_\w+)\b",(ROOT / "include/constants/moves.h").read_text(),re.M))
    affected = []
    for name in TARGETS:
        pairs = re.findall(r"LEVEL_UP_MOVE\(\s*(\d+),\s*(MOVE_\w+)\)",get(actual,name))
        if not all(0 <= int(level) <= 100 and move in moves for level,move in pairs):
            raise ValueError("Invalid restored level/move: " + name)
        affected += re.findall(r"\[(SPECIES_\w+)\]\s*=\s*s"+name+r"LevelUpLearnset\b",actual)
    print("PASS: five exact tracked-source restorations, no unrelated changes, "
          + str(len(affected)) + " species/form pointers retain their bindings")


if __name__ == "__main__": check_source_contract()
