#!/usr/bin/env python3
"""#727 Stage A: public text sources and synthetic memory ONLY (stdlib).

No compiler, linker, inserter, binary, ROM, map or runtime inputs. Thumb words
below model the declared fixed bridge; they do not establish assembled output.
DPE/UPR evidence is read exclusively from pinned public Git text objects;
asset existence uses Git tree NAMES, never PNG contents or generated files.
"""
import argparse
import ast
from functools import lru_cache
import io
import hashlib
import ctypes
from pathlib import Path
import re
import struct
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]
BASE = "e27e2113e4d59dc76cf5da8d4c43b067addae348"
DPE_SHA = "d887185de1f6ae6a78e85c4311bbadde17041d00"
UPR_SHA = "e1127cfde58af359e458f8d6a19339f3db3c8589"
DPE = UPR = None
ASM = "assembly/data/oak_intro_contract.s"
HEADER = "include/new/oak_intro.h"
ALLOWLIST = {"src/scripting.c", HEADER, ASM,
             "scripts/tests/test_oak_intro_abi.py", "docs/testing/oak-intro-abi-v1.md"}
PAIRS = (("CreateOakIntroPokemonSprite", "OakIntroSpriteConsumer", "sprite"),
         ("Task_OakSpeech_IsInhabitedFarAndWide", "OakIntroCryConsumer", "cry"))
# Deliberately synthetic labels. No selected output identity/ownership implied.
SYMBOLS = {"gOakIntroContract": 0x09001000, "gOakIntroEligibility": 0x09001100,
           "CreateOakIntroPokemonSprite": 0x09001201,
           "OakIntroSpriteConsumer": 0x09001401,
           "Task_OakSpeech_IsInhabitedFarAndWide": 0x09001301,
           "OakIntroCryConsumer": 0x09001601}
U8, U16, U32 = ctypes.c_uint8, ctypes.c_uint16, ctypes.c_uint32


def read(path):
    return (ROOT / path).read_text()


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True)


def pinned(root, sha, path):
    # Call sites enumerate only known public text files, no arbitrary input.
    return git(root, "show", sha + ":" + path)


def require(value):
    if not value:
        raise ValueError("source/synthetic contract rejected")


def body(text, name):
    match = re.search(r"\b" + name + r"\([^;{}]*\)\s*\{", text)
    require(match is not None)
    start, depth = match.end(), 1
    end = start
    while depth:
        depth += (text[end] == "{") - (text[end] == "}")
        end += 1
    return text[start:end - 1]


def clean(text):
    return re.sub(r"\s+", "", re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S))


def data_section(text, start, end, symbols=SYMBOLS):
    """Parse a bounded subset of *source directives*, not binary output."""
    result = bytearray()
    for line in text.split(start + ":", 1)[1].split(end + ":", 1)[0].splitlines():
        line = line.split("@", 1)[0].strip()
        if not line or line.endswith(":"):
            continue
        directive, value = line.split(None, 1)
        if directive == ".ascii":
            require(value == '"CFROAK01"')
            result.extend(b"CFROAK01")
        elif directive == ".space":
            count, fill = map(int, value.split(","))
            result.extend(bytes([fill]) * count)
        else:
            require(directive in (".word", ".hword", ".byte"))
            fmt = {".word": "I", ".hword": "H", ".byte": "B"}[directive]
            for token in value.split(","):
                token = token.strip()
                number = symbols[token] if token in symbols else int(token, 0)
                result.extend(struct.pack("<" + fmt, number))
    return result


def bitmap():
    return data_section(read(ASM), "gOakIntroEligibility", ".Loak_eligibility_end")


def source_bridge(text, entry, consumer, label):
    lines = [x.split("@", 1)[0].strip() for x in
             text.split(entry + ":", 1)[1].split(".Loak_" + label + "_end:", 1)[0].splitlines()]
    lines = [x for x in lines if x and not x.endswith(":")]
    require(lines == ["push {r4, lr}", f"ldr r1, .Loak_{label}_descriptor",
                      f"ldr r3, .Loak_{label}_consumer", f"bl .Loak_{label}_call",
                      "pop {r4}", "pop {r0}", "bx r0", "bx r3", "nop",
                      ".word gOakIntroContract", ".word " + consumer])
    require(re.search(r"\.align 2\s+\.global " + entry + r"\s+\.type " + entry
                      + r", %function\s+\.thumb_func\s+" + entry + ":", text))
    # Fixed Thumb-1 layout specified by the source above; never assembled bytes.
    return struct.pack("<10H2I", 0xB510, 0x4904, 0x4B04, 0xF000, 0xF803,
                       0xBC10, 0xBC01, 0x4700, 0x4718, 0x46C0,
                       SYMBOLS["gOakIntroContract"], SYMBOLS[consumer])


