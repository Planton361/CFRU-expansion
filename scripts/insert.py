#!/usr/bin/env python3

import os
import subprocess
import shutil
import sys
from datetime import datetime
import _io

OFFSET_TO_PUT = 0x1000000
SOURCE_ROM = "BPRE0.gba"
ROM_NAME = "test.gba"

if sys.platform.startswith('win'):
    PathVar = os.environ.get('Path')
    Paths = PathVar.split(';')
    PATH = ''
    for candidatePath in Paths:
        if 'devkitARM' in candidatePath:
            PATH = candidatePath
            break
    if PATH == '':
        PATH = 'C://devkitPro//devkitARM//bin'
        if os.path.isdir(PATH) is False:
            print('Devkit not found.')
            sys.exit(1)

    PREFIX = 'arm-none-eabi-'
    OBJDUMP = os.path.join(PATH, PREFIX + 'objdump')
    NM = os.path.join(PATH, PREFIX + 'nm')
    AS = os.path.join(PATH, PREFIX + 'as')

else:  # Linux, OSX, etc.
    PREFIX = 'arm-none-eabi-'
    OBJDUMP = (PREFIX + 'objdump')
    NM = (PREFIX + 'nm')
    AS = (PREFIX + 'as')

OUTPUT = 'build/output.bin'
BYTE_REPLACEMENT = 'bytereplacement'
HOOKS = 'hooks'
REPOINTS = 'repoints'
GENERATED_REPOINTS = 'generatedrepoints'
REPOINT_ALL = 'repointall'
ROUTINE_POINTERS = 'routinepointers'
FUNCTION_REWRITES = 'functionrewrites'
EVENT_SCRIPTS = "eventscripts"
MAP_OBJECT_OVERLAYS = "mapobjectoverlays"
SONGS = "songs"
SPECIAL_INSERTS = 'special_inserts.asm'
SPECIAL_INSERTS_OUT = 'build/special_inserts.bin'
FREE_BYTE_REPLACEMENTS = 'free_bytereplacements'
MAP_BANKS_HEADER_POINTER = 0x5524C
MAP_HEADER_EVENTS_OFFSET = 0x4
EVENT_OBJECT_TEMPLATE_SIZE = 0x18
FIND_ITEM_SCRIPT_SIZE = 0xC


def ExtractPointer(byteList: [bytes]):
    pointer = 0
    for a in range(len(byteList)):
        pointer += (int(byteList[a])) << (8 * a)

    return pointer


def AlignOffset(offset: int, alignment: int = 4) -> int:
    while offset % alignment != 0:
        offset += 1
    return offset


def ReadPointer(rom: _io.BufferedReader, offset: int) -> int:
    rom.seek(offset)
    return ExtractPointer(rom.read(4))


def WritePointer(rom: _io.BufferedReader, offset: int, pointer: int):
    rom.seek(offset)
    rom.write(pointer.to_bytes(4, 'little'))


def ResolveNumericOrDefine(token: str, definesDict: dict) -> int:
    if token in definesDict:
        token = definesDict[token]

    return int(str(token), 0)


def ResolveMapHeader(rom: _io.BufferedReader, mapBanksHeader: int, mapBank: int, mapNum: int) -> int:
    mapBankHeader = ReadPointer(rom, mapBanksHeader + mapBank * 4) - 0x08000000
    if mapBankHeader == (0xF7F7F7F7 - 0x08000000):
        raise ValueError("Garbage map bank header")

    mapHeader = ReadPointer(rom, mapBankHeader + mapNum * 4) - 0x08000000
    if mapHeader == (0xF7F7F7F7 - 0x08000000):
        raise ValueError("Garbage map header")

    return mapHeader


def BuildEventObjectTemplate(localId: int, graphicsId: int, x: int, y: int, elevation: int, movementType: int,
                             movementRangeX: int, movementRangeY: int, trainerType: int, trainerRange: int,
                             scriptPointer: int, flagId: int, flagId2: int) -> bytes:
    data = bytearray()
    data += localId.to_bytes(1, 'little')
    data += (graphicsId & 0xFF).to_bytes(1, 'little')
    data += (0).to_bytes(1, 'little')  # inConnection
    data += ((graphicsId >> 8) & 0xFF).to_bytes(1, 'little')
    data += x.to_bytes(2, 'little', signed=True)
    data += y.to_bytes(2, 'little', signed=True)
    data += elevation.to_bytes(1, 'little')
    data += movementType.to_bytes(1, 'little')
    data += ((movementRangeX & 0xF) | ((movementRangeY & 0xF) << 4)).to_bytes(1, 'little')
    data += (0).to_bytes(1, 'little')  # struct padding before u16 fields
    data += trainerType.to_bytes(2, 'little')
    data += trainerRange.to_bytes(2, 'little')
    data += scriptPointer.to_bytes(4, 'little')
    data += flagId.to_bytes(2, 'little')
    data += flagId2.to_bytes(2, 'little')
    return bytes(data)


def ReadEventObjectTemplate(data: bytes) -> dict:
    if len(data) != EVENT_OBJECT_TEMPLATE_SIZE:
        raise ValueError("Event object template must be exactly {} bytes".format(EVENT_OBJECT_TEMPLATE_SIZE))

    return {
        "localId": data[0],
        "graphicsId": data[1] | (data[3] << 8),
        "graphicsIdLowerByte": data[1],
        "inConnection": data[2],
        "graphicsIdUpperByte": data[3],
        "x": int.from_bytes(data[4:6], 'little', signed=True),
        "y": int.from_bytes(data[6:8], 'little', signed=True),
        "elevation": data[8],
        "movementType": data[9],
        "movementRangeX": data[10] & 0xF,
        "movementRangeY": (data[10] >> 4) & 0xF,
        "padding": data[11],
        "trainerType": int.from_bytes(data[12:14], 'little'),
        "trainerRange": int.from_bytes(data[14:16], 'little'),
        "scriptPointer": int.from_bytes(data[16:20], 'little'),
        "flagId": int.from_bytes(data[20:22], 'little'),
        "flagId2": int.from_bytes(data[22:24], 'little'),
    }


