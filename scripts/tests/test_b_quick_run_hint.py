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


def indexed_pixels(path):
    # Decode committed indexed source PNGs, not generated graphics or a ROM.
    data = path.read_bytes()
    assert data[:8] == b'\x89PNG\r\n\x1a\n'
    pos, compressed = 8, b''
    while pos < len(data):
        size = struct.unpack('>I', data[pos:pos+4])[0]
        kind, chunk = data[pos+4:pos+8], data[pos+8:pos+8+size]
        pos += size + 12
        if kind == b'IHDR':
            width, height, depth, color, compression, filtering, interlace = struct.unpack('>IIBBBBB', chunk)
            assert (depth, color, compression, filtering, interlace) == (4, 3, 0, 0, 0)
        if kind == b'IDAT':
            compressed += chunk
    raw = zlib.decompress(compressed)
    stride = (width + 1) // 2 + 1
    assert len(raw) == height * stride
    assert all(raw[y*stride] == 0 for y in range(height))
    return [[(raw[y*stride+1+x//2] >> (4 if x%2 == 0 else 0)) & 15
             for x in range(width)] for y in range(height)]


def main():
    assert subprocess.check_output(['git', 'merge-base', BASE, 'HEAD'], cwd=ROOT, text=True).strip() == BASE
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=PRET, text=True).strip() == PRET_BASE
    menu = (ROOT / 'src/move_menu.c').read_text()
    old = snapshot('src/move_menu.c')
    helper = c_function(menu, 'static bool8 CanUseBQuickRunHere(void)')
    old_helper = c_function(old, 'static bool8 CanUseBQuickRunHere(void)')
    assert c_function(menu, 'void HandleInputChooseAction(void)') == c_function(old, 'void HandleInputChooseAction(void)')
    # Exactly one definition, one prototype, and the rendering/input callers.
    assert len(re.findall(r'static bool8 CanUseBQuickRunHere\(void\)\s*\{', menu)) == 1
    assert menu.count('CanUseBQuickRunHere()') == 2
    block = rendering(menu)
    original_block = rendering(old)
    assert block[:block.index('\n\telse\n\t{')] == original_block[:original_block.index('\n\telse\n\t{')]
    remap = c_function(menu, 'static void RemapBQuickRunHint(void)')
    assert 'LoadPalette' not in block + remap
    normalized = menu.replace(helper, old_helper, 1).replace(block, original_block).replace(remap + '\n\n', '', 1)
    normalized = normalized.replace('extern const u8 gText_BattleMenuBQuickRun[];\n', '')
    normalized = normalized.replace('extern const u8 gText_BattleMenuNoItemsBQuickRun[];\n', '')
    normalized = normalized.replace('static bool8 CanUseBQuickRunHere(void);\n', '')
    normalized = normalized.replace('static void RemapBQuickRunHint(void);\n', '')
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
    keypad = indexed_pixels(PRET / 'graphics/fonts/keypad_icons.png')
    assert len(keypad) == 32 and len(keypad[0]) == 128
    pixels = [row[8:16] for row in keypad[:12]]
    assert [''.join(f'{x:X}' for x in row) for row in pixels] == [
        '00000000', '00000000', '00000000', '00000000', '01111120', '11223112',
        '11212112', '11223112', '11212112', '11223112', '21111120', '02222200']
    assert {value for row in pixels for value in row} == {0, 1, 2, 3}
    # White button face (14), dark B/outline (13), light lettering shadow (15).

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
    move_window = bg.split('[B_WIN_MOVE_TYPE] = {', 1)[1].split('}', 1)[0]
    assert '.paletteNum = 5' in move_window
    pss = indexed_pixels(ROOT / 'graphics/Battle_UI/PSS_Icons/PSSIcons.png')
    assert {pixel for row in pss for pixel in row} == {0, 1, 3, 10, 13, 15}
    move_type = c_function(menu, 'static void MoveSelectionDisplayMoveType(void)')
    assert 'BlitBitmapToWindow(8, PSSIconsTiles + 24 * 8 * split, 38, 3, 24, 15);' in move_type
    assert move_type == c_function(old, 'static void MoveSelectionDisplayMoveType(void)')
    for index, rgb in [(13, '9,  9,  9'), (14, '31, 31, 31'), (15, '26,  26,  25')]:
        assert re.search(rf'BG_PLTT_ID\(5\) \+ {index}\] = RGB\(\s*{rgb}\);', bg)
    assert 'static const u8 colors[] = {0, 14, 13, 15};' in remap
    # Action-menu speed zero renders synchronously before the local remap.
    printer = c_function((PRET / 'src/text_printer.c').read_text(), 'bool16 AddTextPrinter(struct TextPrinterTemplate *textSubPrinter, u8 speed, void (*callback)(struct TextPrinterTemplate *, u16))')
    assert 'if (speed != TEXT_SKIP_DRAW && speed != 0)' in printer
    assert 'RenderFont(&sTempTextPrinter)' in printer

    constants = '\n'.join(line for line in (ROOT / 'include/constants/battle.h').read_text().splitlines() if line.startswith('#define BATTLE_TYPE_'))
    harness = r'''
#include <assert.h>
#include <stdint.h>
#include <string.h>
typedef uint8_t bool8;
typedef uint8_t u8;
typedef uint32_t u32;
typedef uint16_t u16;
#define RGB(r,g,b) ((r)|((g)<<5)|((b)<<10))
#define IS_DOUBLE_BATTLE (gBattleTypeFlags & BATTLE_TYPE_DOUBLE)
#define B_POSITION_PLAYER_RIGHT 2
#define B_POSITION_PLAYER_LEFT 0
#define ACTION_USE_ITEM 1
static unsigned gBattleTypeFlags, gActiveBattler, gAbsentBattlerFlags;
static unsigned gBattleBufferA[4][2], gBitTable[]={1,2,4,8};
static u16 gPlttBufferUnfaded[256], gPlttBufferFaded[256];
static int raid, raidBattleEnd, bag, chosen, copies;
#define WINDOW_TILE_DATA 7
#define WINDOW_WIDTH 3
#define COPYWIN_GFX 2
static u8 tileData[96*32/2];
static unsigned offset(unsigned x,unsigned y) { return ((y/8)*12+x/8)*32+(y%8)*4+(x%8)/2; }
static u8 pixel(unsigned x,unsigned y) { return (tileData[offset(x,y)]>>((x&1)*4))&15; }
static void putPixel(unsigned x,unsigned y,u8 color) {
    unsigned shift=(x&1)*4;
    tileData[offset(x,y)]=(tileData[offset(x,y)]&~(15<<shift))|(color<<shift);
}
static uintptr_t GetWindowAttribute(int win,int attr) {
    assert(win==2);
    if(attr==WINDOW_TILE_DATA) return (uintptr_t)tileData;
    assert(attr==WINDOW_WIDTH); return 12;
}
static void CopyWindowToVram(int win,int mode) {
    assert(win==2 && mode==COPYWIN_GFX); copies++;
}
enum {gText_BattleMenuRaidEnd, gText_BattleMenu2NoItems, gText_BattleMenu2,
      gText_BattleMenuNoItems, gText_BattleMenu, gText_BattleMenuNoItemsBQuickRun,
      gText_BattleMenuBQuickRun};
static int IsRaidBattle(void) { return raid; }
static int IsBagDisabled(void) { return bag; }
static unsigned GetBattlerPosition(unsigned b) { return b; }
static unsigned GetBattlerAtPosition(unsigned b) { return b; }
static void BattlePutTextOnWindow(int text,int win) {
    assert(win==2); chosen=text;
    memset(tileData,0x55,sizeof(tileData));
    if(text==gText_BattleMenuBQuickRun||text==gText_BattleMenuNoItemsBQuickRun) {
        for(unsigned y=0;y<12;y++) for(unsigned x=0;x<8;x++)
            putPixel(x+79,y+20,bGlyph[y*8+x] ? bGlyph[y*8+x] : 14);
    }
}
static void CpuCopy16(const void *src,void *dst,unsigned size) { memcpy(dst,src,size); }

'''
    witnesses = r'''
static void check(unsigned flags,int isRaid,int end,int right,int absent,int item,int disabled) {
    gBattleTypeFlags=flags; raid=isRaid; raidBattleEnd=end; gActiveBattler=right?2:0;
    gAbsentBattlerFlags=absent; gBattleBufferA[gActiveBattler][1]=item; bag=disabled;
    for(unsigned i=0;i<256;i++) gPlttBufferUnfaded[i]=gPlttBufferFaded[i]=0x4000+i;
    copies=0;
    int back=(flags&BATTLE_TYPE_DOUBLE)&&right&&!absent&&!(flags&(BATTLE_TYPE_MULTI|BATTLE_TYPE_INGAME_PARTNER))&&item!=ACTION_USE_ITEM;
    int hint=!end&&!back&&CanUseBQuickRunHere();
    render();
    assert(chosen==(end?gText_BattleMenuRaidEnd:back?(disabled?gText_BattleMenu2NoItems:gText_BattleMenu2):hint?(disabled?gText_BattleMenuNoItemsBQuickRun:gText_BattleMenuBQuickRun):(disabled?gText_BattleMenuNoItems:gText_BattleMenu)));
    assert(copies==hint);
    for(unsigned y=0;y<32;y++) for(unsigned x=0;x<96;x++) {
        u8 expected=5;
        if(hint&&x>=79&&x<87&&y>=20) {
            static const u8 mapping[]={14,14,13,15};
            expected=mapping[bGlyph[(y-20)*8+x-79]];
        }
        assert(pixel(x,y)==expected);
    }
    // Every PSS pixel resolves to exactly its pre-hint palette color.
    for(unsigned i=0;i<sizeof(pssPixels);i++) {
        assert(gPlttBufferUnfaded[80+pssPixels[i]]==0x4000+80+pssPixels[i]);
        assert(gPlttBufferFaded[80+pssPixels[i]]==0x4000+80+pssPixels[i]);
    }
    for(int i=0;i<256;i++) {
        u16 expected=0x4000+i;
        if(!end&&disabled&&i==91) expected=RGB(28,28,27);
        assert(gPlttBufferUnfaded[i]==expected && gPlttBufferFaded[i]==expected);
    }
}
int main(void) {
    unsigned origin=BATTLE_TYPE_SCRIPTED_WILD_2|BATTLE_TYPE_WILD_PREBATTLE;
    for(int dbl=0;dbl<2;dbl++) for(int master=0;master<2;master++)
    for(int disabled=0;disabled<2;disabled++) {
        unsigned flags=origin|(dbl?BATTLE_TYPE_DOUBLE:0)|(master?BATTLE_TYPE_IS_MASTER:0);
        gBattleTypeFlags=flags; raid=0; assert(CanUseBQuickRunHere());
        check(flags,0,0,0,0,0,disabled);
        check(flags,0,0,1,0,0,disabled);
        for(int bit=0;bit<32;bit++) {
            unsigned special=(unsigned)1<<bit;
            if(special&(origin|BATTLE_TYPE_IS_MASTER|BATTLE_TYPE_DOUBLE)) continue;
            gBattleTypeFlags=flags|special; assert(!CanUseBQuickRunHere());
            check(flags|special,0,0,0,0,0,disabled);
        }
        check(flags,1,0,0,0,0,disabled);
    }
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
        pixel_arrays = 'static const unsigned char bGlyph[] = {' + ','.join(str(p) for row in pixels for p in row) + '};\n'
        pixel_arrays += 'static const unsigned char pssPixels[] = {' + ','.join(str(p) for row in pss for p in row) + '};\n'
        source.write_text(constants+'\n'+pixel_arrays+harness+helper+'\n'+grey+'\n'+remap+'\nstatic void render(void) {\n'+block+'\n}\n'+witnesses)
        subprocess.run(['cc', '-std=c99', '-Wall', '-Wextra', '-Werror', str(source), '-o', str(binary)], check=True)
        subprocess.run([str(binary)], check=True)
    print(f'B hint: production rendering/context/Bag/local pixels/shared palette/PSS PASS; Run space={run_width}px, icon=8x12, end={56+run_width+8}/96px')


if __name__ == '__main__':
    main()