def bridge_call(code, task_id, caller_lr):
    """Small fixed-layout Thumb model with adversarial AAPCS scratch clobbers."""
    r = [0] * 16
    r[0], r[4], r[13], r[14] = task_id, 0x1234, 0x800, caller_lr
    stack, calls, pc = {}, [], 0
    for _ in range(12):
        op = struct.unpack_from("<H", code, pc)[0]
        if op == 0xB510:
            r[13] -= 8
            stack[r[13]], stack[r[13] + 4] = r[4], r[14]
            pc += 2
        elif op in (0x4904, 0x4B04):
            literal = ((pc + 4) & ~3) + (op & 255) * 4
            r[(op >> 8) & 7] = struct.unpack_from("<I", code, literal)[0]
            pc += 2
        elif op == 0xF000:
            require(struct.unpack_from("<H", code, pc + 2)[0] == 0xF803)
            r[14] = pc + 5
            pc += 10
        elif op == 0x4718:
            require(r[3] & 1 and r[13] % 8 == 0)
            calls.append(tuple(r[:4]))
            pc = r[14] & ~1
            r[:4], r[12], r[14] = [0xCAFE] * 4, 0xBEEF, 0xDEAD
        elif op in (0xBC10, 0xBC01):
            r[4 if op == 0xBC10 else 0] = stack[r[13]]
            r[13] += 4
            pc += 2
        elif op == 0x4700:
            return calls, r[0], r[4], r[13]
        else:
            raise ValueError("unsupported bridge instruction")
    raise ValueError("bridge did not return")


def wrapped_call(entry, consumer, label, task, caller_lr):
    """Execute *only* public FunctionWrap on BytesIO, then model nested calls.

    This invokes no inserter main, source ROM, file, tool or actual output.
    """
    tree = ast.parse(read("scripts/insert.py"))
    definition = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "FunctionWrap")
    namespace = {"_io": io}
    exec(compile(ast.Module(body=[definition], type_ignores=[]), "<public FunctionWrap on synthetic IO>", "exec"), namespace)
    memory = io.BytesIO()
    namespace["FunctionWrap"](memory, (SYMBOLS[entry] & ~1) - 0x08000000, 0, 0, 1)
    wrapper = memory.getvalue()
    require(wrapper == bytes.fromhex("10b5034c00f003f810bc02bc08472047")
            + struct.pack("<I", SYMBOLS[entry]))
    wrapper_at = 0x09000000
    bridge_at = SYMBOLS[entry] & ~1
    regions = {wrapper_at: wrapper, bridge_at: source_bridge(read(ASM), entry, consumer, label)}
    r, stack, calls, pc = [0] * 16, {}, [], wrapper_at
    r[0], r[4], r[13], r[14] = task, 0x5678, 0x800, caller_lr
    def halfword(at):
        for base, data in regions.items():
            if base <= at < base + len(data):
                return struct.unpack_from("<H", data, at - base)[0]
        raise ValueError("unbound synthetic PC")
    for _ in range(24):
        op = halfword(pc)
        if op == 0xB510:
            r[13] -= 8
            stack[r[13]], stack[r[13] + 4] = r[4], r[14]
            pc += 2
        elif op in (0x4904, 0x4B04, 0x4C03):
            at = ((pc + 4) & ~3) + (op & 255) * 4
            r[(op >> 8) & 7] = halfword(at) | (halfword(at + 2) << 16)
            pc += 2
        elif op == 0xF000:
            low = halfword(pc + 2)
            require(low == 0xF803)
            r[14] = pc + 5
            pc += 4 + (low & 2047) * 2
        elif op in (0xBC10, 0xBC01, 0xBC02):
            register = {0xBC10: 4, 0xBC01: 0, 0xBC02: 1}[op]
            r[register] = stack[r[13]]
            r[13] += 4
            pc += 2
        elif op in (0x4700, 0x4708, 0x4718, 0x4720):
            target = r[(op >> 3) & 15]
            if target == SYMBOLS[consumer]:
                require(r[13] % 8 == 0)
                calls.append((r[0], r[1], target, r[13]))
                pc = r[14] & ~1
                r[:4], r[12], r[14] = [0xFACE] * 4, 0xCAFE, 0xDEAD
            elif any(base <= (target & ~1) < base + len(data) for base, data in regions.items()):
                require(target & 1)
                pc = target & ~1
            else:
                require(target == caller_lr)
                return calls, target, r[4], r[13]
        else:
            raise ValueError("unmodeled nested instruction")
    raise ValueError("nested wrapper did not return")


