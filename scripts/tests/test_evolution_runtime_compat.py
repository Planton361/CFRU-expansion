#!/usr/bin/env python3
"""#722 public-source / in-memory regressions, Python stdlib only.

This executes a deliberately bounded model of extracted C predicates, NOT
compiled C, ARM code, an inserter, or gameplay. Legacy preservation is checked
against the exact base function. The locator/write model specifies a future
preflight contract; it is not UPR integration. No binary/build/private inputs.
"""
import argparse
import ast
import copy
import io
from pathlib import Path
import re
import struct
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[2]
BASE = "e68a701aa4e68733ef8ad1e7cadb68825c0d16c2"
DPE_SHA = "d887185de1f6ae6a78e85c4311bbadde17041d00"
DPE = None
MAGIC = b"CFRUEVO1"
RECORD = struct.Struct("<8sIIHHHHHHBBH")
ORIGIN = 0x09000000
NEW_METHODS = ("EVO_COINS", "EVO_MAUSHOLD_THREE", "EVO_MAUSHOLD_FOUR")


def read(path):
    return (ROOT / path).read_text()


def git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def function(source, name):
    match = re.search(r"\b" + name + r"\([^;{}]*\)\s*\{", source)
    if not match:
        raise AssertionError("missing function " + name)
    start = source.index("{", match.start())
    depth = 1
    end = start + 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[start:end]


def method_names(source):
    enum = source.split("enum EvolutionMethods", 1)[1].split("{", 1)[1].split("}", 1)[0]
    return re.findall(r"\bEVO_[A-Z_]+\b", re.sub(r"//[^\n]*", "", enum))


def select_defines(source, defined):
    """Only the simple #ifdef/#ifndef/#else/#endif forms in these predicates."""
    active = [True]
    output = []
    for line in source.splitlines():
        text = line.strip()
        if text.startswith(("#ifdef ", "#ifndef ")):
            condition = text.split()[1] in defined
            if text.startswith("#ifndef"):
                condition = not condition
            active.append(active[-1] and condition)
        elif text == "#else":
            active[-1] = active[-2] and not active[-1]
        elif text == "#endif":
            active.pop()
        elif active[-1]:
            output.append(line)
    if len(active) != 1:
        raise AssertionError("unbalanced model preprocessor")
    return "\n".join(output)


def case(source, name):
    body = function(source, "GetEvolutionTargetSpecies")
    normal = body.split("case EVO_MODE_NORMAL:", 1)[1].split("case EVO_MODE_TRADE:", 1)[0]
    return normal.split("case " + name + ":", 1)[1].split("case ", 1)[0]


def expression(text, values):
    text = text.replace("gEvolutionTable[species][i].param", "param")
    text = text.replace("gEvolutionTable[species][i].unknown", "unknown")
    text = text.replace("GetCoins()", "coins").replace("IsDayTime()", "day")
    text = text.replace("IsNightTime()", "night")
    text = text.replace("&&", " and ").replace("||", " or ")
    tree = ast.parse(text.strip(), mode="eval")
    allowed = (ast.Expression, ast.BoolOp, ast.And, ast.Or, ast.Compare,
               ast.GtE, ast.Lt, ast.Eq, ast.NotEq, ast.BinOp, ast.Mod,
               ast.Name, ast.Load, ast.Constant)
    if any(not isinstance(node, allowed) for node in ast.walk(tree)):
        raise AssertionError("unmodeled expression: " + text)
    return eval(compile(tree, "<extracted-public-C-predicate>", "eval"), {"__builtins__": {}}, values)


def threshold(source, value):
    body = function(source, "GetEvolutionFriendshipThreshold")
    assert "u8 threshold = gEvolutionFriendshipContract.threshold;" in body
    condition = re.search(r"if \((.*?)\)\s*return threshold;", body, re.S).group(1)
    values = {"threshold": value, "EVOLUTION_FRIENDSHIP_DEFAULT": 220,
              "EVOLUTION_FRIENDSHIP_EASIER": 160}
    assert body.strip().endswith("return EVOLUTION_FRIENDSHIP_DEFAULT;\n}")
    return value if expression(condition, values) else 220


