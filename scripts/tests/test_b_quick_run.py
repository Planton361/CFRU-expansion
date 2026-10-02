#!/usr/bin/env python3
"""ROM-free production action-menu witnesses for Workspace #603."""
from pathlib import Path
import re
import subprocess
import tempfile
from audit_early_running_lifecycle import c_function

ROOT = Path(__file__).resolve().parents[2]
BASE = 'e368068b3e4307bb53fa054b3dda45e2fac98a7a'


def baseline(name):
    return subprocess.check_output(['git', 'show', f'{BASE}:{name}'], cwd=ROOT, text=True)


def main():
    menu = (ROOT / 'src/move_menu.c').read_text()
    old = baseline('src/move_menu.c')
    current = c_function(menu, 'void HandleInputChooseAction(void)')
    helper = c_function(menu, 'static bool8 CanUseBQuickRunHere(void)')
    addition = '''\t\t// Keep an explicitly configured B + A cursor shortcut above B-only Run.
\t\telse if (CanUseBQuickRunHere())
\t\t{
\t\t\tPlaySE(SE_SELECT);
\t\t\tgoto NORMAL_RUN;
\t\t}
'''
    assert menu.replace(helper + '\n\n', '', 1).replace(addition, '', 1) == old
    assert 'HandleInputChooseAction 0802E438 0' in (ROOT / 'hooks').read_text()
    assert current.index('CANCEL_PARTNER:') < current.index('CanUseBQuickRunHere()')
    assert current.index('else if (VarGet(VAR_QUICK_RUN_COMBO) == 1)') < current.index('CanUseBQuickRunHere()')
    for name in ('src/end_battle.c', 'src/battle_start_turn_start.c', 'hooks',
                 'assembly/hooks/general_hooks.s', 'src/config.h', 'src/save.c',
                 'include/new/ram_locs.h', 'include/constants/battle.h'):
        assert (ROOT / name).read_text() == baseline(name), name
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
    u32 ordinary[]={0,BATTLE_TYPE_IS_MASTER,BATTLE_TYPE_DOUBLE,BATTLE_TYPE_IS_MASTER|BATTLE_TYPE_DOUBLE};
    for (unsigned i=0;i<4;i++) for (int cursor=0;cursor<4;cursor++) {
        reset(ordinary[i],0,B_BUTTON); gActionSelectionCursor[0]=cursor;
        HandleInputChooseAction(); check_run(); assert(gActionSelectionCursor[0]==cursor);
    }
    // Every special or unknown bit, including unnamed 0x100000, fails closed.
    for (unsigned bit=0;bit<32;bit++) {
        u32 flag=(u32)1<<bit;
        if (flag & (BATTLE_TYPE_IS_MASTER|BATTLE_TYPE_DOUBLE)) continue;
        reset(flag|BATTLE_TYPE_IS_MASTER,0,B_BUTTON);
        HandleInputChooseAction(); assert(emitted==-1 && completed==0 && sound==0);
    }
    for (int end=0;end<2;end++) {
        reset(0,0,B_BUTTON); raid=1; raidEnd=end;
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
    print('B quick Run: production input (default + optional combo), escape success/failure/prevention and source preservation PASS')


if __name__ == '__main__':
    main()