def source_bindings(c):
    for entry, consumer, _ in PAIRS:
        require(not re.search(r"\bvoid\s+" + entry + r"\([^;{}]*\)\s*\{", c))
        require(c.count("void " + consumer + "(") == 1)
        require(re.search(r"void " + consumer + r"\(u8 taskId, const volatile struct OakIntroContractV1 \*intro\)", c))
        consumer_body = body(c, consumer)
        require(consumer_body.count("OakIntroSelectedSpecies(intro)") == 1)
        require("OAK_INTRO_SPECIES" not in consumer_body and "gOakIntroContract" not in consumer_body)
    sprite = body(c, "OakIntroSpriteConsumer")
    for text in ("&gMonFrontPicTable[species]", "&gMonPaletteTable[species]",
                 "LoadCompressedSpriteSheetUsingHeap(front);",
                 "LoadCompressedSpritePaletteUsingHeap(palette);",
                 "SetMultiuseSpriteTemplateToPokemon(front->tag, 0);",
                 "gMultiuseSpriteTemplate->tileTag = front->tag;",
                 "gMultiuseSpriteTemplate->paletteTag = palette->tag;",
                 "gMultiuseSpriteTemplate->images = NULL;",
                 "CreateSprite(gMultiuseSpriteTemplate, 96, 96, 1)"):
        require(text in sprite)
    require("struct SpriteTemplate " not in sprite)  # no stack template
    require("gSprites[spriteId].invisible = TRUE;" in sprite)
    require("gTasks[taskId].tNidoranFSpriteId = spriteId;" in sprite)


@lru_cache(maxsize=4)
def selection_predicate(c):
    # Fail if the implementation no longer matches this bounded model.
    require(clean(body(c, "OakIntroSelectedSpecies")) == clean('''
        u16 species;
        if (intro != &gOakIntroContract) return OAK_INTRO_DEFAULT_SPECIES;
        species = intro->selectedSpecies;
        if (species >= OAK_INTRO_SPECIES_CAPACITY
            || !(gOakIntroEligibility[species >> 3] & (1u << (species & 7))))
            return OAK_INTRO_DEFAULT_SPECIES;
        return species;
    '''))
    predicate = body(c, "OakIntroSelectedSpecies").split("if (species", 1)[1].split("return", 1)[0]
    predicate = ("species" + predicate).strip().removesuffix(")")
    predicate = predicate.replace("||", " or ").replace("!(", "not (").replace("1u", "1")
    predicate = predicate.replace("gOakIntroEligibility", "bits")
    tree = ast.parse(re.sub(r"\s+", " ", predicate), mode="eval")
    allowed = (ast.Expression, ast.BoolOp, ast.Or, ast.UnaryOp, ast.Not,
               ast.Compare, ast.GtE, ast.BinOp, ast.BitAnd, ast.LShift,
               ast.RShift, ast.Subscript, ast.Name, ast.Load, ast.Constant)
    require(all(isinstance(node, allowed) for node in ast.walk(tree)))
    return compile(tree, "<extracted Oak selection predicate>", "eval")


def selected(c, descriptor_address, species, bits):
    require(0 <= species <= 65535)
    predicate = selection_predicate(c)
    if descriptor_address != SYMBOLS["gOakIntroContract"]:
        return 29
    invalid = eval(predicate, {"__builtins__": {}},
                   {"species": species, "bits": bits, "OAK_INTRO_SPECIES_CAPACITY": 1440})
    return 29 if invalid else species


def definitions(c, asm):
    result = {}
    names = ["gOakIntroContract", "gOakIntroEligibility"] + [x for p in PAIRS for x in p[:2]]
    for name in names:
        c_definitions = len(re.findall(r"\bvoid\s+" + name + r"\([^;{}]*\)\s*\{", c))
        if name.startswith("gOakIntro"):
            c_definitions += len(re.findall(r"(?m)^(?!extern\b)[^\n;{}]*\b" + name
                                            + r"\s*(?:\[[^\]]*\])?\s*(?:=|;)", c))
        result[name] = len(re.findall(r"^" + name + r":", asm, re.M)) + c_definitions
    require(all(x == 1 for x in result.values()))
    return result


def validate_record(record, bits, addresses=SYMBOLS, owner_counts=None):
    """Future ownership preflight SPECIFICATION MODEL, not a UPR locator."""
    require(addresses["gOakIntroContract"] % 4 == 0)
    require(owner_counts is None or all(x == 1 for x in owner_counts.values()))
    expected = data_section(read(ASM), "gOakIntroContract", ".Loak_contract_end", addresses)
    require(len(record) == len(expected) == 96 and len(bits) == 180)
    require(record[:92] == expected[:92] and record[94:] == expected[94:])
    require(bits == bitmap())
    # Symbols/intervals must be distinct, never alias Pickup/Evolution/native rows.
    intervals = [(addresses["gOakIntroContract"], 96), (addresses["gOakIntroEligibility"], 180)]
    intervals += [(addresses[p[0]] & ~1, 28) for p in PAIRS]
    intervals += [(addresses[p[1]] & ~1, 64) for p in PAIRS]  # mock consumer extents
    intervals += [(0x09001800, 64), (0x09001900, 32), (0x09001A00, 8)]
    for i, (start, size) in enumerate(intervals):
        require(start % 4 == 0)
        for other, length in intervals[i + 1:]:
            require(start + size <= other or other + length <= start)
    for entry, consumer, label in PAIRS:
        require(addresses[entry] & 1 and addresses[consumer] & 1)
        require(addresses[entry] == SYMBOLS[entry] and addresses[consumer] == SYMBOLS[consumer])
        calls, _, _, _ = bridge_call(source_bridge(read(ASM), entry, consumer, label), 7, 0x101)
        require(calls[0][1] == addresses["gOakIntroContract"] and calls[0][3] == addresses[consumer])
    species = struct.unpack_from("<H", record, 92)[0]
    require(species < 1440 and bits[species >> 3] & (1 << (species & 7)))


