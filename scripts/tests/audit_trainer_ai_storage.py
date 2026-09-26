#!/usr/bin/env python3
"""Exercise the production expanded-var pointer and audit the R1 profile slot."""

from pathlib import Path
import re
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[2]
PROFILE_ID = 0x515B
INDEX = PROFILE_ID - 0x5000
ADDRESS = 0x0203B174 + 0x200 + INDEX * 2


def require(condition, message):
    if not condition:
        raise SystemExit("Trainer AI storage closure failed: " + message)


def function(source, signature):
    start = source.index(signature)
    opened = source.index("{", start)
    depth = 0
    for pos in range(opened, len(source)):
        if source[pos] == "{":
            depth += 1
        elif source[pos] == "}":
            depth -= 1
            if depth == 0:
                return source[start:pos + 1]
    raise AssertionError(signature)


def main():
    save = (ROOT / "src/save.c").read_text()
    config = (ROOT / "src/config.h").read_text()
    ram = (ROOT / "include/new/ram_locs.h").read_text()
    hooks = (ROOT / "assembly/hooks/general_hooks.s").read_text()
    symbols = (ROOT / "BPRE.ld").read_text()
    settings = (ROOT / "src/settings.c").read_text()
    option = (ROOT / "src/option_menu.c").read_text()
    util = (ROOT / "src/util.c").read_text()
    require("#define VAR_TRAINER_AI_PROFILE 0x515B" in config, "profile ID changed")
    require("#define SAVE_BLOCK_EXPANSION" in config, "save expansion disabled")
    require("#define gExpandedVars ((u16*) (0x0203B174 + 0x200))" in ram,
            "expanded-var base or width changed")
    require(INDEX == 0x15B and ADDRESS == 0x0203B62A,
            "profile address arithmetic changed")
    require("#define SAVE_BLOCK_PARASITE 0x0203B174" in save
            and "#define PARASITE_SIZE 0xEC4" in save
            and 0 <= ADDRESS - 0x0203B174 < 0xEC4 - 1,
            "profile slot outside saved parasite")
    require("Memset((void*) SAVE_BLOCK_PARASITE, 0, 0x2EA4);" in save
            and save.index("Memset((void*) SAVE_BLOCK_PARASITE, 0, 0x2EA4);")
            < save.index("ApplyFreshNewGameSettings();"),
            "fresh default does not follow the whole expansion clear")
    require("NewGameSaveClearHook 8054A60 0" in (ROOT / "hooks").read_text()
            and "bl NewGameWipeNewSaveData" in hooks,
            "fresh new-game hook/clear path missing")
    hook = hooks[hooks.index("ExpandedVarsHook:"):hooks.index("ExpandedFlagsHook:")]
    for fragment in ("lsl r0, r0, #0x10", "lsr r4, r0, #0x10",
                     "bl GetExpandedVarPointer", "bne ExpandedVarsPop",
                     "ldr r0, =0x806E45C | 1", "pop {r4-r6,pc}"):
        require(fragment in hook, "expanded-var Thumb hook changed: " + fragment)
    require("ExpandedVarsHook 806E454 1" in (ROOT / "hooks").read_text(),
            "expanded-var hook insertion missing")
    for definition in ("GetVarPointer = 0x806E454 | 1;",
                       "VarGet = 0x806E568 | 1;",
                       "VarSet = 0x806E584 | 1;"):
        require(definition in symbols, "base variable API address changed: " + definition)
    require("VarSet(VAR_TRAINER_AI_PROFILE, TRAINER_AI_PROFILE_STANDARD + 1);" in settings
            and "VarSet(VAR_TRAINER_AI_PROFILE, TRAINER_AI_PROFILE_IRONMON_SMART + 1);" in settings,
            "new-game/preset raw mapping changed")
    require("trainerAIProfileOriginalRaw = VarGet(VAR_TRAINER_AI_PROFILE);" in option
            and "trainerAIProfileDirty" in option
            and "VarSet(VAR_TRAINER_AI_PROFILE," in option,
            "option menu load/dirty/save closure changed")
    require("case TRAINER_AI_PROFILE_STANDARD + 1:" in util
            and "case TRAINER_AI_PROFILE_IRONMON_SMART + 1:" in util,
            "profile decoder changed")

    get_pointer = function(save, "u16* GetExpandedVarPointer(u16 id)")
    harness = f'''#include <assert.h>
#include <stdint.h>
#include <stddef.h>
typedef uint16_t u16;
#define SAVE_BLOCK_EXPANSION 1
#define VARS_START 0x4000
#define SPECIAL_VARS_START 0x8000
static u16 storage[0x200];
#define gExpandedVars storage
{get_pointer}
int main(void) {{
    assert(GetExpandedVarPointer(0x515B) == &storage[0x15B]);
    *GetExpandedVarPointer(0x515B) = 7;
    assert(storage[0x15B] == 7);
    *GetExpandedVarPointer(0x515B) = 8;
    assert(storage[0x15B] == 8);
    assert(GetExpandedVarPointer(0x5000) == &storage[0]);
    assert(GetExpandedVarPointer(0x51FF) == &storage[0x1FF]);
    assert(GetExpandedVarPointer(0x5200) == (u16*)1);
    return 0;
}}
'''
    with tempfile.TemporaryDirectory(prefix="cfru-profile-storage-") as temporary:
        src = Path(temporary) / "storage.c"
        binary = Path(temporary) / "storage"
        src.write_text(harness)
        subprocess.run(["cc", "-std=c99", "-Wall", "-Wextra", "-Werror",
                        str(src), "-o", str(binary)], check=True)
        subprocess.run([str(binary)], check=True)

    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
    unexpected = []
    for name in tracked:
        if not name or name.startswith(("deps/", "docs/", "scripts/tests/")):
            continue
        if not name.endswith((".c", ".h", ".s", ".inc", ".string", ".json")):
            continue
        source = (ROOT / name).read_text(errors="ignore")
        if re.search(r"0x0*515b\b|\b20827\b|0x0*203b62a\b", source, re.I):
            if name not in {"src/config.h", "assembly/followingmon_normal_pals.s"}:
                unexpected.append(name)
    require(not unexpected, "unexpected direct profile ID/address sources: " + repr(unexpected))
    print("profile raw 7/8, production expanded-var pointer index 0x15B/address 0x0203B62A, source write/clear audit: PASS")


if __name__ == "__main__":
    main()
