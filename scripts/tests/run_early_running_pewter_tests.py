#!/usr/bin/env python3
"""Run #583 native movement, stateless settings and Pewter checks."""

from pathlib import Path
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    subprocess.run(["python3", "scripts/tests/audit_early_running_pewter.py"], cwd=ROOT, check=True)
    subprocess.run(["python3", "scripts/tests/audit_early_running_lifecycle.py"], cwd=ROOT, check=True)
    from audit_early_running_lifecycle import c_function
    with tempfile.TemporaryDirectory(prefix="cfru-early-running-lifecycle-") as directory:
        overworld = (ROOT / "src/overworld.c").read_text()
        signatures = ("static bool8 IsRunningDisabledByFlag(void)",
                      "bool8 IsRunningDisallowedByMetatile(u8 tile)",
                      "bool8 IsRunningDisallowed(u8 tile)",
                      "bool8 ShouldPlayerRun(u16 heldKeys)")
        source = "\n".join(c_function(overworld, signature) for signature in signatures)
        source += "\n" + c_function((ROOT / "src/read_keys.c").read_text(),
                                    "bool8 StartLButtonFunc(void)")
        (Path(directory) / "early_running_functions.inc").write_text(source)
        binary = Path(directory) / "early_running_lifecycle_host"
        subprocess.run([
            "cc", "-std=c99", "-Wall", "-Wextra", "-Werror",
            "-Wno-unknown-attributes", "-Iinclude", "-Isrc", "-I", directory,
            "scripts/tests/early_running_lifecycle_host.c", "src/settings.c", "-o", str(binary),
        ], cwd=ROOT, check=True)
        subprocess.run([str(binary)], cwd=ROOT, check=True)
    subprocess.run(["python3", "scripts/insert.py", "--check-map-object-overlays"], cwd=ROOT, check=True)
    print("Issues #538/#583 targeted tests: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
