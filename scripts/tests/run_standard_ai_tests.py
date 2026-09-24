#!/usr/bin/env python3
"""Run the source-owned Standard policy and fairness checks on a host."""

from pathlib import Path
import argparse
import ast
import re
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[2]


def run(command):
    subprocess.run(command, cwd=ROOT, check=True)


def check_arm_objects(compiler):
    # Parse the literal, never import build.py (which has build side effects).
    tree = ast.parse((ROOT / "scripts/build.py").read_text())
    flags = next(ast.literal_eval(node.value) for node in tree.body
                 if isinstance(node, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id == "CFLAGS" for t in node.targets))
    prefix = compiler.removesuffix("gcc")
    linker_symbols = set(re.findall(r"^(\w+)\s*=", (ROOT / "BPRE.ld").read_text(), re.M))
    def symbols(arguments):
        return {line.split()[-1] for line in subprocess.check_output(
            [prefix + "nm", *arguments], cwd=ROOT, text=True).splitlines() if line.strip()}
    with tempfile.TemporaryDirectory(prefix="standard-arm-objects-") as directory:
        helper = str(Path(directory) / "existing_helpers.o")
        run([prefix + "as", "-mthumb", "-I", "assembly", "assembly/thumb_compiler_helper.s", "-o", helper])
        bound = symbols(["--defined-only", "-g", helper])
        dependencies = symbols(["-u", helper])
        assert dependencies <= linker_symbols, sorted(dependencies - linker_symbols)
        objects = []
        for source in ("src/Battle_AI/ai_standard_policy.c",
                       "src/Battle_AI/ai_standard_mechanics.c",
                       "src/Battle_AI/ai_standard.c",
                       "src/Battle_AI/ai_ironmon_policy.c",
                       "src/Battle_AI/ai_ironmon.c",
                       "src/battle_strings.c",
                       "src/general_bs_commands.c", "src/switching.c"):
            name = Path(source).stem
            obj = str(Path(directory) / (name + ".o"))
            print("ARM object command:", "arm-none-eabi-gcc", *flags, "-c", source, "-o", f"<temporary>/{name}.o", flush=True)
            run([compiler, *flags, "-fstack-usage", "-c", source, "-o", obj])
            undefined = symbols(["-u", obj])
            print(name + " undefined:", ", ".join(sorted(undefined)), flush=True)
            runtime = {s for s in undefined if s.startswith("__")}
            assert runtime <= bound | linker_symbols, sorted(runtime - bound - linker_symbols)
            print(name + " bound runtime:", ", ".join(sorted(runtime)) or "none")
            stack = Path(directory) / (name + ".su")
            if stack.is_file():
                rows = [row for row in stack.read_text().splitlines() if row.strip()]
                maximum = max(int(row.split("\t")[1]) for row in rows)
                print(f"{name} stack-usage maximum static estimate: {maximum} bytes; functions={len(rows)}")
            size_output = subprocess.check_output(
                [prefix + "size", obj], cwd=ROOT, text=True).splitlines()
            print(name + " object size:", size_output[-1].strip())
            objects.append(obj)
        # A relocatable direct-ld closure proves the existing source wrappers
        # resolve the emitted runtime names; engine relocations remain expected.
        combined = str(Path(directory) / "standard_runtime_closure.o")
        run([prefix + "ld", "-r", *objects, helper, "-o", combined])
        remaining = symbols(["-u", combined])
        assert {s for s in remaining if s.startswith("__")} <= linker_symbols
        print("ARM direct-ld runtime closure PASS; remaining engine/BPRE symbol count:", len(remaining))
    print("ARM unsupported compiler runtime helpers: NONE; temporary objects deleted")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm-cc", help="already-installed approved devkitARM compiler")
    args = parser.parse_args()
    run(["python3", "scripts/tests/audit_ai_damage_overrides.py"])
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
            "src/Battle_AI/ai_standard_mechanics.c",
            "src/Battle_AI/ai_ironmon_policy.c", "-o", str(adapter_binary),
        ])
        subprocess.run([str(adapter_binary)], cwd=ROOT, check=True)

        history_binary = Path(directory) / "ironmon_history_clear_host"
        run([
            "cc", "-std=gnu99", "-w", "-Wno-unknown-attributes", "-Iinclude",
            "-ffunction-sections", "-fdata-sections",
            "scripts/tests/ironmon_history_clear_host.c", "src/battle_util.c",
            "-Wl,-dead_strip", "-o", str(history_binary),
        ])
        subprocess.run([str(history_binary)], cwd=ROOT, check=True)
        print("Ironmon real ClearBattlerMoveHistory lifecycle: usedMoves/counts cleared PASS")

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
        sources = {source for source in sources if source.startswith("src/")}
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
        check_arm_objects(args.arm_cc)
        print(f"ARM object revision: {revision}; dirty={dirty}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
