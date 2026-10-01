#!/usr/bin/env python3
"""ROM-free source/layout and production-function host checks for #600."""

from pathlib import Path
import re
import subprocess
import tempfile

from audit_early_running_lifecycle import c_function, check_source_contract
from test_settings_legacy_ux import PRET, char_codes, glyph_widths


ROOT = Path(__file__).resolve().parents[2]
BASE = "e4ffb9bae4b399867189134b8579b11cea600271"


def read(name):
    return (ROOT / name).read_text()


def main():
    menu = read("src/option_menu.c")
    save = read("src/save.c")
    config = read("src/config.h")
    hooks = read("assembly/hooks/general_hooks.s")
    engine = read("src/general_bs_commands.c")
    original = subprocess.check_output(
        ["git", "show", f"{BASE}:src/general_bs_commands.c"], cwd=ROOT, text=True)
    assert engine == original, "battle engine changed"
    sites = [i for i, line in enumerate(engine.splitlines(), 1)
             if "FlagGet(FLAG_FAST_BATTLE_MESSAGES)" in line]
    assert sites == [477, 547, 1261, 2004]
    assert re.search(r"^#define FLAG_FAST_BATTLE_MESSAGES 0x925\b", config, re.M)
    assert re.search(r"^#define SAVE_BLOCK_EXPANSION\b", config, re.M)
    assert not re.search(r"^\s*#define UNBOUND\b", config, re.M)
    assert "#define gExpandedFlags ((u8*) 0x0203B174)" in read("include/new/ram_locs.h")
    assert "#define SAVE_BLOCK_PARASITE 0x0203B174" in save
    assert "#define PARASITE_SIZE 0xEC4" in save
    assert "Memset((void*) SAVE_BLOCK_PARASITE, 0, 0x2EA4);" in save
    assert "NewGameSaveClearHook 8054A60 0" in read("hooks")
    assert "bl NewGameWipeNewSaveData" in hooks
    assert "ExpandedFlagsHook 806E5C0 1" in read("hooks")
    assert "bl GetExpandedFlagPointer" in hooks
    assert "SaveParasite();" in c_function(save, "u8 HandleWriteSector(u16 chunkId, const struct SaveBlockChunk* location)")
    assert "LoadParasite();" in c_function(save, "u8 HandleLoadSector(unusedArg u16 a1, const struct SaveBlockChunk* location)")
    check_source_contract()  # Existing post-reset defaults remain exactly four Vars.

    enum = re.search(r"enum\s*\{\s*MENUITEM_TRAINER_LEVEL_SCALING.*?\};", menu, re.S).group()
    items = re.findall(r"MENUITEM_\w+", enum)
    assert items == ["MENUITEM_TRAINER_LEVEL_SCALING", "MENUITEM_TRAINER_AI_PROFILE",
                     "MENUITEM_HARD_LEVEL_CAP", "MENUITEM_NUZLOCKE", "MENUITEM_WILD_PREBATTLE",
                     "MENUITEM_FAST_BATTLE_MESSAGES", "MENUITEM_CANCEL_PAGE_3", "MENUITEM_PAGE3_COUNT"]
    assert "[MENUITEM_FAST_BATTLE_MESSAGES] = gText_FastBattleMessages," in menu
    assert "{6, TRAINER_AI_PROFILE_MENU_OPTION_COUNT, 3, 2, 2, 2, 0};" in menu
    assert re.search(r"case MENUITEM_NUZLOCKE:\s*case MENUITEM_WILD_PREBATTLE:\s*"
                     r"case MENUITEM_FAST_BATTLE_MESSAGES:.*?sOffOnOptions\[", menu, re.S)
    entry = c_function(menu, "void CB2_OptionsMenuFromStartMenu(void)")
    assert "AllocZeroed(sizeof(struct OptionMenu))" in entry
    initialize = re.search(r"sOptionMenuPtr->option_thirdPage\[MENUITEM_FAST_BATTLE_MESSAGES\] =\s*"
                           r"FlagGet\(FLAG_FAST_BATTLE_MESSAGES\) \? 1 : 0;", entry).group()
    assert "FlagSet(" not in entry and "FlagClear(" not in entry
    close = c_function(menu, "void CloseAndSaveOptionMenu(u8 taskId)")
    apply = re.search(r"if \(sOptionMenuPtr->fastBattleMessagesModeDirty\)\s*"
                     r"ApplyFastBattleMessagesMode\(sOptionMenuPtr->option_thirdPage"
                     r"\[MENUITEM_FAST_BATTLE_MESSAGES\]\);", close).group()

    codes, widths = char_codes(), glyph_widths("Normal")
    label = re.search(r"#org @gText_FastBattleMessages\n([^\n]+)", read("strings/option_menu.string")).group(1)
    assert label == "Fast Battle Messages"
    pixels = sum(widths[codes[c]] for c in label)
    assert pixels == 112 and 8 + pixels < 0x82
    pret_menu = (PRET / "src/option_menu.c").read_text()
    assert re.search(r"\.tilemapTop = 7,\s*\.width = 26,\s*\.height = 12", pret_menu)
    fonts = (PRET / "src/new_menu_helpers.c").read_text()
    assert re.search(r"\[FONT_NORMAL\].*?\.maxLetterHeight = 14,", fonts, re.S)
    assert (7 - 1) * (14 - 1) + 2 + 14 <= 12 * 8
    assert "InitOptionMenuBg();" in menu and "x = 0x82;" in menu

    # Compile the actual input, dirty tracking, application, flag pointer,
    # new-save wipe and parasite copy functions; stub only host UI/I/O.
    enums = menu[menu.index("// Menu items"):menu.index("// Window Ids")]
    struct = re.search(r"struct OptionMenu\s*\{.*?\};", menu, re.S).group()
    counts = "\n".join(re.findall(r"static const u16 sOptionMenuItemCounts[^;]+;", menu))
    functions = "\n".join(c_function(menu, sig) for sig in (
        "static void MarkSecondPageOptionDirty(u16 selection)",
        "static void MarkThirdPageOptionDirty(u16 selection)",
        "static void ApplyFastBattleMessagesMode(u16 selection)",
        "u8 OptionMenu_ProcessInput(void)"))
    storage_functions = "\n".join(c_function(save, sig) for sig in (
        "u8* GetExpandedFlagPointer(u16 id)", "void NewGameWipeNewSaveData(void)",
        "void SaveParasite(void)", "static void LoadParasite(void)"))
    event = (PRET / "src/event_data.c").read_text()
    flag_functions = "\n".join(c_function(event, sig) for sig in (
        "bool8 FlagGet(u16 idx)", "bool8 FlagSet(u16 idx)", "bool8 FlagClear(u16 idx)"))
    harness = r'''
#include <assert.h>
#include <stdint.h>
#include <string.h>
#include <stddef.h>
typedef uint8_t u8;
typedef uint16_t u16;
typedef uint32_t u32;
typedef u8 bool8;
#define TRUE 1
#define FALSE 0
#define FLAG_FAST_BATTLE_MESSAGES 0x925
#define SAVE_BLOCK_EXPANSION
static u8 storage[0x2EA4];
static u16 Var8000;
#define gExpandedFlags storage
#define SAVE_BLOCK_PARASITE ((uintptr_t)storage)
#define SECTOR_DATA_SIZE 0xFF0
#define Memcpy memcpy
#define Memset memset
struct SaveSection { u8 data[SECTOR_DATA_SIZE]; u16 id; };
static struct SaveSection sector;
static struct SaveSection *gFastSaveSection = &sector;
static const u16 sSaveBlockParasiteSizes[3] = {0xCC, 0x258, 0xBA0};
'''+storage_functions+r'''
static u8 *GetFlagAddr(u16 id) { return GetExpandedFlagPointer(id); }
'''+flag_functions+r'''
#define TRAINER_AI_PROFILE_MENU_OPTION_COUNT 9
enum { DPAD_RIGHT=1, DPAD_LEFT=2, DPAD_UP=4, DPAD_DOWN=8,
       R_BUTTON=16, L_BUTTON=32, A_BUTTON=64, B_BUTTON=128 };
static u16 keys;
#define JOY_REPT(k) (keys & (k))
#define JOY_NEW(k) (keys & (k))
#define SE_SELECT 0
static void PlaySE(u16 unused) { (void)unused; }
'''+enums+struct+r'''
static struct OptionMenu state;
static struct OptionMenu *sOptionMenuPtr = &state;
'''+counts+functions+r'''
static void open_menu(void) {
    memset(&state, 0, sizeof(state));
'''+initialize+r'''
    state.page = 2;
    state.cursorPos = MENUITEM_FAST_BATTLE_MESSAGES;
}
static void close_menu(void) {
'''+apply+r'''
}
int main(void) {
    memset(storage, 0xFF, sizeof(storage));
    NewGameWipeNewSaveData();
    assert(GetExpandedFlagPointer(0x925) == storage + 4);
    assert(!FlagGet(0x925));
    for (int initial = 0; initial <= 1; initial++) {
        if (initial) FlagSet(0x925); else FlagClear(0x925);
        open_menu();
        assert(state.option_thirdPage[MENUITEM_FAST_BATTLE_MESSAGES] == initial);
        keys = A_BUTTON; assert(OptionMenu_ProcessInput() == 1);
        close_menu(); assert(FlagGet(0x925) == initial);
        open_menu();
        keys = B_BUTTON; assert(OptionMenu_ProcessInput() == 1);
        close_menu(); assert(FlagGet(0x925) == initial);
        // Editing a different flag option must not dirty D11.
        open_menu(); state.cursorPos = MENUITEM_NUZLOCKE;
        keys = DPAD_RIGHT; assert(OptionMenu_ProcessInput() == 4);
        assert(!state.fastBattleMessagesModeDirty);
        close_menu(); assert(FlagGet(0x925) == initial);
        for (int direction = DPAD_RIGHT; direction <= DPAD_LEFT; direction++) {
            open_menu(); keys = direction;
            assert(OptionMenu_ProcessInput() == 4);
            assert(state.fastBattleMessagesModeDirty);
            assert(FlagGet(0x925) == initial); // Deferred until close.
            close_menu(); assert(FlagGet(0x925) == !initial);
            sector.id = 0; SaveParasite();
            memset(storage, 0, sizeof(storage)); LoadParasite();
            assert(FlagGet(0x925) == !initial); // Actual parasite copy round-trip.
            open_menu(); assert(OptionMenu_ProcessInput() == 4);
            close_menu(); assert(FlagGet(0x925) == initial);
        }
    }
    open_menu(); keys = DPAD_DOWN;
    assert(OptionMenu_ProcessInput() == 3 && state.cursorPos == MENUITEM_CANCEL_PAGE_3);
    assert(OptionMenu_ProcessInput() == 3 && state.cursorPos == 0);
    keys = DPAD_UP;
    assert(OptionMenu_ProcessInput() == 3 && state.cursorPos == MENUITEM_CANCEL_PAGE_3);
    assert(OptionMenu_ProcessInput() == 3 && state.cursorPos == MENUITEM_FAST_BATTLE_MESSAGES);
    keys = L_BUTTON; assert(OptionMenu_ProcessInput() == 5 && state.page == 1);
    keys = R_BUTTON; assert(OptionMenu_ProcessInput() == 7 && state.page == 2);
    assert(OptionMenu_ProcessInput() == 0 && state.page == 2);
    assert(!state.fastBattleMessagesModeDirty);
    return 0;
}
'''
    with tempfile.TemporaryDirectory(prefix="cfru-fast-messages-") as directory:
        source, binary = Path(directory) / "test.c", Path(directory) / "test"
        source.write_text(harness)
        subprocess.run(["cc", "-std=c99", "-Wall", "-Wextra", "-Werror",
                        str(source), "-o", str(binary)], check=True)
        subprocess.run([str(binary)], check=True)
    print(f"Engine reads unchanged: {sites}; label: {pixels}/122 px; seven rows: PASS")
    print("Expanded flag byte 4/bit 5, default wipe, persistence copies, dirty edits, A/B close, navigation: PASS")


if __name__ == "__main__":
    main()
