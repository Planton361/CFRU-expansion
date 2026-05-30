.thumb
.align 2

.include "../xse_commands.s"
.include "../xse_defines.s"
.include "../asm_defines.s"

.global EventScript_PokeCenterNameRater

EventScript_PokeCenterNameRater:
    lock
    faceplayer
    msgbox gText_PokeCenterNameRater_Intro MSG_YESNO
    compare LASTRESULT YES
    if TRUE _goto EventScript_PokeCenterNameRater_ChooseMon
    goto EventScript_PokeCenterNameRater_No

EventScript_PokeCenterNameRater_ChooseMon:
    msgbox gText_PokeCenterNameRater_ChooseMon MSG_NORMAL
    special 0x9F
    waitstate
    compare 0x8004 PARTY_SIZE
    if lessthan _goto EventScript_PokeCenterNameRater_CheckCanRateMon
    goto EventScript_PokeCenterNameRater_No

EventScript_PokeCenterNameRater_CheckCanRateMon:
    specialvar LASTRESULT 0x147
    compare LASTRESULT SPECIES_EGG
    if TRUE _goto EventScript_PokeCenterNameRater_Egg

    special 0x7C
    special 0x7D
    compare LASTRESULT TRUE
    if TRUE _goto EventScript_PokeCenterNameRater_TradeMon

    specialvar LASTRESULT 0x150
    special 0x7C
    compare LASTRESULT TRUE
    if TRUE _goto EventScript_PokeCenterNameRater_TradeMon

    msgbox gText_PokeCenterNameRater_Rename MSG_YESNO
    compare LASTRESULT YES
    if TRUE _goto EventScript_PokeCenterNameRater_ChooseNewNickname
    goto EventScript_PokeCenterNameRater_No

EventScript_PokeCenterNameRater_ChooseNewNickname:
    msgbox gText_PokeCenterNameRater_NewName MSG_NORMAL
    special 0x9E
    waitstate
    specialvar LASTRESULT 0x7B
    special 0x7C
    compare LASTRESULT TRUE
    if TRUE _goto EventScript_PokeCenterNameRater_Changed

    msgbox gText_PokeCenterNameRater_Unchanged MSG_NORMAL
    release
    end

EventScript_PokeCenterNameRater_Changed:
    msgbox gText_PokeCenterNameRater_Changed MSG_NORMAL
    release
    end

EventScript_PokeCenterNameRater_Egg:
    msgbox gText_PokeCenterNameRater_Egg MSG_NORMAL
    release
    end

EventScript_PokeCenterNameRater_TradeMon:
    msgbox gText_PokeCenterNameRater_TradeMon MSG_NORMAL
    release
    end

EventScript_PokeCenterNameRater_No:
    msgbox gText_PokeCenterNameRater_No MSG_NORMAL
    release
    end
