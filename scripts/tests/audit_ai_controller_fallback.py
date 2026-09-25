#!/usr/bin/env python3
"""Audit the source-owned early trainer bindings and safe AI handoff route."""

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]


def block(source: str, name: str) -> str:
    match = re.search(rf"static const struct TrainerMon\w+ {name}\[\] = \{{(.*?)\n\}};",
                      source, re.S)
    assert match, f"trainer party array missing: {name}"
    return match.group(1)


def mon_block(party: str, species: str) -> str:
    species_at = party.index(f".species = {species}")
    start = party.rfind("{", 0, species_at)
    end = party.index("},", species_at) + 1
    return party[start:end]


def main() -> None:
    parties = (ROOT / "src/Tables/trainer_parties.h").read_text()
    learns = (ROOT / "src/Tables/level_up_learnsets.c").read_text()
    learn_source = (ROOT / "src/learn_move.c").read_text()
    trainer_data = (ROOT / "src/Tables/trainer_data.c").read_text()
    trainer_ivs = (ROOT / "src/Tables/trainers_with_evs_table.h").read_text()
    build_pokemon = (ROOT / "src/build_pokemon.c").read_text()
    controller = (ROOT / "src/battle_controller_opponent.c").read_text()
    standard = (ROOT / "src/Battle_AI/ai_standard.c").read_text()
    ironmon = (ROOT / "src/Battle_AI/ai_ironmon.c").read_text()
    standard_policy = (ROOT / "src/Battle_AI/ai_standard_policy.c").read_text()
    ironmon_policy = (ROOT / "src/Battle_AI/ai_ironmon_policy.c").read_text()
    util = (ROOT / "src/util.c").read_text()

    rival = block(parties, "sParty_TrainerRivalCeruleanSquirtle")
    squirtle = mon_block(rival, "SPECIES_SQUIRTLE")
    for token in (".iv = 100", ".lvl = 18", "MOVE_TACKLE", "MOVE_TAILWHIP",
                  "MOVE_WITHDRAW", "MOVE_WATERGUN"):
        assert token in squirtle, f"Rival Squirtle source binding missing {token}"

    brock = block(parties, "sParty_TrainerLeaderBrock")
    onix = mon_block(brock, "SPECIES_ONIX")
    for token in (".lvl = 14", "MOVE_TACKLE", "MOVE_BIND", "MOVE_ROCKTOMB"):
        assert token in onix, f"Brock Onix source binding missing {token}"

    sandshrew = mon_block(block(parties, "sParty_TrainerCamperLiam"), "SPECIES_SANDSHREW")
    assert ".lvl = 11" in sandshrew
    assert re.search(r"\.moves\s*=\s*\{MOVE_SCRATCH,\s*MOVE_DEFENSECURL,\s*MOVE_SANDATTACK,\s*MOVE_NONE\}",
                     sandshrew)

    rick = block(parties, "sParty_TrainerBugCatcherRick")
    weedle = rick[:rick.index("},") + 1]
    assert ".lvl = 6" in weedle and ".species = SPECIES_WEEDLE" in weedle
    assert ".moves" not in weedle, "Weedle default moves must be derived from the level-up table"
    learnset = re.search(r"static const struct LevelUpMove sWeedleLevelUpLearnset\[\] = \{(.*?)\n\};",
                         learns, re.S)
    assert learnset
    moves = re.findall(r"LEVEL_UP_MOVE\(\s*(\d+),\s*(MOVE_\w+)\)", learnset.group(1))
    assert moves[:2] == [("1", "MOVE_POISONSTING"), ("1", "MOVE_STRINGSHOT")]
    assert all(int(level) <= 6 for level, _ in moves[:2])
    defaults = learn_source[learn_source.index("void GiveBoxMonInitialMoveset"):learn_source.index("u16 MonTryLearningNewMove")]
    assert "moveStack[k++] = move" in defaults
    assert "GiveMoveToBoxMon(boxMon, moveStack[index++])" in defaults

    trainer_classes = {
        "TRAINER_RIVAL_CERULEAN_SQUIRTLE": ("CLASS_RIVAL", 25),
        "TRAINER_LEADER_BROCK": ("CLASS_LEADER", 31),
        "TRAINER_CAMPER_LIAM": ("CLASS_CAMPER", 5),
        "TRAINER_BUG_CATCHER_RICK": ("CLASS_BUG_CATCHER", 1),
    }
    for trainer, (trainer_class, iv) in trainer_classes.items():
        entry = trainer_data[trainer_data.index(f"[{trainer}]"):]
        entry = entry[:entry.index("\n\t},")]
        assert f".trainerClass = {trainer_class}" in entry
        assert re.search(rf"\[{trainer_class}\]\s*=\s*{iv}\b", trainer_ivs)
    assert "baseIV = MathMin(gBaseIVsByTrainerClass[trainer->trainerClass], 31)" in build_pokemon
    assert "u32 n = 2 * baseHP + ivs[STAT_HP]" in build_pokemon
    assert "u32 n = (((2 * base + iv + ev / 4) * level) / 100) + 5" in build_pokemon

    supported = controller[controller.index("bool8 OpponentHandleSupportedAIMoveChoice"):controller.index("void OpponentHandleChooseMove")]
    outer = controller[controller.index("void OpponentHandleChooseMove"):controller.index("#define STATE_BEFORE_ACTION_CHOSEN")]
    assert "BattleAI_SetupAIData(0xF);" in supported
    assert "IronmonAI_ChooseMoveOrAction()" in supported
    assert "StandardAI_ChooseMoveOrAction()" in supported
    assert "EmitMoveChosen(1, chosenMovePos" in supported
    assert outer.index("OpponentHandleSupportedAIMoveChoice(moveInfo)") < outer.index("BattleAI_SetupAIData(0xF)")
    assert "OpponentNormalizeSupportedMoveInfo" in supported
    assert "moveInfo->moves[i] = gBattleMons[bank].moves[i]" in controller
    assert "FALLBACK_TO_ENGINE" not in standard + ironmon
    assert "StandardAI_ChooseEmergencyMoveSlot(bank)" in controller
    assert "chosenMovePos = 0;" not in standard[standard.index("u8 StandardAI_ChooseMoveOrAction"):]
    assert "choice = 0;" not in ironmon[ironmon.index("u8 IronmonAI_ChooseMoveOrAction"):]

    assert "case TRAINER_AI_PROFILE_STANDARD + 1:" in util
    assert "case TRAINER_AI_PROFILE_IRONMON_SMART + 1:" in util
    assert "TRAINER_AI_PROFILE_SMART_AI + 1" in util
    assert "TRAINER_AI_PROFILE_STANDARD" in standard[standard.index("bool8 StandardAI_IsSupportedBattle"):]
    assert "TRAINER_AI_PROFILE_IRONMON_SMART" in ironmon[ironmon.index("bool8 IronmonAI_IsSupportedBattle"):]

    assert "candidate->immediate_future_gain <= 40" in standard_policy
    assert "b->future_gain_undiscounted > 80" in ironmon_policy
    assert "STANDARD_POLICY_EPSILON 8" in (ROOT / "include/new/ai_standard_policy.h").read_text()
    assert "IRONMON_POLICY_EPSILON 4" in (ROOT / "include/new/ai_ironmon_policy.h").read_text()
    print("controller fallback source audit: early source moves/order, supported outer route, profile dispatch, no silent adapter slot-0 fallback PASS")


if __name__ == "__main__":
    main()
