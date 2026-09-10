#!/usr/bin/env python3
"""M-011 source-only contract and production C host tests; no ROM access."""
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]

def main():
    source = (ROOT / 'src/hospitality.c').read_text()
    start = (ROOT / 'src/battle_start_turn_start.c').read_text()
    switch = (ROOT / 'src/switching.c').read_text()
    effects = (ROOT / 'src/ability_battle_effects.c').read_text()
    script = (ROOT / 'assembly/battle_scripts/ability_battle_scripts.s').read_text().split('BattleScript_Hospitality:')[1]
    # Dedicated entry phases preserve normal ordering and advance before yielding.
    assert start.index('case BTSTART_SWITCH_IN_ABILITIES:') < start.index('case BTSTART_HOSPITALITY:') < start.index('case BTSTART_SWITCH_IN_ITEMS:')
    start_phase = start.split('case BTSTART_HOSPITALITY:')[1].split('case BTSTART_SWITCH_IN_ITEMS:')[0]
    phase = start_phase
    assert phase.index('(*bank)++') < phase.index('TryActivateHospitality(')
    assert switch.index('case SwitchIn_Abilities:') < switch.index('case SwitchIn_Hospitality:') < switch.index('case SwitchIn_Items:')
    switch_phase = switch.split('case SwitchIn_Hospitality:')[1].split('case SwitchIn_Items:')[0]
    phase = switch_phase
    assert phase.index('++gNewBS->switchInEffectsState') < phase.index('TryActivateHospitality(')
    callers = [p.name for p in (ROOT / 'src').glob('*.c') if p.name != 'hospitality.c' and 'TryActivateHospitality(' in p.read_text()]
    assert sorted(callers) == ['battle_start_turn_start.c', 'switching.c'], callers
    assert 'case ABILITY_HEALER:\n\t\t\t\t\tif (!SpeciesHasHospitality(SPECIES(bank))' in effects
    assert 'graphicalhpupdate BANK_TARGET' in script and 'datahpupdate BANK_TARGET' in script
    assert 'datahpupdate BANK_SCRIPTING' not in script
    assert '#define ABILITY_HOSPITALITY ABILITY_HEALER' in (ROOT / 'include/constants/abilities.h').read_text()
    for path, current, first, last in [
        ('src/battle_start_turn_start.c', start, 'BTSTART_SWITCH_IN_ABILITIES', 'BTSTART_SWITCH_IN_ITEMS'),
        ('src/switching.c', switch, 'SwitchIn_Abilities', 'SwitchIn_Items'),
    ]:
        baseline = subprocess.check_output(['git', 'show', '827fa1ef04bd43e5c6bad5c47f7d8690ea6823ec:' + path], cwd=ROOT, text=True)
        original = baseline.split('case ' + first + ':')[1].split('case ' + last + ':')[0].strip()
        added = 'BTSTART_HOSPITALITY' if path.endswith('battle_start_turn_start.c') else 'SwitchIn_Hospitality'
        retained = current.split('case ' + first + ':')[1].split('case ' + added + ':')[0].strip()
        assert retained == original, path + ': ordinary ability phase changed'
    print('M-011 entry-only call sites, once-per-entry cursors, ordering, ally script and Healer separation PASS')
    with tempfile.TemporaryDirectory(prefix='m011-host-') as tmp:
        tmp = Path(tmp)
        (tmp / 'hospitality_impl.c').write_text(re.sub(r'^#include .*\n', '', source, flags=re.M))
        (tmp / 'hospitality_entry_impl.c').write_text(
            'static void runStart(void) { u8 *bank = &startBank, *state = &startState; switch (*state) { case 0: ' + start_phase + 'case 1: break; }}\n'
            + 'static void runSwitch(void) { switch (gNewBS->switchInEffectsState) { case 0: ' + switch_phase + 'case 1: break; }}\n')
        exe = tmp / 'hospitality-test'
        subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-fsanitize=undefined,bounds',
                        '-I', str(tmp), str(ROOT / 'scripts/tests/m011_hospitality_host.c'), '-o', str(exe)], check=True)
        subprocess.run([str(exe)], check=True)

if __name__ == '__main__':
    main()
