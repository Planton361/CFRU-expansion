.thumb
.align 2

.include "../xse_commands.s"
.include "../xse_defines.s"
.include "../asm_defines.s"

@ M-003: normal Pokemon Center Nurse fast path.
@
@ The map-object overlay repoints only the 19 normal Center Nurse objects to
@ this script. Trainer Tower deliberately retains its vanilla object script.
@ The special IDs below are the BPRE special-table entries confirmed against
@ pret/pokefirered data/specials.inc.
.equ SPECIAL_HEAL_PLAYER_PARTY, 0x000
.equ SPECIAL_SET_USED_POKECENTER_QUEST_LOG_EVENT, 0x169
.equ SPECIAL_BUFFER_UNION_ROOM_PLAYER_NAME, 0x183
.equ SPECIAL_GET_QUEST_LOG_STATE, 0x187
.equ GAME_STAT_USED_POKECENTER, 15
.equ FLAG_SYS_INFORMED_OF_LOCAL_WIRELESS_PLAYER, 0x842
.equ FLDEFF_POKECENTER_HEAL, 25

.global EventScript_InstantPokeCenterNurse

EventScript_InstantPokeCenterNurse:
    lock
    faceplayer

    @ Match the vanilla common script's Quest Log early exit after lock/face.
    special SPECIAL_GET_QUEST_LOG_STATE
    compare LASTRESULT 2
    if equal _goto EventScript_InstantPokeCenterNurse_QuestLogRelease

    incrementgamestat GAME_STAT_USED_POKECENTER
    applymovement LASTTALKED Movement_InstantPokeCenterNurse_Left
    waitmovement 0
    dofieldeffect FLDEFF_POKECENTER_HEAL
    waitfieldeffect FLDEFF_POKECENTER_HEAL
    applymovement LASTTALKED Movement_InstantPokeCenterNurse_Down
    waitmovement 0
    special SPECIAL_HEAL_PLAYER_PARTY
    special SPECIAL_SET_USED_POKECENTER_QUEST_LOG_EVENT

    @ Preserve the Union Room bookkeeping that Cyan's direct return bypasses.
    specialvar LASTRESULT SPECIAL_BUFFER_UNION_ROOM_PLAYER_NAME
    compare LASTRESULT 1
    if equal _goto EventScript_InstantPokeCenterNurse_UnionRoomPlayerWaiting
    goto EventScript_InstantPokeCenterNurse_Return

EventScript_InstantPokeCenterNurse_UnionRoomPlayerWaiting:
    checkflag FLAG_SYS_INFORMED_OF_LOCAL_WIRELESS_PLAYER
    if TRUE _goto EventScript_InstantPokeCenterNurse_Return
    setflag FLAG_SYS_INFORMED_OF_LOCAL_WIRELESS_PLAYER

EventScript_InstantPokeCenterNurse_Return:
    applymovement LASTTALKED Movement_InstantPokeCenterNurse_Bow
    waitmovement 0
    applymovement PLAYER Movement_InstantPokeCenterNurse_PlayerFaceDown
    waitmovement 0
    release
    end

EventScript_InstantPokeCenterNurse_QuestLogRelease:
    release
    end

@ BPRE movement-action values, matching pret's Common_Movement_* scripts.
Movement_InstantPokeCenterNurse_Left:
    .byte walk_left_onspot_fastest, end_m
Movement_InstantPokeCenterNurse_Down:
    .byte walk_down_onspot_fastest, end_m
Movement_InstantPokeCenterNurse_Bow:
    .byte nurse_bow, pause_vshort, end_m
Movement_InstantPokeCenterNurse_PlayerFaceDown:
    .byte look_down, end_m
