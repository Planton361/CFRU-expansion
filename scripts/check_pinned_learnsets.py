#!/usr/bin/env python3
"""ROM-free source ownership and actual initial-moveset host checks."""
import hashlib
import json
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "827fa1ef04bd43e5c6bad5c47f7d8690ea6823ec"
REFERENCE = "b1156ff19204e48089e2384eb2c9c1a8004f57ce"
TABLE = "src/Tables/level_up_learnsets.c"
BLOCK = re.compile(r"static const struct LevelUpMove (s\w+)\[\] = \{.*?\};", re.S)


def require(condition, message):
    if not condition:
        raise ValueError("Pinned learnsets fail-closed: " + message)


def baseline(path):
    return subprocess.check_output(["git", "-C", str(ROOT), "show", BASE + ":" + path], text=True)


def validate_source(before, after, record):
    require(record["canonical_cfru_pin"] == BASE and record["showdown_revision"] == REFERENCE, "wrong source provenance")
    require(hashlib.sha256(before.encode()).hexdigest() == record["baseline_sha256"], "wrong baseline contents")
    require(hashlib.sha256(after.encode()).hexdigest() == record["candidate_sha256"], "candidate source hash mismatch")
    old = {m[1]: m[0] for m in BLOCK.finditer(before)}
    new = {m[1]: m[0] for m in BLOCK.finditer(after)}
    require(old.keys() == new.keys(), "added/removed/renamed table")
    require(BLOCK.sub(lambda m: m[1], before) == BLOCK.sub(lambda m: m[1], after), "text outside table bodies changed")
    changed = sorted(name for name in old if old[name] != new[name])
    require(changed == record["changed_tables"] and len(changed) == 89, "unapproved table replacement")
    require(not set(changed).intersection(record["blocked_shared_tables"]), "blocked shared table was written")


def check_source_contract():
    record = json.loads((ROOT / "docs/pinned-learnsets-provenance.json").read_text())
    validate_source(baseline(TABLE), (ROOT / TABLE).read_text(), record)
    for path in ("src/learn_move.c", "include/new/learn_move.h", "include/pokemon.h",
                 "include/constants/moves.h", "include/constants/species.h", "src/config.h"):
        require((ROOT / path).read_text() == baseline(path), "engine/layout/config changed: " + path)
    print("PASS: exactly 89 approved tables; blocked tables, pointers, outside text and engine/layout unchanged")


def function(source, name):
    match = re.search(r"void " + name + r"\([^)]*\)\s*\{", source)
    require(match is not None, "missing initial-moveset function")
    end, depth = match.end(), 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[match.start():end]


def check_host():
    source = re.sub(r"^#include[^\n]*\n", "", (ROOT / TABLE).read_text(), flags=re.M)
    initial = function((ROOT / "src/learn_move.c").read_text(), "GiveBoxMonInitialMoveset")
    harness = r'''
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include "include/constants/moves.h"
#include "include/constants/species.h"
typedef uint8_t u8; typedef uint16_t u16; typedef int32_t s32;
struct LevelUpMove {u16 move; u8 level;};
struct BoxPokemon {u16 species; s32 level; u16 moves[4]; int count;};
#define MAX_LEARNABLE_MOVES 50
#define MAX_MON_MOVES 4
#define MON_DATA_SPECIES 0
u16 GetBoxMonData(struct BoxPokemon* m, int f, void* p){(void)f;(void)p;return m->species;}
s32 GetLevelFromBoxMonExp(struct BoxPokemon* m){return m->level;}
int FlagGet(int flag){(void)flag;return 0;} /* Normal pilot, no in-engine move shuffle. */
u16 RandomizeMove(u16 move){(void)move;abort();}
u16 GiveMoveToBoxMon(struct BoxPokemon* m,u16 move){
    for(int i=0;i<m->count;i++)if(m->moves[i]==move)return 0xFFFE;
    if(m->count==4)return 0xFFFF;
    m->moves[m->count++]=move; return move;
}
/* TABLES */
/* INITIAL */
static void require(int ok){if(!ok){fprintf(stderr,"initial-moveset invariant failed\n");exit(1);}}
int main(void){
    int tested=0,missing=0,noL1=0;
    for(size_t species=0;species<sizeof(gLevelUpLearnsets)/sizeof(gLevelUpLearnsets[0]);species++){
        const struct LevelUpMove* table=gLevelUpLearnsets[species];
        if(!table){require(species==SPECIES_ZARUDE_DADA);missing++;continue;}
        int rows=0,prev=0;
        while(table[rows].level!=255){
            require(rows<50 && table[rows].level>=prev && table[rows].level<=100);
            require(table[rows].move>0 && table[rows].move<MOVES_COUNT);
            prev=table[rows].level;rows++;
        }
        require(table[rows].move==0);
        if(rows==0 || table[0].level>1)noL1++;
        for(int level=1;level<=100;level++){
            struct BoxPokemon actual={.species=(u16)species,.level=level};
            struct BoxPokemon expected={.species=(u16)species,.level=level};
            int eligible=0;
            while(eligible<rows && table[eligible].level<=level)eligible++;
            for(int i=eligible>4?eligible-4:0;i<eligible;i++)GiveMoveToBoxMon(&expected,table[i].move);
            GiveBoxMonInitialMoveset(&actual);
            require(actual.count==expected.count);
            for(int i=0;i<actual.count;i++)require(actual.moves[i]==expected.moves[i]);
            tested++;
        }
    }
    require(tested==143900 && missing==1 && noL1==65);
    printf("PASS: actual GiveBoxMonInitialMoveset, %d species/level cases; %d source pointer holes; %d bindings lack L1 moves (documented, not repaired by fallback)\n",tested,missing,noL1);
}
'''
    with tempfile.TemporaryDirectory(prefix="pinned-learnsets-host-") as tmp:
        test = Path(tmp) / "initial.c"
        binary = Path(tmp) / "initial-test"
        test.write_text(harness.replace("/* TABLES */", source).replace("/* INITIAL */", initial))
        subprocess.run(["cc", "-std=c11", "-O1", "-Wall", "-Wextra", "-Werror",
                        "-fsanitize=undefined,bounds,address", "-I", str(ROOT), str(test), "-o", str(binary)], check=True)
        subprocess.run([str(binary)], check=True)


def check_rejections():
    record = json.loads((ROOT / "docs/pinned-learnsets-provenance.json").read_text())
    before, after = baseline(TABLE), (ROOT / TABLE).read_text()
    cases = [after.replace("MOVE_SCRATCH", "MOVE_NONE", 1),
             after + "\n/* unapproved outside text */\n",
             after.replace("sRotomLevelUpLearnset[] = {", "sRotomLevelUpLearnset[] = {\n LEVEL_UP_MOVE(1, MOVE_TACKLE),", 1)]
    for modified in cases:
        # Recompute the manifest hash to exercise the structural allowlist too.
        test_record = {**record, "candidate_sha256": hashlib.sha256(modified.encode()).hexdigest()}
        try:
            validate_source(before, modified, test_record)
        except ValueError:
            continue
        raise AssertionError("unapproved edit accepted")
    print("PASS: unrelated/blocked source mutations rejected")


if __name__ == "__main__":
    check_source_contract()
    check_rejections()
    check_host()