def FindEventObjectTemplate(objectData: bytes, localId: int) -> (int, dict):
    if len(objectData) % EVENT_OBJECT_TEMPLATE_SIZE != 0:
        raise ValueError("Object table is not a sequence of 24-byte templates")

    matches = []
    for objectIndex in range(len(objectData) // EVENT_OBJECT_TEMPLATE_SIZE):
        offset = objectIndex * EVENT_OBJECT_TEMPLATE_SIZE
        template = ReadEventObjectTemplate(objectData[offset:offset + EVENT_OBJECT_TEMPLATE_SIZE])
        if template["localId"] == localId:
            matches.append((offset, template))

    if len(matches) != 1:
        raise ValueError("Expected exactly one object with local id {}, found {}".format(localId, len(matches)))

    return matches[0]


def ValidateEventObjectTemplate(template: dict, expected: dict, label: str):
    expectedFields = (
        "localId", "graphicsId", "x", "y", "elevation", "movementType",
        "movementRangeX", "movementRangeY", "trainerType", "trainerRange",
        "flagId", "flagId2",
    )
    for field in expectedFields:
        if field in expected and template[field] != expected[field]:
            raise ValueError("{} {} expected {}, found {}".format(label, field, expected[field], template[field]))

    if template["inConnection"] != 0:
        raise ValueError("{} unexpectedly uses an in-connection template".format(label))
    if template["padding"] != 0:
        raise ValueError("{} has nonzero struct padding".format(label))
    if template["scriptPointer"] < 0x08000000:
        raise ValueError("{} has an invalid script pointer".format(label))
    if "scriptPointer" in expected and template["scriptPointer"] != expected["scriptPointer"]:
        raise ValueError("{} scriptPointer expected {}, found {}".format(
            label, expected["scriptPointer"], template["scriptPointer"]))


def FindEventObjectTemplateByExpectation(objectData: bytes, expected: dict) -> (int, dict):
    if len(objectData) % EVENT_OBJECT_TEMPLATE_SIZE != 0:
        raise ValueError("Object table is not a sequence of 24-byte templates")

    expectedFields = (
        "localId", "graphicsId", "x", "y", "elevation", "movementType",
        "movementRangeX", "movementRangeY", "trainerType", "trainerRange",
        "flagId", "flagId2",
    )
    matches = []
    for objectIndex in range(len(objectData) // EVENT_OBJECT_TEMPLATE_SIZE):
        offset = objectIndex * EVENT_OBJECT_TEMPLATE_SIZE
        template = ReadEventObjectTemplate(objectData[offset:offset + EVENT_OBJECT_TEMPLATE_SIZE])
        if all(field not in expected or template[field] == expected[field] for field in expectedFields):
            matches.append((offset, template))

    if len(matches) != 1:
        raise ValueError("Expected exactly one object matching the source-backed template, found {}".format(len(matches)))

    offset, template = matches[0]
    ValidateEventObjectTemplate(template, expected, "target object")
    return offset, template


def ValidatePokeCenterNurseWrapperBytes(script: bytes, label: str) -> int:
    # lock; faceplayer; call EventScript_PkmnCenterNurse; release; end
    if len(script) != 9 or script[0:3] != bytes([0x6A, 0x5A, 0x04]) or script[7:9] != bytes([0x6C, 0x02]):
        raise ValueError("{} is not the expected vanilla PokeCenter Nurse wrapper".format(label))
    commonScriptPointer = int.from_bytes(script[3:7], 'little')
    if commonScriptPointer < 0x08000000:
        raise ValueError("{} has an invalid common Nurse script pointer".format(label))
    return commonScriptPointer


def ValidatePokeCenterNurseWrapper(rom: _io.BufferedReader, scriptPointer: int, label: str) -> int:
    rom.seek(scriptPointer - 0x08000000)
    return ValidatePokeCenterNurseWrapperBytes(rom.read(9), label)


def ReplaceEventObjectScript(objectData: bytes, expectedCount: int, expected: dict, scriptPointer: int) -> (bytes, int, int):
    if len(objectData) != expectedCount * EVENT_OBJECT_TEMPLATE_SIZE:
        raise ValueError("Object data length does not match expected object count {}".format(expectedCount))

    targetOffset, targetTemplate = FindEventObjectTemplateByExpectation(objectData, expected)
    replaced = bytearray(objectData)
    replaced[targetOffset + 16:targetOffset + 20] = scriptPointer.to_bytes(4, 'little')
    return bytes(replaced), targetOffset, targetTemplate["scriptPointer"]


def BuildFindItemScript(expectedItem: int) -> bytes:
    return bytes([
        0x1A, 0x00, 0x80, expectedItem & 0xFF, (expectedItem >> 8) & 0xFF,
        0x1A, 0x01, 0x80, 0x01, 0x00,
        0x09, 0x01,
    ])


def ValidateFindItemScriptBytes(script: bytes, expectedItem: int, label: str):
    expected = bytes([
        0x1A, 0x00, 0x80, expectedItem & 0xFF, (expectedItem >> 8) & 0xFF,
        0x1A, 0x01, 0x80, 0x01, 0x00,
        0x09, 0x01,
    ])
    if script != expected:
        raise ValueError("{} does not point to the expected standard finditem script".format(label))


def ValidateFindItemScript(rom: _io.BufferedReader, scriptPointer: int, expectedItem: int, label: str):
    rom.seek(scriptPointer - 0x08000000)
    ValidateFindItemScriptBytes(rom.read(FIND_ITEM_SCRIPT_SIZE), expectedItem, label)


def ReplaceEventObjectGraphics(objectData: bytes, expectedCount: int, target: dict, control: dict = None) -> (bytes, int, int):
    if len(objectData) != expectedCount * EVENT_OBJECT_TEMPLATE_SIZE:
        raise ValueError("Object data length does not match expected object count {}".format(expectedCount))

    targetOffset, targetTemplate = FindEventObjectTemplate(objectData, target["localId"])
    ValidateEventObjectTemplate(targetTemplate, target, "target object")
    controlOffset = None
    if control is not None:
        controlOffset, controlTemplate = FindEventObjectTemplate(objectData, control["localId"])
        ValidateEventObjectTemplate(controlTemplate, control, "control object")

    oldGraphicsId = target["graphicsId"]
    newGraphicsId = target["newGraphicsId"]
    if oldGraphicsId != 0x005C or newGraphicsId != 0x065C:
        raise ValueError("TM itemball rollout requires the exact 0x005C -> 0x065C graphics contract")
    if (oldGraphicsId & 0xFF) != 0x5C or (newGraphicsId & 0xFF) != 0x5C:
        raise ValueError("TM itemball rollout must retain graphics-id lower byte 0x5C")

    replaced = bytearray(objectData)
    replaced[targetOffset + 3] = (newGraphicsId >> 8) & 0xFF
    replaced = bytes(replaced)

    changedOffsets = [i for i, (before, after) in enumerate(zip(objectData, replaced)) if before != after]
    if changedOffsets != [targetOffset + 3]:
        raise ValueError("Serialized target must differ only at graphics-id upper byte")
    if replaced[targetOffset + 1] != 0x5C:
        raise ValueError("Serialized target graphics-id lower byte changed")
    if controlOffset is not None and replaced[controlOffset:controlOffset + EVENT_OBJECT_TEMPLATE_SIZE] != \
            objectData[controlOffset:controlOffset + EVENT_OBJECT_TEMPLATE_SIZE]:
        raise ValueError("Serialized control object changed")

    return replaced, targetOffset, controlOffset


def ParseEventObjectExpectation(tokens: [str], definesDict: dict) -> dict:
    fieldNames = [
        "localId", "graphicsId", "x", "y", "elevation", "movementType", "movementRangeX", "movementRangeY",
        "trainerType", "trainerRange", "scriptPointer", "flagId", "flagId2",
    ]
    if len(tokens) != len(fieldNames):
        raise ValueError("Invalid replace object expectation")
    return {field: ResolveNumericOrDefine(token, definesDict) for field, token in zip(fieldNames, tokens)}


def ParseEventObjectReplacement(tokens: [str], definesDict: dict) -> dict:
    fieldNames = [
        "graphicsId", "x", "y", "elevation", "movementType", "movementRangeX", "movementRangeY",
        "trainerType", "trainerRange", "scriptSymbol", "flagId", "flagId2",
    ]
    if len(tokens) != len(fieldNames):
        raise ValueError("Invalid replace object replacement")

    replacement = {}
    for field, token in zip(fieldNames, tokens):
        replacement[field] = token if field == "scriptSymbol" else ResolveNumericOrDefine(token, definesDict)
    return replacement


def ReplaceEventObject(objectData: bytes, expectedCount: int, expected: dict, replacement: dict,
                       replacementScriptPointer: int) -> (bytes, int):
    if len(objectData) != expectedCount * EVENT_OBJECT_TEMPLATE_SIZE:
        raise ValueError("Object data length does not match expected object count {}".format(expectedCount))

    targetOffset, targetTemplate = FindEventObjectTemplate(objectData, expected["localId"])
    ValidateEventObjectTemplate(targetTemplate, expected, "target object")

    replacementTemplate = BuildEventObjectTemplate(
        expected["localId"], replacement["graphicsId"], replacement["x"], replacement["y"],
        replacement["elevation"], replacement["movementType"], replacement["movementRangeX"],
        replacement["movementRangeY"], replacement["trainerType"], replacement["trainerRange"],
        replacementScriptPointer, replacement["flagId"], replacement["flagId2"])
    replaced = bytearray(objectData)
    replaced[targetOffset:targetOffset + EVENT_OBJECT_TEMPLATE_SIZE] = replacementTemplate
    replaced = bytes(replaced)

    if replaced[:targetOffset] != objectData[:targetOffset] or \
            replaced[targetOffset + EVENT_OBJECT_TEMPLATE_SIZE:] != \
            objectData[targetOffset + EVENT_OBJECT_TEMPLATE_SIZE:]:
        raise ValueError("Object replacement changed a non-target object")
    if replaced[targetOffset:targetOffset + EVENT_OBJECT_TEMPLATE_SIZE] != replacementTemplate:
        raise ValueError("Object replacement did not serialize the requested target")

    return replaced, targetOffset


def BuildMapEvents(eventObjectCount: int, warpCount: int, coordEventCount: int, bgEventCount: int,
                   eventObjectsPointer: int, warpsPointer: int, coordEventsPointer: int,
                   bgEventsPointer: int) -> bytes:
    data = bytearray([eventObjectCount, warpCount, coordEventCount, bgEventCount])
    data += eventObjectsPointer.to_bytes(4, 'little')
    data += warpsPointer.to_bytes(4, 'little')
    data += coordEventsPointer.to_bytes(4, 'little')
    data += bgEventsPointer.to_bytes(4, 'little')
    return bytes(data)


def RunMapObjectOverlaySelfTest():
    expectedRows = [
        (1, 1, 14, 9, 'ITEM_TM09', 'FLAG_HIDE_MT_MOON_1F_TM09'),
        (1, 3, 11, 9, 'ITEM_TM46', 'FLAG_HIDE_MT_MOON_B2F_TM46'),
        (3, 22, 7, 3, 'ITEM_TM05', 'FLAG_HIDE_ROUTE4_TM05'),
        (3, 43, 8, 8, 'ITEM_TM45', 'FLAG_HIDE_ROUTE24_TM45'),
        (3, 44, 13, 10, 'ITEM_TM43', 'FLAG_HIDE_ROUTE25_TM43'),
        (1, 13, 4, 4, 'ITEM_TM31', 'FLAG_HIDE_SSANNE_1F_ROOM2_TM31'),
        (1, 25, 2, 2, 'ITEM_TM44', 'FLAG_HIDE_SSANNE_B1F_ROOM2_TM44'),
        (3, 27, 12, 11, 'ITEM_TM40', 'FLAG_HIDE_ROUTE9_TM40'),
        (1, 43, 5, 4, 'ITEM_TM12', 'FLAG_HIDE_ROCKET_HIDEOUT_B2F_TM12'),
        (1, 44, 5, 4, 'ITEM_TM21', 'FLAG_HIDE_ROCKET_HIDEOUT_B3F_TM21'),
        (1, 45, 9, 7, 'ITEM_TM49', 'FLAG_HIDE_ROCKET_HIDEOUT_B4F_TM49'),
        (3, 30, 14, 10, 'ITEM_TM48', 'FLAG_HIDE_ROUTE12_TM48'),
        (3, 33, 14, 11, 'ITEM_TM18', 'FLAG_HIDE_ROUTE15_TM18'),
        (1, 64, 4, 3, 'ITEM_TM11', 'FLAG_HIDE_SAFARI_ZONE_EAST_TM11'),
        (1, 65, 3, 2, 'ITEM_TM47', 'FLAG_HIDE_SAFARI_ZONE_NORTH_TM47'),
        (1, 66, 4, 2, 'ITEM_TM32', 'FLAG_HIDE_SAFARI_ZONE_WEST_TM32'),
        (1, 51, 9, 7, 'ITEM_TM01', 'FLAG_HIDE_SILPH_CO_5F_TM01'),
        (1, 53, 11, 11, 'ITEM_TM08', 'FLAG_HIDE_SILPH_CO_7F_TM08'),
        (1, 95, 8, 2, 'ITEM_TM17', 'FLAG_HIDE_POWER_PLANT_TM17'),
        (1, 95, 8, 3, 'ITEM_TM25', 'FLAG_HIDE_POWER_PLANT_TM25'),
        (1, 62, 6, 1, 'ITEM_TM22', 'FLAG_HIDE_POKEMON_MANSION_B1F_TM22'),
        (1, 62, 6, 4, 'ITEM_TM14', 'FLAG_HIDE_POKEMON_MANSION_B1F_TM14'),
        (1, 39, 7, 4, 'ITEM_TM02', 'FLAG_HIDE_VICTORY_ROAD_1F_TM02'),
        (1, 40, 13, 7, 'ITEM_TM07', 'FLAG_HIDE_VICTORY_ROAD_2F_TM07'),
        (1, 40, 13, 9, 'ITEM_TM37', 'FLAG_HIDE_VICTORY_ROAD_2F_TM37'),
        (1, 41, 12, 6, 'ITEM_TM50', 'FLAG_HIDE_VICTORY_ROAD_3F_TM50'),
        (1, 111, 2, 2, 'ITEM_HM07_WATERFALL', 'FLAG_HIDE_FOUR_ISLAND_ICEFALL_CAVE_1F_HM07'),
        (1, 114, 10, 8, 'ITEM_TM36', 'FLAG_HIDE_FIVE_ISLAND_ROCKET_WAREHOUSE_TM36'),
        (1, 50, 8, 8, 'ITEM_TM41', 'FLAG_HIDE_SILPH_CO_4F_TM41'),
    ]
    expectedByKey = {(bank, mapNum, localId): (count, item, flag)
                     for bank, mapNum, count, localId, item, flag in expectedRows}
    noControlKeys = {
        (3, 22, 3), (3, 43, 8), (3, 44, 10),
        (1, 13, 4), (1, 25, 2), (3, 33, 11), (1, 66, 2),
    }
    assert len(expectedRows) == len(expectedByKey) == 29

    definesDict = {}
    conditionals = []
    replaceLines = []
    with open(MAP_OBJECT_OVERLAYS, 'r') as overlayFile:
        for line in overlayFile:
            if TryProcessFileInclusion(line, definesDict):
                continue
            if TryProcessConditionalCompilation(line, definesDict, conditionals):
                continue
            if line.strip().lower().startswith('replace_graphics '):
                replaceLines.append(line.split())
    assert len(replaceLines) == 29

    actualKeys = set()
    actualItems = []
    for line in replaceLines:
        assert len(line) in (18, 31)
        _, mapBank, mapNum, expectedCount = line[:4]
        mapBank = ResolveNumericOrDefine(mapBank, definesDict)
        mapNum = ResolveNumericOrDefine(mapNum, definesDict)
        expectedCount = ResolveNumericOrDefine(expectedCount, definesDict)
        target = ParseReplacementExpectation(line[4:18], definesDict, True)
        key = (mapBank, mapNum, target['localId'])
        assert key in expectedByKey
        assert key not in actualKeys
        actualKeys.add(key)
        expectedObjectCount, expectedItemToken, expectedFlagToken = expectedByKey[key]
        assert expectedCount == expectedObjectCount
        assert target['graphicsId'] == 0x005C
        assert target['newGraphicsId'] == 0x065C
        assert target['graphicsId'] & 0xFF == target['newGraphicsId'] & 0xFF == 0x5C
        assert target['expectedItem'] == ResolveNumericOrDefine(expectedItemToken, definesDict)
        assert target['flagId'] == ResolveNumericOrDefine(expectedFlagToken, definesDict)
        assert target['flagId2'] == 0
        actualItems.append(target['expectedItem'])
        ValidateFindItemScriptBytes(BuildFindItemScript(target['expectedItem']), target['expectedItem'], 'target object')

        hasControl = len(line) == 31
        assert hasControl == (key not in noControlKeys)
        control = ParseReplacementExpectation(line[18:31], definesDict, False) if hasControl else None
        if control is not None:
            assert control['localId'] != target['localId']
            assert control['graphicsId'] == 0x005C
            assert control['flagId2'] == 0
            ValidateFindItemScriptBytes(BuildFindItemScript(control['expectedItem']), control['expectedItem'], 'control object')

        templates = []
        for localId in range(1, expectedCount + 1):
            expectation = target if localId == target['localId'] else control if control is not None and localId == control['localId'] else None
            if expectation is None:
                templates.append(BuildEventObjectTemplate(localId, 1, localId, localId, 3, 8, 1, 1, 0, 0, 0x08000100, 0, 0))
            else:
                templates.append(BuildEventObjectTemplate(
                    expectation['localId'], expectation['graphicsId'], expectation['x'], expectation['y'],
                    expectation['elevation'], expectation['movementType'], expectation['movementRangeX'],
                    expectation['movementRangeY'], expectation['trainerType'], expectation['trainerRange'],
                    0x08000200, expectation['flagId'], expectation['flagId2']))
        objects = b''.join(templates)
        replaced, targetOffset, controlOffset = ReplaceEventObjectGraphics(objects, expectedCount, target, control)
        assert [index for index, pair in enumerate(zip(objects, replaced)) if pair[0] != pair[1]] == [targetOffset + 3]
        assert replaced[targetOffset + 1] == 0x5C
        if controlOffset is not None:
            assert replaced[controlOffset:controlOffset + EVENT_OBJECT_TEMPLATE_SIZE] == \
                objects[controlOffset:controlOffset + EVENT_OBJECT_TEMPLATE_SIZE]

        beforeEvents = BuildMapEvents(expectedCount, 2, 1, 4, 0x08001000, 0x08002000, 0x08003000, 0x08004000)
        afterEvents = BuildMapEvents(expectedCount, 2, 1, 4, 0x08100000, 0x08002000, 0x08003000, 0x08004000)
        assert beforeEvents[0] == afterEvents[0] == expectedCount
        assert beforeEvents[8:] == afterEvents[8:]

    assert actualKeys == set(expectedByKey)
    assert actualItems.count(ResolveNumericOrDefine('ITEM_TM09', definesDict)) == 1
    assert actualItems.count(ResolveNumericOrDefine('ITEM_HM07_WATERFALL', definesDict)) == 1

    with open('src/character_customization.c', 'r') as graphicsSwitcherFile:
        graphicsSwitcherSource = graphicsSwitcherFile.read()
    switcherStart = graphicsSwitcherSource.index('gOverworldTableSwitcher[255]')
    switcherEnd = graphicsSwitcherSource.index('};', switcherStart)
    switcherInitializer = graphicsSwitcherSource[switcherStart:switcherEnd]
    assert switcherInitializer.count('[TM_ITEM_BALL_GRAPHICS_TABLE_ID]') == 1
    assert switcherInitializer.count('gTmItemBallOverworldTable') == 1

    with open('src/Tables/tm_itemball_graphics.c', 'r') as graphicsTableFile:
        graphicsTableSource = graphicsTableFile.read()
    assert graphicsTableSource.count('[TM_ITEM_BALL_GRAPHICS_INDEX] = &sTmItemBallGraphicsInfo') == 1
    print("mapobjectoverlays replace_graphics serialized-diff checks passed")


def RunViridianForestNurseOverlaySelfTest():
    definesDict = {}
    conditionals = []
    replaceLines = []
    with open(MAP_OBJECT_OVERLAYS, 'r') as overlayFile:
        for line in overlayFile:
            if TryProcessFileInclusion(line, definesDict):
                continue
            if TryProcessConditionalCompilation(line, definesDict, conditionals):
                continue
            if line.strip().lower().startswith('replace '):
                replaceLines.append(line.split())

    assert len(replaceLines) == 1
    line = replaceLines[0]
    assert len(line) == 29
    _, mapBank, mapNum, expectedCount = line[:4]
    assert ResolveNumericOrDefine(mapBank, definesDict) == 1
    assert ResolveNumericOrDefine(mapNum, definesDict) == 0
    assert ResolveNumericOrDefine(expectedCount, definesDict) == 11

    expected = ParseEventObjectExpectation(line[4:17], definesDict)
    replacement = ParseEventObjectReplacement(line[17:29], definesDict)
    assert expected == {
        "localId": 1, "graphicsId": 0x12,
        "x": 29, "y": 58, "elevation": 3,
        "movementType": ResolveNumericOrDefine("MOVEMENT_TYPE_FACE_UP", definesDict),
        "movementRangeX": 1, "movementRangeY": 1, "trainerType": 0, "trainerRange": 0,
        "scriptPointer": 0x08160529, "flagId": 0, "flagId2": 0,
    }
    assert replacement == {
        "graphicsId": 0x40,
        "x": 29, "y": 58, "elevation": 3,
        "movementType": ResolveNumericOrDefine("MOVEMENT_TYPE_FACE_DOWN", definesDict),
        "movementRangeX": 1, "movementRangeY": 1, "trainerType": 0, "trainerRange": 0,
        "scriptSymbol": "EventScript_ViridianForest_Nurse", "flagId": 0, "flagId2": 0,
    }

    otherObjects = [
        BuildEventObjectTemplate(localId, 1, localId, localId, 3, 8, 1, 1, 0, 0, 0x08000100, 0, 0)
        for localId in range(2, 12)
    ]
    original = BuildEventObjectTemplate(
        expected["localId"], expected["graphicsId"], expected["x"], expected["y"], expected["elevation"],
        expected["movementType"], expected["movementRangeX"], expected["movementRangeY"], expected["trainerType"],
        expected["trainerRange"], expected["scriptPointer"], expected["flagId"], expected["flagId2"]) + b''.join(otherObjects)
    replaced, targetOffset = ReplaceEventObject(original, 11, expected, replacement, 0x08100000)
    assert targetOffset == 0
    assert replaced[EVENT_OBJECT_TEMPLATE_SIZE:] == original[EVENT_OBJECT_TEMPLATE_SIZE:]
    assert ReadEventObjectTemplate(replaced[:EVENT_OBJECT_TEMPLATE_SIZE]) == {
        "localId": 1, "graphicsId": replacement["graphicsId"], "graphicsIdLowerByte": replacement["graphicsId"] & 0xFF,
        "inConnection": 0, "graphicsIdUpperByte": replacement["graphicsId"] >> 8,
        "x": 29, "y": 58, "elevation": 3, "movementType": replacement["movementType"],
        "movementRangeX": 1, "movementRangeY": 1, "padding": 0, "trainerType": 0, "trainerRange": 0,
        "scriptPointer": 0x08100000, "flagId": 0, "flagId2": 0,
    }

    beforeEvents = BuildMapEvents(11, 6, 0, 8, 0x08001000, 0x08002000, 0x08003000, 0x08004000)
    afterEvents = BuildMapEvents(11, 6, 0, 8, 0x08100000, 0x08002000, 0x08003000, 0x08004000)
    assert beforeEvents[0] == afterEvents[0] == 11
    assert beforeEvents[8:] == afterEvents[8:]
    print("Viridian Forest nurse object replacement checks passed")


def RunInstantPokeCenterHealingOverlaySelfTest():
    definesDict = {}
    conditionals = []
    scriptLines = []
    with open(MAP_OBJECT_OVERLAYS, 'r') as overlayFile:
        for line in overlayFile:
            if TryProcessFileInclusion(line, definesDict):
                continue
            if TryProcessConditionalCompilation(line, definesDict, conditionals):
                continue
            if line.strip().lower().startswith('replace_script '):
                scriptLines.append(line.split())

    expectedMapKeys = {
        (5, 4), (10, 12), (11, 5), (8, 0), (21, 0), (16, 0), (14, 6),
        (7, 3), (12, 5), (13, 0), (33, 2), (34, 1), (35, 1), (36, 0),
        (37, 0), (31, 3), (32, 0), (6, 5), (9, 1),
    }
    assert len(scriptLines) == len(expectedMapKeys)
    actualMapKeys = set()
    for line in scriptLines:
        assert len(line) == 16
        _, mapBank, mapNum, expectedCount = line[:4]
        mapBank = ResolveNumericOrDefine(mapBank, definesDict)
        mapNum = ResolveNumericOrDefine(mapNum, definesDict)
        assert mapBank != 10 or mapNum != 10  # Trainer Tower is intentionally untouched.
        actualMapKeys.add((mapBank, mapNum))
        assert ResolveNumericOrDefine(expectedCount, definesDict) >= 4
        expected = ParseScriptReplacementExpectation(line[4:15], definesDict)
        assert expected["graphicsId"] == ResolveNumericOrDefine("MAP_OBJ_GFX_NURSE", definesDict)
        assert expected["movementType"] == ResolveNumericOrDefine("MOVEMENT_TYPE_FACE_DOWN", definesDict)
        assert expected["movementRangeX"] == expected["movementRangeY"] == 1
        assert expected["trainerType"] == expected["trainerRange"] == expected["flagId"] == expected["flagId2"] == 0
        assert line[15] == "EventScript_InstantPokeCenterNurse"
    assert actualMapKeys == expectedMapKeys

    expected = ParseScriptReplacementExpectation(scriptLines[0][4:15], definesDict)
    nurse = BuildEventObjectTemplate(
        7, expected["graphicsId"], expected["x"], expected["y"], expected["elevation"],
        expected["movementType"], expected["movementRangeX"], expected["movementRangeY"],
        expected["trainerType"], expected["trainerRange"], 0x08123456, expected["flagId"], expected["flagId2"])
    decoy = BuildEventObjectTemplate(8, 1, 1, 1, 3, 8, 1, 1, 0, 0, 0x08000100, 0, 0)
    original = nurse + decoy
    replaced, targetOffset, originalScriptPointer = ReplaceEventObjectScript(
        original, 2, expected, 0x08100000)
    assert targetOffset == 0
    assert originalScriptPointer == 0x08123456
    assert replaced[:16] == original[:16]
    assert replaced[16:20] == (0x08100000).to_bytes(4, 'little')
    assert replaced[20:] == original[20:]

    commonScriptPointer = ValidatePokeCenterNurseWrapperBytes(
        bytes([0x6A, 0x5A, 0x04]) + (0x08123456).to_bytes(4, 'little') + bytes([0x6C, 0x02]),
        "self-test Nurse wrapper")
    assert commonScriptPointer == 0x08123456
    try:
        ValidatePokeCenterNurseWrapperBytes(bytes([0x6A, 0x5A, 0x05, 0, 0, 0, 0, 0x6C, 0x02]), "invalid wrapper")
        raise AssertionError("invalid Nurse wrapper unexpectedly validated")
    except ValueError:
        pass
    print("instant PokeCenter healing overlay checks passed")


def ParseReplacementExpectation(tokens: [str], definesDict: dict, hasNewGraphicsId: bool) -> dict:
    fieldNames = ["localId", "graphicsId"]
    if hasNewGraphicsId:
        fieldNames.append("newGraphicsId")
    fieldNames += [
        "x", "y", "elevation", "movementType", "movementRangeX", "movementRangeY",
        "trainerType", "trainerRange", "expectedItem", "flagId", "flagId2",
    ]
    if len(tokens) != len(fieldNames):
        raise ValueError("Invalid replace_graphics object expectation")
    return {field: ResolveNumericOrDefine(token, definesDict) for field, token in zip(fieldNames, tokens)}


def ParseScriptReplacementExpectation(tokens: [str], definesDict: dict) -> dict:
    fieldNames = [
        "graphicsId", "x", "y", "elevation", "movementType", "movementRangeX", "movementRangeY",
        "trainerType", "trainerRange", "flagId", "flagId2",
    ]
    if len(tokens) != len(fieldNames):
        raise ValueError("Invalid replace_script object expectation")
    return {field: ResolveNumericOrDefine(token, definesDict) for field, token in zip(fieldNames, tokens)}


def InsertMapObjectOverlays(rom: _io.BufferedReader, table: {str: int}, startOffset: int) -> int:
    if not os.path.isfile(MAP_OBJECT_OVERLAYS):
        return startOffset

    insertOffset = AlignOffset(startOffset)
    mapBanksHeader = ReadPointer(rom, MAP_BANKS_HEADER_POINTER) - 0x08000000
    definesDict = {}
    conditionals = []
    commonPokeCenterNurseScriptPointer = None

    with open(MAP_OBJECT_OVERLAYS, 'r') as file:
        for i, line in enumerate(file):
            if TryProcessFileInclusion(line, definesDict):
                continue
            if TryProcessConditionalCompilation(line, definesDict, conditionals):
                continue
            if line.strip().startswith('#') or line.strip() == '':
                continue

            try:
                parts = line.split()
                action = parts[0].lower()
                if action == "append":
                    if len(parts) != 17:
                        raise ValueError("append requires 17 fields")
                    _, mapBank, mapNum, expectedCount, localId, graphicsId, x, y, elevation, movementType, \
                        movementRangeX, movementRangeY, trainerType, trainerRange, scriptSymbol, flagId, flagId2 = parts
                    appendValues = [
                        localId, graphicsId, x, y, elevation, movementType, movementRangeX, movementRangeY,
                        trainerType, trainerRange, flagId, flagId2,
                    ]
                    localId, graphicsId, x, y, elevation, movementType, movementRangeX, movementRangeY, \
                        trainerType, trainerRange, flagId, flagId2 = \
                        [ResolveNumericOrDefine(value, definesDict) for value in appendValues]
                    if scriptSymbol not in table:
                        raise ValueError("Symbol missing: {}".format(scriptSymbol))
                elif action == "replace":
                    if len(parts) != 29:
                        raise ValueError("replace requires 29 fields")
                    _, mapBank, mapNum, expectedCount = parts[:4]
                    expected = ParseEventObjectExpectation(parts[4:17], definesDict)
                    replacement = ParseEventObjectReplacement(parts[17:29], definesDict)
                    if replacement["scriptSymbol"] not in table:
                        raise ValueError("Symbol missing: {}".format(replacement["scriptSymbol"]))
                elif action == "replace_graphics":
                    if len(parts) not in (18, 31):
                        raise ValueError("replace_graphics requires 18 target fields or 31 target/control fields")
                    _, mapBank, mapNum, expectedCount = parts[:4]
                    target = ParseReplacementExpectation(parts[4:18], definesDict, True)
                    control = ParseReplacementExpectation(parts[18:31], definesDict, False) if len(parts) == 31 else None
                elif action == "replace_script":
                    if len(parts) != 16:
                        raise ValueError("replace_script requires 16 fields")
                    _, mapBank, mapNum, expectedCount = parts[:4]
                    expected = ParseScriptReplacementExpectation(parts[4:15], definesDict)
                    scriptSymbol = parts[15]
                    if scriptSymbol not in table:
                        raise ValueError("Symbol missing: {}".format(scriptSymbol))
                else:
                    raise ValueError("Unknown map object overlay action: {}".format(action))

                mapBank = ResolveNumericOrDefine(mapBank, definesDict)
                mapNum = ResolveNumericOrDefine(mapNum, definesDict)
                expectedCount = ResolveNumericOrDefine(expectedCount, definesDict)

                mapHeader = ResolveMapHeader(rom, mapBanksHeader, mapBank, mapNum)
                eventHeader = ReadPointer(rom, mapHeader + MAP_HEADER_EVENTS_OFFSET) - 0x08000000
                rom.seek(eventHeader)
                eventObjectCount = rom.read(1)[0]
                warpCount = rom.read(1)[0]
                coordEventCount = rom.read(1)[0]
                bgEventCount = rom.read(1)[0]
                eventObjectsPointer = ReadPointer(rom, eventHeader + 0x4)
                warpsPointer = ReadPointer(rom, eventHeader + 0x8)
                coordEventsPointer = ReadPointer(rom, eventHeader + 0xC)
                bgEventsPointer = ReadPointer(rom, eventHeader + 0x10)

                if eventObjectCount != expectedCount:
                    print("Error! Map object overlay expected {} objects for map bank {}, map {}, found {} on line {}: {}".format(
                        expectedCount, mapBank, mapNum, eventObjectCount, i, line.strip()))
                    sys.exit(1)

                rom.seek(eventObjectsPointer - 0x08000000)
                objectData = rom.read(eventObjectCount * EVENT_OBJECT_TEMPLATE_SIZE)
                if action == "append":
                    objectData += BuildEventObjectTemplate(
                        localId, graphicsId, x, y, elevation, movementType,
                        movementRangeX, movementRangeY, trainerType, trainerRange,
                        table[scriptSymbol] + 0x08000000, flagId, flagId2)
                    newEventObjectCount = eventObjectCount + 1
                elif action == "replace":
                    objectData, targetOffset = ReplaceEventObject(
                        objectData, expectedCount, expected, replacement,
                        table[replacement["scriptSymbol"]] + 0x08000000)
                    newEventObjectCount = eventObjectCount
                elif action == "replace_graphics":
                    objectData, targetOffset, controlOffset = ReplaceEventObjectGraphics(
                        objectData, expectedCount, target, control)
                    targetTemplate = ReadEventObjectTemplate(
                        objectData[targetOffset:targetOffset + EVENT_OBJECT_TEMPLATE_SIZE])
                    ValidateFindItemScript(rom, targetTemplate["scriptPointer"], target["expectedItem"], "target object")
                    if controlOffset is not None:
                        controlTemplate = ReadEventObjectTemplate(
                            objectData[controlOffset:controlOffset + EVENT_OBJECT_TEMPLATE_SIZE])
                        ValidateFindItemScript(rom, controlTemplate["scriptPointer"], control["expectedItem"], "control object")
                    newEventObjectCount = eventObjectCount
                else:
                    objectData, targetOffset, originalScriptPointer = ReplaceEventObjectScript(
                        objectData, expectedCount, expected, table[scriptSymbol] + 0x08000000)
                    commonScriptPointer = ValidatePokeCenterNurseWrapper(
                        rom, originalScriptPointer, "target object")
                    if commonPokeCenterNurseScriptPointer is None:
                        commonPokeCenterNurseScriptPointer = commonScriptPointer
                    elif commonPokeCenterNurseScriptPointer != commonScriptPointer:
                        raise ValueError("normal PokeCenter Nurse wrappers do not share the expected common script")
                    newEventObjectCount = eventObjectCount

                insertOffset = AlignOffset(insertOffset)
                newObjectTableOffset = insertOffset
                rom.seek(newObjectTableOffset)
                rom.write(objectData)
                insertOffset += len(objectData)

                insertOffset = AlignOffset(insertOffset)
                newMapEventsOffset = insertOffset
                rom.seek(newMapEventsOffset)
                newMapEvents = BuildMapEvents(
                    newEventObjectCount, warpCount, coordEventCount, bgEventCount,
                    newObjectTableOffset + 0x08000000, warpsPointer, coordEventsPointer, bgEventsPointer)
                if newMapEvents[0] != newEventObjectCount or \
                        newMapEvents[8:20] != \
                        warpsPointer.to_bytes(4, 'little') + coordEventsPointer.to_bytes(4, 'little') + \
                        bgEventsPointer.to_bytes(4, 'little'):
                    raise ValueError("MapEvents count or non-object pointers changed unexpectedly")
                rom.write(newMapEvents)
                insertOffset += 0x14

                WritePointer(rom, mapHeader + MAP_HEADER_EVENTS_OFFSET, newMapEventsOffset + 0x08000000)
            except Exception as e:
                print("There was an error inserting the map object overlay on line {}: {}".format(i, line.strip()))
                print(e)
                sys.exit(1)

    return insertOffset


def GetTextSection() -> int:
    try:
        # Dump sections
        out = subprocess.check_output([OBJDUMP, '-t', 'build/linked.o'])
        lines = out.decode().split('\n')

        # Find text section
        text = filter(lambda x: x.strip().endswith('.text'), lines)
        section = (list(text))[0]

        # Get the offset
        offset = int(section.split(' ')[0], 16)
        return offset

    except:
        print("Error: The insertion process could not be completed.\n"
              + "The linker symbol file was not found. Most likely the compilation process was not completed.")
        sys.exit(1)


def GetSymbols(subtract=0) -> {str: int}:
    out = subprocess.check_output([NM, 'build/linked.o'])
    lines = out.decode().split('\n')

    ret = {}
    for line in lines:
        parts = line.strip().split()

        if len(parts) < 3:
            continue

        if parts[1].lower() not in {'t', 'd'}:
            continue

        offset = int(parts[0], 16)
        ret[parts[2]] = offset - subtract

    return ret


def Hook(rom: _io.BufferedReader, space: int, hookAt: int, register=0):
    # Align 2
    if hookAt & 1:
        hookAt -= 1

    rom.seek(hookAt)

    register &= 7

    if hookAt % 4:
        data = bytes([0x01, 0x48 | register, 0x00 | (register << 3), 0x47, 0x0, 0x0])
    else:
        data = bytes([0x00, 0x48 | register, 0x00 | (register << 3), 0x47])

    space += 0x08000001
    data += (space.to_bytes(4, 'little'))
    rom.write(bytes(data))


def FunctionWrap(rom: _io.BufferedReader, space: int, hookAt: int, numParams: int, isReturning: int):
    # Align 2
    if hookAt & 1:
        hookAt -= 1

    rom.seek(hookAt)
    numParams = numParams - 1

    if numParams < 4:
        data = bytes([0x10, 0xB5, 0x3, 0x4C, 0x0, 0xF0, 0x3, 0xF8, 0x10, 0xBC,
                      (isReturning + 1), 0xBC, (isReturning << 3), 0x47, 0x20, 0x47])
    else:
        k = numParams - 3
        data = bytes([0x10, 0xB5, 0x82, 0xB0])
        for i in range(k + 2):
            data += bytes([i + 2, 0x9C, i, 0x94])
        data += bytes([0x0, 0x9C, numParams - 1, 0x94, 0x1, 0x9C, numParams, 0x94, 0x2, 0xB0, k + 8, 0x4C,
                       0x0, 0xF0, (k << 1) + 13, 0xF8, 0x82, 0xB0, numParams, 0x9C, 0x1, 0x94, numParams - 1,
                       0x9C, 0x0, 0x94])

        for i in reversed(range(k + 2)):
            data += bytes([i, 0x9C, i+2, 0x94])
        data += bytes([0x2, 0xB0, 0x10, 0xBC, isReturning + 1, 0xBC, isReturning << 3, 0x47, 0x20, 0x47])

    space += 0x08000001
    data += (space.to_bytes(4, 'little'))
    rom.write(bytes(data))


def Repoint(rom: _io.BufferedReader, space: int, repointAt: int, slideFactor=0):
    rom.seek(repointAt)

    space += (0x08000000 + slideFactor)
    data = (space.to_bytes(4, 'little'))
    rom.write(bytes(data))


def RecordGeneratedRepoint(generatedRepoints: set, symbol: str, offset: int):
    key = (symbol, offset)
    if key in generatedRepoints:
        return

    with open(GENERATED_REPOINTS, 'a') as repointList:
        repointList.write(symbol + ' ' + str(offset) + '\n')
    generatedRepoints.add(key)


# These offsets contain the word 0x8900000 - the attack data from
# Mr. DS's rombase. In order to maintain as much compatibility as
# possible, the data at these offsets is never modified.
IGNORED_OFFSETS = {0x3986C0: True, 0x3986EC: True, 0xDABDF0: True}


def RealRepoint(sourceRom: _io.BufferedReader, targetRom: _io.BufferedReader, offsetTuples: [(int, int, str)], endInsertOffset):
    pointerList = []
    pointerDict = {}
    for tup in offsetTuples:  # Format is (Double Pointer, New Pointer, Symbol)
        offset = tup[0]
        sourceRom.seek(offset)
        pointer = ExtractPointer(sourceRom.read(4))
        pointerList.append(pointer)
        pointerDict[pointer] = (tup[1] + 0x08000000, tup[2])

    offset = 0
    offsetList = []

    while offset < 0xFFFFFD:
        if offset in IGNORED_OFFSETS:
            offset += 4
            continue
        elif OFFSET_TO_PUT <= offset < endInsertOffset:  # Skip insert area
            offset = endInsertOffset
            while offset % 4 != 0:  # End insert offset is not divisible by 4
                offset += 1  # Make divisible by 4
            continue

        sourceRom.seek(offset)
        word = ExtractPointer(sourceRom.read(4))
        targetRom.seek(offset)

        for pointer in pointerList:
            if word == pointer:
                offsetList.append((offset, pointerDict[pointer][1]))
                targetRom.write(bytes(pointerDict[pointer][0].to_bytes(4, 'little')))
                break

        offset += 4

    return offsetList


def ReplaceBytes(rom: _io.BufferedReader, offset: int, data: str):
    ar = offset
    words = data.split()
    for i in range(0, len(words)):
        rom.seek(ar)
        intByte = int(words[i], 16)
        rom.write(bytes(intByte.to_bytes(1, 'big')))
        ar += 1


def TryProcessFileInclusion(line: str, definesDict: dict) -> bool:
    if line.startswith('#include "'):
        try:
            path = line.split('"')[1].strip()
            with open(path, 'r') as file:
                for line in file:
                    if line.startswith('#define '):
                        try:
                            lineList = line.strip().split()
                            title = lineList[1]

                            if len(lineList) == 2 or lineList[2].startswith('//') or lineList[2].startswith('/*'):
                                define = True
                            else:
                                define = lineList[2]

                            definesDict[title] = define
                        except IndexError:
                            print('Error reading define on line"' + line.strip() + '" in file "' + path + '".')

        except Exception as e:
            print('Error including file on line "' + line.strip() + '".')
            print(e)

        return True  # Inclusion line; don't read otherwise

    return False


def TryProcessConditionalCompilation(line: str, definesDict: dict, conditionals: [(str, bool)]) -> bool:
    line = line.strip()
    upperLine = line.upper()
    numWordsOnLine = len(line.split())

    if upperLine.startswith('#IFDEF ') and numWordsOnLine > 1:
        condition = line.strip().split()[1]
        conditionals.insert(0, (condition, True))  # Insert at front
        return True
    elif upperLine.startswith('#IFNDEF ') and numWordsOnLine > 1:
        condition = line.strip().split()[1]
        conditionals.insert(0, (condition, False))  # Insert at front
        return True
    elif upperLine == '#ELSE':
        if len(conditionals) >= 1:  # At least one statement was pushed before
            condition = conditionals.pop(0)
            if condition[1] is True:
                conditionals.insert(0, (condition[0], False))  # Invert old statement
            else:
                conditionals.insert(0, (condition[0], True))  # Invert old statement
            return True
    elif upperLine == '#ENDIF':
        conditionals.pop(0)  # Remove first element (last pushed)
        return True
    else:
        for condition in conditionals:
            definedType = condition[1]
            condition = condition[0]

            if definedType is True:  # From #ifdef
                if condition not in definesDict:
                    return True  # If something isn't defined then skip the line
            else:  # From #ifndef
                if condition in definesDict:
                    return True  # If something is defined then skip the line

    return False


def main():
    startTime = datetime.now()

    try:
        shutil.copyfile(SOURCE_ROM, ROM_NAME)
    except FileNotFoundError:
        print('Error: Insertion could not be completed.\n'
              + 'Could not find source rom: "' + SOURCE_ROM + '".\n'
              + 'Please make sure a rom with this name exists in the root.')
        sys.exit(1)
    except PermissionError:
        print('Error: Insertion could not be completed.\n'
              + '"' + ROM_NAME + '" is currently in use by another application.'
              + '\nPlease free it up before trying again.')
        sys.exit(1)

    with open(ROM_NAME, 'rb+') as rom:
        print("Inserting code.")
        table = GetSymbols(GetTextSection())
        rom.seek(OFFSET_TO_PUT)
        with open(OUTPUT, 'rb') as binary:
            endInsertOffset = OFFSET_TO_PUT + os.path.getsize(OUTPUT)
            rom.write(binary.read())
            binary.close()

        # Adjust symbol table
        for entry in table:
            table[entry] += OFFSET_TO_PUT

        # Deal with en masse repoints
        symbolsRepointed = set()
        generatedRepoints = set()
        if os.path.isfile(GENERATED_REPOINTS):
            with open(GENERATED_REPOINTS, 'r') as repointList:
                for line in repointList:
                    if line.strip().startswith('#') or line.strip() == '':
                        continue

                    symbol, address = line.split()
                    offset = int(address)
                    generatedRepoints.add((symbol, offset))
                    try:
                        code = table[symbol]
                    except KeyError:
                        print('Symbol missing:', symbol)
                        continue

                    symbolsRepointed.add(symbol)
                    Repoint(rom, code, offset)

        else:
            with open(GENERATED_REPOINTS, 'w') as repointList:
                repointList.write('##This is a generated file at runtime. Do not modify it!\n')

        if os.path.isfile(REPOINT_ALL):
            offsetsToRepointTogether = []
            with open(REPOINT_ALL, 'r') as repointList:
                definesDict = {}
                conditionals = []
                for line in repointList:
                    if TryProcessFileInclusion(line, definesDict):
                        continue
                    if TryProcessConditionalCompilation(line, definesDict, conditionals):
                        continue
                    if line.strip().startswith('#') or line.strip() == '':
                        continue

                    symbol, address = line.split()
                    offset = int(address, 16) - 0x08000000

                    if symbol in symbolsRepointed:
                        continue

                    try:
                        code = table[symbol]
                    except KeyError:
                        print('Symbol missing:', symbol)
                        continue
                    offsetsToRepointTogether.append((offset, code, symbol))

                if offsetsToRepointTogether != []:
                    with open(SOURCE_ROM, 'rb') as sourceRom: # Repoint from source rom so new data doesn't accidentally get repointed
                        offsets = RealRepoint(sourceRom, rom, offsetsToRepointTogether, endInsertOffset) # Format is [(offset, symbol), ...]

                        output = open(GENERATED_REPOINTS, 'a')
                        for tup in offsets:
                            output.write(tup[1] + ' ' + str(tup[0]) + '\n')
                            generatedRepoints.add((tup[1], tup[0]))
                        output.close()

        # Do Special Inserts - Before bytereplacement!
        if os.path.isfile(SPECIAL_INSERTS) and os.path.isfile(SPECIAL_INSERTS_OUT):
            with open(SPECIAL_INSERTS, 'r') as file:
                offsetList = []
                for line in file:
                    if line.strip().startswith('.org '):
                        offsetList.append(int(line.split('.org ')[1].split(',')[0], 16))

                offsetList.sort()

            with open(SPECIAL_INSERTS_OUT, 'rb') as binFile:
                for offset in offsetList:
                    originalOffset = offset
                    dataList = ""

                    if offsetList.index(offset) == len(offsetList) - 1:
                        while True:
                            try:
                                binFile.seek(offset)
                                dataList += hex(binFile.read(1)[0]) + ' '
                            except IndexError:
                                break

                            offset += 1
                    else:
                        binFile.seek(offset)
                        word = ExtractPointer(binFile.read(4))

                        while word != 0xFFFFFFFF:
                            binFile.seek(offset)
                            dataList += hex(binFile.read(1)[0]) + ' '
                            offset += 1

                            if offset in offsetList:  # Overlapping data
                                break

                            word = ExtractPointer(binFile.read(4))

                    ReplaceBytes(rom, originalOffset, dataList.strip())
                # Insert free byte replacements


        if os.path.isfile(FREE_BYTE_REPLACEMENTS):


            FREE_BYTE_SEARCH_START = 0x900000  # Adjust to your preferred free space startMore actions
            MINIMUM_FREE_LENGTH = 0x100        # Minimum space to be considered free

            def FindFreeSpace(rom: _io.BufferedReader, length: int, start: int = FREE_BYTE_SEARCH_START) -> int:
                rom.seek(start)
                data = rom.read()
                index = 0
                while index + length <= len(data):
                    chunk = data[index:index+length]
                    if all(b in (0x00, 0xFF) for b in chunk):
                        return start + index
                    index += 4
                raise Exception(f"No free space found for {length} bytes.")

            with open('free_bytereplacements', 'r') as file:
                for line in file:
                    if line.strip().startswith('#') or line.strip() == '':
                        continue
                    try:
                        label, *hexbytes = line.strip().split()
                        byte_data = bytes([int(x, 16) for x in hexbytes])
                        insert_len = max(len(byte_data), MINIMUM_FREE_LENGTH)
                        insert_at = FindFreeSpace(rom, insert_len)
                        rom.seek(insert_at)
                        rom.write(byte_data)
                        table[label] = insert_at  # Add to symbol table
                    except Exception as e:
                        print(f"Error processing line: {line.strip()}")
                        print(e)

        # Insert byte changes
        if os.path.isfile(BYTE_REPLACEMENT):
            with open(BYTE_REPLACEMENT, 'r') as replacelist:
                definesDict = {}
                conditionals = []
                for line in replacelist:
                    if TryProcessFileInclusion(line, definesDict):
                        continue
                    if TryProcessConditionalCompilation(line, definesDict, conditionals):
                        continue
                    if line.strip().startswith('#') or line.strip() == '':
                        continue
 
                    offset = int(line[:8], 16) - 0x08000000
                    try:
                        ReplaceBytes(rom, offset, line[9:].strip())
                    except ValueError: #Try loading from the defines dict if unrecognizable character
                        newNumber = definesDict[line[9:].strip()]
                        try:
                            newNumber = int(newNumber)
                        except ValueError:
                            newNumber = int(newNumber, 16)

                        newNumber = str(hex(newNumber)).split('0x')[1]
                        ReplaceBytes(rom, offset, newNumber) 


        # Read hooks from a file
        if os.path.isfile(HOOKS):
            with open(HOOKS, 'r') as hookList:
                definesDict = {}
                conditionals = []
                for line in hookList:
                    if TryProcessFileInclusion(line, definesDict):
                        continue
                    if TryProcessConditionalCompilation(line, definesDict, conditionals):
                        continue
                    if line.strip().startswith('#') or line.strip() == '':
                        continue

                    symbol, address, register = line.split()
                    offset = int(address, 16) - 0x08000000
                    try:
                        code = table[symbol]
                    except KeyError:
                        print('Symbol missing:', symbol)
                        continue

                    Hook(rom, code, offset, int(register))

        # Read repoints from a file
        if os.path.isfile(REPOINTS):
            with open(REPOINTS, 'r') as repointList:
                definesDict = {}
                conditionals = []
                for line in repointList:
                    if TryProcessFileInclusion(line, definesDict):
                        continue
                    if TryProcessConditionalCompilation(line, definesDict, conditionals):
                        continue
                    if line.strip().startswith('#') or line.strip() == '':
                        continue

                    if len(line.split()) == 2:
                        symbol, address = line.split()
                        offset = int(address, 16) - 0x08000000
                        try:
                            code = table[symbol]
                        except KeyError:
                            print('Symbol missing:', symbol)
                            continue

                        Repoint(rom, code, offset)
                        RecordGeneratedRepoint(generatedRepoints, symbol, offset)

                    if len(line.split()) == 3:
                        symbol, address, slide = line.split()
                        offset = int(address, 16) - 0x08000000
                        try:
                            code = table[symbol]
                        except KeyError:
                            print('Symbol missing:', symbol)
                            continue

                        Repoint(rom, code, offset, int(slide))
                        RecordGeneratedRepoint(generatedRepoints, symbol, offset)

        # Read routine repoints from a file
        if os.path.isfile(ROUTINE_POINTERS):
            with open(ROUTINE_POINTERS, 'r') as pointerlist:
                definesDict = {}
                conditionals = []
                for line in pointerlist:
                    if TryProcessFileInclusion(line, definesDict):
                        continue
                    if TryProcessConditionalCompilation(line, definesDict, conditionals):
                        continue
                    if line.strip().startswith('#') or line.strip() == '':
                        continue

                    symbol, address = line.split()
                    offset = int(address, 16) - 0x08000000
                    try:
                        code = table[symbol]
                    except KeyError:
                        print('Symbol missing:', symbol)
                        continue

                    Repoint(rom, code, offset, 1)

        # Read routine rewrite wrapper from a file
        if os.path.isfile(FUNCTION_REWRITES):
            with open(FUNCTION_REWRITES, 'r') as frwlist:
                definesDict = {}
                conditionals = []
                for line in frwlist:
                    if TryProcessFileInclusion(line, definesDict):
                        continue
                    if TryProcessConditionalCompilation(line, definesDict, conditionals):
                        continue
                    if line.strip().startswith('#') or line.strip() == '':
                        continue

                    symbol, address, numParams, isReturning = line.split()
                    offset = int(address, 16) - 0x08000000
                    try:
                        code = table[symbol]
                    except KeyError:
                        print('Symbol missing:', symbol)
                        continue

                    FunctionWrap(rom, code, offset, int(numParams), int(isReturning))

        # Insert Event Scripts
        if os.path.isfile(EVENT_SCRIPTS):
            definesDict = {}

            mapHeaders = {}  # For signpost events
            npcTables = {}  # For people events
            tileTables = {}  # For script tiles
            signTables = {}  # For signpost events

            npcCounts = {}  # For people events
            tileCounts = {}  # For script tiles
            signCounts = {}  # For signpost events

            conditionals = []
            rom.seek(0x5524C)
            mapBanksHeader = ExtractPointer(rom.read(4)) - 0x08000000

            with open(EVENT_SCRIPTS, 'r') as file:
                for i, line in enumerate(file):
                    if TryProcessFileInclusion(line, definesDict):
                        continue
                    if TryProcessConditionalCompilation(line, definesDict, conditionals):
                        continue
                    if line.strip().startswith('#') or line.strip() == '':
                        continue

                    try:
                        eventId = -1  # Reset just in case of error
                        if len(line.split()) == 4 or len(line.split()) == 5:
                            if len(line.split()) == 5:
                                eventType, mapBank, mapNum, eventId, symbol = line.split()
                                eventId = int(eventId)
                            else:  # 4
                                eventType, mapBank, mapNum, symbol = line.split()

                            eventType = eventType.lower()
                            mapBank = int(mapBank)
                            mapNum = int(mapNum)
                            dictId = (mapBank << 8) | mapNum

                            if dictId not in mapHeaders:
                                rom.seek(mapBanksHeader + mapBank * 4)
                                mapBankHeader = ExtractPointer(rom.read(4)) - 0x08000000
                                if mapBankHeader == (0xF7F7F7F7 - 0x08000000):
                                    continue  # Garbage map bank header
                                rom.seek(mapBankHeader + mapNum * 4)
                                mapHeader = ExtractPointer(rom.read(4)) - 0x08000000
                                if mapHeader == (0xF7F7F7F7 - 0x08000000):
                                    continue  # Garbage map header
                                mapHeaders[dictId] = mapHeader  # Store for later
                            else:
                                mapHeader = mapHeaders[dictId]

                            if eventType == "map":
                                offset = mapHeader + 0x8
                            elif eventType == "npc" or eventType == "trainer" or eventType == "item":
                                if eventId < 0:
                                    raise(OSError)
                                if dictId not in npcTables:
                                    rom.seek(mapHeader + 0x4)
                                    eventHeader = ExtractPointer(rom.read(4)) - 0x08000000
                                    rom.seek(eventHeader)
                                    npcCount = int(rom.read(1)[0])
                                    rom.seek(eventHeader + 0x4)
                                    npcTable = ExtractPointer(rom.read(4)) - 0x08000000
                                    npcTables[dictId] = npcTable  # Store for later
                                    npcCounts[dictId] = npcCount  # Store for later
                                else:
                                    npcTable = npcTables[dictId]
                                    npcCount = npcCounts[dictId]

                                # Check if valid npc
                                if eventId >= npcCount:
                                    print("Errror! NPC id {} exceeds the count of {} on line {}: {}".format(eventId, npcCount, i, line.strip()))
                                    continue

                                # Check shortcut npcs and modify symbol
                                if eventType == "trainer":
                                    symbol = "EventScript_" + symbol
                                elif eventType == "item":
                                    symbol = "ItemFindScript_" + symbol

                                length = 0x18  # Length of one entry
                                offset = npcTable + eventId * 0x18 + 0x10

                            elif eventType == "tile":
                                if eventId < 0:
                                    raise(OSError)
                                if dictId not in tileTables:
                                    rom.seek(mapHeader + 0x4)
                                    eventHeader = ExtractPointer(rom.read(4)) - 0x08000000
                                    rom.seek(eventHeader + 0xC)
                                    tileTable = ExtractPointer(rom.read(4)) - 0x08000000
                                    tileTables[dictId] = tileTable  # Store for later
                                else:
                                    tileTable = tileTables[dictId]
                                length = 0x10  # Length of one entry
                                offset = tileTable + eventId * length + 0xC

                            elif eventType == "sign":
                                if eventId < 0:
                                    raise(OSError)
                                if dictId not in signTables:
                                    rom.seek(mapHeader + 0x4)
                                    eventHeader = ExtractPointer(rom.read(4)) - 0x08000000
                                    rom.seek(eventHeader + 0x10)
                                    signTable = ExtractPointer(rom.read(4)) - 0x08000000
                                    signTables[dictId] = signTable  # Store for later
                                else:
                                    signTable = signTables[dictId]
                                length = 0xC  # Length of one entry
                                offset = signTable + eventId * length + 0x8

                            else:
                                print("Unknown event type \"{}\"!".format(eventType))
                                continue

                            if symbol in definesDict:
                                symbol = definesDict[symbol]

                            try:
                                code = table[symbol]
                            except KeyError:
                                try:
                                    code = int(symbol, 16)  # If script offset was written in hex
                                except ValueError:
                                    print('Symbol missing:', symbol)
                                    continue

                            Repoint(rom, code, offset)
                    except OSError:
                        print("There was an error inserting the event script on line {}: {}".format(i, line.strip()))

        endInsertOffset = InsertMapObjectOverlays(rom, table, endInsertOffset)

        # Insert Song Pointers
        if os.path.isfile(SONGS):
            rom.seek(0x1DD11C)  # m4aSongNumStart
            songTable = ExtractPointer(rom.read(4)) - 0x08000000

            with open(SONGS, "r") as file:
                for i, line in enumerate(file):
                    if TryProcessFileInclusion(line, definesDict):
                        continue
                    if TryProcessConditionalCompilation(line, definesDict, conditionals):
                        continue
                    if line.strip().startswith('#') or line.strip() == '':
                        continue

                    try:
                        lineList = line.split()
                        try:
                            songId = int(lineList[0])
                        except ValueError:
                            songId = int(lineList[0], 16)  # Hex
                        song = lineList[1]
                        offset = songTable + songId * 8

                        try:
                                code = table[song]
                        except KeyError:
                            try:
                                code = int(song, 16)  # If script offset was written in hex
                            except ValueError:
                                print('Symbol missing:', song)
                                continue

                        Repoint(rom, code, offset)
                    except:
                        print("There was an error inserting the song on line {}: {}".format(i, line.strip()))

        width = max(map(len, table.keys())) + 1
        if os.path.isfile('offsets.ini'):
            offsetIni = open('offsets.ini', 'r+')
        else:
            offsetIni = open('offsets.ini', 'w')

        offsetIni.truncate()
        for key in sorted(table.keys()):
            fstr = ('{:' + str(width) + '} {:08X}')
            offsetIni.write(fstr.format(key + ':', table[key] + 0x08000000) + '\n')
        offsetIni.close()

        print('Inserted in ' + str(datetime.now() - startTime) + '.')


if __name__ == '__main__':
    if sys.argv[1:] == ['--check-map-object-overlays']:
        RunMapObjectOverlaySelfTest()
        RunViridianForestNurseOverlaySelfTest()
        RunInstantPokeCenterHealingOverlaySelfTest()
    else:
        main()
