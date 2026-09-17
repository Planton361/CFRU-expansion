#!/usr/bin/env python3
"""ROM-free exact data ownership and actual initial-moveset host regression."""
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
MANIFEST = "docs/coherent-learnsets-provenance.json"
BLOCK = re.compile(r"static const struct LevelUpMove (s\w+)\[\] = \{.*?\};", re.S)
BINDINGS = {
    "SPECIES_PIKACHU_COSPLAY": "sPikachuCosplayLevelUpLearnset",
    "SPECIES_PIKACHU_LIBRE": "sPikachuCosplayLevelUpLearnset",
    "SPECIES_PIKACHU_POP_STAR": "sPikachuCosplayLevelUpLearnset",
    "SPECIES_PIKACHU_ROCK_STAR": "sPikachuCosplayLevelUpLearnset",
    "SPECIES_PIKACHU_BELLE": "sPikachuCosplayLevelUpLearnset",
    "SPECIES_PIKACHU_PHD": "sPikachuCosplayLevelUpLearnset",
    "SPECIES_PICHU_SPIKY": "sPichuSpikyLevelUpLearnset",
    "SPECIES_ZARUDE_DADA": "sZarudeLevelUpLearnset",
}


def require(condition, message):
    if not condition:
        raise ValueError("Coherent learnsets fail-closed: " + message)


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def baseline(path):
    return subprocess.check_output(["git", "-C", str(ROOT), "show", BASE + ":" + path], text=True)


def validate_source(before, after, record):
    require(record["canonical_cfru_pin"] == BASE and record["showdown_revision"] == REFERENCE, "wrong source provenance")
    require(record["historical_showdown_revision"] == "UNKNOWN", "historical provenance invented")
    require(sha(before) == record["baseline_sha256"] and sha(after) == record["candidate_sha256"], "source hash mismatch")
    old = {m[1]: m[0] for m in BLOCK.finditer(before)}
    new = {m[1]: m[0] for m in BLOCK.finditer(after)}
    added = {"sPikachuCosplayLevelUpLearnset", "sPichuSpikyLevelUpLearnset"}
    require(new.keys() - old.keys() == added and not old.keys() - new.keys(), "unapproved table addition/removal")
    changed = {name for name in old if old[name] != new[name]}
    require(len(changed) == 820, "unexpected canonical table change count")
    require(changed | added == record["approved_table_sha256"].keys(), "unapproved table replacement")
    for name in changed | added:
        require(sha(new[name]) == record["approved_table_sha256"][name], "unapproved table body: " + name)
    expected = before
    for constant, target in BINDINGS.items():
        if constant == "SPECIES_ZARUDE_DADA":
            anchor = "const struct LevelUpMove* const gLevelUpLearnsets[] =\n{"
            require(expected.count(anchor) == 1, "pointer insertion anchor drift")
            expected = expected.replace(anchor, anchor + f"\n\t[{constant}] = {target},", 1)
        else:
            expected, count = re.subn(r"(\[" + constant + r"\]\s*=\s*)s\w+", lambda m: m[1] + target, expected)
            require(count == 1, "pointer replacement anchor drift")
    normalized = after
    for name in added:
        require(normalized.count(new[name] + "\n\n") == 1, "new table boundary drift")
        normalized = normalized.replace(new[name] + "\n\n", "", 1)
    require(BLOCK.sub(lambda m: m[1], normalized) == BLOCK.sub(lambda m: m[1], expected),
            "text outside approved tables/pointer rows changed")


