#!/usr/bin/env python3
"""Focused ROM-free tests for native source identity and compositional guards."""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BASE_SHA = "e37d36174c2341d43a6649fc73240c3388e19243"
sys.path.insert(0, str(ROOT / "scripts"))

from check_hidden_item_sparkle import (  # noqa: E402
    check_composition_variants,
    check_rejections,
    check_source_contract,
)


def require(condition, message):
    if not condition:
        raise AssertionError("native build contract regression: " + message)


def run_identity(checker, checkout):
    return subprocess.run(
        [sys.executable, str(checker), "--root", str(checkout)],
        cwd=checkout,
        text=True,
        capture_output=True,
        check=False,
    )


def test_tracked_source_identity_allows_private_and_ignored_inputs():
    with tempfile.TemporaryDirectory(prefix="cfru-native-source-identity-") as temp:
        checkout = Path(temp) / "checkout"
        subprocess.run(
            ["git", "clone", "--shared", "--no-checkout", str(ROOT), str(checkout)],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        subprocess.run(["git", "-C", str(checkout), "checkout", "--detach", BASE_SHA],
                       check=True, stdout=subprocess.DEVNULL)
        head = subprocess.check_output(
            ["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True).strip()
        require(head == BASE_SHA, "identity fixture is not the exact accepted CFRU base")

        checker = Path(temp) / "check_native_source_identity.py"
        shutil.copyfile(ROOT / "scripts" / "check_native_source_identity.py", checker)
        result = run_identity(checker, checkout)
        require(result.returncode == 0 and "PASS" in result.stdout,
                "clean exact-base checkout did not pass")

        # Empty placeholders only: these paths stand in for ignored inputs and
        # generated names; no ROM contents are opened or inspected.
        (checkout / "BPRE0.gba").touch()
        (checkout / "test.gba").touch()
        build_output = checkout / "build" / "identity-fixture.o"
        build_output.parent.mkdir()
        build_output.touch()
        result = run_identity(checker, checkout)
        require(result.returncode == 0,
                "untracked BPRE0.gba or ignored build/test output broke source identity")

        untracked_source = checkout / "src" / "identity-fixture.c"
        untracked_source.touch()
        result = run_identity(checker, checkout)
        require(result.returncode != 0 and "unexpected untracked files" in result.stderr,
                "untracked source file did not fail")
        untracked_source.unlink()

        source = checkout / "src" / "overworld.c"
        original = source.read_text(encoding="utf-8")
        source.write_text(original + "\n/* synthetic tracked edit */\n", encoding="utf-8")
        result = run_identity(checker, checkout)
        require(result.returncode != 0 and "clean tracked source" in result.stderr,
                "tracked source modification did not fail")
        source.write_text(original, encoding="utf-8")
        result = run_identity(checker, checkout)
        require(result.returncode == 0, "restored exact-base checkout did not pass")


def main():
    check_source_contract()
    check_composition_variants()
    check_rejections()
    test_tracked_source_identity_allows_private_and_ignored_inputs()
    print("native build source-identity and compositional guard tests: PASS")


if __name__ == "__main__":
    main()
