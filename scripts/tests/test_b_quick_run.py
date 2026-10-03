#!/usr/bin/env python3
"""ROM-free production action-menu witnesses for Workspace #603."""
from pathlib import Path
import re
import subprocess
import tempfile
from audit_early_running_lifecycle import c_function

ROOT = Path(__file__).resolve().parents[2]
BASE = 'fe61d5473c015db71f5f4c5a3335a4a67f943254'
ACCEPTED_D22 = '41ac6081ccf27170f361c4ed7d50ad546817c2cb'


def baseline(name):
    return subprocess.check_output(['git', 'show', f'{BASE}:{name}'], cwd=ROOT, text=True)


def provenance_witnesses(constants):
    # Pin the source/address chain; never infer an address from an adjacent owner.
    pret = ROOT.parent / 'references/pret-pokefirered'
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=pret, text=True).strip() == 'e060ab955b5dc9ac1c4904c2cd141683615cf477'
    asm = subprocess.check_output(['git', 'show', '2822d29c0bd7e579388f9d0772a7b5d1af430b31:asm/scrcmd.s'], cwd=pret, text=True)
    assert 'ScrCmd_dowildbattle: @ 806C39C' in asm
    command_asm = asm.split('ScrCmd_dowildbattle: @ 806C39C', 1)[1].split('thumb_func_end ScrCmd_dowildbattle', 1)[0]
    assert '\tbl sub_807F8C4' in command_asm and '\tbl ScriptContext1_Stop' in command_asm
    assert 'ScrCmd_pokemart: @ 806C3AC' in asm  # command span = 16 bytes
    start_asm = subprocess.check_output(['git', 'show', 'e48725d9b54ed9f71f65c3ba5577cffa8f4887d1:asm/battle_setup.s'], cwd=pret, text=True)
    assert 'BattleSetup_StartScriptedWildBattle: @ 807F8C4' in start_asm
    for revision in ('2822d29c0bd7e579388f9d0772a7b5d1af430b31', 'e48725d9b54ed9f71f65c3ba5577cffa8f4887d1'):
        subprocess.run(['git', 'merge-base', '--is-ancestor', revision, 'HEAD'], cwd=pret, check=True)
    assert 'ScrCmd_dowildbattle 806C39C 1' in (ROOT / 'hooks').read_text()
    # Execute only the source Hook emitter on an in-memory synthetic buffer.
    import ast
    import io
    tree = ast.parse((ROOT / 'scripts/insert.py').read_text())
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'Hook')
    scope = {'_io': io}
    exec(compile(ast.Module(body=[node], type_ignores=[]), 'Hook source', 'exec'), scope)
    buffer = io.BytesIO(bytes([0xAA]) * 32)
    scope['Hook'](buffer, 0x1000000, 0, 1)
    assert buffer.getvalue()[:8] == bytes.fromhex('0049084701000009')
    assert buffer.getvalue()[8:] == bytes([0xAA]) * 24  # adjacent command untouched

    source = (ROOT / 'src/wild_encounter.c').read_text()
    command = c_function(source, 'bool8 ScrCmd_dowildbattle(struct ScriptContext* ctx)')
    inserted = ('// BPRE ScrCmd_dowildbattle (0x0806C39C): retain vanilla scripted-wild setup.\n'
                '// Var800B is only a pre-start handshake, never the battle-time policy owner.\n'
                + command + '\n\n')
    assert source.replace(inserted, '', 1) == baseline('src/wild_encounter.c')
    script = (ROOT / 'assembly/overworld_scripts/system_scripts.s').read_text()
    clear = '\tsetvar 0x800B 0x0 @;Discard prior scratch use; Ignore never owns provenance.\n'
    set_magic = '\tsetvar 0x800B 0xB632 @;One-command handshake, consumed before battle execution.\n'
    assert script.replace(clear, '', 1).replace(set_magic, '', 1) == baseline('assembly/overworld_scripts/system_scripts.s')
    assert script.count(set_magic) == 1
    assert 'SystemScript_PokemonEncounter:\n\tlock\n' + clear in script
    assert 'selectedOption2:\n\thidepokepic\n' + set_magic + '\tdowildbattle' in script
    ignore = script.split('selectedOption1:\n', 1)[1].split('selectedOption2:', 1)[0]
    assert 'dowildbattle' not in ignore and '0xB632' not in ignore
    # Other CFRU callers/macros and all five vanilla map callers stay unmarked.
    assert (ROOT / 'xse_commands.s').read_text() == baseline('xse_commands.s')
    for name in ('PowerPlant', 'Route12', 'Route16', 'ThreeIsland_BerryForest'):
        direct = (pret / f'data/maps/{name}/scripts.inc').read_text()
        assert 'dowildbattle' in direct and '0xB632' not in direct
    old_start = c_function((pret / 'src/battle_setup.c').read_text(), 'void StartScriptedWildBattle(void)')
    # Names differ between modern pret and the CFRU vanilla bindings.
    for line in ('ScriptContext2_Enable();', 'gMain.savedCallback = CB2_EndScriptedWildBattle;',
                 'gBattleTypeFlags = BATTLE_TYPE_SCRIPTED_WILD_2;',
                 'CreateBattleStartTask(GetWildBattleTransition(), 0);',
                 'IncrementGameStat(GAME_STAT_TOTAL_BATTLES);',
                 'IncrementGameStat(GAME_STAT_WILD_BATTLES);'):
        assert line in command
        assert line.replace('ScriptContext2_Enable', 'LockPlayerFieldControls').replace('BATTLE_TYPE_SCRIPTED_WILD_2', 'BATTLE_TYPE_WILD_SCRIPTED') in old_start
    harness = r"""
#include <assert.h>
#include <stdint.h>
typedef uint8_t bool8;
typedef uint16_t u16;
#define TRUE 1
#define GAME_STAT_TOTAL_BATTLES 7
#define GAME_STAT_WILD_BATTLES 8
struct ScriptContext { int unused; };
static u16 Var800B;
static unsigned gBattleTypeFlags, step;
static struct { void (*savedCallback)(void); } gMain;
static void CB2_EndScriptedWildBattle(void) {}
static void ScriptContext2_Enable(void) { assert(!Var800B && step++ == 0); }
static unsigned GetWildBattleTransition(void) { assert(!Var800B && step++ == 1); return 9; }
static void CreateBattleStartTask(unsigned transition, unsigned music) {
    assert(!Var800B && step++ == 2 && transition == 9 && music == 0);
    assert(gMain.savedCallback == CB2_EndScriptedWildBattle);
}
static void IncrementGameStat(unsigned stat) { assert(stat == (step == 3 ? 7 : 8) && step++ < 5); }
static void ScriptContext1_Stop(void) { assert(!Var800B && step++ == 5); }
"""
    witness = r"""
int main(void) {
    // Every u16 input: only the exact magic may produce the battle-local bit.
    for(unsigned value=0;value<65536;value++) {
        Var800B=value; step=0; gBattleTypeFlags=0xFFFFFFFF;
        assert(ScrCmd_dowildbattle(0) == TRUE && !Var800B && step == 6);
        assert(gBattleTypeFlags == (BATTLE_TYPE_SCRIPTED_WILD_2 |
            (value == 0xB632 ? BATTLE_TYPE_WILD_PREBATTLE : 0)));
        // A later direct scripted battle resets previous origin without resume cleanup.
        step=0; assert(ScrCmd_dowildbattle(0) == TRUE);
        assert(gBattleTypeFlags == BATTLE_TYPE_SCRIPTED_WILD_2 && !Var800B);
    }
    return 0;
}
"""
    with tempfile.TemporaryDirectory(prefix='cfru-prebattle-origin-') as temp:
        src, binary = Path(temp)/'origin.c', Path(temp)/'origin'
        src.write_text(constants + '\n' + harness + command + witness)
        subprocess.run(['cc', '-std=c99', '-Wall', '-Wextra', '-Werror', str(src), '-o', str(binary)], check=True)
        subprocess.run([str(binary)], check=True)
    print('Prebattle provenance: exact owner/address, bounded hook, script/direct callers, all 65536 handshake values, consume-before-start/nonresume PASS')


