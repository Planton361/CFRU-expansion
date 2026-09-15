#!/usr/bin/env python3
"""Compile the real M-013 callback with synthetic host services; no ROM input."""
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    source = (ROOT / "src/item.c").read_text()
    start = source.index("// Premier Ball Bonus\n")
    end = source.index("\n\n#define tItemCount", start)
    callback = source[start:end]
    assert (ROOT / "hooks").read_text().splitlines().count(
        "Task_ReturnToItemListAfterItemPurchase 809BF68 1") == 1
    config = (ROOT / "src/config.h").read_text()
    for flag in ("MULTIPLE_PREMIER_BALLS_AT_ONCE", "ENABLE_MULTIPLE_PURCHASE_REWARDS"):
        assert re.search(r"^#define " + flag + r"\b", config, re.M), flag
    harness = (ROOT / "scripts/tests/m013_premier_host.c").read_text()
    assert harness.count("/* PURCHASE_SOURCE */") == 1
    with tempfile.TemporaryDirectory(prefix="m013-host-") as tmp:
        path = Path(tmp) / "test.c"
        path.write_text(harness.replace("/* PURCHASE_SOURCE */", callback))
        exe = Path(tmp) / "test"
        subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror",
                        "-fsanitize=undefined,bounds", "-I", str(ROOT), str(path),
                        "-o", str(exe)], check=True)
        subprocess.run([str(exe)], check=True)


if __name__ == "__main__":
    main()
