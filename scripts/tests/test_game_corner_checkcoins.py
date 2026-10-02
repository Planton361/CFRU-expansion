#!/usr/bin/env python3
"""#611 ROM-free production command and pinned vanilla caller regressions.

Requires the persistent Workspace's pret reference. Host adapters own only
operand/Var access and RAM storage; wallet/command bodies are production C.
Caller models cover eligibility/capacity, not acquire UI or emulator rendering.
"""
from pathlib import Path
import re
import subprocess
import tempfile

from audit_early_running_lifecycle import c_function

ROOT = Path(__file__).resolve().parents[2]
PRET = ROOT.parent / "references/pret-pokefirered"
BASE = "ebdc896f7bf740bd62ad19ef30af37cac3e88554"
PRET_SHA = "e060ab955b5dc9ac1c4904c2cd141683615cf477"
BALANCES = (0, 1, 9999, 65535, 65536, 65716, 75535, 999999999)
EXPORTS = (0, 1, 9999, 65535, 65535, 65535, 65535, 65535)


def git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def read(path):
    return (ROOT / path).read_text()


def pinned(path):
    return git(PRET, "show", f"{PRET_SHA}:{path}")


def block(source, label):
    return source.split(label + "::", 1)[1].split("\n\n", 1)[0]


def main():
    assert git(ROOT, "rev-parse", BASE) == BASE
    assert git(ROOT, "merge-base", BASE, "HEAD") == BASE
    assert git(PRET, "rev-parse", "HEAD") == PRET_SHA
    source, config = read("src/scripting.c"), read("src/config.h")
    original = git(ROOT, "show", f"{BASE}:src/scripting.c")
    command_sig = "bool8 scrB3_CheckCoins(struct ScriptContext *ctx)"
    command = c_function(source, command_sig)
    old_command = c_function(original, command_sig)
    vanilla = command.split("#ifndef REPLACE_SOME_VANILLA_SPECIALS", 1)[1].split("#else", 1)[0]
    assert vanilla.count("ScriptReadHalfword(ctx)") == 1
    assert "GetVarPointer(ScriptReadHalfword(ctx))" in vanilla
    assert "ScriptReadWord" not in vanilla
    assert command.split("#else", 1)[1] == old_command.split("#else", 1)[1]
    signatures = ("u32 GetCoins(void)", "void SetCoins(u32 numCoins)",
                  "bool8 GiveCoins(u32 toAdd)", "bool8 TakeCoins(u32 toTake)",
                  "bool8 scrB4_AddCoins(struct ScriptContext *ctx)",
                  "bool8 scrB5_SubtractCoins(struct ScriptContext *ctx)")
    for signature in signatures:
        assert c_function(source, signature) == c_function(original, signature), signature
    # Entire production diff is bounded to this command and the stale warning.
    assert source.replace(command, old_command, 1).strip() == original
    old_config = git(ROOT, "show", f"{BASE}:src/config.h")
    assert config.strip() == old_config.replace(" Breaks FR Game Corner prize room", "")
    assert "Breaks FR Game Corner prize room" not in config
    for name in ("SAVE_BLOCK_EXPANSION", "ITEM_PICTURE_ACQUIRE", "ITEM_DESCRIPTION_ACQUIRE"):
        assert re.search(r"^#define " + name + r"\b", config, re.M)
    assert re.search(r"^#define MAX_COINS_DIGITS 9\b", config, re.M)
    assert not re.search(r"^\s*#\s*define\s+REPLACE_SOME_VANILLA_SPECIALS\b", config, re.M)
    assert "#define gPlayerCoins (*((u32*) 0x203B814))" in read("include/new/ram_locs.h")
    for path in ("src/save.c", "include/new/ram_locs.h", "routinepointers", "hooks",
                 "assembly/overworld_scripts/system_scripts.s"):
        assert read(path).strip() == git(ROOT, "show", f"{BASE}:{path}"), path

    prize = pinned("data/maps/CeladonCity_GameCorner_PrizeRoom/scripts.inc")
    corner = pinned("data/maps/CeladonCity_GameCorner/scripts.inc")
    hidden = pinned("data/scripts/obtain_item.inc")
    prefix = "CeladonCity_GameCorner_PrizeRoom_EventScript_"
    prices = {}
    for name, expected in (("Abra", 180), ("Porygon", 9999),
                           ("TM13", 4000), ("MiracleSeed", 1000)):
        entry = block(prize, prefix + name)
        if name in ("Abra", "Porygon"):
            assert entry.lstrip().startswith(".ifdef FIRERED")
        price = int(re.search(r"setvar VAR_TEMP_2, (\d+)", entry).group(1))
        assert price == expected
        prices[name] = price
    for name in ("ConfirmPrizeMon", "TryGivePrize"):
        assert re.search(r"checkcoins VAR_RESULT\s+goto_if_lt VAR_RESULT, VAR_TEMP_2, "
                         + prefix + "NotEnoughCoins", block(prize, prefix + name))
    assert "removecoins VAR_TEMP_2" in block(prize, prefix + "TryGivePrize")
    assert "giveitem VAR_TEMP_1" in block(prize, prefix + "TryGivePrize")
    assert "removecoins VAR_TEMP_2" in prize and "givemon VAR_TEMP_1" in prize
    vanilla_max = int(re.search(r"#define MAX_COINS (\d+)",
                               pinned("include/constants/coins.h")).group(1))
    assert vanilla_max == 9999
    capacities = {}
    for name, amount in (("Buy500Coins", 500), ("Buy50Coins", 50),
                         ("Fisher", 10), ("Scientist", 20), ("Gentleman", 20)):
        entry = block(corner, "CeladonCity_GameCorner_EventScript_" + name)
        match = re.search(r"checkcoins VAR_TEMP_1\s+goto_if_ge VAR_TEMP_1, "
                          r"\(MAX_COINS \+ 1\) - (\d+), (\w+NoRoomForCoins)", entry)
        assert match and int(match.group(1)) == amount
        assert f"addcoins {amount}" in entry
        capacities[name] = vanilla_max + 1 - amount
    hidden_entry = block(hidden, "EventScript_TryPickUpHiddenCoins")
    assert re.search(r"checkcoins VAR_RESULT\s+specialvar VAR_RESULT, CheckAddCoins\s+"
                     r"goto_if_eq VAR_RESULT, FALSE, EventScript_HiddenCoinsButCaseIsFull\s+"
                     r"addcoins VAR_0x8006", hidden_entry)
    hidden_check = c_function(pinned("src/field_specials.c"), "bool8 CheckAddCoins(void)")
    assert "gSpecialVar_Result + gSpecialVar_0x8006 > 9999" in hidden_check

    max_defines = source.split("//////////////////EXPANDED COINS///////////////////////", 1)[1].split("u32 GetCoins(void)", 1)[0]
    profile = "\n".join(re.findall(r"^#define (?:SAVE_BLOCK_EXPANSION\b[^\n]*|MAX_COINS_DIGITS\b[^\n]*)", config, re.M))
    functions = "\n".join(c_function(source, sig) for sig in signatures) + "\n" + command
    harness = r'''
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
typedef uint8_t u8;
typedef uint16_t u16;
typedef uint32_t u32;
typedef u8 bool8;
#define TRUE 1
#define FALSE 0
static u32 gPlayerCoins;
static u16 vars[3], gSpecialVar_LastResult, gSpecialVar_0x8006;
#define gSpecialVar_Result vars[1]
struct ScriptContext { const u8 *scriptPtr; unsigned reads; };
static u16 ScriptReadHalfword(struct ScriptContext *ctx) {
    u16 value = ctx->scriptPtr[0] | (ctx->scriptPtr[1] << 8);
    ctx->scriptPtr += 2; ctx->reads++; return value;
}
static u16 *GetVarPointer(u16 id) { assert(id == 0x4001); return &vars[1]; }
static u16 VarGet(u16 value) { return value; }
''' + profile + max_defines + functions + hidden_check + r'''
static u16 exported(u32 balance) {
    const u8 operands[] = {0x01, 0x40, 0xA5, 0x5A};
    struct ScriptContext ctx = {operands, 0};
    SetCoins(balance); vars[0] = 0x1234; vars[1] = 0xABCD; vars[2] = 0x5678;
    gSpecialVar_LastResult = 0xBEEF;
    assert(scrB3_CheckCoins(&ctx) == FALSE);
    assert(ctx.scriptPtr == operands + 2 && ctx.reads == 1);
    assert(vars[0] == 0x1234 && vars[2] == 0x5678);
    assert(gSpecialVar_LastResult == 0xBEEF && GetCoins() == balance);
    return vars[1];
}
int main(void) {
    const u32 balances[] = {''' + ",".join(map(str, BALANCES)) + r'''};
    const u16 expected[] = {''' + ",".join(map(str, EXPORTS)) + r'''};
    const u16 prices[] = {''' + ",".join(map(str, prices.values())) + r'''};
    assert(sizeof(gPlayerCoins) == 4 && MAX_COINS == 999999999);
    for (unsigned i = 0; i < sizeof(balances)/sizeof(*balances); i++) {
        assert(exported(balances[i]) == expected[i]);
        printf("%u -> %u\n", balances[i], vars[1]);
        for (unsigned j = 0; j < sizeof(prices)/sizeof(*prices); j++) {
            SetCoins(balances[i]);
            assert(TakeCoins(prices[j]) == (balances[i] >= prices[j]));
            assert(GetCoins() == (balances[i] >= prices[j] ? balances[i] - prices[j] : balances[i]));
        }
        // Execute the pinned hidden-coins capacity special with actual export.
        for (u16 amount = 10; amount <= 20; amount += 10) {
            exported(balances[i]); gSpecialVar_0x8006 = amount;
            assert(CheckAddCoins() == (balances[i] + amount <= 9999));
        }
    }
    // Vanilla command subtraction still uses the full-width production wallet.
    for (unsigned j = 0; j < sizeof(prices)/sizeof(*prices); j++) {
        u8 operand[] = {prices[j] & 255, prices[j] >> 8};
        struct ScriptContext ctx = {operand, 0};
        SetCoins(MAX_COINS);
        assert(scrB5_SubtractCoins(&ctx) == FALSE && ctx.reads == 1);
        assert(GetCoins() == MAX_COINS - prices[j] && gSpecialVar_LastResult == FALSE);
    }
    SetCoins(MAX_COINS - 1); assert(GiveCoins(20) && GetCoins() == MAX_COINS);
    assert(!GiveCoins(1) && GetCoins() == MAX_COINS);
    SetCoins(65536); assert(GiveCoins(500) && GetCoins() == 66036);
    { const u8 operand[] = {50, 0}; struct ScriptContext ctx = {operand, 0};
      assert(scrB4_AddCoins(&ctx) == FALSE && ctx.reads == 1);
      assert(GetCoins() == 66086 && gSpecialVar_LastResult == FALSE); }
    // Export each caller boundary for the source-derived Python models.
    for (unsigned j = 0; j < sizeof(prices)/sizeof(*prices); j++)
        printf("model %u %u\n", 65536 + prices[j], exported(65536 + prices[j]));
    for (u32 balance = 0; balance <= 10000; balance++) {
        printf("model %u %u\n", balance, exported(balance));
        for (u16 amount = 10; amount <= 20; amount += 10) {
            gSpecialVar_0x8006 = amount;
            assert(CheckAddCoins() == (balance + amount <= 9999));
        }
    }
    return 0;
}
'''
    with tempfile.TemporaryDirectory(prefix="cfru-checkcoins-") as directory:
        host, binary = Path(directory) / "test.c", Path(directory) / "test"
        host.write_text(harness)
        subprocess.run(["cc", "-std=c99", "-Wall", "-Wextra", "-Werror",
                        str(host), "-o", str(binary)], check=True)
        output = subprocess.check_output([str(binary)], text=True)
    exports = {}
    for line in output.splitlines():
        if line.startswith("model "):
            _, balance, value = line.split()
            exports[int(balance)] = int(value)
        else:
            balance, value = line.split(" -> ")
            exports[int(balance)] = int(value)
            print(line)
    # Pinned goto_if_lt and goto_if_ge semantics, driven by production results.
    for name, price in prices.items():
        for balance in (0, price - 1, price, price + 1, 9999, 65536 + price, *BALANCES):
            eligible = not (exports[balance] < price)
            assert eligible == (balance >= price), (name, balance)
        print(f"Prize {name} {price}: insufficient/exact/normal/high eligibility PASS")
    for name, threshold in capacities.items():
        for balance in (0, threshold - 1, threshold, 9999, *BALANCES):
            rejected = exports[balance] >= threshold
            assert rejected == (balance >= threshold), (name, balance)
        print(f"Capacity {name} >= {threshold}: vanilla boundary/high rejection PASS")
    for amount in (10, 20):
        for balance in (0, 9999 - amount, 10000 - amount, 9999, *BALANCES):
            full = exports[balance] + amount > 9999
            assert full == (balance + amount > 9999)
    print("Hidden Coins: pinned CheckAddCoins 10/20 boundaries/high full PASS")
    print("Base/config, wallet/add/subtract identity, one-halfword/u16/FALSE ABI, full-width subtraction, 9-digit maximum: PASS")
    print("Temporary host source/binary: deleted; acquire UI/SaveBlock/layout/pointers unchanged")


if __name__ == "__main__":
    main()
