#!/usr/bin/env python3
"""ROM-free regressions for make.py's semantic configuration edits."""
import ast
import importlib.util
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MAKE_PATH = ROOT / "scripts" / "make.py"
INSERT_PATH = ROOT / "scripts" / "insert.py"
LINKER_PATH = ROOT / "linker.ld"

spec = importlib.util.spec_from_file_location("cfru_make", MAKE_PATH)
make = importlib.util.module_from_spec(spec)
spec.loader.exec_module(make)


def require(condition, message):
    if not condition:
        raise AssertionError("make.py assignment regression: " + message)


def read_text(path):
    with open(path, "r", encoding="utf-8", newline="") as file:
        return file.read()


def write_text(path, value):
    with open(path, "w", encoding="utf-8", newline="") as file:
        file.write(value)


def module_values(source):
    result = {}
    for statement in ast.parse(source).body:
        if isinstance(statement, ast.Assign) and len(statement.targets) == 1:
            target = statement.targets[0]
            if isinstance(target, ast.Name) and target.id in {"OFFSET_TO_PUT", "SOURCE_ROM"}:
                result[target.id] = ast.literal_eval(statement.value)
    return result


def expect_fail_without_write(path, action, label):
    before = read_text(path)
    try:
        action()
    except ValueError:
        require(read_text(path) == before, label + " partially modified its file")
        return
    raise AssertionError("make.py assignment regression: " + label + " was accepted")


def check_insert_updates_after_import_shift():
    original = read_text(INSERT_PATH)
    shifted = original.replace("#!/usr/bin/env python3\n", "#!/usr/bin/env python3\nimport typing\n\n", 1)
    shifted = shifted.replace("OFFSET_TO_PUT = 0x1000000\n",
                              "OFFSET_TO_PUT = 0x1000000  # keep offset note\n", 1)
    shifted = shifted.replace('SOURCE_ROM = "BPRE0.gba"\n',
                              'SOURCE_ROM = "BPRE0.gba"  # keep ROM note\n', 1)
    require(shifted != original, "import/blank-line fixture did not change the source")
    with tempfile.TemporaryDirectory(prefix="cfru-make-insert-") as temp:
        target = Path(temp) / "insert.py"
        write_text(target, shifted)
        original_rom_name = make.ROM_NAME
        make.ROM_NAME = "BPRE1.gba"
        try:
            make.EditInsert(0x1234560, str(target))
        finally:
            make.ROM_NAME = original_rom_name
        actual = read_text(target)
        expected = shifted.replace("OFFSET_TO_PUT = 0x1000000", "OFFSET_TO_PUT = 0x1234560", 1)
        expected = expected.replace('SOURCE_ROM = "BPRE0.gba"', 'SOURCE_ROM = "BPRE1.gba"', 1)
        require(actual == expected, "import shift changed unrelated insert.py text")
        values = module_values(actual)
        require(values["OFFSET_TO_PUT"] == 0x1234560, "offset assignment was not updated")
        require(values["SOURCE_ROM"] == "BPRE1.gba", "source ROM assignment was not updated")
        require("import typing\n\n" in actual, "new import/blank line was not preserved")
        require("# keep offset note" in actual and "# keep ROM note" in actual,
                "assignment-line comments were not preserved")
    require(make.ROM_NAME == "BPRE0.gba", "make.py ROM_NAME default changed")
    print("PASS: shifted imports and blank lines cannot corrupt insert.py; defaults and unrelated text are preserved")


def check_insert_assignment_failures_are_atomic():
    original = read_text(INSERT_PATH)
    cases = (
        ("missing offset", original.replace("OFFSET_TO_PUT = 0x1000000\n", "", 1)),
        ("duplicate offset", original.replace("OFFSET_TO_PUT = 0x1000000\n",
                                               "OFFSET_TO_PUT = 0x1000000\nOFFSET_TO_PUT = 0x1000000\n", 1)),
        ("missing source", original.replace('SOURCE_ROM = "BPRE0.gba"\n', "", 1)),
        ("duplicate source", original.replace('SOURCE_ROM = "BPRE0.gba"\n',
                                                'SOURCE_ROM = "BPRE0.gba"\nSOURCE_ROM = "BPRE0.gba"\n', 1)),
    )
    for label, fixture in cases:
        with tempfile.TemporaryDirectory(prefix="cfru-make-invalid-insert-") as temp:
            target = Path(temp) / "insert.py"
            write_text(target, fixture)
            expect_fail_without_write(target, lambda: make.EditInsert(0x1234560, str(target)), label)
    print("PASS: zero/multiple OFFSET_TO_PUT and SOURCE_ROM assignments fail before any write")


def check_linker_update_and_rejections():
    original = read_text(LINKER_PATH)
    rom_line = "\t\trom     : ORIGIN = (0x08000000 + 0x1000000), LENGTH = 32M\n"
    require(original.count(rom_line) == 1, "linker fixture anchor changed")
    shifted = original.replace(rom_line, "\n" + rom_line, 1)
    with tempfile.TemporaryDirectory(prefix="cfru-make-linker-") as temp:
        target = Path(temp) / "linker.ld"
        write_text(target, shifted)
        make.EditLinker(0x2345678, str(target))
        actual = read_text(target)
        expected = shifted.replace("(0x08000000 + 0x1000000)", "(0x08000000 + 0x2345678)", 1)
        require(actual == expected, "linker edit changed unrelated text or depended on a line number")

    invalid_cases = (
        ("missing rom region", original.replace(rom_line, "", 1)),
        ("duplicate rom region", original.replace(rom_line, rom_line + rom_line, 1)),
        ("invalid rom expression", original.replace("(0x08000000 + 0x1000000)", "0x08000000", 1)),
    )
    for label, fixture in invalid_cases:
        with tempfile.TemporaryDirectory(prefix="cfru-make-invalid-linker-") as temp:
            target = Path(temp) / "linker.ld"
            write_text(target, fixture)
            expect_fail_without_write(target, lambda: make.EditLinker(0x2345678, str(target)), label)
    print("PASS: linker rom-region edit is semantic, exact-one-match and fail-closed")


def main():
    check_insert_updates_after_import_shift()
    check_insert_assignment_failures_are_atomic()
    check_linker_update_and_rejections()
    print("make.py ROM-free regression suite: PASS")


if __name__ == "__main__":
    main()