def evaluate_row(source, row, state, *, time=True):
    """Extracted new/friendship predicates only; unrelated cases are unmodeled."""
    method, param, target, unknown = row
    if state["mode"] != "EVO_MODE_NORMAL" or state.get("everstone", False):
        return 0
    body = select_defines(case(source, method), {"TIME_ENABLED"} if time else set())
    body = re.sub(r"//[^\n]*", "", body).strip()
    values = dict(state, param=param, unknown=unknown,
                  friendshipThreshold=threshold(source, state["threshold"]))
    if method == "EVO_MOVE_TYPE":
        condition = re.search(r"if \((.*?)\)\s*break;", body, re.S).group(1)
        if expression(condition, values):
            return 0
        assert "j < MAX_MON_MOVES" in body
        assert "gBattleMoves[mon->moves[j]].type == gEvolutionTable[species][i].param" in body
        return target if param in state["move_types"] else 0
    match = re.fullmatch(r"if \((.*?)\)\s*targetSpecies = gEvolutionTable\[species\]\[i\].targetSpecies;\s*break;", body, re.S)
    if match:
        return target if expression(match.group(1), values) else 0
    assert body == "break;", (method, body)
    return 0


def evaluate(source, rows, state, *, time=True):
    before = copy.deepcopy((rows, state))
    target = 0
    for row in rows:
        result = evaluate_row(source, row, state, time=time)
        if result:
            target = result  # Preserve the runtime's last matching slot order.
    assert (rows, state) == before
    return target


def level_methods(source):
    return set(re.findall(r"case (EVO_[A-Z_]+):", function(source, "IsLevelUpEvolutionMethod")))


def requires_level(source, method):
    body = function(source, "EvolutionMethodRequiresLevelUp")
    assert "return IsLevelUpEvolutionMethod(method)" in body
    assert "IsFriendshipEvolutionMethod(method)" in body
    friendship = set(re.findall(r"case (EVO_[A-Z_]+):", function(source, "IsFriendshipEvolutionMethod")))
    explicit = set(re.findall(r"method == (EVO_[A-Z_]+)", body))
    return method in level_methods(source) | friendship | explicit


def anchor_bytes(self_address, consumer):
    source = read("assembly/data/evolution_friendship_anchor.s")
    source = source.split("gEvolutionFriendshipContract:", 1)[1]
    output = bytearray()
    for line in source.splitlines():
        line = line.split("@", 1)[0].strip()
        if line.startswith(".ascii "):
            output.extend(ast.literal_eval(line[7:]).encode("ascii"))
        elif line.startswith((".word ", ".hword ", ".byte ")):
            directive, value = line.split()
            value = {"gEvolutionFriendshipContract": self_address,
                     "GetEvolutionTargetSpecies": consumer}.get(value, value)
            size = {".word": 4, ".hword": 2, ".byte": 1}[directive]
            output.extend(int(value).to_bytes(size, "little"))
    return bytes(output)


def actual_hook(consumer):
    """Run ONLY the existing Hook function on a new BytesIO, never its main."""
    tree = ast.parse(read("scripts/insert.py"))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "Hook")
    namespace = {"_io": io}
    exec(compile(ast.Module(body=[node], type_ignores=[]), "<public-Hook-fixture>", "exec"), namespace)
    memory = io.BytesIO()
    namespace["Hook"](memory, (consumer & ~1) - 0x08000000, 0x42EC4, 3)
    return memory.getvalue()[0x42EC4:0x42ECC]


