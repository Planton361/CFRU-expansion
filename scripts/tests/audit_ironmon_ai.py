#!/usr/bin/env python3
"""Fail-closed source audit for the CFRU Ironmon fair adapter and core."""

from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[2]
PURE = (
    ROOT / "include/new/ai_ironmon_policy.h",
    ROOT / "src/Battle_AI/ai_ironmon_policy.c",
)
ADAPTER = ROOT / "src/Battle_AI/ai_ironmon.c"


def fail(message: str) -> None:
    print("FAIL:", message, file=sys.stderr)
    raise SystemExit(1)


def main() -> int:
    pure = "\n".join(path.read_text(encoding="utf-8") for path in PURE)
    adapter = ADAPTER.read_text(encoding="utf-8")
    code = re.sub(r"/\*.*?\*/|//[^\n]*", "", adapter, flags=re.S)
    for token in (
        "gBattle", "gNewBS", "gChosen", "gPlayerParty", "gEnemyParty",
        "AIRandom", "Random(", "Random32", "CalcFinalAIMoveDamage",
    ):
        if token in pure:
            fail(f"pure policy contains forbidden token {token!r}")
    pure_code = re.sub(r"/\*.*?\*/|//[^\n]*|\"(?:\\.|[^\"])*\"", "", pure, flags=re.S)
    for token in ("float", "double", "malloc", "calloc", "realloc", "free"):
        if re.search(rf"\b{token}\b", pure_code):
            fail(f"pure policy contains forbidden float/heap token {token!r}")
    policy_source = PURE[1].read_text(encoding="utf-8")
    for function in ("IronmonPolicyBuildResponses", "IronmonPolicyChoose"):
        if len(re.findall(rf"\b{function}\s*\(", policy_source)) != 1:
            fail(f"pure entry point {function} is recursive or multiply defined")
    for token in (
        "gChosenAction", "CalculateAIPredictions", "ShouldSwitch(",
        "GetMostSuitableMonToSwitchIntoByParty", "CheckMoveLimitations",
        "AIRandom", "Random(", "Random32", "gNewBS->ai.randSeed",
        "AI_SpecialTypeCalc", "AI_TypeCalc", "CalcFinalAIMoveDamage",
        "GetFinalAIMoveDamage", "MoveKnocksOutXHits", "GetAIChosenMove",
        "GetRecordedItemEffect", "GetRecordedAbility",
    ):
        if token in code:
            fail(f"adapter contains forbidden token/helper {token!r}")
    for field in ("moves", "pp", "item", "ability", "attack", "defense",
                  "spAttack", "spDefense", "speed", "species", "type1", "type2", "type3"):
        if re.search(rf"gBattleMons\[foe\]\.{field}\b", code):
            fail(f"adapter reads private opposing field {field}")
    if re.search(r"gBattleMons\[foe\]\.(?:hp|maxHP)\b", code):
        fail("adapter reads exact opposing HP")
    if "opponent_switch" in code.lower():
        fail("adapter invents an opponent switch response")
    if "StandardPolicyBounded" not in pure or "IRONMON_POLICY_EPSILON 4" not in pure:
        fail("accepted RNG/epsilon contract is absent")
    if "IRONMON_SWITCH_RANDOM_MIN 12" not in pure or "thresholdEligible" not in pure:
        fail("per-candidate +12 switch admission is absent")
    history = (ROOT / "src/battle_util.c").read_text(encoding="utf-8")
    if not re.search(
            r"if \(gHitMarker & HITMARKER_ATTACKSTRING_PRINTED\)\s*\{\s*"
            r"StandardAI_ObservePublicMove\(move\);\s*"
            r"IronmonAI_ObservePublicMove\(gBankAttacker, move\);", history):
        fail("public count producer is not gated by printed attack string")
    clear_body = history.split("void ClearBattlerMoveHistory(u8 bank)", 1)[1].split("}", 1)[0]
    if "IronmonAI_ClearPublicMoveCounts(bank);" not in clear_body:
        fail("public count lifecycle is not aligned with move-history clear")
    if "moves[i] = counts[i] ? BATTLE_HISTORY->usedMoves[foe][i] : MOVE_NONE;" not in adapter:
        fail("unprinted generic move history can enter the revealed response model")
    global_header = (ROOT / "include/global.h").read_text(encoding="utf-8")
    positions = [global_header.find(name) for name in (
        "TRAINER_AI_PROFILE_SMART_AI", "TRAINER_AI_PROFILE_STANDARD",
        "TRAINER_AI_PROFILE_IRONMON_SMART")]
    if positions != sorted(positions) or min(positions) < 0:
        fail("Ironmon profile is not appended after Standard")
    util = (ROOT / "src/util.c").read_text(encoding="utf-8")
    if "case TRAINER_AI_PROFILE_IRONMON_SMART + 1:" not in util:
        fail("Ironmon internal raw mapping is missing")
    for path in (ROOT / "src/Battle_AI/ai_master.c",
                 ROOT / "src/battle_controller_opponent.c"):
        dispatch = path.read_text(encoding="utf-8")
        if "IronmonAI_IsSupportedBattle()" not in dispatch:
            fail(f"Ironmon dispatch gate missing from {path.name}")
    if "GetTrainerAIProfile() == TRAINER_AI_PROFILE_IRONMON_SMART" not in adapter:
        fail("Ironmon adapter is not restricted to its distinct profile")
    print("Ironmon fairness/source audit: PASS")
    print("pure core: bounded values only; no battle globals, recursion, heap, float, or RNG during scoring")
    print("adapter: revealed moves/counts only; no submitted action or legacy prediction graph")
    print("dispatch: distinct appended profile; ordinary Trainer Singles gate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
