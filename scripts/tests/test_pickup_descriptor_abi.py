#!/usr/bin/env python3
"""#719 public source + synthetic ABI tests only; NO private artifact mode.

All byte buffers are constructed here in memory. The tiny bridge emulator is
an oracle for the declared v1 instruction layout, not a compiler/disassembler
or a ROM locator. Receipt fixtures model rejection premises, not real proof.
"""

import ast
from bisect import bisect_right
from copy import deepcopy
from pathlib import Path
import re
import struct
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[2]
BASE = "e68a701aa4e68733ef8ad1e7cadb68825c0d16c2"
COMMON = """POTION ANTIDOTE SUPER_POTION GREAT_BALL REPEL ESCAPE_ROPE
FULL_HEAL HYPER_POTION ULTRA_BALL REVIVE RARE_CANDY SUN_STONE MOON_STONE
HEART_SCALE FULL_RESTORE MAX_REVIVE PP_UP MAX_ELIXIR""".split()
RARE = """HYPER_POTION NUGGET KINGS_ROCK FULL_RESTORE ETHER IRON_BALL
DESTINY_KNOT ELIXIR DESTINY_KNOT LEFTOVERS DESTINY_KNOT""".split()
CEILINGS = [19661, 26214, 32768, 39322, 45875, 52429, 58982, 61604, 64225,
            64881, 65536]
WEIGHTS = [19661, 6553, 6554, 6554, 6553, 6554, 6553, 2622, 2621, 656, 655]
WIRE = struct.Struct("<IHHII4I4H12B3I")
WORDS = (0xB510, 0x4804, 0x4B04, 0xF000, 0xF803, 0xBC10, 0xBC01,
         0x4700, 0x4718, 0x46C0)
ROM_BASE = 0x09000000  # synthetic address space, never a real artifact locator
REPOINTS = (0, 4, 8, 12, 16)
COMMAND, BRIDGE, DESCRIPTOR, CONSUMER = 64, 1280, 1408, 1536
TABLES = (1664, 1728, 1792, 1856)
SIZES = (36, 22, 36, 8)
CONSUMER_MODEL = b"PUBLIC_SOURCE_MODEL_ONLY".ljust(32, b"\0")
CHOOSER = """
u32 row_num = (level - 1) / 10;
const item_t* const common_row = pickup->commonItems + row_num;
const item_t* const rare_row = pickup->rareItems + row_num;
const u32* const common_ceilings = pickup->commonCeilings;
const u32* const rare_ceilings = pickup->rareCeilings;
u16 k = Random();
for (u32 i = 0; i < PU_COMMON_PER_ROW; ++i)
    if (k < common_ceilings[i]) return common_row[i];
for (u32 i = 0; i < PU_RARE_PER_ROW; ++i)
    if (k < rare_ceilings[i]) return rare_row[i];
return ITEM_NONE;
"""


def source(path):
    return (ROOT / path).read_text()


def original(path):
    return subprocess.check_output(["git", "show", f"{BASE}:{path}"],
                                   cwd=ROOT, text=True)


def normalized(text):
    return re.sub(r"\s+", "", re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S))


def function_body(text, signature):
    start = text.index(signature + "\n{") + len(signature) + 2
    depth = 1
    end = start
    while depth:
        if text[end] == "{":
            depth += 1
        elif text[end] == "}":
            depth -= 1
        end += 1
    return text[start:end - 1]


def require(condition):
    if not condition:
        raise ValueError("synthetic contract rejected")


def source_coupling(text):
    sig = "static item_t ChoosePickupItem(u8 level, const volatile struct PickupDescriptor* pickup)"
    require(normalized(function_body(text, sig)) == normalized(CHOOSER))
    body = function_body(text, "void PickupItemCalculation(const volatile struct PickupDescriptor* pickup)")
    require(body.count("ChoosePickupItem(level, pickup)") == 1)
    require("gPickupDescriptor" not in body)
    require(text.count("void PickupItemCalculation(") == 1)
    require("void atkE5_pickupitemcalculation(" not in text)


