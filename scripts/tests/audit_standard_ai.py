#!/usr/bin/env python3
"""Source-owned fairness audit for the CFRU Standard AI boundary.

This is intentionally broader than a grep of the pure policy file.  It audits
the adapter, the dispatch surface, and the helper names that are forbidden
because their transitive call graphs read hidden battle state or consume the
legacy AI RNG.
"""

from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[2]
PURE_FILES = (
    ROOT / "include/new/ai_standard_policy.h",
    ROOT / "src/Battle_AI/ai_standard_policy.c",
    ROOT / "include/new/ai_standard_mechanics.h",
    ROOT / "src/Battle_AI/ai_standard_mechanics.c",
)
ADAPTER = ROOT / "src/Battle_AI/ai_standard.c"
DISPATCH = ROOT / "src/Battle_AI/ai_master.c"

PURE_FORBIDDEN = (
    "gBattle", "gNewBS", "gChosen", "gPlayerParty", "gEnemyParty",
    "AIRandom", "Random32", "Random(", "CalcFinalAIMoveDamage",
)

ADAPTER_FORBIDDEN = (
    "gChosenActionByBank", "gChosenActionsByBanks", "gChosenAction",
    "CalculateAIPredictions", "ShouldSwitch", "GetMostSuitableMonToSwitchIntoByParty",
    "CheckMoveLimitations", "AdjustMoveLimitationFlagsForAI", "AIRandom", "Random(", "Random32",
    "gNewBS->ai.randSeed",
    "AI_SpecialTypeCalc", "AI_TypeCalc", "CalcFinalAIMoveDamage",
    "GetFinalAIMoveDamage", "MoveKnocksOutXHits", "IsTrapped", "GetAIAbility",
    "GetAIChosenMove", "gBattleStruct->moveTarget", "gBattleBufferA",
    "GetRecordedItemEffect", "GetRecordedAbility",
    "GetMonEntryHazardDamage", "WillFaintFromEntryHazards", "TypeDamageModificationPartyMon",
    "FlagGet(FLAG_BADGE",
)

FORBIDDEN_OPPONENT_FIELDS = (
    r"gBattleMons\[(?:foe|targetBank|bankDef)\]\.(?:hp|maxHP|species|type[123]|moves|pp|ability|item|attack|defense|spAttack|spDefense|speed)\b",
)

EXCLUDED_BATTLE_FLAGS = (
    "BATTLE_TYPE_DOUBLE", "BATTLE_TYPE_LINK", "BATTLE_TYPE_OAK_TUTORIAL",
    "BATTLE_TYPE_MULTI", "BATTLE_TYPE_SAFARI", "BATTLE_TYPE_ROAMER",
    "BATTLE_TYPE_EREADER_TRAINER", "BATTLE_TYPE_SCRIPTED_WILD_1",
    "BATTLE_TYPE_SCRIPTED_WILD_2", "BATTLE_TYPE_LEGENDARY_FRLG",
    "BATTLE_TYPE_TRAINER_TOWER", "BATTLE_TYPE_TWO_OPPONENTS",
    "BATTLE_TYPE_INGAME_PARTNER", "BATTLE_TYPE_POKE_DUDE",
    "BATTLE_TYPE_OLD_MAN", "BATTLE_TYPE_FRONTIER", "BATTLE_TYPE_SHADOW_WARRIOR",
    "BATTLE_TYPE_DYNAMAX",
)

