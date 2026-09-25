#!/usr/bin/env python3
"""Audit the source-owned early trainer bindings and safe AI handoff route."""

from pathlib import Path
import re
import subprocess


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


def c_function(source: str, signature: str) -> str:
    match = re.search(re.escape(signature) + r"\s*\{", source)
    assert match, f"function body missing: {signature}"
    start = match.start()
    opening = match.end() - 1
    depth = 0
    for position in range(opening, len(source)):
        if source[position] == "{":
            depth += 1
        elif source[position] == "}":
            depth -= 1
            if depth == 0:
                return source[start:position + 1]
    raise AssertionError(f"unterminated function body: {signature}")


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
    battle_strings = (ROOT / "src/battle_strings.c").read_text()
    battle_strings_header = (ROOT / "include/new/battle_strings.h").read_text()
    overworld = (ROOT / "src/overworld.c").read_text()
    hooks = (ROOT / "hooks").read_text()

    rival = block(parties, "sParty_TrainerRivalCeruleanSquirtle")
    squirtle = mon_block(rival, "SPECIES_SQUIRTLE")
    for token in (".iv = 100", ".lvl = 18", "MOVE_TACKLE", "MOVE_TAILWHIP",
                  "MOVE_WITHDRAW", "MOVE_WATERGUN"):
        assert token in squirtle, f"Rival Squirtle source binding missing {token}"

    oak_rival = block(parties, "sParty_TrainerRivalOaksLabSquirtle")
    oak_squirtle = mon_block(oak_rival, "SPECIES_SQUIRTLE")
    assert ".lvl = 5" in oak_squirtle
    assert ".moves" not in oak_squirtle, "Oak's Lab Squirtle must use default moves"
    oak_entry = trainer_data[trainer_data.index("[TRAINER_RIVAL_OAKS_LAB_SQUIRTLE]"):]
    oak_entry = oak_entry[:oak_entry.index("\n\t},")]
    for token in (".trainerClass = CLASS_RIVAL", ".aiFlags = AI_SCRIPT_CHECK_BAD_MOVE | AI_SCRIPT_CHECK_GOOD_MOVE | AI_SCRIPT_SEMI_SMART",
                  ".party = {.NoItemDefaultMoves = sParty_TrainerRivalOaksLabSquirtle}"):
        assert token in oak_entry, f"Oak's Lab trainer data binding missing {token}"
    squirtle_learnset = re.search(
        r"static const struct LevelUpMove sSquirtleLevelUpLearnset\[\] = \{(.*?)\n\};",
        learns, re.S)
    assert squirtle_learnset
    oak_eligible = [(int(level), move) for level, move in re.findall(
        r"LEVEL_UP_MOVE\(\s*(\d+),\s*(MOVE_\w+)\)", squirtle_learnset.group(1))
        if int(level) <= 5]
    assert oak_eligible == [(1, "MOVE_TACKLE"), (1, "MOVE_TAILWHIP"),
                            (3, "MOVE_WATERGUN")]

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
    assert "if (lvlUpMove.level > level)\n\t\t\tbreak;" in defaults
    assert "index = k - MAX_MON_MOVES" in defaults
    assert "if (index < 0)\n\t\tindex = 0;" in defaults
    assert "GiveMoveToBoxMon(boxMon, moveStack[index++])" in defaults
    assert "GiveBoxMonInitialMoveset(boxMon);" in build_pokemon

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

    helper = c_function(battle_strings, "void StandardAI_RecordPublicSendoutSpecies(u8 bank)")
    assert "GetMonData(GetIllusionPartyData(bank), MON_DATA_SPECIES, NULL)" in helper
    assert "void StandardAI_RecordPublicSendoutSpecies(u8 bank);" in battle_strings_header
    intro_case = battle_strings[battle_strings.index("case STRINGID_INTROSENDOUT"):]
    intro_case = intro_case[:intro_case.index("case STRINGID_SWITCHINMON")]
    switch_case = battle_strings[battle_strings.index("case STRINGID_SWITCHINMON"):]
    switch_case = switch_case[:switch_case.index("case ", switch_case.index("case STRINGID_SWITCHINMON") + 5)]
    assert "StandardAI_RecordPublicSendoutSpecies(gActiveBattler);" in intro_case
    assert "StandardAI_RecordPublicSendoutSpecies(gBattleScripting.bank);" in switch_case
    writes = []
    for source_path in (ROOT / "src").rglob("*.c"):
        source = source_path.read_text(errors="ignore")
        for match in re.finditer(r"standardDisplayedSpecies\[[^\]]+\]\s*=(?!=)", source):
            writes.append(source_path.relative_to(ROOT).as_posix())
    assert sorted(writes) == ["src/battle_anims.c", "src/battle_strings.c"], writes

    starter_flags = c_function(overworld, "void BattleSetup_StartTrainerBattle(void)")
    assert "gBattleTypeFlags = BATTLE_TYPE_TRAINER;" in starter_flags
    assert "if (FlagGet(FLAG_ACTIVATE_TUTORIAL))" in starter_flags
    assert "gBattleTypeFlags |= BATTLE_TYPE_OAK_TUTORIAL;" in starter_flags
    assert "//#define TUTORIAL_BATTLES" in (ROOT / "src/config.h").read_text()
    assert not re.search(r"FlagSet\(FLAG_ACTIVATE_TUTORIAL\)", "\n".join(
        path.read_text(errors="ignore") for path in (ROOT / "src").rglob("*.c")))

    pret = ROOT.parent / "references" / "pret-pokefirered"
    if pret.exists():
        battle_main = (pret / "src/battle_main.c").read_text()
        battle_util = (pret / "src/battle_util.c").read_text()
        opponent_controller = (pret / "src/battle_controller_opponent.c").read_text()
        battle_controllers = (pret / "src/battle_controllers.c").read_text()
        battle_anim_mons = (pret / "src/battle_anim_mons.c").read_text()
        new_game = (pret / "src/new_game.c").read_text()
        event_data = (pret / "src/event_data.c").read_text()
        lab_script = (pret / "data/maps/PalletTown_ProfessorOaksLab/scripts.inc").read_text()
        event_macros = (pret / "asm/macros/event.inc").read_text()
        opponent_intro = c_function(battle_main, "static void BattleIntroPrintOpponentSendsOut(void)")
        opponent_animation = c_function(battle_main, "static void BattleIntroOpponentSendsOutMonAnimation(void)")
        dex_record = c_function(battle_main, "static void BattleIntroRecordMonsToDex(void)")
        player_intro = c_function(battle_main, "static void BattleIntroPrintPlayerSendsOut(void)")
        player_animation = c_function(battle_main, "static void BattleIntroPlayerSendsOutMonAnimation(void)")
        preturn = c_function(battle_main, "static void TryDoEventsBeforeFirstTurn(void)")
        selection = c_function(battle_main, "static void HandleTurnActionSelectionState(void)")
        single_player_controllers = c_function(
            battle_controllers, "static void InitSinglePlayerBtlControllers(void)")
        get_battler_at_position = c_function(
            battle_anim_mons, "u8 GetBattlerAtPosition(u8 position)")
        get_public_sprite_species = c_function(
            (ROOT / "src/battle_anims.c").read_text(),
            "u16 GetBattlerYDeltaFromSpriteId(u8 spriteId)")
        init_event_data = c_function(event_data, "void InitEventData(void)")
        new_game_init = c_function(new_game, "void NewGameInitData(void)")
        assert "PrepareStringBattle(STRINGID_INTROSENDOUT, GetBattlerAtPosition(B_POSITION_OPPONENT_LEFT))" in opponent_intro
        assert "gBattleMainFunc = BattleIntroOpponentSendsOutMonAnimation" in opponent_intro
        assert "gBattleMainFunc = BattleIntroRecordMonsToDex" in opponent_animation
        assert "gBattleMainFunc = BattleIntroPrintPlayerSendsOut" in dex_record
        assert "PrepareStringBattle(STRINGID_INTROSENDOUT, GetBattlerAtPosition(B_POSITION_PLAYER_LEFT))" in player_intro
        assert "gBattleMainFunc = BattleIntroPlayerSendsOutMonAnimation" in player_intro
        assert "gBattleMainFunc = TryDoEventsBeforeFirstTurn" in player_animation
        assert "gBattleMainFunc = HandleTurnActionSelectionState" in preturn
        assert "BtlController_EmitChooseMove" in selection
        assert "trainerbattle_earlyrival TRAINER_RIVAL_OAKS_LAB_SQUIRTLE, RIVAL_BATTLE_TUTORIAL" in lab_script
        assert "trainerbattle TRAINER_BATTLE_EARLY_RIVAL" in event_macros
        assert "gBattlerPositions[0] = B_POSITION_PLAYER_LEFT;" in single_player_controllers
        assert "gBattlerPositions[1] = B_POSITION_OPPONENT_LEFT;" in single_player_controllers
        assert "gBattlersCount = 2;" in single_player_controllers
        assert "if (gBattlerPositions[i] == position)" in get_battler_at_position
        assert "memset(gSaveBlock1Ptr->flags, 0, sizeof(gSaveBlock1Ptr->flags));" in init_event_data
        assert "InitEventData();" in new_game_init
        assert "GetMonData(mon, MON_DATA_SPECIES, NULL)" in get_public_sprite_species
        assert "gNewBS->ai.standardDisplayedSpecies[bank] = species;" in get_public_sprite_species
        prepare = c_function(battle_util, "void PrepareStringBattle(u16 stringId, u8 battler)")
        assert "gActiveBattler = battler;" in prepare
        opponent_print = c_function(opponent_controller, "static void OpponentHandlePrintString(void)")
        assert "BufferStringBattle(*stringId);" in opponent_print
        reference_sha = subprocess.check_output(
            ["git", "-C", str(pret), "rev-parse", "HEAD"], text=True).strip()
        assert reference_sha == "e060ab955b5dc9ac1c4904c2cd141683615cf477"
        print(f"source lifecycle reference: pret-pokefirered {reference_sha}; Oak Lab bank mapping player=0/opponent=1; NewGame clears flags PASS")
        print("source lifecycle audit: opponent intro -> player intro -> pre-turn events -> first action selection; gActiveBattler assigned to requested send-out bank PASS")
    assert "PrepareStringBattle 80173AC 3" in hooks
    assert "BufferStringBattle 080D7274 1" in hooks
    assert "OpponentHandleChooseMove 80385B0 0" in hooks
    assert "BattleSetup_StartTrainerBattle 8080464 0" in hooks
    print("controller fallback source audit: Oak's Lab L5 binding/default moves, initial-moveset semantics, public reveal lifecycle, support routing, profile dispatch, no silent adapter slot-0 fallback PASS")


if __name__ == "__main__":
    main()
