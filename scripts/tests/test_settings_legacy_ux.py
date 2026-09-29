#!/usr/bin/env python3
"""ROM-free pixel and menu-index checks for Workspace Issue #547."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
PRET = ROOT.parent / "references" / "pret-pokefirered"
MENU = (ROOT / "src/option_menu.c").read_text()
STRINGS = (ROOT / "strings/option_menu.string").read_text()
PRET_MENU = (PRET / "src/option_menu.c").read_text()
PRET_TEXT = (PRET / "src/text.c").read_text()
PRET_FONTS = (PRET / "src/new_menu_helpers.c").read_text()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def glyph_widths(font: str) -> list[int]:
    match = re.search(
        rf"static const u8 sFont{font}LatinGlyphWidths\[\] =\s*\{{(.*?)\}};",
        PRET_TEXT, re.S,
    )
    require(match is not None, f"missing {font} source glyph widths")
    return [int(value) for value in re.findall(r"\d+", match.group(1))]


def char_codes() -> dict[str, int]:
    result = {}
    for line in (ROOT / "charmap.tbl").read_text(encoding="utf-8-sig").splitlines():
        match = re.fullmatch(r"([0-9A-F]{2})=(.)", line)
        if match:
            result[match.group(2)] = int(match.group(1), 16)
    return result


def text_strings() -> dict[str, str]:
    return dict(re.findall(r"^#org @(\w+)\n([^\n]+)", STRINGS, re.M))


def table(name: str) -> list[str]:
    match = re.search(rf"{name}\[[^]]*\] =\s*\{{(.*?)\}};", MENU, re.S)
    require(match is not None, f"missing table {name}")
    return re.findall(r"gText_\w+", match.group(1))


def main() -> None:
    codes = char_codes()
    normal = glyph_widths("Normal")
    small = glyph_widths("Small")

    def width(value: str, font: list[int]) -> int:
        return sum(font[codes[character]] for character in value)

    # The CFRU code calls the unchanged pret window initializer and uses
    # font 2 at x=0x82. The original window is 26 tiles = 208 local pixels.
    require("InitOptionMenuBg();" in MENU, "option menu initializer changed")
    require(re.search(r"\.tilemapLeft = 2,\s*\.tilemapTop = 7,\s*\.width = 26", PRET_MENU),
            "option value window geometry changed")
    require("FONT_NORMAL" in PRET_FONTS and ".letterSpacing = 1" in PRET_FONTS,
            "font source changed")
    require("x = 0x82;" in MENU, "option value alignment changed")
    require("FillWindowPixelRect(1, 1, x, y, 0x4E," in MENU,
            "the full 78-pixel value field is not cleared")
    require("AddTextPrinterParameterized3(1, 2, x, y, dst, -1," in MENU,
            "option value font/render path changed")
    require("if (fontId != FONT_BRAILLE && isJapanese)" in PRET_TEXT,
            "English glyph width semantics changed")
    value_limit = 26 * 8 - 0x82
    require(value_limit == 78, "unexpected value-field pixel limit")

    expected_scaling = [
        "gText_DifficultyAutoOption", "gText_OffOption", "gText_Easy",
        "gText_Normal", "gText_Hard", "gText_Expert",
    ]
    expected_ai = [
        "gText_DifficultyAutoOption", "gText_LegacyVanillaOption",
        "gText_LegacyEasyOption", "gText_LegacyNormalOption",
        "gText_LegacyHardOption", "gText_LegacyExpertOption",
        "gText_LegacySmartOption", "gText_StandardOption",
        "gText_IronmonSmartOption",
    ]
    require(table("sTrainerLevelScalingOptions") == expected_scaling,
            "Trainer Scaling raw 0..5 menu indexes changed")
    require(table("sTrainerAIProfileOptions") == expected_ai,
            "Trainer AI raw 0..8 menu indexes changed")
    require(table("sGameDifficultyOptions") == [
        "gText_VanillaOption", "gText_Easy", "gText_Normal",
        "gText_Hard", "gText_Expert",
    ], "Difficulty menu indexes changed")
    require(table("sHardLevelCapOptions") == [
        "gText_AutoOption", "gText_OffOption", "gText_OnOption",
    ], "Hard Cap raw indexes changed")

    labels = text_strings()
    exact = {
        "gText_DifficultyAutoOption": ("Auto (Diff.)", 64),
        "gText_LegacyVanillaOption": ("Legacy Vanil.", 73),
        "gText_LegacyEasyOption": ("Legacy Easy", 65),
        "gText_LegacyNormalOption": ("Legacy Normal", 76),
        "gText_LegacyHardOption": ("Legacy Hard", 65),
        "gText_LegacyExpertOption": ("Legacy Expert", 76),
        "gText_LegacySmartOption": ("Legacy Smart", 70),
        "gText_StandardOption": ("Standard", 45),
        "gText_IronmonSmartOption": ("Ironmon Smart", 73),
    }
    for symbol, (literal, pixels) in exact.items():
        require(labels[symbol] == literal, f"{symbol} text changed")
        require(width(literal, normal) == pixels, f"{symbol} width changed")
        require(pixels <= value_limit, f"{symbol} overflows the value window")
        print(f"{literal}: {pixels}/{value_limit} px")
    require(width("Legacy Vanilla", normal) == 79,
            "full Legacy Vanilla width no longer explains the shortened label")
    require(labels["gText_AutoOption"] == "Auto", "Hard Cap Auto changed")

    # The Options menu has no per-setting description region. Its page hint
    # is the only help text, right aligned within the 240-pixel header window.
    footer = labels["gText_PickSwitchCancel_Page3"]
    require(footer == "[L_BUTTON][R_BUTTON]Page 3 [DPAD_UP_DOWN]Pick "
            "[DPAD_LEFT_RIGHT]Switch [A_BUTTON][B_BUTTON]Cancel",
            "Page 3 help text changed")
    for token, pixels in (("L_BUTTON", 16), ("R_BUTTON", 16),
                          ("DPAD_UP_DOWN", 8), ("DPAD_LEFT_RIGHT", 8),
                          ("A_BUTTON", 8), ("B_BUTTON", 8)):
        require(re.search(rf"\[CHAR_{token.replace('UP_DOWN', 'UPDOWN').replace('LEFT_RIGHT', 'LEFTRIGHT')}\]"
                          rf"\s*=\s*\{{[^}}]*,\s*{pixels},\s*12\s*\}}", PRET_TEXT),
                f"keypad icon width changed: {token}")
    help_plain = re.sub(r"\[[A-Z_]+\]", "", footer)
    help_width = width(help_plain, small) + 16 + 16 + 8 + 8 + 8 + 8
    require(help_width == 187, "Page 3 help width changed")
    require("x = 0xE4 - GetStringWidth(0, gText_PickSwitchCancel_Page3, 0);" in MENU,
            "Page 3 help alignment changed")
    require(0 <= 0xE4 - help_width and 0xE4 <= 30 * 8,
            "Page 3 help exceeds its window")
    print(f"Page 3 help: {help_width} px, x={0xE4 - help_width}, end=228/240 px")
    print("Settings legacy UX labels, indexes and pixel layout: PASS")


if __name__ == "__main__":
    main()
