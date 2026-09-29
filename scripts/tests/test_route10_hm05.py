#!/usr/bin/env python3
"""ROM-free Route 10 HM05 source and exact MapEvents append checks."""

import io
from contextlib import redirect_stdout
import json
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import insert


def reference_root(name):
    for parent in ROOT.parents:
        candidates = (parent / "references" / name,
                      parent / "02_external" / "references" / name)
        for candidate in (*candidates, *parent.glob("*/02_external/references/" + name)):
            if candidate.is_dir():
                return candidate
    raise AssertionError("Pinned public source reference is unavailable: " + name)


def write_pointer(data, offset, target):
    data[offset:offset + 4] = (target + 0x08000000).to_bytes(4, "little")


class Route10HM05Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        overlay = (ROOT / "mapobjectoverlays").read_text()
        rows = [line.split() for line in overlay.splitlines()
                if line.startswith("append_object_exact ")]
        assert len(rows) == 1, rows
        cls.row = rows[0]
        cls.script = (ROOT / "assembly/overworld_scripts/route10_hm05.s").read_text()
        cls.pret = reference_root("pret-pokefirered")
        cls.natdex = reference_root("cyansmp64-pokefirered-natdex")

    def fixture(self, counts=(10, 5, 0, 8), object_pointer=0x1400):
        data = bytearray(b"\xff" * 0x60000)
        write_pointer(data, insert.MAP_BANKS_HEADER_POINTER, 0x1000)
        write_pointer(data, 0x1000 + 3 * 4, 0x1100)
        write_pointer(data, 0x1100 + 28 * 4, 0x1200)
        write_pointer(data, 0x1200 + insert.MAP_HEADER_EVENTS_OFFSET, 0x1300)
        data[0x1300:0x1314] = insert.BuildMapEvents(
            *counts, object_pointer + 0x08000000 if object_pointer is not None else 0,
            0x08001500, 0, 0x08001600)
        objects = b"".join(insert.BuildEventObjectTemplate(
            local_id, 0x20 + local_id, local_id, 20 + local_id, 3, 1, 1, 1,
            0, 0, 0x08002000, 0, 0) for local_id in range(1, 11))
        data[0x1400:0x1400 + len(objects)] = objects
        data[0x1500:0x1500 + 5 * 8] = bytes(range(5 * 8))
        data[0x1600:0x1600 + 8 * 12] = bytes(range(8 * 12))
        data[0x2000] = 0x02  # synthetic script target; no source ROM used
        # An unrelated map stands in for Route 2 and must remain byte-identical.
        write_pointer(data, 0x1000 + 15 * 4, 0x1700)
        write_pointer(data, 0x1700 + 2 * 4, 0x1800)
        data[0x1800:0x1820] = bytes(range(32))
        data[0x1900:0x1920] = bytes(range(32, 64))
        return io.BytesIO(data)

    def run_overlay(self, fixture):
        includes = [line for line in (ROOT / "mapobjectoverlays").read_text().splitlines()
                    if line.startswith("#include ")]
        with tempfile.TemporaryDirectory(prefix="route10-exact-overlay-") as directory:
            path = Path(directory) / "overlay"
            path.write_text("\n".join(includes + [" ".join(self.row)]) + "\n")
            return insert.InsertMapObjectOverlays(
                fixture, {"EventScript_Route10HM05": 0x2000}, 0x3000, str(path))

    def test_source_identity_and_counts(self):
        pret_map = json.loads((self.pret / "data/maps/Route10/map.json").read_text())
        groups = json.loads((self.pret / "data/maps/map_groups.json").read_text())
        self.assertEqual(pret_map["id"], "MAP_ROUTE10")
        self.assertEqual(groups["group_order"][3], "gMapGroup_TownsAndRoutes")
        self.assertEqual(groups["gMapGroup_TownsAndRoutes"][28], "Route10")
        self.assertEqual(tuple(len(pret_map[key]) for key in
                               ("object_events", "warp_events", "coord_events", "bg_events")),
                         (10, 5, 0, 8))
        self.assertEqual(self.row[1:7], ["3", "28", "10", "5", "0", "8"])
        self.assertEqual(self.row[7:17], ["11", "0x38", "17", "22", "0",
                                          "MOVEMENT_TYPE_FACE_LEFT", "0", "0", "0", "0"])
        self.assertEqual(self.row[17:], ["EventScript_Route10HM05", "FLAG_GOT_HM05", "0"])
        self.assertEqual(int(re.search(r"OBJ_EVENT_GFX_HIKER\s+(\d+)",
                                      (self.pret / "include/constants/event_objects.h").read_text()).group(1)),
                         0x38)
        pinned_map = json.loads(subprocess.check_output([
            "git", "show", "b84ca974fb33bd5ee69f1e3597d44e8f7d4e3fc7:data/maps/Route10/map.json"],
            cwd=self.natdex, text=True))
        self.assertEqual(tuple(len(pinned_map[key]) for key in
                               ("object_events", "warp_events", "coord_events", "bg_events")),
                         (11, 5, 0, 8))
        hiker = pinned_map["object_events"][-1]
        self.assertEqual((hiker["graphics_id"], hiker["x"], hiker["y"],
                          hiker["trainer_type"], hiker["flag"]),
                         ("OBJ_EVENT_GFX_HIKER", 17, 22, "TRAINER_TYPE_NONE", "FLAG_GOT_HM05"))
        pinned_script = subprocess.check_output([
            "git", "show", "b84ca974fb33bd5ee69f1e3597d44e8f7d4e3fc7:data/maps/Route10/scripts.inc"],
            cwd=self.natdex, text=True)
        self.assertIn("giveitem ITEM_HM05\n\tsetflag FLAG_GOT_HM05", pinned_script)
        self.assertIn("removeobject 11", pinned_script)

    def test_exact_append_preserves_source_and_other_map(self):
        fixture = self.fixture()
        before = fixture.getvalue()
        end = self.run_overlay(fixture)
        after = fixture.getvalue()
        self.assertEqual(end, 0x3000 + 11 * 24 + 20)
        new_header = insert.ReadPointer(fixture, 0x1204) - 0x08000000
        self.assertEqual(new_header, 0x3000 + 11 * 24)
        self.assertEqual(after[0x1300:0x1314], before[0x1300:0x1314])
        self.assertEqual(after[0x1400:0x14F0], before[0x1400:0x14F0])
        self.assertEqual(after[0x1500:0x1528], before[0x1500:0x1528])
        self.assertEqual(after[0x1600:0x1660], before[0x1600:0x1660])
        self.assertEqual(after[0x1700:0x1920], before[0x1700:0x1920])
        self.assertEqual(after[0x3000:0x30F0], before[0x1400:0x14F0])
        self.assertEqual(len(after[0x30F0:new_header]), 24)
        added = insert.ReadEventObjectTemplate(after[0x30F0:new_header])
        self.assertEqual((added["localId"], added["graphicsId"], added["x"], added["y"],
                          added["elevation"], added["trainerType"], added["flagId"]),
                         (11, 0x38, 17, 22, 0, 0, 0x23B))
        self.assertEqual(added["scriptPointer"], 0x08002000)
        self.assertEqual(tuple(after[new_header:new_header + 4]), (11, 5, 0, 8))
        self.assertEqual(after[new_header + 8:new_header + 20], before[0x1308:0x1314])
        self.assertEqual(after[0x1200:0x1204], before[0x1200:0x1204])
        self.assertEqual(after[0x1208:0x121C], before[0x1208:0x121C])

    def test_each_wrong_count_fails_before_any_write(self):
        for index in range(4):
            counts = [10, 5, 0, 8]
            counts[index] += 1
            fixture = self.fixture(tuple(counts))
            before = fixture.getvalue()
            with self.subTest(index=index), redirect_stdout(io.StringIO()), self.assertRaises(SystemExit):
                self.run_overlay(fixture)
            self.assertEqual(fixture.getvalue(), before)

    def test_invalid_or_truncated_object_table_fails_before_any_write(self):
        for pointer in (None, 0x5FFF0, 0x1401):
            fixture = self.fixture(object_pointer=pointer)
            before = fixture.getvalue()
            with self.subTest(pointer=pointer), redirect_stdout(io.StringIO()), self.assertRaises(SystemExit):
                self.run_overlay(fixture)
            self.assertEqual(fixture.getvalue(), before)

    def test_invalid_preserved_pointers_fail_before_any_write(self):
        for field, value in ((8, 0), (12, 0x07FF), (16, 0x1400)):
            fixture = self.fixture()
            fixture.seek(0x1300 + field)
            fixture.write(value.to_bytes(4, "little"))
            before = fixture.getvalue()
            with self.subTest(field=field), redirect_stdout(io.StringIO()), self.assertRaises(SystemExit):
                self.run_overlay(fixture)
            self.assertEqual(fixture.getvalue(), before)

    def test_script_awards_once_and_route2_source_is_untouched(self):
        code = "\n".join(line.split("@", 1)[0].strip() for line in self.script.splitlines())
        self.assertEqual(re.findall(r"(?m)^obtainitem ITEM_HM05 1$", code),
                         ["obtainitem ITEM_HM05 1"])
        self.assertEqual(re.findall(r"(?m)^setflag FLAG_GOT_HM05$", code),
                         ["setflag FLAG_GOT_HM05"])
        self.assertIn("checkflag FLAG_GOT_HM05\nif TRUE _goto EventScript_Route10HM05Done", code)
        self.assertLess(code.index("checkitemspace ITEM_HM05 1"), code.index("obtainitem ITEM_HM05 1"))
        self.assertLess(code.index("obtainitem ITEM_HM05 1"), code.index("setflag FLAG_GOT_HM05"))
        self.assertIn("removeobject LOCALID_ROUTE10_HIKER", code)
        self.assertEqual(re.findall(r"(?m)^\.equ ITEM_HM05, (\d+)$", code), ["343"])
        self.assertEqual(re.findall(r"(?m)^\.equ FLAG_GOT_HM05, (0x[0-9A-Fa-f]+)$", code),
                         ["0x23B"])
        route2 = (self.pret / "data/maps/Route2_EastBuilding/scripts.inc").read_text()
        self.assertIn("giveitem_msg Route2_EastBuilding_Text_ReceivedHM05FromAide, ITEM_HM05", route2)
        self.assertIn("setflag FLAG_GOT_HM05", route2)
        changed = set(subprocess.check_output(
            ["git", "diff", "--name-only", "818f65090b1af2b60287f9dbc60302c2b27ac404", "--"],
            cwd=ROOT, text=True).splitlines())
        changed |= set(subprocess.check_output(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=ROOT, text=True).splitlines())
        self.assertEqual(changed, {"mapobjectoverlays", "scripts/insert.py",
                                   "assembly/overworld_scripts/route10_hm05.s",
                                   "strings/Scripts/route10_hm05.string",
                                   "scripts/tests/test_route10_hm05.py"})


if __name__ == "__main__":
    unittest.main()