def public_policy():
    """Independently extract rejected pilot categories from pinned UPR source."""
    text = pinned(UPR, UPR_SHA, "romio/src/main/java/com/uprfvx/romio/services/SpecialFormPredicates.java")
    method = body(text, "cfruDpePoolCategory")
    excluded = {0}
    categories = set()
    for condition, category in re.findall(r"if \((.*?)\)\s*\{\s*return CfruDpePoolCategory\.(\w+);", method, re.S):
        if category in {"REGIONAL", "PERSISTENT_ALTERNATE"}:
            continue
        categories.add(category)
        excluded.update(int(x, 0) for x in re.findall(r"\bid == (0x[0-9A-Fa-f]+|\d+)", condition))
        for first, last in re.findall(r"between\(id, (0x[0-9A-Fa-f]+|\d+), (0x[0-9A-Fa-f]+|\d+)\)", condition):
            excluded.update(range(int(first, 0), int(last, 0) + 1))
    require(categories == {"INVALID", "MISSING_SOURCE_DATA", "MEGA", "PRIMAL", "GIGANTAMAX",
                           "TERA_TRANSFORMATION", "ETERNAMAX", "BATTLE_TRANSFORMATION", "CONDITION_DEPENDENT"})
    return excluded


def native_sources():
    def dpe(path):
        return pinned(DPE, DPE_SHA, path)
    ids = {name: int(value, 0) for name, value in re.findall(
        r"^#define\s+(SPECIES_\w+)\s+(0x[0-9A-Fa-f]+|\d+)\b", dpe("include/species.h"), re.M)}
    require(ids["SPECIES_PECHARUNT"] == 1439 and ids["SPECIES_NIDORAN_F"] == 29)
    require("#define NUM_SPECIES (SPECIES_PECHARUNT + 1)" in dpe("include/species.h"))
    def rows(path):
        text = re.sub(r"/\*.*?\*/|//[^\n]*", "", dpe(path), flags=re.S)
        values = re.findall(r"\[(SPECIES_\w+|\d+)\]\s*=\s*\{([^}]+)\}", text)
        result = {}
        for name, value in values:
            i = ids[name] if name in ids else int(name)
            require(i not in result)
            result[i] = [x.strip() for x in value.split(",")]
        return result
    front, palette = rows("src/Front_Pic_Table.c"), rows("src/Palette_Table.c")
    dex = {ids[name] for name in re.findall(r"\[(SPECIES_\w+) - 1\]\s*=\s*NATIONAL_DEX_\w+", dpe("src/Species_To_Pokdex_Table.c"))}
    # Metadata only: no image blobs are read, parsed, hashed, copied or decoded.
    manifest = set(git(DPE, "ls-tree", "-r", "--name-only", DPE_SHA, "--", "graphics/frontspr").splitlines())
    declarations = set(re.findall(r"extern const u8 (\w+)\[\];", dpe("include/sprite_data.h")))
    return ids, front, palette, dex, manifest, declarations


def derive_bitmap():
    ids, front, palette, dex, manifest, declarations = native_sources()
    excluded = public_policy() | {ids[x] for x in
        ("SPECIES_DEOXYS", "SPECIES_DEOXYS_ATTACK", "SPECIES_DEOXYS_DEFENSE", "SPECIES_DEOXYS_SPEED")}
    result, missing = bytearray(180), set()
    for i in range(1, 1440):
        if i in excluded:
            continue
        if i not in front or i not in palette or i not in dex:
            missing.add(i)
            continue
        f, p = front[i], palette[i]
        require(f[1] == "(64 * 64) / 2" and ids[f[2]] == i and p[2] == "0x0")
        require(f[0] in declarations and p[0] in declarations)
        front_asset = "graphics/frontspr/" + f[0].removesuffix("Tiles") + ".png"
        palette_asset = "graphics/frontspr/" + p[0].removesuffix("Pal") + ".png"
        if front_asset not in manifest or palette_asset not in manifest:
            missing.add(i)
            continue
        require(0 < ids[p[1]] < 1440)
        result[i >> 3] |= 1 << (i & 7)
    require(missing == {ids["SPECIES_CASTFORM"]})
    return result