def baseline_items():
    tables = source("src/Tables/item_tables.c")
    defines = dict(re.findall(r"^#define (ITEM_\w+) (0[xX][0-9a-fA-F]+|\d+)\b",
                              source("include/constants/items.h"), re.M))
    values = []
    for name, expected in (("sPickupCommonItems", COMMON), ("sPickupRareItems", RARE)):
        text = tables.split("const item_t " + name, 1)[1].split("};", 1)[0]
        tokens = re.findall(r"\bITEM_\w+", text.split("#else", 1)[0])
        require(tokens == ["ITEM_" + x for x in expected])
        values.append([int(defines[x], 0) for x in tokens])
    return values


def fixture():
    image = bytearray(4096)
    for site in REPOINTS:
        struct.pack_into("<I", image, site, ROM_BASE + COMMAND)
    struct.pack_into("<I", image, COMMAND + 0xE5 * 4, ROM_BASE + BRIDGE + 1)
    struct.pack_into("<10H2I", image, BRIDGE, *WORDS,
                     ROM_BASE + DESCRIPTOR, ROM_BASE + CONSUMER + 1)
    fields = [0x31555043, 1, 64, 6, 1, *[ROM_BASE + x for x in TABLES],
              18, 11, 9, 2, 4, 2, 4, 10, 10, 9, 2, 1, 100, 0, 0, 0,
              779, ROM_BASE + CONSUMER + 1, ROM_BASE + BRIDGE + 1]
    WIRE.pack_into(image, DESCRIPTOR, *fields)
    common, rare = baseline_items()
    for pos, fmt, values in zip(TABLES, ("18H", "11H", "9I", "2I"),
                                (common, rare, CEILINGS[:9], CEILINGS[9:])):
        struct.pack_into("<" + fmt, image, pos, *values)
    image[CONSUMER:CONSUMER + 32] = CONSUMER_MODEL
    # This inventory is a MOCK of a unique fresh-link definition receipt.
    definitions = {"anchor": [BRIDGE], "descriptor": [DESCRIPTOR],
                   "consumer": [CONSUMER], "tables": list(TABLES)}
    return image, definitions


def bridge_argument(image, at):
    """Execute only the fixed v1 Thumb bridge's literal/call/return semantics."""
    require(at % 4 == 0 and bytes(image[at:at + 20]) == struct.pack("<10H", *WORDS))
    registers = [0] * 16
    registers[4], registers[13], registers[14] = 123, 800, 0x1021
    stack, calls, pc = {}, [], at
    for _ in range(12):
        opcode = struct.unpack_from("<H", image, pc)[0]
        if opcode == 0xB510:  # push {r4,lr}
            registers[13] -= 8
            stack[registers[13]] = registers[4]
            stack[registers[13] + 4] = registers[14]
            pc += 2
        elif opcode in (0x4804, 0x4B04):  # PC-relative ldr r0/r3
            literal = ((pc + 4) & ~3) + (opcode & 255) * 4
            registers[(opcode >> 8) & 7] = struct.unpack_from("<I", image, literal)[0]
            pc += 2
        elif opcode == 0xF000:  # exact local Thumb-1 BL (no veneer/unknown CFG)
            low = struct.unpack_from("<H", image, pc + 2)[0]
            require(low == 0xF803)
            registers[14] = ROM_BASE + pc + 4 + 1
            pc += 4 + (low & 2047) * 2
        elif opcode == 0x4718:  # bx r3: mock externally compiled C consumer
            require(registers[3] & 1 and registers[13] % 8 == 0)
            calls.append((registers[0], registers[3]))
            # Mock C returns through its saved LR and may clobber scratch regs.
            registers[0], registers[3] = 999, 777
            pc = (registers[14] & ~1) - ROM_BASE
        elif opcode in (0xBC10, 0xBC01):  # pop r4 / pop saved LR into r0
            registers[4 if opcode == 0xBC10 else 0] = stack[registers[13]]
            registers[13] += 4
            pc += 2
        elif opcode == 0x4700:  # bx r0 to original caller, restoring state
            require(registers[0] == 0x1021 and registers[4] == 123 and registers[13] == 800)
            require(len(calls) == 1)
            return calls[0]
        else:
            raise ValueError("unsupported synthetic bridge instruction")
    raise ValueError("synthetic bridge did not return")