def main():
    menu = (ROOT / 'src/move_menu.c').read_text()
    accepted = subprocess.check_output(
        ['git', 'show', f'{ACCEPTED_D22}:src/move_menu.c'], cwd=ROOT, text=True)
    current = c_function(menu, 'void HandleInputChooseAction(void)')
    helper = c_function(menu, 'static bool8 CanUseBQuickRunHere(void)')
    assert current == c_function(accepted, 'void HandleInputChooseAction(void)')
    assert 'HandleInputChooseAction 0802E438 0' in (ROOT / 'hooks').read_text()
    assert current.index('CANCEL_PARTNER:') < current.index('CanUseBQuickRunHere()')
    assert current.index('else if (VarGet(VAR_QUICK_RUN_COMBO) == 1)') < current.index('CanUseBQuickRunHere()')
    for name in ('src/end_battle.c', 'src/battle_start_turn_start.c', 'hooks',
                 'assembly/hooks/general_hooks.s', 'src/config.h', 'src/save.c',
                 'include/new/ram_locs.h', 'include/constants/battle.h'):
        source = (ROOT / name).read_text()
        if name == 'hooks':
            source = source.replace('## #632: 8-byte entry hook fits the 16-byte BPRE command; preserve ctx in r0.\nScrCmd_dowildbattle 806C39C 1\n', '', 1)
        if name == 'include/constants/battle.h':
            source = source.replace('#define BATTLE_TYPE_WILD_PREBATTLE\t\t0x100000 // Random wild Engage origin; battle-local only.\n', '', 1)
        assert source == baseline(name), name
    assert not re.search(r'^\s*#define VAR_QUICK_RUN_COMBO\b', (ROOT / 'src/config.h').read_text(), re.M)
    downstream = (ROOT / 'src/end_battle.c').read_text()
    run = c_function(downstream, 'bool8 TryRunFromBattle(u8 bank)')
    for witness in ('AreAllKindsOfRunningPrevented()', 'Random() & 0xFF',
                    'gBattleStruct->runTries++', 'return effect;', 'B_OUTCOME_RAN'):
        assert witness in run
    restrictions = c_function(downstream, 'u8 IsRunningFromBattleImpossible(void)')
    for witness in ('IsTrappedByAbility', 'STATUS2_ESCAPE_PREVENTION', 'STATUS2_WRAPPED',
                    'STATUS3_ROOTED', 'IsFairyLockActive'):
        assert witness in restrictions
    constants = '\n'.join(line for line in (ROOT / 'include/constants/battle.h').read_text().splitlines()
                          if line.startswith('#define BATTLE_TYPE_'))
    harness = r'''
#include <assert.h>
#include <stdint.h>
#include <string.h>
typedef uint8_t u8;
typedef uint32_t u32;
typedef u8 bool8;
#define FALSE 0
#define PARTNER(b) ((b) ^ 2)
#define IS_DOUBLE_BATTLE (gBattleTypeFlags & BATTLE_TYPE_DOUBLE)
#define RAID_BATTLE_END raidEnd
#define B_POSITION_PLAYER_RIGHT 2
#define B_POSITION_PLAYER_LEFT 0
#define BOUNCE_HEALTHBOX 0
#define BOUNCE_MON 1
#define SE_SELECT 0
enum { A_BUTTON=1, B_BUTTON=2, DPAD_LEFT=4, DPAD_RIGHT=8, DPAD_UP=16,
       DPAD_DOWN=32, START_BUTTON=64, L_BUTTON=128, R_BUTTON=256 };
enum { ACTION_USE_MOVE, ACTION_USE_ITEM, ACTION_SWITCH, ACTION_RUN, ACTION_CANCEL_PARTNER };
static struct { unsigned newKeys; } gMain;
static u32 gBattleTypeFlags;
static u8 gActiveBattler, gAbsentBattlerFlags, gActionSelectionCursor[4], gBattleBufferA[4][2];
static const u32 gBitTable[] = {1,2,4,8};
static struct { struct { u8 chosen[4]; } megaData, ultraData;
                struct { u8 toBeUsed[4]; } dynamaxData; } state, *gNewBS = &state;
static int raid, raidEnd, combo, emitted, completed, sound, destroyed, created;
static bool8 IsRaidBattle(void) { return raid; }
#ifdef VAR_QUICK_RUN_COMBO
static int VarGet(int id) { (void)id; return combo; }
#endif
static int GetBattlerPosition(int b) { return b; }
static int GetBattlerAtPosition(int b) { return b; }
static void DoBounceEffect(int a,int b,int c,int d) { (void)a;(void)b;(void)c;(void)d; }
static void PlaySE(int s) { (void)s; sound++; }
static void EmitTwoReturnValues(int a,int b,int c) { assert(a==1 && c==0); emitted=b; }
static void PlayerBufferExecCompleted(void) { completed++; }
static void ActionSelectionDestroyCursorAt(int c) { (void)c; destroyed++; }
static void ActionSelectionCreateCursorAt(int c,int z) { (void)c; (void)z; created++; }
static void SwapHpBarsWithHpText(void) {}
'''
    witnesses = r'''
static void reset(u32 flags, int bank, int keys) {
    memset(&state, 1, sizeof(state));
    memset(gBattleBufferA, 0, sizeof(gBattleBufferA));
    memset(gActionSelectionCursor, 0, sizeof(gActionSelectionCursor));
    gBattleTypeFlags=flags; gActiveBattler=bank; gMain.newKeys=keys;
    raid=raidEnd=combo=gAbsentBattlerFlags=0;
    emitted=-1; completed=sound=destroyed=created=0;
}
static void check_run(void) {
    assert(emitted==ACTION_RUN && completed==1 && sound==1);
    assert(!state.megaData.chosen[gActiveBattler] && !state.ultraData.chosen[gActiveBattler]);
}
int main(void) {
    u32 origin=BATTLE_TYPE_SCRIPTED_WILD_2|BATTLE_TYPE_WILD_PREBATTLE;
    u32 ordinary[]={0,BATTLE_TYPE_IS_MASTER,BATTLE_TYPE_DOUBLE,BATTLE_TYPE_IS_MASTER|BATTLE_TYPE_DOUBLE,
                    origin,origin|BATTLE_TYPE_IS_MASTER,origin|BATTLE_TYPE_DOUBLE,
                    origin|BATTLE_TYPE_IS_MASTER|BATTLE_TYPE_DOUBLE};
    for (unsigned i=0;i<8;i++) for (int cursor=0;cursor<4;cursor++) {
        reset(ordinary[i],0,B_BUTTON); gActionSelectionCursor[0]=cursor;
        HandleInputChooseAction(); check_run(); assert(gActionSelectionCursor[0]==cursor);
    }
    // Either origin bit alone and every other special/unknown bit fail closed.
    for (unsigned bit=0;bit<32;bit++) {
        u32 flag=(u32)1<<bit;
        if (flag & (BATTLE_TYPE_IS_MASTER|BATTLE_TYPE_DOUBLE)) continue;
        reset(flag|BATTLE_TYPE_IS_MASTER,0,B_BUTTON);
        HandleInputChooseAction(); assert(emitted==-1 && completed==0 && sound==0);
        if (flag & origin) continue;
        reset(origin|flag|BATTLE_TYPE_IS_MASTER|BATTLE_TYPE_DOUBLE,0,B_BUTTON);
        HandleInputChooseAction(); assert(emitted==-1 && completed==0 && sound==0);
    }
    for (int prebattle=0;prebattle<2;prebattle++) for (int end=0;end<2;end++) {
        reset(prebattle ? origin : 0,0,B_BUTTON); raid=1; raidEnd=end;
        HandleInputChooseAction(); assert(emitted==-1 && completed==0);
    }
    for (int trainer=0;trainer<2;trainer++) {
        reset(BATTLE_TYPE_DOUBLE|(trainer ? BATTLE_TYPE_TRAINER:0),2,B_BUTTON);
        HandleInputChooseAction(); assert(emitted==ACTION_CANCEL_PARTNER && completed==1);
        assert(!state.dynamaxData.toBeUsed[0] && state.megaData.chosen[2]);
        reset(BATTLE_TYPE_DOUBLE|(trainer ? BATTLE_TYPE_TRAINER:0),2,B_BUTTON);
        gBattleBufferA[2][1]=ACTION_USE_ITEM;
        HandleInputChooseAction(); assert(emitted==-1 && completed==0);
    }
    reset(BATTLE_TYPE_DOUBLE,2,B_BUTTON); gAbsentBattlerFlags=1;
    HandleInputChooseAction(); check_run();
    u32 contexts[]={0,BATTLE_TYPE_TRAINER,BATTLE_TYPE_SAFARI,BATTLE_TYPE_GHOST,
                    BATTLE_TYPE_LINK|BATTLE_TYPE_MULTI,BATTLE_TYPE_FRONTIER};
    for (unsigned i=0;i<sizeof(contexts)/sizeof(contexts[0]);i++) {
        reset(contexts[i],0,A_BUTTON); gActionSelectionCursor[0]=3;
        HandleInputChooseAction(); check_run();
        reset(contexts[i],0,R_BUTTON); HandleInputChooseAction(); check_run();
    }
    for (int key=A_BUTTON; ;key=R_BUTTON) {
        reset(0,0,key); raid=raidEnd=1; gActionSelectionCursor[0]=1;
        HandleInputChooseAction(); assert(emitted==ACTION_RUN && completed==1 && state.megaData.chosen[0]);
        if (key==R_BUTTON) break;
    }
    reset(0,0,A_BUTTON|B_BUTTON); HandleInputChooseAction(); assert(emitted==ACTION_USE_MOVE);
    reset(0,0,DPAD_RIGHT|B_BUTTON); HandleInputChooseAction(); assert(emitted==-1 && gActionSelectionCursor[0]==1);
#ifdef VAR_QUICK_RUN_COMBO
    for (int end=0;end<2;end++) {
        reset(0,0,B_BUTTON); combo=1; raid=raidEnd=end;
        HandleInputChooseAction(); assert(emitted==-1 && completed==0);
        assert(gActionSelectionCursor[0]==(end ? 1:3) && destroyed==1 && created==1);
        gMain.newKeys=A_BUTTON; HandleInputChooseAction(); assert(emitted==ACTION_RUN && completed==1);
        reset(0,0,R_BUTTON); combo=1; HandleInputChooseAction(); assert(emitted==-1);
    }
    reset(BATTLE_TYPE_DOUBLE,2,B_BUTTON); combo=1;
    HandleInputChooseAction(); assert(emitted==ACTION_CANCEL_PARTNER && !destroyed);
    reset(BATTLE_TYPE_TRAINER,0,B_BUTTON); combo=1;
    HandleInputChooseAction(); assert(emitted==-1 && gActionSelectionCursor[0]==3);
#endif
    return 0;
}
'''
    # Execute the unchanged production escape calculation with deterministic host inputs.
    escape_harness = r'''
#include <assert.h>
#include <stdint.h>
typedef uint8_t u8;
typedef u8 bool8;
#define FALSE 0
#define TRUE 1
#define NO_GHOST_BATTLES
#define TYPE_GHOST 1
#define ITEM_EFFECT_CAN_ALWAYS_RUN 1
#define ABILITY_RUNAWAY 1
#define B_OUTCOME_RAN 1
#define RAID_BATTLE_END 0
#define BATTLE_OPPOSITE(b) ((b)^1)
#define PARTNER(b) ((b)^2)
#define ITEM_EFFECT(b) 0
#define ITEM(b) 0
#define ABILITY(b) 0
static unsigned gBattleTypeFlags;
static u8 gStringBank, gLastUsedItem, gLastUsedAbility, gCurrentTurnActionNumber, gBattlersCount=2, gBattleOutcome;
static struct { u8 fleeFlag; } gProtectStructs[4];
static struct { unsigned speed; unsigned hp; } gBattleMons[4];
static struct { unsigned runTries; } battleStruct, *gBattleStruct=&battleStruct;
static int prevented, randomValue;
static int AreAllKindsOfRunningPrevented(void) { return prevented; }
static int IsRaidBattle(void) { return 0; }
static int IsOfType(int bank,int type) { (void)bank;(void)type;return 0; }
static unsigned udivsi(unsigned a,unsigned b) { return a/b; }
static int Random(void) { return randomValue; }
''' + run + r'''
int main(void) {
    gBattleMons[0].speed=10; gBattleMons[1].speed=100;
    randomValue=255;
    assert(!TryRunFromBattle(0) && !gBattleOutcome && battleStruct.runTries==1);
    randomValue=0;
    assert(TryRunFromBattle(0) && gBattleOutcome==B_OUTCOME_RAN && battleStruct.runTries==2);
    gBattleOutcome=0; prevented=1;
    assert(!TryRunFromBattle(0) && !gBattleOutcome && battleStruct.runTries==2);
    prevented=0; gBattleTypeFlags=BATTLE_TYPE_DOUBLE;
    gBattleMons[1].hp=1; randomValue=255; battleStruct.runTries=0;
    assert(!TryRunFromBattle(0));
    gBattleMons[1].hp=0; gBattleMons[3].speed=100;
    assert(!TryRunFromBattle(0));
    randomValue=0; assert(TryRunFromBattle(0));
    return 0;
}
'''
    with tempfile.TemporaryDirectory(prefix='cfru-b-quick-run-') as temp:
        source = Path(temp) / 'action_menu.c'
        source.write_text(constants+'\n'+harness+helper+'\n'+current+witnesses)
        for configured in (False, True):
            binary = Path(temp) / f'action_menu_{configured}'
            command = ['cc', '-std=c99', '-Wall', '-Wextra', '-Werror']
            if configured:
                command += ['-DVAR_QUICK_RUN_COMBO=1']
            subprocess.run(command+[str(source), '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True)
        escape_source = Path(temp) / 'escape.c'
        escape_binary = Path(temp) / 'escape'
        escape_source.write_text(constants+'\n'+escape_harness)
        subprocess.run(['cc', '-std=c99', '-Wall', '-Wextra', '-Werror',
                        str(escape_source), '-o', str(escape_binary)], check=True)
        subprocess.run([str(escape_binary)], check=True)
    provenance_witnesses(constants)
    print('B quick Run: production input (default + optional combo), escape success/failure/prevention and source preservation PASS')


if __name__ == '__main__':
    main()
