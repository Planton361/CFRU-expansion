#!/usr/bin/env python3
"""Run the source-owned Standard policy and fairness checks on a host."""

from pathlib import Path
import argparse
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[2]


def run(command):
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm-cc", help="already-installed approved devkitARM compiler")
    args = parser.parse_args()
    run(["python3", "scripts/tests/audit_standard_ai.py"])
    with tempfile.TemporaryDirectory(prefix="cfru-standard-ai-") as directory:
        binary = Path(directory) / "standard_ai_policy_host"
        run([
            "cc", "-std=c99", "-Wall", "-Wextra", "-Werror", "-Iinclude",
            "scripts/tests/standard_ai_policy_host.c",
            "src/Battle_AI/ai_standard_policy.c",
            "-o", str(binary),
        ])
        subprocess.run([str(binary)], cwd=ROOT, check=True)

        adapter_binary = Path(directory) / "standard_ai_adapter_host"
        run([
            "cc", "-std=gnu99", "-Wall", "-Wextra", "-Werror",
            "-Wno-unknown-attributes", "-Iinclude",
            "scripts/tests/standard_ai_adapter_host.c",
            "src/Battle_AI/ai_standard_policy.c",
            "src/Battle_AI/ai_standard_mechanics.c", "-o", str(adapter_binary),
        ])
        subprocess.run([str(adapter_binary)], cwd=ROOT, check=True)

        layout_binary = Path(directory) / "standard_ai_layout_host"
        run([
            "cc", "-std=gnu99", "-Wno-unknown-attributes", "-Iinclude",
            "scripts/tests/standard_ai_layout_host.c", "-o", str(layout_binary),
        ])
        subprocess.run([str(layout_binary)], cwd=ROOT, check=True)
    print("standard AI source tests: PASS")
    if args.arm_cc:
        base = "8bc8c38210ddba0b05c933dbda06cb4539254c7a"
        sources = set(subprocess.check_output(
            ["git", "diff", "--name-only", base, "--", "*.c"], cwd=ROOT, text=True).splitlines())
        sources.update(subprocess.check_output(
            ["git", "ls-files", "--others", "--exclude-standard", "--", "*.c"], cwd=ROOT, text=True).splitlines())
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT))
        run([args.arm_cc, "--version"])
        for source in sorted(sources):
            # Production build uses relative includes. -Iinclude would shadow
            # newlib's <strings.h> with this engine's unrelated strings.h.
            run([args.arm_cc, "-std=gnu99", "-mthumb", "-mcpu=arm7tdmi",
                 "-march=armv4t", "-Wall", "-Wextra", "-fsyntax-only", source])
            print("ARM syntax PASS:", source)
        print(f"ARM syntax revision: {revision}; dirty={dirty}; {len(sources)} C files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