class OakIntroAbiTests(unittest.TestCase):
    def test_01_header_layout_size_offsets_alignment_and_widths(self):
        text = read(HEADER)
        declaration = text.split("struct OakIntroContractV1\n{", 1)[1].split("};", 1)[0]
        declaration = re.sub(r"/\*.*?\*/", "", declaration, flags=re.S)
        fields = []
        for line in declaration.splitlines():
            if not line.strip():
                continue
            match = re.fullmatch(r"\s*(.*?)\s+(\*?\w+)(?:\[(\d+)\])?;\s*", line)
            self.assertIsNotNone(match, line)
            kind, name, count = match.groups()
            if name.startswith("*"):
                kind += " *"
                name = name[1:]
            self.assertIn(kind, {"u8", "u16", "u32", "const volatile struct OakIntroContractV1 *",
                                 "const u8 *", "OakIntroEntry", "OakIntroConsumer"})
            ctype = {"u8": U8, "u16": U16, "u32": U32}.get(kind, U32)
            fields.append((name, ctype * int(count) if count else ctype))
        wire = type("PublicWire", (ctypes.LittleEndianStructure,), {"_fields_": fields})
        self.assertEqual(ctypes.sizeof(wire), 96)
        self.assertEqual(ctypes.alignment(wire), 4)
        self.assertEqual(wire.selectedSpecies.offset, 92)
        constants = dict(re.findall(r"^#define (OAK_INTRO_\w+) (\d+)$", text, re.M))
        self.assertEqual({k: int(v) for k, v in constants.items()}, {
            "OAK_INTRO_ABI_VERSION": 1, "OAK_INTRO_ABI_SIZE": 96, "OAK_INTRO_PROFILE": 1,
            "OAK_INTRO_SPECIES_CAPACITY": 1440, "OAK_INTRO_DEFAULT_SPECIES": 29,
            "OAK_INTRO_SELECTOR_OFFSET": 92, "OAK_INTRO_SELECTOR_WIDTH": 2,
            "OAK_INTRO_BITMAP_BYTES": 180, "OAK_INTRO_POLICY_VERSION": 1,
            "OAK_INTRO_BRIDGE_SIZE": 28, "OAK_INTRO_BRIDGE_DESCRIPTOR_OFFSET": 20,
            "OAK_INTRO_BRIDGE_CONSUMER_OFFSET": 24})
        assertions = re.findall(r"^OAK_ABI_OFFSET\((\w+), (\w+)\);", text, re.M)
        self.assertEqual({x for x, _ in assertions}, {x for x, _ in fields})
        for name, offset in assertions:
            self.assertEqual(getattr(wire, name).offset, int(constants.get(offset, offset)))
        for fragment in ("sizeof(u16) == 2", "sizeof(u32) == 4", "sizeof(void *) == 4",
                         "sizeof(OakIntroConsumer) == 4", "__alignof__(struct OakIntroContractV1) == 4",
                         "sizeof(struct CompressedSpriteSheet) == 8", "sizeof(struct CompressedSpritePalette) == 8"):
            self.assertIn(fragment, text)

    def test_02_descriptor_source_fields(self):
        record = data_section(read(ASM), "gOakIntroContract", ".Loak_contract_end")
        self.assertEqual(len(record), 96)
        self.assertEqual(record[:8], b"CFROAK01")
        self.assertEqual(struct.unpack_from("<HHI4HI2H4I2I6H", record, 12),
                         (1, 96, 1, 1440, 29, 92, 2, SYMBOLS["gOakIntroEligibility"], 180, 1,
                          SYMBOLS[PAIRS[0][0]], SYMBOLS[PAIRS[0][1]], SYMBOLS[PAIRS[1][0]], SYMBOLS[PAIRS[1][1]],
                          0x08000128, 0x08000130, 8, 8, 28, 20, 24, 4))
        self.assertEqual(record[72:92], bytes(20))
        self.assertEqual(record[92:], struct.pack("<HH", 29, 0))
        self.assertIn(".align 2\n.global gOakIntroContract", read(ASM))
        validate_record(record, bitmap())

    def test_03_unique_public_symbols_and_actual_hook_connections(self):
        c, asm = read("src/scripting.c"), read(ASM)
        definitions(c, asm)
        source_bindings(c)
        rewrites = read("functionrewrites")
        for entry, consumer, label in PAIRS:
            self.assertEqual(len(re.findall(r"^" + entry + r"\s", rewrites, re.M)), 1)
            source_bridge(asm, entry, consumer, label)
        all_c = "\n".join(p.read_text() for p in (ROOT / "src").rglob("*.c"))
        all_asm = "\n".join(p.read_text() for p in (ROOT / "assembly").rglob("*.s"))
        definitions(all_c, all_asm)

    def test_04_bridge_task_argument_stack_and_return_states(self):
        for entry, consumer, label in PAIRS:
            code = source_bridge(read(ASM), entry, consumer, label)
            self.assertEqual(len(code), 28)
            for task in (0, 7, 15, 255):
                for lr in (0x100, 0x101):
                    calls, returned, preserved, sp = bridge_call(code, task, lr)
                    self.assertEqual(len(calls), 1)
                    self.assertEqual(calls[0][0], task)
                    self.assertEqual(calls[0][1], SYMBOLS["gOakIntroContract"])
                    self.assertEqual(calls[0][3], SYMBOLS[consumer])
                    self.assertEqual((returned, preserved, sp), (lr, 0x1234, 0x800))

    def test_05_default_all_u16_selections_and_foreign_record(self):
        c, bits = read("src/scripting.c"), bitmap()
        allowed = {i for i in range(1440) if bits[i >> 3] & (1 << (i & 7))}
        for i in range(65536):
            self.assertEqual(selected(c, SYMBOLS["gOakIntroContract"], i, bits), i if i in allowed else 29)
        for i in (0, 1, 29, 251, 252, 255, 256, 276, 277, 410, 412, 413, 1040, 1439, 1440, 65535):
            expected = i if i < 1440 and bits[i >> 3] & (1 << (i & 7)) else 29
            self.assertEqual(selected(c, SYMBOLS["gOakIntroContract"], i, bits), expected)
            self.assertEqual(selected(c, 0x09002000, i, bits), 29)

    def test_06_bitmap_entire_pinned_public_source_derivation(self):
        self.assertEqual(bitmap(), derive_bitmap())
        self.assertEqual(sum(x.bit_count() for x in bitmap()), 1250)
        self.assertIn(".align 2\n.global gOakIntroEligibility", read(ASM))

    def test_07_bitmap_special_cases_and_shared_unown_tags(self):
        ids, front, palettes, *_ = native_sources()
        bits = bitmap()
        yes = ("SPECIES_NIDORAN_F", "SPECIES_TREECKO", "SPECIES_UNOWN", "SPECIES_UNOWN_B",
               "SPECIES_UNOWN_QUESTION", "SPECIES_PECHARUNT", "SPECIES_TAUROS_P", "SPECIES_OGERPON")
        no = ("SPECIES_NONE", "SPECIES_EGG", "SPECIES_CASTFORM", "SPECIES_DEOXYS",
              "SPECIES_DEOXYS_ATTACK", "SPECIES_DEOXYS_DEFENSE", "SPECIES_DEOXYS_SPEED",
              "SPECIES_OGERPON_TERASTAL", "SPECIES_TERAPAGOS_STELLAR")
        for name in yes:
            i = ids[name]
            self.assertTrue(bits[i >> 3] & (1 << (i & 7)), name)
        for i in [ids[name] for name in no] + list(range(252, 277)):
            self.assertFalse(bits[i >> 3] & (1 << (i & 7)), i)
        for i in range(413, 440):
            self.assertEqual(palettes[i][1], "SPECIES_UNOWN")
            self.assertEqual(ids[front[i][2]], i)
        for i in range(252, 277):
            self.assertEqual(front[i][0], "gFrontSprite252Tiles")

    def test_08_full_sheet_palette_metadata_and_template(self):
        source_bindings(read("src/scripting.c"))
        # Read exact public vanilla loader implementation, already documented
        # by the source contract; source signatures here retain typed full rows.
        self.assertIn("const struct CompressedSpriteSheet* src", read("include/decompress.h"))
        self.assertIn("const struct CompressedSpritePalette *src", read("include/decompress.h"))
        sprite = body(read("src/scripting.c"), "OakIntroSpriteConsumer")
        self.assertNotIn("2048", sprite)
        self.assertNotIn("DecompressPicFromTable", sprite)
        self.assertNotIn("gMonShinyPaletteTable", sprite)

    def test_09_existing_intro_title_hooks_and_non_stage_sources_unchanged(self):
        for path in ("functionrewrites", "hooks", "BPRE.ld", "linker.ld", "scripts/build.py", "scripts/make.py",
                     "scripts/insert.py", "src/oak_minimal_exposition.c", "src/catching.c", "src/config.h",
                     "assembly/data/pickup_descriptor_bridge.s", "assembly/data/evolution_friendship_anchor.s",
                     "include/new/pickup_items.h", "include/new/evolution.h", "src/item.c", "src/build_pokemon.c"):
            # Missing baseline path is a test error, never silently skipped.
            self.assertEqual(read(path), pinned(ROOT, BASE, path), path)
        c, original = read("src/scripting.c"), pinned(ROOT, BASE, "src/scripting.c")
        self.assertEqual(body(c, "SetTitleScreenScene_Cry"), body(original, "SetTitleScreenScene_Cry"))
        self.assertEqual(body(c, "OakIntroCryConsumer").replace("OakIntroSelectedSpecies(intro)", "OAK_INTRO_SPECIES"),
                         body(original, "Task_OakSpeech_IsInhabitedFarAndWide"))
        # Original sprite lifecycle after creation remains byte-for-byte source.
        self.assertEqual(body(c, "OakIntroSpriteConsumer").split("spriteId = CreateSprite", 1)[1],
                         body(original, "CreateOakIntroPokemonSprite").split("spriteId = CreateSprite", 1)[1])
        self.assertIn("DestroySprite(&gSprites[gTasks[taskId].data[4]]);", read("src/oak_minimal_exposition.c"))
        self.assertNotIn("OAK_INTRO_SPECIES", body(c, "OakIntroSpriteConsumer"))

    def test_10_build_source_inclusion_and_no_name_conflicts(self):
        build = read("scripts/build.py")
        for fragment in ("'**/*.s': ProcessAssembly", "directory = ASSEMBLY", "'-mthumb'", "'-march=armv4t'"):
            self.assertIn(fragment, build)
        self.assertIn("*(.text)", read("linker.ld"))
        for name in SYMBOLS:
            self.assertNotRegex(read("BPRE.ld"), r"(?m)^" + name + r"\s*=")
        tracked = git(ROOT, "ls-tree", "-r", "--name-only", BASE).splitlines()
        paths = [p for p in tracked if (p.startswith("src/") and p.endswith(".c"))
                 or (p.startswith("assembly/") and p.endswith((".s", ".json")))]
        paths += [p[:-7] + ".s" for p in tracked if p.startswith("strings/") and p.endswith(".string")]
        digest = lambda path: hashlib.md5(("./" + path).encode()).hexdigest()[:8]
        self.assertEqual([p for p in paths if digest(p) == digest(ASM)], [])
        self.assertNotIn(ASM, tracked)
        self.assertIn("hashlib.md5", build)

    def test_11_missing_duplicate_and_disconnected_source_rejected(self):
        c, asm = read("src/scripting.c"), read(ASM)
        for entry, consumer, label in PAIRS:
            for changed in (asm.replace(entry + ":", "missing_entry:"), asm + "\n" + entry + ":\n"):
                with self.assertRaises(ValueError):
                    definitions(c, changed)
            with self.assertRaises(ValueError):
                definitions(c + f"\nvoid {entry}(u8 taskId) {{}}", asm)
            with self.assertRaises(ValueError):
                source_bridge(asm.replace("ldr r1, .Loak_" + label, "ldr r0, .Loak_" + label), entry, consumer, label)
            with self.assertRaises(ValueError):
                other_consumer = PAIRS[1 if label == "sprite" else 0][1]
                source_bridge(asm.replace(".word " + consumer, ".word " + other_consumer), entry, consumer, label)
        for name in ("gOakIntroContract", "gOakIntroEligibility"):
            with self.assertRaises(ValueError):
                definitions(c + "\nconst u32 " + name + " = 0;\n", asm)
        for old, new in (("OakIntroSelectedSpecies(intro)", "OAK_INTRO_DEFAULT_SPECIES"),
                         ("paletteTag = palette->tag", "paletteTag = species"),
                         ("LoadCompressedSpriteSheetUsingHeap(front)", "LoadCompressedSpriteSheetUsingHeap(&gMonFrontPicTable[29])")):
            with self.assertRaises(ValueError):
                source_bindings(c.replace(old, new))

    def test_12_every_immutable_descriptor_byte_rejects_mutation(self):
        record = data_section(read(ASM), "gOakIntroContract", ".Loak_contract_end")
        for i in list(range(92)) + [94, 95]:
            broken = bytearray(record)
            broken[i] ^= 1
            with self.assertRaises(ValueError, msg=f"offset {i}"):
                validate_record(broken, bitmap())
        for length in (0, 92, 95, 97):
            with self.assertRaises(ValueError):
                validate_record((record + b"\0")[:length], bitmap())
        for i in (0, 92, 179):
            broken = bitmap()
            broken[i] ^= 1
            with self.assertRaises(ValueError):
                validate_record(record, broken)

    def test_13_selector_write_budget_and_invalid_preflight(self):
        record = data_section(read(ASM), "gOakIntroContract", ".Loak_contract_end")
        bits = bitmap()
        for i in range(1440):
            candidate = bytearray(record)
            struct.pack_into("<H", candidate, 92, i)
            if bits[i >> 3] & (1 << (i & 7)):
                validate_record(candidate, bits)
                self.assertEqual(candidate[:92] + candidate[94:], record[:92] + record[94:])
            else:
                with self.assertRaises(ValueError):
                    validate_record(candidate, bits)
        for i in (1440, 65535):
            candidate = bytearray(record)
            struct.pack_into("<H", candidate, 92, i)
            with self.assertRaises(ValueError):
                validate_record(candidate, bits)

    def test_14_copy_alias_overlap_and_duplicate_owner_rejected(self):
        record = data_section(read(ASM), "gOakIntroContract", ".Loak_contract_end")
        for symbol in SYMBOLS:
            for address in (0x09001002, SYMBOLS["gOakIntroEligibility"], 0x09001800, 0x09001900, 0x09001A00):
                addresses = dict(SYMBOLS, **{symbol: address})
                if addresses == SYMBOLS:
                    continue
                with self.assertRaises(ValueError):
                    validate_record(record, bitmap(), addresses)
        for count in (0, 2):
            owners = {x: 1 for x in SYMBOLS}
            owners["gOakIntroContract"] = count
            with self.assertRaises(ValueError):
                validate_record(record, bitmap(), owner_counts=owners)

    def test_16_real_public_functionwrap_to_bridge_to_consumer_model(self):
        for entry, consumer, label in PAIRS:
            for task in (0, 7, 15, 255):
                for lr in (0x100, 0x101):
                    calls, returned, preserved, sp = wrapped_call(entry, consumer, label, task, lr)
                    self.assertEqual(calls, [(task, SYMBOLS["gOakIntroContract"], SYMBOLS[consumer], 0x7F0)])
                    self.assertEqual((returned, preserved, sp), (lr, 0x5678, 0x800))
        rows = {line.split()[0]: line.split()[1:] for line in read("functionrewrites").splitlines()
                if line.startswith(tuple(p[0] for p in PAIRS))}
        self.assertEqual(rows, {PAIRS[0][0]: ["0x08130f2c", "0", "1"],
                                PAIRS[1][0]: ["0x0812fa78", "0", "1"]})

    def test_17_only_authorized_consumer_regions_change_in_scripting(self):
        current, original = read("src/scripting.c"), pinned(ROOT, BASE, "src/scripting.c")
        # Whitelist the include and the three named function bodies. Everything
        # else, including macro roots, all unrelated specials and title cry,
        # must be exactly the original public text.
        current = current.replace('#include "../include/new/oak_intro.h"\n', '')
        begin = current.index('/* Both real consumers read the bridge argument')
        end = current.index('#define OakSpeechPrintMessage', begin)
        old_begin = original.index('void CreateOakIntroPokemonSprite(u8 taskId)')
        old_end = original.index('#define OakSpeechPrintMessage', old_begin)
        current = current[:begin] + original[old_begin:old_end] + current[end:]
        begin = current.index('/* Assembly owns Task_OakSpeech_IsInhabitedFarAndWide. */')
        end = current.index('#define tSceneNum', begin)
        old_begin = original.index('void Task_OakSpeech_IsInhabitedFarAndWide(u8 taskId)')
        old_end = original.index('#define tSceneNum', old_begin)
        current = current[:begin] + original[old_begin:old_end] + current[end:]
        self.assertEqual(current, original)

    def test_18_exact_pinned_evolution_enum_and_rows_without_checkout_assumptions(self):
        # Replacement for the old test's local DPE HEAD prerequisite. Reads
        # only exact public objects, never updates or disguises a checkout.
        cfru = read("include/pokemon.h")
        dpe = pinned(DPE, DPE_SHA, "include/evolution.h")
        def methods(text):
            enum = text.split("enum EvolutionMethods", 1)[1].split("{", 1)[1].split("}", 1)[0]
            return re.findall(r"\bEVO_[A-Z_]+\b", re.sub(r"//[^\n]*", "", enum))
        self.assertEqual(methods(cfru), methods(dpe))
        for text in (cfru, dpe):
            evolution = text.split("struct Evolution\n", 1)[1].split("}", 1)[0]
            self.assertEqual(re.findall(r"u16 (\w+);", evolution), ["method", "param", "targetSpecies", "unknown"])
        self.assertIn("#define EVOS_PER_MON 16", read("src/config.h"))
        table = pinned(DPE, DPE_SHA, "src/Evolution Table.c")
        self.assertEqual(re.findall(r"\{(EVO_COINS|EVO_MAUSHOLD_THREE|EVO_MAUSHOLD_FOUR), (\d+), (SPECIES_\w+), (\d+)\}", table),
                         [("EVO_MAUSHOLD_THREE", "25", "SPECIES_MAUSHOLD", "0"),
                          ("EVO_MAUSHOLD_FOUR", "25", "SPECIES_MAUSHOLD_FOUR", "0"),
                          ("EVO_COINS", "2999", "SPECIES_GHOLDENGO", "0"),
                          ("EVO_COINS", "2999", "SPECIES_GHOLDENGO", "0")])



    def test_19_both_pinned_native_cry_rows_exist_and_api_is_u16(self):
        ids, *_ = native_sources()
        bits = bitmap()
        eligible = {i for i in range(1440) if bits[i >> 3] & (1 << (i & 7))}
        for path in ("src/Cry_Table.c", "src/Cry_Table_2.c"):
            text = pinned(DPE, DPE_SHA, path)
            rows = {ids[name]: value for name, value in re.findall(
                r"\[(SPECIES_\w+)\]\s*=\s*\{([^}]+)\}", text)}
            self.assertTrue(eligible <= rows.keys(), path)
            for i in eligible:
                self.assertRegex(rows[i], r"\.wav\s*=\s*(?:gCry\w+|\(u8\*\) 0x[0-9A-Fa-f]+)")
        self.assertRegex(read("include/sound.h"), r"PlayCry1\(u16 species, s8 pan\)")

    def test_15_exact_allowlist_ancestry_modes_and_no_gitlinks(self):
        self.assertEqual(git(ROOT, "merge-base", BASE, "HEAD").strip(), BASE)
        changes = set(git(ROOT, "diff", BASE, "--name-only").splitlines())
        changes.update(git(ROOT, "ls-files", "--others", "--exclude-standard").splitlines())
        self.assertEqual(changes, ALLOWLIST)
        modes = git(ROOT, "diff", BASE, "--raw")
        self.assertNotIn("160000", modes)
        self.assertNotIn("100755", modes)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dpe-root", type=Path, required=True)
    parser.add_argument("--upr-root", type=Path, required=True)
    args = parser.parse_args()
    DPE, UPR = args.dpe_root.resolve(), args.upr_root.resolve()
    unittest.main(argv=[__file__], verbosity=2)
