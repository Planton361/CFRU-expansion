#!/usr/bin/env python3

import ast
import json
import re
import shutil
import subprocess
import sys

############
# Options go here.
############

ROM_NAME = "BPRE0.gba"  # The name of your rom
OFFSET_TO_PUT = 0x1000000
SEARCH_FREE_SPACE = False  # Set to True if you want the script to search for free space
                           # Set to False if you don't want to search for free space as you for example update the engine

#############
# Options end here.
#############

###############
# Functions start here.
###############


def MakeOffset0x100Aligned(offset: int) -> int:
    while offset % 16 != 0:
        offset += 1

    return offset


def FindOffsetToPut(rom, neededBytes: int, startOffset: int) -> int:
    offset = startOffset
    rom.seek(0, 2)
    maxPosition = rom.tell()
    numFoundBytes = 0

    while numFoundBytes < neededBytes:
        if offset + numFoundBytes >= maxPosition:
            print("End of file reached. Not enough free space.")
            return 0

        numFoundBytes += 1
        rom.seek(offset + numFoundBytes)
        if rom.read(1) != b'\xFF':
            offset = MakeOffset0x100Aligned(offset + numFoundBytes)
            numFoundBytes = 0

    return offset


def ChangeFileLine(filePath: str, lineToChange: int, replacement: str):
    with open(filePath, 'r') as file:
        copy = file.read()
        file.seek(0x0)
        lineNum = 1
        for line in file:
            if lineNum == lineToChange:
                copy = copy.replace(line, replacement)
                break
            lineNum += 1

    with open(filePath, 'w') as file:
        file.write(copy)


def _SourceOffset(source: str, line: int, byteColumn: int) -> int:
    lines = source.splitlines(keepends=True)
    if line < 1 or line > len(lines):
        raise ValueError("Assignment source position is outside the file")

    prefix = "".join(lines[:line - 1])
    bytePrefix = lines[line - 1].encode('utf-8')[:byteColumn]
    try:
        characterPrefix = bytePrefix.decode('utf-8')
    except UnicodeDecodeError as error:
        raise ValueError("Assignment source position is not on a UTF-8 boundary") from error
    return len(prefix) + len(characterPrefix)


def UpdatePythonAssignments(filePath: str, replacements: dict):
    with open(filePath, 'r', encoding='utf-8', newline='') as file:
        source = file.read()

    tree = ast.parse(source, filename=filePath)
    assignmentNodes = {name: [] for name in replacements}
    for statement in tree.body:
        if not isinstance(statement, ast.Assign) or len(statement.targets) != 1:
            continue
        target = statement.targets[0]
        if isinstance(target, ast.Name) and target.id in assignmentNodes:
            assignmentNodes[target.id].append(statement.value)

    spans = []
    for name, replacement in replacements.items():
        matches = assignmentNodes[name]
        if len(matches) != 1:
            raise ValueError("Expected exactly one top-level assignment to {}; found {}".format(name, len(matches)))
        expression = matches[0]
        if not hasattr(expression, 'end_lineno') or not hasattr(expression, 'end_col_offset'):
            raise ValueError("Python runtime cannot locate the assignment expression for " + name)
        start = _SourceOffset(source, expression.lineno, expression.col_offset)
        end = _SourceOffset(source, expression.end_lineno, expression.end_col_offset)
        spans.append((start, end, replacement))

    updated = source
    for start, end, replacement in sorted(spans, reverse=True):
        updated = updated[:start] + replacement + updated[end:]
    ast.parse(updated, filename=filePath)

    with open(filePath, 'w', encoding='utf-8', newline='') as file:
        file.write(updated)


def UpdateLinkerRomOrigin(filePath: str, offset: int):
    with open(filePath, 'r', encoding='utf-8', newline='') as file:
        source = file.read()

    pattern = re.compile(
        r"(?m)^(?P<prefix>[ \t]*rom[ \t]*:[ \t]*ORIGIN[ \t]*=[ \t]*)"
        r"(?P<expression>[^,\r\n]+?)(?P<spacing>[ \t]*)"
        r"(?P<suffix>,[ \t]*LENGTH[ \t]*=[ \t]*32M[ \t]*(?:\#.*)?)"
        r"(?P<newline>\r?\n|\Z)"
    )
    matches = list(pattern.finditer(source))
    if len(matches) != 1:
        raise ValueError("Expected exactly one rom ORIGIN region in {}; found {}".format(filePath, len(matches)))

    match = matches[0]
    expression = match.group('expression').strip()
    if re.fullmatch(r"\(\s*0x08000000\s*\+\s*0[xX][0-9a-fA-F]+\s*\)", expression) is None:
        raise ValueError("The rom ORIGIN expression in {} is not the expected FireRed offset form".format(filePath))

    replacement = (match.group('prefix') + "(0x08000000 + " + hex(offset) + ")"
                   + match.group('spacing') + match.group('suffix') + match.group('newline'))
    updated = source[:match.start()] + replacement + source[match.end():]
    with open(filePath, 'w', encoding='utf-8', newline='') as file:
        file.write(updated)


def EditLinker(offset: int, filePath: str = "linker.ld"):
    UpdateLinkerRomOrigin(filePath, offset)


def EditInsert(offset: int, filePath: str = "./scripts/insert.py"):
    UpdatePythonAssignments(filePath, {
        "OFFSET_TO_PUT": hex(offset),
        "SOURCE_ROM": json.dumps(ROM_NAME),
    })


def RunPythonScript(scriptPath: str):
    interpreter = "python3" if shutil.which('python3') is not None else "python"
    try:
        return subprocess.run([interpreter, scriptPath], check=True)
    except OSError:
        print("Error: Could not execute " + scriptPath + ".", file=sys.stderr)
        sys.exit(1)


def BuildCode():
    RunPythonScript("scripts/build.py")


def InsertCode():
    RunPythonScript("scripts/insert.py")


def CheckNativeSourceIdentity():
    RunPythonScript("scripts/check_native_source_identity.py")


def ClearFromTo(rom, from_: int, to_: int):
    rom.seek(from_)
    for i in range(0, to_ - from_):
        rom.write(b'\xFF')

##############
# Functions end here.
##############


def main():
    CheckNativeSourceIdentity()
    try:
        with open(ROM_NAME, 'rb+') as rom:
            offset = OFFSET_TO_PUT
            if SEARCH_FREE_SPACE is True:
                offset = FindOffsetToPut(rom, 0x50000, MakeOffset0x100Aligned(offset))

            EditLinker(offset)
            EditInsert(offset)
            BuildCode()
            InsertCode()
            rom.close()

    except FileNotFoundError:
        print('Error: Could not find source rom: "' + ROM_NAME + '".\n'
              + 'Please make sure a rom with this name exists in the root.')
        sys.exit(1)


if __name__ == '__main__':
    main()