def validate_fixture(image, definitions):
    """Structural mock ONLY; cannot accept files, receipts or real artifacts."""
    def region(pointer, size, align):
        pos = pointer - ROM_BASE
        require(pointer % align == 0 and 0 <= pos <= len(image) - size)
        return pos, pos + size

    def word(pos):
        return struct.unpack_from("<I", image, pos)[0]

    roots = [word(site) for site in REPOINTS]
    require(len(set(roots)) == 1)
    command, command_end = region(roots[0], 1024, 4)
    e5 = word(command + 0xE5 * 4)
    require(e5 & 1)
    bridge, bridge_end = region(e5 & ~1, 28, 4)
    descriptor_pointer, consumer_pointer = bridge_argument(image, bridge)
    require(consumer_pointer & 1)
    descriptor, descriptor_end = region(descriptor_pointer, 64, 4)
    consumer, consumer_end = region(consumer_pointer & ~1, 32, 2)
    require(definitions == {"anchor": [bridge], "descriptor": [descriptor],
                            "consumer": [consumer], "tables": list(TABLES)})
    # A mock fresh-compile identity. Real acceptance requires actual compiler
    # data-use proof and entire selected-output binding, NOT this sentinel.
    require(image[consumer:consumer_end] == CONSUMER_MODEL)
    f = WIRE.unpack_from(image, descriptor)
    require(f[:5] == (0x31555043, 1, 64, 6, 1))
    require(f[9:13] == (18, 11, 9, 2))
    require(f[13:25] == (4, 2, 4, 10, 10, 9, 2, 1, 100, 0, 0, 0))
    require(f[25:] == (779, consumer_pointer, e5))
    ranges = [region(p, size, align) for p, size, align in zip(f[5:9], SIZES, (2, 2, 4, 4))]
    require([a for a, b in ranges] == definitions["tables"])
    ranges += [(command, command_end), (bridge, bridge_end),
               (descriptor, descriptor_end), (consumer, consumer_end)]
    ranges += [(site, site + 4) for site in REPOINTS]
    for i, (lo, hi) in enumerate(ranges):
        for other_lo, other_hi in ranges[i + 1:]:
            require(hi <= other_lo or other_hi <= lo)
    common = list(struct.unpack_from("<18H", image, f[5] - ROM_BASE))
    rare = list(struct.unpack_from("<11H", image, f[6] - ROM_BASE))
    # Baseline allowed raw IDs are explicit, never "anything fitting u16".
    require([common, rare] == baseline_items())
    ceilings = list(struct.unpack_from("<9I", image, f[7] - ROM_BASE))
    ceilings += list(struct.unpack_from("<2I", image, f[8] - ROM_BASE))
    require(ceilings == CEILINGS)
    return common, rare, ceilings


def choose_model(tables, level, draw):
    common, rare, ceilings = tables
    row = (level - 1) // 10
    for i in range(9):
        if draw < ceilings[i]:
            return common[row + i]
    for i in range(2):
        if draw < ceilings[9 + i]:
            return rare[row + i]
    return 0


def receipt_model():
    # Text-only identities invented for this test. No user receipt is loaded.
    identity = dict(source="reviewed-source", headers="all-headers", config="selected",
                    flags="no-lto", toolchain="approved-tools", link="all-link-inputs")
    return dict(expected=identity, actual=identity.copy(), preexisting=0,
                cache_disabled=True, run="fresh-run", compiled={
                    name: "fresh-run" for name in ("e5", "bridge", "consumer", "tables")},
                required=("e5", "bridge", "consumer", "tables"), link_run="fresh-run")


def validate_receipt_model(receipt):
    require(receipt["preexisting"] == 0 and receipt["cache_disabled"])
    require(receipt["expected"] == receipt["actual"])
    require(set(receipt["compiled"]) == set(receipt["required"]))
    require(set(receipt["compiled"].values()) == {receipt["run"]})
    require(receipt["link_run"] == receipt["run"])