def locate(image, hook, owned_ranges):
    """MODEL of future revision-bound preflight on a small synthetic segment.

    owned_ranges must come from separately accepted candidate output ownership,
    including the live consumer. Signature alone never authorizes a write.
    """
    if len(hook) != 8 or hook[:4] != bytes.fromhex("004b1847"):
        raise ValueError("wrong live evolution hook")
    consumer = int.from_bytes(hook[4:], "little")
    if not consumer & 1 or not ORIGIN <= consumer - 1 < ORIGIN + len(image):
        raise ValueError("consumer outside accepted output")
    if not any(start <= consumer - 1 < end for start, end in owned_ranges):
        raise ValueError("missing accepted consumer ownership")
    matches = [i for i in range(len(image)) if image.startswith(MAGIC, i)]
    if len(matches) != 1:
        raise ValueError("missing/ambiguous record")
    offset = matches[0]
    if offset % 4 or offset + RECORD.size > len(image):
        raise ValueError("alignment/bounds")
    fields = RECORD.unpack_from(image, offset)
    if fields[:3] != (MAGIC, ORIGIN + offset, consumer):
        raise ValueError("self/consumer anchor mismatch")
    if fields[3:9] != (1, 32, 28, 1, 220, 160) or fields[10:] != (0, 0):
        raise ValueError("invalid version/layout/identity")
    if fields[9] not in (220, 160):
        raise ValueError("invalid threshold")
    if any(ORIGIN + offset < end and start < ORIGIN + offset + 32 for start, end in owned_ranges):
        raise ValueError("overlap with independently owned data/code")
    return offset + 28


def patch_model(image, hook, owned_ranges, value):
    if value not in (160, 220):
        raise ValueError("unapproved value")
    offset = locate(image, hook, owned_ranges)
    result = bytearray(image)
    result[offset] = value
    return bytes(result)


