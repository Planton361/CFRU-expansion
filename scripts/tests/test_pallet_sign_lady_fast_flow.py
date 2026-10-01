"""ROM-free #586 contract: only M-006 skips the Sign Lady tutorial."""
import json
from pathlib import Path
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]
BASE = '7151288c63e54f406dffe630cff091603c627c5f'
PRET = 'e060ab955b5dc9ac1c4904c2cd141683615cf477'
MOM = 'assembly/overworld_scripts/talk_to_mom.s'
BINDING = '.equ VAR_MAP_SCENE_PALLET_TOWN_SIGN_LADY, 0x4070\n'
WRITE = '    setvar VAR_MAP_SCENE_PALLET_TOWN_SIGN_LADY 1\n'
PRESERVED = (
    'assembly/overworld_scripts/Pallet_town.s',
    'assembly/overworld_scripts/shortened_oak_parcel_flow.s',
    'eventscripts', 'mapobjectoverlays',
)


def at(repo, sha, path):
    return subprocess.check_output(['git', 'show', sha + ':' + path], cwd=repo)


def contract(source, preserved):
    # The exact two-line delta also rejects numeric aliases, extra writes,
    # START_MENU spoofing, and hide/remove operations elsewhere in M-006.
    assert source.count(BINDING) == 1
    assert source.count(WRITE) == 1
    assert ('setvar VAR_MAP_SCENE_PALLET_TOWN_PROFESSOR_OAKS_LAB 2\n'
            + WRITE + '    releaseall\n    end') in source
    assert source.replace(BINDING, '').replace(WRITE, '') == at(ROOT, BASE, MOM).decode()
    for path in PRESERVED:
        assert preserved[path] == at(ROOT, BASE, path), path


class PalletSignLadyFastFlowTests(unittest.TestCase):
    def setUp(self):
        self.source = (ROOT / MOM).read_text()
        self.preserved = {p: (ROOT / p).read_bytes() for p in PRESERVED}

    def test_fast_start_only_and_existing_npc_overlay_preservation(self):
        contract(self.source, self.preserved)
        self.assertIn(b'EventScript_Pallet_Girl:', self.preserved[PRESERVED[0]])
        self.assertIn(b'npc 3 0 0 EventScript_Pallet_Girl', self.preserved['eventscripts'])
        parcel = self.preserved[PRESERVED[1]]
        self.assertNotIn(b'0x4070', parcel)
        self.assertNotIn(b'VAR_MAP_SCENE_PALLET_TOWN_SIGN_LADY', parcel)

    def test_negative_witness_missing_write(self):
        with self.assertRaises(AssertionError):
            contract(self.source.replace(WRITE, ''), self.preserved)

    def test_negative_witness_start_menu_spoof(self):
        with self.assertRaises(AssertionError):
            contract(self.source.replace(WRITE, '    setflag FLAG_OPENED_START_MENU\n'), self.preserved)

    def test_negative_witness_global_hide_remove_or_repoint(self):
        for mutation in ('    hideobject 1 3 0\n', '    removeobject 1\n'):
            with self.subTest(mutation=mutation), self.assertRaises(AssertionError):
                contract(self.source + mutation, self.preserved)
        mutations = (
            (PRESERVED[0], self.preserved[PRESERVED[0]].replace(
                b'EventScript_Pallet_Girl:', b'EventScript_RemovedGirl:')),
            ('eventscripts', self.preserved['eventscripts'].replace(
                b'npc 3 0 0 EventScript_Pallet_Girl', b'npc 3 0 0 EventScript_HideGirl')),
            ('mapobjectoverlays', self.preserved['mapobjectoverlays'] +
                b'\nreplace_script 3 0 0 EventScript_HideGirl\n'),
        )
        for path, content in mutations:
            altered = dict(self.preserved)
            altered[path] = content
            with self.subTest(path=path), self.assertRaises(AssertionError):
                contract(self.source, altered)

    def test_public_vanilla_lifecycle(self):
        candidates = []
        for parent in ROOT.parents:
            candidates.extend((parent / 'references/pret-pokefirered',
                               parent / '02_external/references/pret-pokefirered'))
            if any(p.is_dir() for p in candidates):
                break
            if parent != parent.parent:
                candidates.extend(parent.glob('*/02_external/references/pret-pokefirered'))
        repo = next((p for p in candidates if p.is_dir()), None)
        self.assertIsNotNone(repo, 'Pinned public pret source reference required')
        read = lambda path: at(repo, PRET, path).decode()
        town = json.loads(read('data/maps/PalletTown/map.json'))
        lady = town['object_events'][0]
        self.assertEqual((lady['local_id'], lady['x'], lady['y'], lady['flag']),
                         ('LOCALID_PALLET_SIGN_LADY', 3, 10, '0'))
        self.assertTrue(any(e['x'] == 13 and e['y'] == 2 and
                            e['script'] == 'PalletTown_EventScript_SignLadyTrigger'
                            for e in town['coord_events']))
        self.assertRegex(read('include/constants/flags.h'),
                         r'FLAG_PALLET_LADY_NOT_BLOCKING_SIGN\s+0x291')
        self.assertRegex(read('include/constants/vars.h'),
                         r'VAR_MAP_SCENE_PALLET_TOWN_SIGN_LADY\s+0x4070')
        lab = read('data/maps/PalletTown_ProfessorOaksLab/scripts.inc')
        self.assertIn('setflag FLAG_PALLET_LADY_NOT_BLOCKING_SIGN', lab)
        helper = lab.split('PalletTown_ProfessorOaksLab_EventScript_ReadyEndSignLadyScene::', 1)[1]
        self.assertRegex(helper, r'^\s*setvar VAR_MAP_SCENE_PALLET_TOWN_SIGN_LADY, 1\s+return')
        scripts = read('data/maps/PalletTown/scripts.inc')
        self.assertIn('call_if_eq VAR_MAP_SCENE_PALLET_TOWN_SIGN_LADY, 0,', scripts)
        self.assertIn('call_if_eq VAR_MAP_SCENE_PALLET_TOWN_SIGN_LADY, 1,', scripts)
        self.assertIn('setvar VAR_MAP_SCENE_PALLET_TOWN_SIGN_LADY, 2', scripts)
        self.assertRegex(scripts, r'setobjectxyperm LOCALID_PALLET_SIGN_LADY, 12, 2')
        self.assertNotRegex(lab + scripts, r'setvar VAR_MAP_SCENE_PALLET_TOWN_SIGN_LADY, 0\b')


if __name__ == '__main__':
    unittest.main()
