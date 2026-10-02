#!/usr/bin/env python3
"""ROM-free #606 production rendering, pinned glyph/palette and layout witnesses."""
from pathlib import Path
import ast
import re
import sys
import struct
import subprocess
import tempfile
import zlib
from audit_early_running_lifecycle import c_function

ROOT = Path(__file__).resolve().parents[2]
PRET = ROOT.parent / 'references/pret-pokefirered'
BASE = '41ac6081ccf27170f361c4ed7d50ad546817c2cb'
PRET_BASE = 'e060ab955b5dc9ac1c4904c2cd141683615cf477'


def snapshot(path):
    return subprocess.check_output(['git', 'show', f'{BASE}:{path}'], cwd=ROOT, text=True)


def rendering(source):
    start = source.index('\tif (raidBattleEnd) //Time to catch Raid opponent')
    end = source.index('\n\tfor (i = 0; i < MAX_MON_MOVES;', start)
    return source[start:end]


def glyph_pixels():
    # Decode the pinned indexed source PNG, not generated graphics or a ROM.
    data = (PRET / 'graphics/fonts/keypad_icons.png').read_bytes()
    assert data[:8] == b'\x89PNG\r\n\x1a\n'
    pos, compressed = 8, b''
    while pos < len(data):
        size = struct.unpack('>I', data[pos:pos+4])[0]
        kind, chunk = data[pos+4:pos+8], data[pos+8:pos+8+size]
        pos += size + 12
        if kind == b'IHDR':
            assert struct.unpack('>IIBBBBB', chunk) == (128, 32, 4, 3, 0, 0, 0)
        if kind == b'IDAT':
            compressed += chunk
    raw = zlib.decompress(compressed)
    assert len(raw) == 32 * 65
    assert all(raw[y*65] == 0 for y in range(32))
    return [[(raw[y*65+1+x//2] >> (4 if x%2 == 0 else 0)) & 15
             for x in range(8, 16)] for y in range(12)]


def main():
    assert subprocess.check_output(['git', 'merge-base', BASE, 'HEAD'], cwd=ROOT, text=True).strip() == BASE
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=PRET, text=True).strip() == PRET_BASE
    menu = (ROOT / 'src/move_menu.c').read_text()
    old = snapshot('src/move_menu.c')
    helper = c_function(menu, 'static bool8 CanUseBQuickRunHere(void)')
    assert helper == c_function(old, 'static bool8 CanUseBQuickRunHere(void)')
    assert c_function(menu, 'void HandleInputChooseAction(void)') == c_function(old, 'void HandleInputChooseAction(void)')
    # Exactly one definition, one prototype, and the rendering/input callers.
    assert len(re.findall(r'static bool8 CanUseBQuickRunHere\(void\)\s*\{', menu)) == 1
    assert menu.count('CanUseBQuickRunHere()') == 2
    d22_test = (ROOT / 'scripts/tests/test_b_quick_run.py').read_text()
    marker = "    assert 'HandleInputChooseAction"
    assert d22_test.split(marker, 1)[1] == snapshot('scripts/tests/test_b_quick_run.py').split(marker, 1)[1]
    block = rendering(menu)
    original_block = rendering(old)
    assert block[:block.index('\n\telse\n\t{')] == original_block[:original_block.index('\n\telse\n\t{')]
    normalized = menu.replace(block, original_block)
    normalized = normalized.replace('extern const u8 gText_BattleMenuBQuickRun[];\n', '')
    normalized = normalized.replace('extern const u8 gText_BattleMenuNoItemsBQuickRun[];\n', '')
    normalized = normalized.replace('static bool8 CanUseBQuickRunHere(void);\n', '')
    assert normalized == old  # No other production source changes.
    grey = c_function(menu, 'static void LoadShadowColourForGreyedOutBagText(void)')
    assert grey == c_function(old, 'static void LoadShadowColourForGreyedOutBagText(void)')

    general = (ROOT / 'strings/general_battle_strings.string').read_text()
    assert general == snapshot('strings/general_battle_strings.string')
    strings = (ROOT / 'strings/move_menu_strings.string').read_text()
    assert strings.endswith(snapshot('strings/move_menu_strings.string'))
    # Run only the source string encoder in memory; never import the inserter.
    encoder_tree = ast.parse((ROOT / 'scripts/string.py').read_text())
    selected = [node for node in encoder_tree.body
                if isinstance(node, ast.FunctionDef) and node.name in ('ProcessString', 'PokeByteTableMaker')
                or isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'SpecialBuffers' for t in node.targets)]
    encoder = {'CharMap': str(ROOT / 'charmap.tbl'), 'sys': sys}
    exec(compile(ast.Module(body=selected, type_ignores=[]), 'string encoder', 'exec'), encoder)
    for original, hinted in [('gText_BattleMenu', 'gText_BattleMenuBQuickRun'),
                             ('gText_BattleMenuNoItems', 'gText_BattleMenuNoItemsBQuickRun')]:
        originals = re.findall(r'#org @'+original+r'\n([^\n]+)', general)
        hints = re.findall(r'#org @'+hinted+r'\n([^\n]+)', strings)
        assert hints == [line+' [B_BUTTON]' for line in originals]
        for line, hint in zip(originals, hints):
            assert encoder['ProcessString'](hint, 1) == encoder['ProcessString'](line, 1)+'0x0, 0xF8, 0x01, '
        assert all(line.count('[ALIGN][38]') == 2 for line in hints)
    assert '#include "src/config.h"\n\n#ifndef UNBOUND' in strings
    text = (PRET / 'src/text.c').read_text()
    assert '[CHAR_B_BUTTON]       = {  0x1,  8, 12 }' in text
    assert '"B_BUTTON": ["F8", "01"]' in (ROOT / 'scripts/string.py').read_text()
    chars = (PRET / 'include/characters.h').read_text()
    assert '#define CHAR_KEYPAD_ICON       0xF8' in chars
    assert '#define CHAR_B_BUTTON       0x01' in chars
    assert 'DrawKeypadIcon' in text and 'gKeypadIconTiles + (sKeypadIcons[keypadIconId].tileOffset * 0x20)' in text
    assert 'BlitBitmapRect4Bit(&sourceRect, &destRect, srcX, srcY, destX, destY, rectWidth, rectHeight, 0);' in (PRET / 'src/window.c').read_text()
    pixels = glyph_pixels()
    assert [''.join(f'{x:X}' for x in row) for row in pixels] == [
        '00000000', '00000000', '00000000', '00000000', '01111120', '11223112',
        '11212112', '11223112', '11212112', '11223112', '21111120', '02222200']
    assert {value for row in pixels for value in row} == {0, 1, 2, 3}
    # White button face (1), dark B/outline (2), light lettering shadow (3).

    bg = (PRET / 'src/battle_bg.c').read_text()
    assert re.search(r'\[B_WIN_ACTION_MENU\] = \{.*?\.width = 12,.*?\.height = 4,.*?\.paletteNum = 5,', bg, re.S)
    settings = (PRET / 'src/battle_message.c').read_text().split('[B_WIN_ACTION_MENU] = {', 1)[1].split('}', 1)[0]
    assert '.fontId = FONT_NORMAL_COPY_1' in settings and '.letterSpacing = 0' in settings
    widths = [int(x) for x in re.findall(r'\d+', re.search(r'sFontNormalCopy1LatinGlyphWidths\[\] =\s*\{(.*?)\};', text, re.S)[1])]
    codes = dict((m[2], int(m[1], 16)) for m in re.finditer(r'^([0-9A-F]{2})=(.)$', (ROOT / 'charmap.tbl').read_text(encoding='utf-8-sig'), re.M))
    run_width = sum(widths[codes[c]] for c in 'Run ')
    assert run_width == 23
    assert 56 + run_width + 8 == 87 < 96
    cursor = c_function((PRET / 'src/battle_controller_player.c').read_text(), 'void ActionSelectionCreateCursorAt(u8 cursorPosition, u8 arg1)')
    assert '7 * (cursorPosition & 1) + 16' in cursor
    # RUN cursor occupies local x=48..55; RUN begins at 56, icon at 79.
    assert (23 - 17) * 8 + 8 == 56 < 56 + run_width
    assert '.y = 2' in settings and '.lineSpacing = 2' in settings
    assert 2 + 16 + 2 + 12 <= 32
    palette = c_function((PRET / 'src/palette.c').read_text(), 'void LoadPalette(const void *src, u16 offset, u16 size)')
    assert 'CpuCopy16(src, &gPlttBufferUnfaded[offset], size)' in palette
    assert 'CpuCopy16(src, &gPlttBufferFaded[offset], size)' in palette

    constants = '\n'.join(line for line in (ROOT / 'include/constants/battle.h').read_text().splitlines() if line.startswith('#define BATTLE_TYPE_'))
    harness = r'''
#include <assert.h>
#include <stdint.h>
#include <string.h>
typedef uint8_t bool8;
typedef uint16_t u16;
#define RGB(r,g,b) ((r)|((g)<<5)|((b)<<10))
#define IS_DOUBLE_BATTLE (gBattleTypeFlags & BATTLE_TYPE_DOUBLE)
#define B_POSITION_PLAYER_RIGHT 2
#define B_POSITION_PLAYER_LEFT 0
#define ACTION_USE_ITEM 1
static unsigned gBattleTypeFlags, gActiveBattler, gAbsentBattlerFlags;
static unsigned gBattleBufferA[4][2], gBitTable[]={1,2,4,8};
static u16 gPlttBufferUnfaded[256], gPlttBufferFaded[256];
static int raid, raidBattleEnd, bag, chosen, loads;
enum {gText_BattleMenuRaidEnd, gText_BattleMenu2NoItems, gText_BattleMenu2,
      gText_BattleMenuNoItems, gText_BattleMenu, gText_BattleMenuNoItemsBQuickRun,
      gText_BattleMenuBQuickRun};
static int IsRaidBattle(void) { return raid; }
static int IsBagDisabled(void) { return bag; }
static unsigned GetBattlerPosition(unsigned b) { return b; }
static unsigned GetBattlerAtPosition(unsigned b) { return b; }
static void BattlePutTextOnWindow(int text,int win) { assert(win==2); chosen=text; }
static void CpuCopy16(const void *src,void *dst,unsigned size) { memcpy(dst,src,size); }
static void LoadPalette(const void *src,u16 offset,u16 size) {
    assert(offset==81 && size==6); loads++;
    CpuCopy16(src,&gPlttBufferUnfaded[offset],size);
    CpuCopy16(src,&gPlttBufferFaded[offset],size);
}
'''
    witnesses = r'''
static void check(unsigned flags,int isRaid,int end,int right,int absent,int item,int disabled) {
    gBattleTypeFlags=flags; raid=isRaid; raidBattleEnd=end; gActiveBattler=right?2:0;
    gAbsentBattlerFlags=absent; gBattleBufferA[gActiveBattler][1]=item; bag=disabled;
    memset(gPlttBufferUnfaded,0x55,sizeof(gPlttBufferUnfaded));
    memset(gPlttBufferFaded,0x55,sizeof(gPlttBufferFaded)); loads=0;
    int back=(flags&BATTLE_TYPE_DOUBLE)&&right&&!absent&&!(flags&(BATTLE_TYPE_MULTI|BATTLE_TYPE_INGAME_PARTNER))&&item!=ACTION_USE_ITEM;
    int hint=!end&&!back&&CanUseBQuickRunHere();
    render();
    assert(chosen==(end?gText_BattleMenuRaidEnd:back?(disabled?gText_BattleMenu2NoItems:gText_BattleMenu2):hint?(disabled?gText_BattleMenuNoItemsBQuickRun:gText_BattleMenuBQuickRun):(disabled?gText_BattleMenuNoItems:gText_BattleMenu)));
    assert(loads==hint);
    for(int i=0;i<256;i++) {
        u16 expected=0x5555;
        if(hint&&i==81) expected=RGB(31,31,31);
        if(hint&&i==82) expected=RGB(9,9,9);
        if(hint&&i==83) expected=RGB(26,26,25);
        if(!end&&disabled&&i==91) expected=RGB(28,28,27);
        assert(gPlttBufferUnfaded[i]==expected && gPlttBufferFaded[i]==expected);
    }
}
int main(void) {
    for(int bit=-1;bit<32;bit++) for(int master=0;master<2;master++)
    for(int dbl=0;dbl<2;dbl++) for(int right=0;right<2;right++)
    for(int disabled=0;disabled<2;disabled++) for(int absent=0;absent<2;absent++)
    for(int item=0;item<2;item++) {
        unsigned flags=(bit<0?0:(unsigned)1<<bit)|(master?BATTLE_TYPE_IS_MASTER:0)|(dbl?BATTLE_TYPE_DOUBLE:0);
        check(flags,0,0,right,absent,item,disabled);
        check(flags,1,0,right,absent,item,disabled);
        check(flags,1,1,right,absent,item,disabled);
    }
    return 0;
}
'''
    with tempfile.TemporaryDirectory(prefix='cfru-b-hint-') as temp:
        source, binary = Path(temp)/'hint.c', Path(temp)/'hint'
        source.write_text(constants+'\n'+harness+helper+'\n'+grey+'\nstatic void render(void) {\n'+block+'\n}\n'+witnesses)
        subprocess.run(['cc', '-std=c99', '-Wall', '-Wextra', '-Werror', str(source), '-o', str(binary)], check=True)
        subprocess.run([str(binary)], check=True)
    print(f'B hint: production rendering/context/Bag/palette PASS; Run space={run_width}px, icon=8x12, end={56+run_width+8}/96px')


if __name__ == '__main__':
    main()
