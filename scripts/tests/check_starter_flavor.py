"""#595: source-only BPRE starter binding/lifecycle guard; no game artifacts."""
import argparse
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
BASE = '20b58bd980f55d57faf78ff29922b98874a4df22'
PRET = 'e060ab955b5dc9ac1c4904c2cd141683615cf477'
HISTORY = '44c9109c2a04fbbf01268f53f0f4a57174563fb1'
LAB = 'data/maps/PalletTown_ProfessorOaksLab/scripts.inc'
PREFIX = 'PalletTown_ProfessorOaksLab_EventScript_'
SCRIPT = 'assembly/overworld_scripts/starter_flavor.s'
ALLOWED = {SCRIPT, 'repoints', 'scripts/tests/check_starter_flavor.py',
           'docs/starter-flavor.md'}
ROWS = ('\n## #595: only the three BPRE starter-confirmation YES pointers.\n'
        'EventScript_ChoseStarterNoFlavor 08169C23\n'
        'EventScript_ChoseStarterNoFlavor 08169C42\n'
        'EventScript_ChoseStarterNoFlavor 08169C61\n')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def git(repo, *args):
    return subprocess.check_output(['git', *args], cwd=repo, text=True)


def block(source, label):
    match = re.search(r'^' + re.escape(label) + r'::?[^\n]*\n(.*?)(?=^\w+::?|\Z)',
                      source, re.M | re.S)
    require(match is not None, 'Missing script: ' + label)
    return [line.split('@')[0].strip() for line in match[1].splitlines()
            if line.split('@')[0].strip()]


def macro(source, name):
    match = re.search(r'\.macro ' + name + r'(?:[ \t][^\n]*)?\n(.*?)\.endm', source, re.S)
    require(match is not None, 'Missing macro: ' + name)
    return [line.strip() for line in match[1].splitlines() if line.strip()]


def contract(source, repoints):
    require(repoints == git(ROOT, 'show', BASE + ':repoints') + ROWS,
            'Repoint binding drift')
    # Accept comments only; reject extra directives, aliases or commands.
    lines = [line.split('@')[0].strip() for line in source.splitlines()
             if line.split('@')[0].strip()]
    require(lines == [
        '.align 2', '.thumb', '.include "../xse_commands.s"',
        '.include "../xse_defines.s"',
        '.equ ChoseStarter_RestoreAndAward, 0x08169C80',
        '.global EventScript_ChoseStarterNoFlavor', 'EventScript_ChoseStarterNoFlavor:',
        'erasemonpic', 'removeobject LASTTALKED', 'goto ChoseStarter_RestoreAndAward'],
        'Replacement script/continuation drift')