REVIEWED_HELPERS = {
    "EmitTwoReturnValues", "GetMonAbility", "GetMonItemEffect", "FlagGet", "IsInverseBattle",
    "LoadPartyRange", "IsFrontierTrainerId", "IsRaidBattle", "GetTrainerAIProfile",
    "ItemId_GetHoldEffect", "CheckGrounding",
    "StandardMechanicsDamage", "StandardMechanicsAccuracy", "StandardMechanicsQualifySwitches",
    "StandardMechanicsSpeed", "StandardMechanicsStage",
    "StandardPolicyChoose", "StandardPolicyNormalizeEffectFamily",
}


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> int:
    pure = "\n".join(path.read_text(encoding="utf-8") for path in PURE_FILES)
    adapter = ADAPTER.read_text(encoding="utf-8")
    mechanics = (ROOT / "src/Battle_AI/ai_standard_mechanics.c").read_text(encoding="utf-8")
    code = re.sub(r"/\*.*?\*/|//[^\n]*", "", adapter, flags=re.S)
    dispatch = DISPATCH.read_text(encoding="utf-8")

    for token in PURE_FORBIDDEN:
        if token in pure:
            fail(f"pure policy contains forbidden token {token!r}")
    for token in ADAPTER_FORBIDDEN:
        if token in code:
            fail(f"adapter contains forbidden token/helper {token!r}")
    if "input.base_defense = MathMin(255" in adapter:
        fail("possible Badge defense is being approximated by scaling base_defense")
    if "possible_defense_badge" not in adapter or "possible_defense_badge" not in mechanics:
        fail("full-stat possible Badge defense path is missing")
    if "value = value * 11 / 10" not in mechanics:
        fail("possible Badge defense is not applied at the full-stat mechanics layer")
    # The sole permitted HP read is a public-display projection. Remove only
    # this exact small body, then audit all other opponent fields normally.
    public_hp = re.search(r"static u8 StandardAI_PublicHpPixels\(u8 foe\)\n\{[^}]+\}", adapter)
    if public_hp is None or "current * 48 / maximum" not in public_hp.group():
        fail("public 48-pixel HP projection is missing")
    projected_adapter = adapter.replace(public_hp.group(), "")
    for pattern in FORBIDDEN_OPPONENT_FIELDS:
        if re.search(pattern, projected_adapter):
            fail(f"adapter reads a forbidden unrevealed opponent field: {pattern}")

    if '#include "../../include/new/ai_util.h"' in adapter:
        fail("adapter includes the legacy AI utility graph")
    if '#include "../../include/new/ai_switching.h"' in adapter:
        fail("adapter includes the legacy switching/prediction graph")
    if "StandardAI_IsSupportedBattle" not in dispatch:
        fail("dispatch does not expose the explicit Standard gate")
    if "StandardAI_ChooseMoveOrAction" not in dispatch:
        fail("move dispatch does not enter the Standard adapter")
    if "StandardAI_TrySwitchOrUseItem" not in dispatch:
        fail("switch/item dispatch does not enter the Standard adapter")
    if "BATTLE_TYPE_TRAINER" not in adapter or "GetTrainerAIProfile() == TRAINER_AI_PROFILE_STANDARD" not in adapter:
        fail("Standard dispatch is not restricted to the appended Trainer profile")
    for flag in EXCLUDED_BATTLE_FLAGS:
        if flag not in adapter:
            fail(f"Standard gate does not explicitly exclude {flag}")

    # The profile is appended after all legacy values, and the legacy switch
    # remains before the Standard case.  This protects raw enum/save mappings
    # while permitting an internal source-only profile identifier.
    global_header = (ROOT / "include/global.h").read_text(encoding="utf-8")
    util = (ROOT / "src/util.c").read_text(encoding="utf-8")
    legacy_order = [
        "TRAINER_AI_PROFILE_VANILLA",
        "TRAINER_AI_PROFILE_EASY",
        "TRAINER_AI_PROFILE_NORMAL",
        "TRAINER_AI_PROFILE_HARD",
        "TRAINER_AI_PROFILE_EXPERT",
        "TRAINER_AI_PROFILE_SMART_AI",
        "TRAINER_AI_PROFILE_STANDARD",
    ]
    positions = [global_header.find(name) for name in legacy_order]
    if any(position < 0 for position in positions) or positions != sorted(positions):
        fail("Standard profile is not appended after the legacy profile values")
    if "case TRAINER_AI_PROFILE_SMART_AI + 1:" not in util:
        fail("legacy Smart raw mapping is missing")
    if "case TRAINER_AI_PROFILE_STANDARD + 1:" not in util:
        fail("Standard raw mapping is missing")

    # Standard guards must precede the legacy prediction/limitation graphs.
    setup_guard = dispatch.find("if (StandardAI_IsSupportedBattle())", dispatch.find("void BattleAI_SetupAIData"))
    legacy_limitations = dispatch.find("moveLimitations = CheckMoveLimitations", setup_guard)
    choose_guard = dispatch.find("if (StandardAI_IsSupportedBattle())", dispatch.find("u8 BattleAI_ChooseMoveOrAction"))
    legacy_mega = dispatch.find("TryTempMegaEvolveAllBanks", choose_guard)
    switch_guard = dispatch.find("if (StandardAI_IsSupportedBattle())", dispatch.find("void AI_TrySwitchOrUseItem"))
    legacy_prediction = dispatch.find("CalculateAIPredictions()", switch_guard)
    if min(setup_guard, choose_guard, switch_guard) < 0 or min(legacy_limitations, legacy_mega, legacy_prediction) < 0:
        fail("legacy isolation guard or legacy call graph is missing")
    if not (setup_guard < legacy_limitations and choose_guard < legacy_mega and switch_guard < legacy_prediction):
        fail("Standard dispatch guard occurs after a legacy AI graph entry")

    controller = (ROOT / "src/battle_controller_opponent.c").read_text(encoding="utf-8")
    presentation = (ROOT / "src/battle_anims.c").read_text(encoding="utf-8")
    if "gNewBS->ai.standardDisplayedSpecies[bank] = species;" not in presentation:
        fail("public display identity producer is missing")
    strings = (ROOT / "src/battle_strings.c").read_text(encoding="utf-8")
    if not re.search(r"case STRINGID_INTROSENDOUT:[^:]*StandardAI_RecordPublicSendoutSpecies\(gActiveBattler\)", strings):
        fail("first-sendout public species producer is missing")
    if not re.search(r"case STRINGID_SWITCHINMON:[^:]*StandardAI_RecordPublicSendoutSpecies\(gBattleScripting.bank\)", strings):
        fail("replacement-sendout public species producer is missing")
    if "GetMonData(GetIllusionPartyData(bank), MON_DATA_SPECIES, NULL)" not in strings:
        fail("sendout identity must match Illusion-aware public appearance")
    switching = (ROOT / "src/switching.c").read_text(encoding="utf-8")
    faint = (ROOT / "src/general_bs_commands.c").read_text(encoding="utf-8")
    if not re.search(r"oldData = gBattleMons\[gActiveBattler\];\s*StandardAI_FinalizePendingForTarget\(gActiveBattler\);\s*monData", switching):
        fail("target switch must finalize pending public effect before replacement")
    if not re.search(r"case Faint_ClearEffects:\s*StandardAI_FinalizePendingForTarget\(gActiveBattler\);\s*gBattleMons", faint):
        fail("target faint must finalize pending public effect before cleanup")
    history_source = (ROOT / "src/battle_util.c").read_text(encoding="utf-8")
    if not re.search(
            r"if \(gHitMarker & HITMARKER_ATTACKSTRING_PRINTED\)\s*\{\s*"
            r"StandardAI_ObservePublicMove\(move\);", history_source):
        fail("type uncertainty producer must require a printed public move")
    if "StandardAI_ObservePublicAbility(bank, ability);" not in history_source:
        fail("public ability type uncertainty producer missing")
    if "8 + 4 * delta" in code or "missingHpFraction / 4" in code:
        fail("generic stage or duplicate recovery bonus restored")
    move_path = controller.split("void OpponentHandleChooseMove(void)", 1)[1].split("//You get 1", 1)[0]
    replacement = controller.split("void OpponentHandleChoosePokemon(void)", 1)[1].split("CalcMostSuitableMonToSwitchInto", 1)[0]
    if "StandardAI_ChooseMoveOrAction()" not in move_path or "return;" not in move_path:
        fail("Standard controller reaches legacy gimmick prediction")
    if "StandardAI_ChooseReplacement()" not in replacement or "return;" not in replacement:
        fail("Standard replacement reaches legacy matchup selection")

    # Review every call-like identifier in the adapter against a small
    # documented surface.  Local/static helpers and C/GBA primitives are
    # excluded; anything else is printed for human review rather than silently
    # accepted as a transitive dependency.
    local_names = set(re.findall(r"\b(StandardAI_[A-Za-z0-9_]+)\s*\(", adapter))
    code = re.sub(r"/\*.*?\*/|//[^\n]*", "", adapter, flags=re.S)
    calls = set(re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", code))
    c_primitives = {
        "if", "for", "while", "switch", "sizeof", "MathMin", "MathMax", "Memset", "return", "defined",
    }
    unknown = sorted(
        call for call in calls
        if call.startswith("StandardPolicy") is False
        and call not in local_names
        and call not in REVIEWED_HELPERS
        and call not in c_primitives
        and not call.startswith("STANDARD_")
    )
    # The engine's type/macros and struct fields do not appear as calls here.
    # Keep this list explicit and reviewable as the adapter grows.
    allowed_engine_calls = {
        "FOE", "SIDE", "BATTLER_ALIVE", "SPLIT", "TRUE", "FALSE",
    }
    unknown = [call for call in unknown if call not in allowed_engine_calls]
    if unknown:
        fail("unreviewed adapter call surface: " + ", ".join(unknown))

    print("standard AI fairness audit: PASS")
    print("pure policy: no battle globals, submitted actions, or RNG")
    print("adapter: no legacy prediction/damage/switching helper graph")
    print("dispatch: ordinary Trainer Singles only; excluded modes stay on legacy routing")
    print("legacy isolation: profile mappings and guarded legacy entry points present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