def check_source_contract():
    record = json.loads((ROOT / MANIFEST).read_text())
    validate_source(baseline(TABLE), (ROOT / TABLE).read_text(), record)
    for path in ("src/learn_move.c", "include/new/learn_move.h", "include/pokemon.h",
                 "include/constants/moves.h", "include/constants/species.h", "src/config.h"):
        require((ROOT / path).read_text() == baseline(path), "engine/layout/config changed: " + path)
    print("PASS: 820 exact table replacements, 2 new form tables, 7 rebindings, 1 existing-ID null-pointer repair; engine unchanged")


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
int FlagGet(int flag){(void)flag;return 0;}
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
    int tested=0,noL1=0;
    require(gLevelUpLearnsets[SPECIES_ZARUDE_DADA]==sZarudeLevelUpLearnset);
    require(gLevelUpLearnsets[SPECIES_PICHU_SPIKY]==sPichuSpikyLevelUpLearnset);
    require(gLevelUpLearnsets[SPECIES_PICHU]==sPichuLevelUpLearnset);
    require(gLevelUpLearnsets[SPECIES_PIKACHU]==sPikachuLevelUpLearnset);
    const u16 cosplay[]={SPECIES_PIKACHU_COSPLAY,SPECIES_PIKACHU_LIBRE,
        SPECIES_PIKACHU_POP_STAR,SPECIES_PIKACHU_ROCK_STAR,SPECIES_PIKACHU_BELLE,SPECIES_PIKACHU_PHD};
    for(size_t i=0;i<sizeof(cosplay)/sizeof(cosplay[0]);i++)
        require(gLevelUpLearnsets[cosplay[i]]==sPikachuCosplayLevelUpLearnset);
    for(size_t species=0;species<sizeof(gLevelUpLearnsets)/sizeof(gLevelUpLearnsets[0]);species++){
        const struct LevelUpMove* table=gLevelUpLearnsets[species];
        require(table!=NULL);
        int rows=0,prev=0;
        while(table[rows].level!=255){
            require(rows<50 && table[rows].level>=prev && table[rows].level<=100);
            require(table[rows].move>0 && table[rows].move<MOVES_COUNT);
            prev=table[rows].level;rows++;
        }
        require(table[rows].move==0);
        if(rows==0 || table[0].level>1){require(table==sEmptyMoveset);noL1++;}
        for(int level=1;level<=100;level++){
            struct BoxPokemon actual={.species=(u16)species,.level=level};
            struct BoxPokemon expected={.species=(u16)species,.level=level};
            int eligible=0;
            while(eligible<rows && table[eligible].level<=level)eligible++;
            for(int i=eligible>4?eligible-4:0;i<eligible;i++)GiveMoveToBoxMon(&expected,table[i].move);
            GiveBoxMonInitialMoveset(&actual);
            require(actual.count==expected.count);
            require(table==sEmptyMoveset || actual.count>0);
            for(int i=0;i<actual.count;i++)require(actual.moves[i]==expected.moves[i]);
            tested++;
        }
    }
    require(tested==144000 && noL1==27);
    printf("PASS: actual GiveBoxMonInitialMoveset, %d cases (every ID, levels 1..100); no null pointers; no non-sentinel L1 gaps; %d reserved sentinel bindings\n",tested,noL1);
}
'''
    with tempfile.TemporaryDirectory(prefix="coherent-learnsets-host-") as tmp:
        test = Path(tmp) / "initial.c"
        binary = Path(tmp) / "initial-test"
        test.write_text(harness.replace("/* TABLES */", source).replace("/* INITIAL */", initial))
        subprocess.run(["cc", "-std=c11", "-O1", "-Wall", "-Wextra", "-Werror",
                        "-fsanitize=undefined,bounds,address", "-I", str(ROOT), str(test), "-o", str(binary)], check=True)
        subprocess.run([str(binary)], check=True)


def check_rejections():
    record = json.loads((ROOT / MANIFEST).read_text())
    before, after = baseline(TABLE), (ROOT / TABLE).read_text()
    cases = [after.replace("MOVE_SCRATCH", "MOVE_NONE", 1), after + "\n/* unapproved */\n",
             after.replace("[SPECIES_PICHU_SPIKY] = sPichuSpikyLevelUpLearnset", "[SPECIES_PICHU_SPIKY] = sPichuLevelUpLearnset"),
             after.replace("\t[SPECIES_ZARUDE_DADA] = sZarudeLevelUpLearnset,\n", ""),
             after.replace("sRotomLevelUpLearnset[] = {", "sRotomLevelUpLearnset[] = {\n LEVEL_UP_MOVE(1, MOVE_TACKLE),", 1)]
    for modified in cases:
        require(modified != after, "mutation fixture failed to modify source")
        try:
            validate_source(before, modified, {**record, "candidate_sha256": sha(modified)})
        except ValueError:
            continue
        raise AssertionError("unapproved edit accepted")
    print("PASS: invalid rows, outside edits, shared-pointer regressions and null-pointer regression rejected")


if __name__ == "__main__":
    check_source_contract()
    check_rejections()
    check_host()
