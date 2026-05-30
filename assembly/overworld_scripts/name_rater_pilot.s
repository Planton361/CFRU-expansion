.thumb
.align 2

.include "../xse_commands.s"
.include "../xse_defines.s"
.include "../asm_defines.s"

.equ SPECIAL_NAME_RATER_WAS_NICKNAME_CHANGED, 0x7B
.equ SPECIAL_BUFFER_MON_NICKNAME, 0x7C
.equ SPECIAL_IS_MON_OT_ID_NOT_PLAYERS, 0x7D
.equ SPECIAL_CHANGE_POKEMON_NICKNAME, 0x9E
.equ SPECIAL_CHOOSE_PARTY_MON, 0x9F
.equ SPECIAL_GET_PARTY_MON_SPECIES, 0x147
.equ SPECIAL_IS_MON_OT_NAME_NOT_PLAYERS, 0x150

.equ CONDITION_GREATER_OR_EQUAL, 0x4

.global EventScript_PilotPokeCenterNameRater

EventScript_PilotPokeCenterNameRater:
    lock
    faceplayer
    msgbox gText_PilotNameRater_Intro, MSG_YESNO
    compare LASTRESULT, YES
    if TRUE _goto EventScript_PilotNameRater_ChooseMon
    goto EventScript_PilotNameRater_Goodbye

EventScript_PilotNameRater_ChooseMon:
    msgbox gText_PilotNameRater_WhichMon, MSG_NORMAL
    special SPECIAL_CHOOSE_PARTY_MON
    waitstate
    compare 0x8004, PARTY_SIZE
    if CONDITION_GREATER_OR_EQUAL _goto EventScript_PilotNameRater_Goodbye

EventScript_PilotNameRater_CheckMon:
    specialvar LASTRESULT, SPECIAL_GET_PARTY_MON_SPECIES
    compare LASTRESULT, SPECIES_EGG
    if TRUE _goto EventScript_PilotNameRater_Egg
    special SPECIAL_BUFFER_MON_NICKNAME
    special SPECIAL_IS_MON_OT_ID_NOT_PLAYERS
    compare LASTRESULT, TRUE
    if TRUE _goto EventScript_PilotNameRater_NotYours
    specialvar LASTRESULT, SPECIAL_IS_MON_OT_NAME_NOT_PLAYERS
    special SPECIAL_BUFFER_MON_NICKNAME
    compare LASTRESULT, TRUE
    if TRUE _goto EventScript_PilotNameRater_NotYours
    msgbox gText_PilotNameRater_RenameAsk, MSG_YESNO
    compare LASTRESULT, YES
    if TRUE _goto EventScript_PilotNameRater_Rename
    goto EventScript_PilotNameRater_Goodbye

EventScript_PilotNameRater_Rename:
    msgbox gText_PilotNameRater_NewName, MSG_NORMAL
    fadescreen FADEOUT_BLACK
    special SPECIAL_CHANGE_POKEMON_NICKNAME
    waitstate
    specialvar LASTRESULT, SPECIAL_NAME_RATER_WAS_NICKNAME_CHANGED
    special SPECIAL_BUFFER_MON_NICKNAME
    compare LASTRESULT, TRUE
    if TRUE _goto EventScript_PilotNameRater_Renamed
    msgbox gText_PilotNameRater_SameName, MSG_NORMAL
    release
    end

EventScript_PilotNameRater_Renamed:
    msgbox gText_PilotNameRater_Renamed, MSG_NORMAL
    release
    end

EventScript_PilotNameRater_Egg:
    msgbox gText_PilotNameRater_Egg, MSG_NORMAL
    release
    end

EventScript_PilotNameRater_NotYours:
    msgbox gText_PilotNameRater_NotYours, MSG_NORMAL
    release
    end

EventScript_PilotNameRater_Goodbye:
    msgbox gText_PilotNameRater_Goodbye, MSG_NORMAL
    release
    end