class EvolutionCompatibility(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = read("src/evolution.c")
        cls.old = git(ROOT, "show", BASE + ":src/evolution.c")

    def state(self, **overrides):
        return dict(mode="EVO_MODE_NORMAL", level=25, personality=0,
                    friendship=220, coins=2999, day=True, night=False,
                    threshold=220, move_types=(18,), **overrides)

    def changed_state(self, **overrides):
        result = self.state()
        result.update(overrides)
        return result

    def fixture(self):
        image = bytearray(2048)
        consumer = ORIGIN + 0x401
        image[0x100:0x120] = anchor_bytes(ORIGIN + 0x100, consumer)
        return bytes(image), actual_hook(consumer), [(ORIGIN + 0x400, ORIGIN + 0x600),
                                                    (ORIGIN + 0x700, ORIGIN + 0x780)]

    def test_exact_dpe_enum_and_existing_abi(self):
        self.assertEqual(git(DPE, "rev-parse", "HEAD"), DPE_SHA)
        current = method_names(read("include/pokemon.h"))
        old = method_names(git(ROOT, "show", BASE + ":include/pokemon.h"))
        dpe = method_names((DPE / "include/evolution.h").read_text())
        self.assertEqual(current, dpe)
        self.assertEqual(current[:40], old)
        self.assertEqual(current[40:], list(NEW_METHODS))
        for path, text in (("include/pokemon.h", read("include/pokemon.h")),
                           ("include/evolution.h", (DPE / "include/evolution.h").read_text())):
            body = text.split("struct Evolution\n", 1)[1].split("}", 1)[0]
            self.assertEqual(re.findall(r"u16 (\w+);", body), ["method", "param", "targetSpecies", "unknown"], path)
        self.assertIn("#define EVOS_PER_MON 16", read("src/config.h"))
        self.assertIn("sizeof(struct Evolution) == 8 && EVOS_PER_MON == 16", self.source)
        self.assertIn("#define EVO_GIGANTAMAX 0xFD", read("include/pokemon.h"))
        self.assertIn("#define EVO_MEGA 0xFE", read("include/pokemon.h"))

    def test_exact_four_dpe_slots_and_target_source_tables(self):
        table = (DPE / "src/Evolution Table.c").read_text()
        slots = re.findall(r"\{(EVO_COINS|EVO_MAUSHOLD_THREE|EVO_MAUSHOLD_FOUR), (\d+), (SPECIES_\w+), (\d+)\}", table)
        self.assertEqual(slots, [("EVO_MAUSHOLD_THREE", "25", "SPECIES_MAUSHOLD", "0"),
                                 ("EVO_MAUSHOLD_FOUR", "25", "SPECIES_MAUSHOLD_FOUR", "0"),
                                 ("EVO_COINS", "2999", "SPECIES_GHOLDENGO", "0"),
                                 ("EVO_COINS", "2999", "SPECIES_GHOLDENGO", "0")])
        for species, value in (("TANDEMAUS", "0x521"), ("MAUSHOLD", "0x522"), ("MAUSHOLD_FOUR", "0x523"),
                               ("GIMMIGHOUL", "0x574"), ("GIMMIGHOUL_ROAMING", "0x575"), ("GHOLDENGO", "0x576")):
            for text in (read("include/constants/species.h"), (DPE / "include/species.h").read_text()):
                self.assertRegex(text, r"#define SPECIES_" + species + r" " + value + r"\b")
        for path in ("src/Base_Stats.c", "src/Front_Pic_Table.c", "src/Back_Pic_Table.c", "src/Icon_Table.c"):
            text = (DPE / path).read_text()
            for species in ("MAUSHOLD", "MAUSHOLD_FOUR", "GHOLDENGO"):
                self.assertIn("[SPECIES_" + species + "]", text)

    def test_legacy_consumers_unchanged_after_bounded_delta(self):
        current = function(self.source, "GetEvolutionTargetSpecies")
        for method in NEW_METHODS:
            current = re.sub(r"\s*case " + method + r":.*?break;\n", "\n", current, count=1, flags=re.S)
        current = current.replace("\n\tu8 friendshipThreshold;", "")
        current = current.replace("\n\t\tfriendshipThreshold = GetEvolutionFriendshipThreshold();", "")
        current = current.replace("friendshipThreshold", "220")
        self.assertEqual(re.sub(r"\s+", " ", current), re.sub(r"\s+", " ", function(self.old, "GetEvolutionTargetSpecies")))
        # Every other original function retains its body except the two classifiers.
        names = re.findall(r"(?:u8|u16|bool8|void) (\w+)\([^;{}]*\)\s*\{", self.old)
        for name in names:
            if name not in ("GetEvolutionTargetSpecies", "GetMinimumLevel", "EvolutionMethodRequiresLevelUp"):
                self.assertEqual(function(self.source, name), function(self.old, name), name)

    def test_coin_owner_profile_and_read_paths(self):
        config = read("src/config.h")
        self.assertRegex(config, r"(?m)^#define SAVE_BLOCK_EXPANSION\b")
        self.assertRegex(config, r"(?m)^#define MAX_COINS_DIGITS 9\b")
        self.assertIn("#define gPlayerCoins (*((u32*) 0x203B814))", read("include/new/ram_locs.h"))
        body = function(read("src/scripting.c"), "GetCoins")
        expanded = select_defines(body, {"SAVE_BLOCK_EXPANSION"})
        vanilla = select_defines(body, set())
        self.assertIn("return gPlayerCoins;", expanded)
        self.assertNotIn("gSaveBlock1->coins", expanded)
        self.assertIn("return gSaveBlock1->coins;", vanilla)
        self.assertIn("GetCoins 080D0554 0", read("hooks"))
        self.assertIn("scrB3_CheckCoins 0815FC80", read("routinepointers"))
        # Existing save parasite owns 0x203B814; no new storage is introduced.
        self.assertIn("#define SAVE_BLOCK_PARASITE 0x0203B174", read("src/save.c"))
        self.assertIn("SECTOR_DATA_SIZE - 0x450", read("src/save.c"))
        self.assertLess(0x203B814 + 4, 0x203B174 + 0xEC4)

    def test_coin_thresholds_full_width_no_deduction(self):
        row = ("EVO_COINS", 2999, 0x576, 0)
        for coins in (0, 1, 2998, 2999, 3000, 65535, 65536, 999999999, 0xFFFFFFFF):
            for level in (1, 24, 25, 100):
                for personality in (0, 1, 99, 100, 0xFFFFFFFF):
                    state = self.changed_state(coins=coins, level=level, personality=personality)
                    self.assertEqual(evaluate(self.source, [row], state), 0x576 if coins >= 2999 else 0)
                    self.assertEqual(state["coins"], coins)
        for param in (0, 1, 2999, 65535):
            for coins in (0, 1, 2998, 2999, 65534, 65535, 65536):
                self.assertEqual(evaluate(self.source, [("EVO_COINS", param, 0x576, 0)], self.changed_state(coins=coins)),
                                 0x576 if coins >= param else 0)

    def test_coin_counter_mismatch_control(self):
        body = function(read("src/scripting.c"), "GetCoins")
        for expanded in (False, True):
            selected = select_defines(body, {"SAVE_BLOCK_EXPANSION"} if expanded else set())
            owner = re.search(r"return (.*?);", selected).group(1)
            for full, legacy in ((2998, 65535), (2999, 0), (65536, 1), (0, 2999)):
                storage = {"gPlayerCoins": full, "gSaveBlock1->coins": legacy}
                state = self.changed_state(coins=storage[owner])
                result = evaluate(self.source, [("EVO_COINS", 2999, 0x576, 0)], state)
                self.assertEqual(result, 0x576 if (full if expanded else legacy) >= 2999 else 0)

    def test_maushold_level_personality_form_and_repeat(self):
        rows = [("EVO_MAUSHOLD_THREE", 25, 0x522, 0), ("EVO_MAUSHOLD_FOUR", 25, 0x523, 0)]
        for personality in (0, 1, 99, 100, 101, 200, 65536, 0xFFFFFFFF):
            for level in (1, 24, 25, 26, 100):
                expected = (0x522 if personality % 100 == 0 else 0x523) if level >= 25 else 0
                state = self.changed_state(personality=personality, level=level)
                for _ in range(3):
                    self.assertEqual(evaluate(self.source, rows, state), expected)
                    self.assertEqual(evaluate(self.source, list(reversed(rows)), state), expected)
                    self.assertEqual(state["personality"], personality)

    def test_new_methods_ignore_non_normal_modes_and_everstone(self):
        for method in NEW_METHODS:
            row = (method, 25 if method != "EVO_COINS" else 2999, 0x522, 0)
            for mode in ("EVO_MODE_TRADE", "EVO_MODE_ITEM_USE", "EVO_MODE_ITEM_CHECK", "INVALID_MODE"):
                self.assertEqual(evaluate(self.source, [row], self.changed_state(mode=mode)), 0)
            self.assertEqual(evaluate(self.source, [row], self.changed_state(everstone=True)), 0)
        body = function(self.source, "GetEvolutionTargetSpecies")
        self.assertIn("holdEffect == ITEM_EFFECT_PREVENT_EVOLVE && type != 3", body)
        self.assertTrue(all(method not in body.split("case EVO_MODE_TRADE:", 1)[1] for method in NEW_METHODS))

    def test_helpers_do_not_treat_coins_as_level(self):
        levels = level_methods(self.source)
        self.assertNotIn("EVO_COINS", levels)
        self.assertEqual(levels, level_methods(self.old))
        for method in NEW_METHODS:
            self.assertTrue(requires_level(self.source, method))
        for method in method_names(read("include/pokemon.h"))[:40]:
            self.assertEqual(requires_level(self.source, method), requires_level(self.old, method), method)
        # GetMinimumLevel's extracted classification: coin evolution adds one
        # level to its ancestor's 1, whereas Tandemaus uses its real param 25.
        for method, param, expected in (("EVO_COINS", 2999, 2), ("EVO_MAUSHOLD_THREE", 25, 25),
                                        ("EVO_MAUSHOLD_FOUR", 25, 25)):
            minimum = function(self.source, "GetMinimumLevel")
            threshold_condition = re.search(r"if \((IsLevelUpEvolutionMethod\(method\).*?)\)\s*return gEvolutionTable", minimum, re.S).group(1)
            explicit_levels = set(re.findall(r"method == (EVO_[A-Z_]+)", threshold_condition))
            modeled_minimum = param if method in levels | explicit_levels else 1 + int(requires_level(self.source, method))
            self.assertEqual(modeled_minimum, expected)
        minimum = function(self.source, "GetMinimumLevel")
        self.assertIn("if (IsLevelUpEvolutionMethod(method)", minimum)
        self.assertIn("else if (EvolutionMethodRequiresLevelUp(method))", minimum)
        self.assertIn("increase = 1;", minimum)

    def test_species_only_forced_evolution_helpers_do_not_guess_new_conditions(self):
        # Actual metadata consumers have no coin/personality predicate. Keep
        # new conditional methods out of these approximate source groupings.
        utility = read("src/util.c")
        self.assertIn("IsLevelUpEvolutionMethod(evolutions[i].method)", function(utility, "CouldHaveEvolvedViaLevelUp"))
        forced = function(utility, "EvolveSpeciesByLevel")
        self.assertNotIn("personality", forced)
        self.assertNotIn("GetCoins", forced)
        self.assertIn("level >= evolutions[i].param", forced)
        groups = level_methods(self.source)
        for name in ("IsOtherEvolutionMethod", "IsItemEvolutionMethod", "IsFriendshipEvolutionMethod"):
            groups |= set(re.findall(r"case (EVO_[A-Z_]+):", function(self.source, name)))
        self.assertTrue(set(NEW_METHODS).isdisjoint(groups))
        normalized = function(self.source, "GetMinimumLevel")
        normalized = normalized.replace("// These identity-dependent methods have real level thresholds, but\n\t\t\t\t// must not enter util.c's species-only forced-evolution grouping.\n\t\t\t\t", "")
        normalized = normalized.replace("if (IsLevelUpEvolutionMethod(method)\n\t\t\t\t|| method == EVO_MAUSHOLD_THREE || method == EVO_MAUSHOLD_FOUR)", "if (IsLevelUpEvolutionMethod(method))")
        self.assertEqual(normalized, function(self.old, "GetMinimumLevel"))

    def test_friendship_boundaries_all_four_predicates(self):
        for value in (220, 160):
            for friendship in (159, 160, 219, 220):
                for method in ("EVO_FRIENDSHIP", "EVO_FRIENDSHIP_DAY", "EVO_FRIENDSHIP_NIGHT", "EVO_MOVE_TYPE"):
                    for time in (False, True):
                        for day, night in ((True, False), (False, True), (False, False)):
                            state = self.changed_state(threshold=value, friendship=friendship, day=day, night=night)
                            row = (method, 18 if method == "EVO_MOVE_TYPE" else 0, 700, 1)
                            expected = friendship >= value
                            if method == "EVO_FRIENDSHIP_DAY":
                                expected = expected and time and day
                            if method == "EVO_FRIENDSHIP_NIGHT":
                                expected = expected and time and night
                            self.assertEqual(evaluate(self.source, [row], state, time=time), 700 if expected else 0)

    def test_sylveon_unknown_flag_and_fairy_move_requirement(self):
        for value in (220, 160):
            for friendship in (159, 160, 219, 220):
                for unknown in (0, 1, 65535):
                    for moves in ((0, 1, 2, 3), (18, 0, 0, 0), (0, 0, 0, 18)):
                        row = ("EVO_MOVE_TYPE", 18, 0x2EE, unknown)
                        state = self.changed_state(threshold=value, friendship=friendship, move_types=moves)
                        expected = (not unknown or friendship >= value) and 18 in moves
                        self.assertEqual(evaluate(self.source, [row], state), 0x2EE if expected else 0)

    def test_invalid_runtime_threshold_falls_back_to_default(self):
        for value in range(256):
            self.assertEqual(threshold(self.source, value), value if value in (160, 220) else 220)
        for value in (0, 159, 161, 219, 221, 255):
            for friendship in (159, 160, 219, 220):
                row = ("EVO_FRIENDSHIP", 0, 700, 0)
                self.assertEqual(evaluate(self.source, [row], self.changed_state(threshold=value, friendship=friendship)),
                                 700 if friendship >= 220 else 0)

    def test_anchor_encoding_and_real_consumer_coupling(self):
        record = anchor_bytes(ORIGIN + 0x100, ORIGIN + 0x401)
        self.assertEqual(len(record), 32)
        self.assertEqual(RECORD.unpack(record), (MAGIC, ORIGIN + 0x100, ORIGIN + 0x401, 1, 32, 28, 1, 220, 160, 220, 0, 0))
        header = read("include/new/evolution.h")
        self.assertIn("extern const volatile struct EvolutionFriendshipContract gEvolutionFriendshipContract;", header)
        self.assertIn("gEvolutionFriendshipContract.threshold", function(self.source, "GetEvolutionFriendshipThreshold"))
        normal = function(self.source, "GetEvolutionTargetSpecies").split("case EVO_MODE_NORMAL:", 1)[1]
        self.assertEqual(normal.count("friendshipThreshold = GetEvolutionFriendshipThreshold();"), 1)
        self.assertEqual(len(re.findall(r"friendship (?:>=|<) friendshipThreshold", normal)), 4)
        self.assertNotRegex(normal, r"friendship (?:>=|<) 220")
        self.assertIn("GetEvolutionTargetSpecies 08042EC4 3", read("hooks"))
        self.assertIn("'**/*.s': ProcessAssembly", read("scripts/build.py"))
        self.assertIn("directory = ASSEMBLY", read("scripts/build.py"))
        self.assertIn("*(.text)", read("linker.ld"))
        self.assertIn(".word GetEvolutionTargetSpecies", read("assembly/data/evolution_friendship_anchor.s"))

    def test_locator_valid_and_one_byte_atomic_write_model(self):
        image, hook, ranges = self.fixture()
        self.assertEqual(locate(image, hook, ranges), 0x11C)
        easier = patch_model(image, hook, ranges, 160)
        self.assertEqual([i for i in range(len(image)) if image[i] != easier[i]], [0x11C])
        self.assertEqual(patch_model(easier, hook, ranges, 160), easier)
        self.assertEqual(patch_model(easier, hook, ranges, 220), image)
        self.assertEqual(image[0x11C], 220)

    def test_locator_rejects_invalid_descriptor_fields_without_write(self):
        image, hook, ranges = self.fixture()
        for relative, replacement in ((0, b"X"), (8, struct.pack("<I", ORIGIN + 0x104)),
                                       (12, struct.pack("<I", ORIGIN + 0x405)),
                                       (16, b"\x02"), (18, b"\x20\x01"), (20, b"\x1d"), (22, b"\x02"),
                                       (24, b"\xa0"), (26, b"\xdc"), (28, b"\x00"), (28, b"\x9f"),
                                       (28, b"\xff"), (29, b"\x01"), (30, b"\x01")):
            broken = bytearray(image)
            broken[0x100 + relative:0x100 + relative + len(replacement)] = replacement
            before = bytes(broken)
            with self.assertRaises(ValueError):
                patch_model(broken, hook, ranges, 160)
            self.assertEqual(bytes(broken), before)

    def test_locator_rejects_hook_alignment_bounds_collision_and_overlap(self):
        image, hook, ranges = self.fixture()
        for bad_hook in (b"", bytes(8), hook[:4] + struct.pack("<I", ORIGIN + 0x400),
                          hook[:4] + struct.pack("<I", 0x08001001)):
            with self.assertRaises(ValueError):
                locate(image, bad_hook, ranges)
        for offset in (0x101, len(image) - 8):
            bad = bytearray(len(image))
            record = anchor_bytes(ORIGIN + offset, ORIGIN + 0x401)
            bad[offset:] = record[:len(image) - offset]
            with self.assertRaises(ValueError):
                locate(bad, hook, ranges)
        duplicate = bytearray(image)
        duplicate[0x200:0x220] = anchor_bytes(ORIGIN + 0x200, ORIGIN + 0x401)
        with self.assertRaises(ValueError):
            locate(duplicate, hook, ranges)
        for bad_ranges in ([], [(ORIGIN + 0x100, ORIGIN + 0x120), *ranges],
                            [(ORIGIN + 0x11C, ORIGIN + 0x180), *ranges]):
            with self.assertRaises(ValueError):
                locate(image, hook, bad_ranges)
        with self.assertRaises(ValueError):
            patch_model(image, hook, ranges, 159)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dpe-root", type=Path, required=True, help="exact public DPE source checkout")
    args, remaining = parser.parse_known_args()
    DPE = args.dpe_root.resolve()
    unittest.main(argv=[__file__, *remaining])