def prove_reference(pret):
    require(git(pret, 'rev-parse', PRET + '^{commit}').strip() == PRET, 'pret pin')
    require(git(pret, 'merge-base', HISTORY, PRET).strip() == HISTORY, 'pret ancestry')
    old = git(pret, 'show', HISTORY + ':' + LAB)
    lab = git(pret, 'show', PRET + ':' + LAB)
    macros = git(pret, 'show', HISTORY + ':asm/macros/event.inc')
    expected_macros = {
        'loadword': ['.byte 0x0f', '.byte \\destination', '.4byte \\value'],
        'callstd': ['.byte 0x09', '.byte \\function'],
        'msgbox': ['loadword 0, \\text', 'callstd \\type'],
        'compare_var_to_value': ['.byte 0x21', '.2byte \\var', '.2byte \\value'],
        'goto_if': ['.byte 0x06', '.byte \\condition', '.4byte \\destination'],
        'goto_if_eq': ['goto_if 1, \\dest'],
        'erasemonpic': ['.byte 0x76'],
    }
    for name, expected in expected_macros.items():
        require(macro(macros, name) == expected, 'Historical command width: ' + name)
    require(macro(macros, 'removeobject')[:3] ==
            ['.ifb \\mapGroup', '.byte 0x53', '.2byte \\localId'], 'removeobject width')
    require('compare_var_to_value \\var, \\arg' in macro(macros, 'compare'), 'compare width')
    # Widths from the verified macro bodies, not another ROM layout:
    # msgbox = loadword(6)+callstd(2); compare(5); goto_if header(2)+pointer(4).
    for start, slot in [(0x08169C14, 0x08169C23), (0x08169C33, 0x08169C42),
                        (0x08169C52, 0x08169C61)]:
        match = re.search(r'^(\w+):: @ ' + f'{start:X}' + r'\n', old, re.M)
        require(match is not None, 'Historical confirmation address')
        commands = block(old, match[1])
        require(commands[0].endswith(', MSGBOX_YESNO') and commands[0].startswith('msgbox '),
                'Historical confirmation prompt')
        require(commands[1:] == ['compare VAR_RESULT, YES', 'goto_if_eq ' + PREFIX + 'ChoseStarter',
                'compare VAR_RESULT, NO', 'goto_if_eq ' + PREFIX + 'DeclinedStarter', 'end'],
                'Historical YES/NO owner')
        require(start + 6 + 2 + 5 + 2 == slot, 'YES operand position')
    require(PREFIX + 'ChoseStarter:: @ 8169C74' in old, 'ChoseStarter entry')
    require(block(old, PREFIX + 'ChoseStarter')[:4] == [
        'erasemonpic', 'removeobject VAR_LAST_TALKED',
        'msgbox PalletTown_ProfessorOaksLab_Text_OakThisMonIsEnergetic',
        'call EventScript_1A6675'], 'Historical prefix/tail')
    require(0x08169C74 + 1 + 3 + 6 + 2 == 0x08169C80, 'Restore tail address')
    for num, choice, rival in [(0, 'Bulbasaur', 'Charmander'), (1, 'Squirtle', 'Bulbasaur'),
                               (2, 'Charmander', 'Squirtle')]:
        ball = block(lab, PREFIX + choice + 'Ball')
        for command in ['setvar PLAYER_STARTER_NUM, ' + str(num),
                        'setvar PLAYER_STARTER_SPECIES, SPECIES_' + choice.upper(),
                        'setvar RIVAL_STARTER_SPECIES, SPECIES_' + rival.upper(),
                        'setvar RIVAL_STARTER_ID, LOCALID_' + rival.upper() + '_BALL',
                        'goto_if_eq VAR_MAP_SCENE_PALLET_TOWN_PROFESSOR_OAKS_LAB, 2, '
                        + PREFIX + 'ConfirmStarterChoice']:
            require(command in ball, 'Choice ownership: ' + command)
        require('goto_if_eq PLAYER_STARTER_NUM, ' + str(num) + ', ' + PREFIX + 'Confirm' + choice
                in block(lab, PREFIX + 'ConfirmStarterChoice'), 'Confirmation dispatch')
        require(block(lab, PREFIX + 'Confirm' + choice) == [
            'msgbox PalletTown_ProfessorOaksLab_Text_OakChoosing' + choice + ', MSGBOX_YESNO',
            'goto_if_eq VAR_RESULT, YES, ' + PREFIX + 'ChoseStarter',
            'goto_if_eq VAR_RESULT, NO, ' + PREFIX + 'DeclinedStarter', 'end'], 'YES/NO convergence')
        require('goto_if_eq PLAYER_STARTER_NUM, ' + str(num) + ', ' + PREFIX + 'RivalWalksTo' + rival
                in block(lab, PREFIX + 'RivalPicksStarter'), 'Rival counter-starter mapping')
        require('goto ' + PREFIX + 'RivalTakesStarter' in block(lab, PREFIX + 'RivalWalksTo' + rival),
                'Rival continuation')
    require(block(lab, PREFIX + 'DeclinedStarter') == ['hidemonpic', 'release', 'end'], 'NO retry')
    require(block(lab, PREFIX + 'ChoseStarter') == [
        'hidemonpic', 'removeobject VAR_LAST_TALKED',
        'msgbox PalletTown_ProfessorOaksLab_Text_OakThisMonIsEnergetic',
        'call EventScript_RestorePrevTextColor', 'setflag FLAG_SYS_POKEMON_GET',
        'setflag FLAG_PALLET_LADY_NOT_BLOCKING_SIGN', 'givemon PLAYER_STARTER_SPECIES, 5',
        'copyvar VAR_STARTER_MON, PLAYER_STARTER_NUM', 'bufferspeciesname STR_VAR_1, PLAYER_STARTER_SPECIES',
        'message PalletTown_ProfessorOaksLab_Text_ReceivedMonFromOak', 'waitmessage',
        'playfanfare MUS_OBTAIN_KEY_ITEM', 'waitfanfare', 'msgbox Text_GiveNicknameToThisMon, MSGBOX_YESNO',
        'goto_if_eq VAR_RESULT, YES, EventScript_GiveNicknameToStarter',
        'goto_if_eq VAR_RESULT, NO, ' + PREFIX + 'RivalPicksStarter', 'end'], 'Retained award/nickname tail')
    require(block(lab, 'EventScript_GiveNicknameToStarter') == ['setvar VAR_0x8004, 0',
        'call EventScript_ChangePokemonNickname', 'goto ' + PREFIX + 'RivalPicksStarter', 'end'], 'Nickname YES')
    takes = block(lab, PREFIX + 'RivalTakesStarter')
    require(takes[-4:] == ['setvar VAR_MAP_SCENE_PALLET_TOWN_PROFESSOR_OAKS_LAB, 3',
        'call_if_set FLAG_OPENED_START_MENU, ' + PREFIX + 'ReadyEndSignLadyScene', 'release', 'end'],
        'Scene 3 / Sign Lady state')
    require(block(lab, PREFIX + 'ReadyEndSignLadyScene') ==
            ['setvar VAR_MAP_SCENE_PALLET_TOWN_SIGN_LADY, 1', 'return'], 'Sign Lady continuation')
    battle = block(lab, PREFIX + 'RivalBattle')
    for num, rival in [(0, 'Charmander'), (1, 'Bulbasaur'), (2, 'Squirtle')]:
        require('goto_if_eq VAR_STARTER_MON, ' + str(num) + ', ' + PREFIX
                + 'RivalApproachForBattle' + rival in battle, 'Retained Rival battle mapping')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pret-root', type=Path, required=True)
    args = parser.parse_args()
    require(git(ROOT, 'merge-base', BASE, 'HEAD').strip() == BASE, 'Exact CFRU base')
    changed = set(git(ROOT, 'diff', BASE, '--name-only').splitlines())
    changed.update(git(ROOT, 'ls-files', '--others', '--exclude-standard').splitlines())
    require(changed <= ALLOWED, 'Out-of-scope paths: ' + str(changed - ALLOWED))
    # The accepted base has no competing source-manifest patch in the starter
    # selection/award/nickname/Rival region. Existing map overlays remain exact
    # through the scope gate above (M-006 owns scene 1, not starter ball scripts).
    for path in ['repoints', 'repointall', 'hooks', 'routinepointers',
                 'functionrewrites', 'bytereplacement', 'eventscripts', 'mapobjectoverlays']:
        for line in git(ROOT, 'show', BASE + ':' + path).splitlines():
            if line.strip().startswith('#'):
                continue
            for token in re.findall(r'\b(?:0x)?0?8[0-9a-fA-F]{6}\b', line):
                require(not 0x08169BAB <= int(token, 16) < 0x08169DF0,
                        'Competing starter manifest owner: ' + path)
    source = (ROOT / SCRIPT).read_text()
    repoints = (ROOT / 'repoints').read_text()
    contract(source, repoints)
    prove_reference(args.pret_root.resolve())
    # CFRU dispatches scripts with the same bytecode, with no Thumb pointer bit.
    commands = (ROOT / 'xse_commands.s').read_text()
    require(macro(commands, 'goto') == ['.byte 0x05', '.4byte \\destination'], 'CFRU goto')
    require(macro(commands, 'erasemonpic') == ['hidepokepic'], 'CFRU hide alias')
    require(macro(commands, 'hidepokepic') == ['.byte 0x76'], 'CFRU hide opcode')
    require(macro(commands, 'removeobject')[:3] ==
            ['.ifb \\mapGroup', '.byte 0x53', '.2byte \\localId'], 'CFRU remove opcode')
    require('.equ LASTTALKED, 0x800F' in (ROOT / 'xse_defines.s').read_text(), 'Selected ball variable')
    # Mutation witnesses are in memory only: drift must fail even under python -O.
    mutations = [(source.replace('0x08169C80', '0x08169C81'), repoints),
                 (source + '\n    givemon 1 5\n', repoints),
                 (source.replace('removeobject LASTTALKED', 'removeobject 5'), repoints)]
    for slot in ['08169C23', '08169C42', '08169C61']:
        mutations.append((source, repoints.replace(slot, f'{int(slot, 16) + 1:08X}')))
        mutations.append((source, repoints.replace('EventScript_ChoseStarterNoFlavor ' + slot + '\n', '')))
    for altered_source, altered_repoints in mutations:
        try:
            contract(altered_source, altered_repoints)
        except ValueError:
            continue
        raise ValueError('Negative binding witness unexpectedly passed')
    print('PASS: exact base, BPRE owner/three YES slots, NO retry, award/VAR_STARTER_MON')
    print('PASS: nickname YES/NO, Rival mapping, scene 3/Sign Lady; original tail retained')
    print('PASS: 9 fail-closed mutation witnesses; bounded diff, no fixed species/SaveBlock/layout changes')
    print('SOURCE ONLY: runtime, Rival battle and Lab exit/Parcel acceptance remain user-owned')


if __name__ == '__main__':
    main()