class PickupDescriptorTests(unittest.TestCase):
    def test_source_consumes_only_supplied_descriptor(self):
        text = source("src/general_bs_commands.c")
        source_coupling(text)
        for before, after in (("pickup->commonItems", "sPickupCommonItems"),
                              ("pickup->rareItems", "sPickupRareItems"),
                              ("pickup->commonCeilings", "pickup_common_item_ceilings"),
                              ("pickup->rareCeilings", "pickup_rare_item_ceilings"),
                              ("ChoosePickupItem(level, pickup)", "ChoosePickupItem(level, &gPickupDescriptor)")):
            with self.subTest(bypass=after), self.assertRaises(ValueError):
                source_coupling(text.replace(before, after))

    def test_gameplay_and_table_source_unchanged(self):
        text = source("src/general_bs_commands.c")
        restored = text.replace("void PickupItemCalculation(const volatile struct PickupDescriptor* pickup)",
                                "void atkE5_pickupitemcalculation(void)")
        restored = restored.replace("ChoosePickupItem(level, pickup)", "ChoosePickupItem(level)")
        restored = restored.replace("static item_t ChoosePickupItem(u8 level, const volatile struct PickupDescriptor* pickup)",
                                    "static item_t ChoosePickupItem(u8 level)")
        sig = "static item_t ChoosePickupItem(u8 level)"
        old = original("src/general_bs_commands.c")
        restored = restored.replace(function_body(restored, sig), function_body(old, sig))
        self.assertEqual(restored, old)  # activation/Honey/bag/knocked-off included
        tables = source("src/Tables/item_tables.c")
        descriptor = re.search(r"\nconst struct PickupDescriptor gPickupDescriptor =\n\{.*?\n\};\n", tables, re.S)
        self.assertEqual(tables.replace(descriptor.group(), ""), original("src/Tables/item_tables.c"))
        baseline_items()
        for name, expected in (("pickup_common_item_ceilings", CEILINGS[:9]),
                               ("pickup_rare_item_ceilings", CEILINGS[9:])):
            body = tables.split("const u32 " + name, 1)[1].split("{", 1)[1].split("}", 1)[0]
            self.assertEqual([int(x) for x in re.findall(r"\d+", body)], expected)

    def test_wire_layout_and_declarations(self):
        header = source("include/new/pickup_items.h")
        self.assertEqual(WIRE.size, 64)
        fields = re.search(r"struct PickupDescriptor\n\{(.*?)\n\};", header, re.S).group(1)
        fields = re.sub(r"/\*.*?\*/", "", fields, flags=re.S)
        field_names = re.findall(r"\b(\w+)(?:\[3\])?;|\(\*(\w+)\)", fields)
        names = [a or b for a, b in field_names]
        offsets = [0, 4, 6, 8, 12, 16, 20, 24, 28, 32, 34, 36, 38,
                   40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 52, 56, 60]
        self.assertEqual(len(names), len(offsets))
        for name, offset in zip(names, offsets):
            self.assertIn(f"PU_ABI_OFFSET({name}, {offset});", header)
        for contract in ("sizeof(item_t) == 2", "sizeof(u32) == 4", "sizeof(void*) == 4",
                         "sizeof(gPickupDescriptor.consumer) == 4",
                         "sizeof(struct PickupDescriptor) == PU_DESCRIPTOR_SIZE",
                         "__alignof__(struct PickupDescriptor) == 4"):
            self.assertIn(contract, header)
        for macro, value in (("MAGIC", "0x31555043u"), ("VERSION", "1"),
                             ("SIZE", "64"), ("ITEM_SCHEMA", "1")):
            self.assertRegex(header, rf"#define PU_DESCRIPTOR_{macro} {value}\b")
        init = source("src/Tables/item_tables.c").split("const struct PickupDescriptor gPickupDescriptor =", 1)[1].split("};", 1)[0]
        for field, value in (("magic", "PU_DESCRIPTOR_MAGIC"), ("version", "PU_DESCRIPTOR_VERSION"),
                            ("size", "PU_DESCRIPTOR_SIZE"), ("itemSchema", "PU_DESCRIPTOR_ITEM_SCHEMA"),
                            ("commonCount", "PU_NUM_COMMON_ITEMS"), ("rareCount", "PU_NUM_RARE_ITEMS"),
                            ("commonCeilingCount", "PU_COMMON_PER_ROW"), ("rareCeilingCount", "PU_RARE_PER_ROW"),
                            ("pointerWidth", "4"), ("itemWidth", "sizeof(item_t)"), ("ceilingWidth", "sizeof(u32)"),
                            ("levelRanges", "10"), ("levelStep", "10"), ("commonWindow", "PU_COMMON_PER_ROW"),
                            ("rareWindow", "PU_RARE_PER_ROW"), ("minLevel", "1"), ("maxLevel", "100"),
                            ("reserved", "{0, 0, 0}"), ("itemCount", "ITEMS_COUNT")):
            self.assertIn(f".{field} = {value},", init)
        self.assertIn(".config = 0", init)
        for field, symbol in (("commonItems", "sPickupCommonItems"), ("rareItems", "sPickupRareItems"),
                              ("commonCeilings", "pickup_common_item_ceilings"),
                              ("rareCeilings", "pickup_rare_item_ceilings"),
                              ("consumer", "PickupItemCalculation"), ("anchor", "atkE5_pickupitemcalculation")):
            self.assertIn(f".{field} = {symbol},", init)
        for macro, bit in (("UNBOUND", "UNBOUND"), ("PICKUP_ITEMS_STRAIGHT_TO_BAG", "STRAIGHT_TO_BAG"),
                           ("PICK_UP_KNOCKED_OFF_ITEMS", "KNOCKED_OFF")):
            self.assertRegex(init, rf"#ifdef {macro}\s+\| PU_CONFIG_{bit}\s+#endif")
        self.assertIn("typedef u16 item_t;", source("include/gba/types.h"))
        for macro, value in (("UNBOUND", 1), ("STRAIGHT_TO_BAG", 2), ("KNOCKED_OFF", 4)):
            self.assertIn(f"#define PU_CONFIG_{macro} {value}u", header)
        item_defines = source("include/constants/items.h")
        self.assertIn("#define ITEM_FREE_SPACE3 0x30A", item_defines)
        self.assertIn("#define ITEMS_COUNT (ITEM_FREE_SPACE3 + 1)", item_defines)
        config = source("src/config.h")
        self.assertNotRegex(config, r"(?m)^\s*#define UNBOUND\b")
        for macro in ("PICKUP_ITEMS_STRAIGHT_TO_BAG", "PICK_UP_KNOCKED_OFF_ITEMS"):
            self.assertRegex(config, rf"(?m)^#define {macro}\b")

    def test_fixed_bridge_source_and_dispatch(self):
        asm = source("assembly/data/pickup_descriptor_bridge.s")
        instructions = []
        for line in asm.splitlines():
            line = line.split("@", 1)[0].strip()
            if line and not line.startswith(".") and not line.endswith(":"):
                instructions.append(line)
        self.assertEqual(instructions, ["push {r4, lr}", "ldr r0, .Lpickup_descriptor",
            "ldr r3, .Lpickup_consumer", "bl .Lpickup_call", "pop {r4}", "pop {r0}", "bx r0", "bx r3", "nop"])
        self.assertIn(".word gPickupDescriptor", asm)
        self.assertIn(".word PickupItemCalculation", asm)
        self.assertIn(".thumb_func\natkE5_pickupitemcalculation:", asm)
        self.assertIn(".cpu arm7tdmi\n.syntax unified\n.thumb", asm)
        for label, offset in (("call", 16), ("descriptor", 20), ("consumer", 24), ("end", 28)):
            self.assertIn(f".if (.Lpickup_{label} - atkE5_pickupitemcalculation) != {offset}", asm)
        table = source("assembly/data/battle_script_commands_table.s")
        self.assertEqual(table, original("assembly/data/battle_script_commands_table.s"))
        entries = re.findall(r"^\.word (\S+)", table.split("gBattleScriptingCommandsTable2:", 1)[0], re.M)
        self.assertEqual(len(entries), 256)
        self.assertEqual(entries[0xE5], "atkE5_pickupitemcalculation")
        self.assertEqual(source("repoints"), original("repoints"))
        self.assertEqual(source("linker.ld"), original("linker.ld"))
        self.assertEqual(source("scripts/insert.py"), original("scripts/insert.py"))

    def test_positive_anchor_parameter_and_return(self):
        image, definitions = fixture()
        tables = validate_fixture(image, definitions)
        self.assertEqual(bridge_argument(image, BRIDGE),
                         (ROM_BASE + DESCRIPTOR, ROM_BASE + CONSUMER + 1))
        # bridge_argument executes BL/BX and checks saved LR, r4 and SP even
        # when the mock C callee clobbers r0/r3 before returning.
        self.assertEqual(tables[:2], tuple(baseline_items()))

    def test_all_ten_windows_and_exact_probabilities(self):
        image, definitions = fixture()
        tables = validate_fixture(image, definitions)
        for row in range(10):
            bins = [0] * 11
            for draw in range(65536):
                slot = bisect_right(CEILINGS, draw)  # independent interval oracle
                bins[slot] += 1
                expected = tables[0][row + slot] if slot < 9 else tables[1][row + slot - 9]
                self.assertEqual(choose_model(tables, row * 10 + 1, draw), expected)
            self.assertEqual(bins, WEIGHTS)
        for level in range(1, 101):
            row = (level - 1) // 10
            for slot, draw in enumerate([0] + CEILINGS[:-1]):
                expected = tables[0][row + slot] if slot < 9 else tables[1][row + slot - 9]
                self.assertEqual(choose_model(tables, level, draw), expected)
        self.assertEqual(tables[1][6], tables[1][8])
        self.assertEqual(tables[1][8], tables[1][10])

    def test_descriptor_parameter_controls_all_four_reads(self):
        source_coupling(source("src/general_bs_commands.c"))
        # An alternate supplied object MUST change selection. Tests the source
        # contract's indirection under both inline and separate model calls.
        alternative = ([100 + i for i in range(18)], [200 + i for i in range(11)],
                       list(range(1, 10)) + [10, 65536])
        for call in (choose_model, lambda d, l, k: choose_model(d, l, k)):
            self.assertEqual(call(alternative, 1, 0), 100)
            self.assertEqual(call(alternative, 1, 8), 108)
            self.assertEqual(call(alternative, 1, 9), 200)
            self.assertEqual(call(alternative, 91, 10), 210)

    def test_bad_schema_and_config_fields(self):
        for index in list(range(5)) + list(range(9, 28)):
            image, definitions = fixture()
            fields = list(WIRE.unpack_from(image, DESCRIPTOR))
            fields[index] ^= 1
            WIRE.pack_into(image, DESCRIPTOR, *fields)
            with self.subTest(field=index), self.assertRaises(ValueError):
                validate_fixture(image, definitions)

    def test_missing_forged_and_dormant_roots(self):
        for site in REPOINTS + (COMMAND + 0xE5 * 4,):
            image, definitions = fixture()
            struct.pack_into("<I", image, site, 0)
            with self.subTest(site=site), self.assertRaises(ValueError):
                validate_fixture(image, definitions)
        for at in (BRIDGE, BRIDGE + 20, BRIDGE + 24, CONSUMER):
            image, definitions = fixture()
            image[at] ^= 1
            with self.subTest(corrupt=at), self.assertRaises(ValueError):
                validate_fixture(image, definitions)
        image, definitions = fixture()
        # A copied valid descriptor, even with matching contents, is not the
        # uniquely fresh-link-defined object passed from the active bridge.
        image[2048:2112] = image[DESCRIPTOR:DESCRIPTOR + 64]
        struct.pack_into("<I", image, BRIDGE + 20, ROM_BASE + 2048)
        with self.assertRaises(ValueError):
            validate_fixture(image, definitions)
        for symbol in ("anchor", "descriptor", "consumer"):
            image, definitions = fixture()
            definitions[symbol].append(definitions[symbol][0])
            with self.subTest(duplicate=symbol), self.assertRaises(ValueError):
                validate_fixture(image, definitions)
        image, definitions = fixture()
        image[:] = b"\0" * len(image)  # vanilla / old build: no v1 root
        with self.assertRaises(ValueError):
            validate_fixture(image, definitions)

    def test_pointer_bounds_aliases_and_overlaps(self):
        for slot in range(4):
            for pointer in (0, ROM_BASE - 4, ROM_BASE + len(fixture()[0]),
                            ROM_BASE + TABLES[slot] + 1, ROM_BASE + TABLES[0],
                            ROM_BASE + DESCRIPTOR, ROM_BASE + BRIDGE,
                            ROM_BASE + CONSUMER, ROM_BASE + COMMAND, ROM_BASE):
                if slot == 0 and pointer == ROM_BASE + TABLES[0]:
                    continue
                image, definitions = fixture()
                struct.pack_into("<I", image, DESCRIPTOR + 16 + 4 * slot, pointer)
                with self.subTest(slot=slot, pointer_case=pointer), self.assertRaises(ValueError):
                    validate_fixture(image, definitions)
        # Legitimate-inventory equality must not mask partial overlap.
        image, definitions = fixture()
        fields = list(WIRE.unpack_from(image, DESCRIPTOR))
        fields[6] = fields[5] + 2
        definitions["tables"][1] = TABLES[0] + 2
        WIRE.pack_into(image, DESCRIPTOR, *fields)
        with self.assertRaises(ValueError):
            validate_fixture(image, definitions)

    def test_invalid_raw_items_and_ceilings(self):
        for pos, fmt, value in ((TABLES[0], "H", 0), (TABLES[1], "H", 65535),
                                (TABLES[0], "H", 778), (TABLES[2], "I", 0),
                                (TABLES[3] + 4, "I", 65535)):
            image, definitions = fixture()
            struct.pack_into("<" + fmt, image, pos, value)
            with self.subTest(raw_case=(pos, value)), self.assertRaises(ValueError):
                validate_fixture(image, definitions)

    def test_cache_bug_and_fresh_receipt_rejection_model(self):
        build = source("scripts/build.py")
        self.assertEqual(build, original("scripts/build.py"))
        tree = ast.parse(build)
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "CreateOutputFile")
        class FakePath:
            isfile = staticmethod(lambda p: p != "absent")
            getmtime = staticmethod(lambda p: 3 if p == "newer-source" else 2 if p == "cached-object" else 1)
        class FakeOs:
            path = FakePath
        scope = {"os": FakeOs}
        exec(compile(ast.Module(body=[fn], type_ignores=[]), "public-cache-model", "exec"), scope)
        for ignored_change in ("source-unchanged", "header-changed", "flags-changed", "compiler-changed"):
            self.assertFalse(scope["CreateOutputFile"](ignored_change, "cached-object")[1])
        self.assertTrue(scope["CreateOutputFile"]("source-unchanged", "absent")[1])
        self.assertTrue(scope["CreateOutputFile"]("newer-source", "cached-object")[1])
        good = receipt_model()
        validate_receipt_model(good)
        for field in good["actual"]:
            bad = deepcopy(good)
            bad["actual"][field] = "changed"
            with self.subTest(identity=field), self.assertRaises(ValueError):
                validate_receipt_model(bad)
        for field, value in (("preexisting", 1), ("cache_disabled", False),
                             ("link_run", "old-run"), ("compiled", {}),
                             ("compiled", dict(good["compiled"], consumer="old-run"))):
            bad = deepcopy(good)
            bad[field] = value
            with self.subTest(receipt=field), self.assertRaises(ValueError):
                validate_receipt_model(bad)

    def test_output_binding_requires_entire_selected_output(self):
        image, definitions = fixture()
        expected = bytes(image)  # mock independently reconstructed output
        selected = bytearray(image)
        validate_fixture(selected, definitions)
        self.assertEqual(bytes(selected), expected)
        for position in (0, BRIDGE, DESCRIPTOR, TABLES[0], 3500):
            bad = bytearray(selected)
            bad[position] ^= 1
            self.assertNotEqual(bytes(bad), expected)  # includes unrelated patches
        # A stale output with plausible valid ABI is still a different output.
        stale = bytearray(selected)
        stale[3500] = 1
        validate_fixture(stale, definitions)
        self.assertNotEqual(bytes(stale), expected)


if __name__ == "__main__":
    unittest.main(verbosity=2)
