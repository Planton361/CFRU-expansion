.thumb
.align 2

.include "../xse_commands.s"
.include "../xse_defines.s"
.include "../asm_defines.s"

@ M-006: source-backed BPRE/pret/Cyan Player House 1F Mom handoff.
@
@ These values are BPRE script constants confirmed against pret's flags, vars,
@ maps, songs, and specials tables. The existing Oak's Lab scene owns the
@ starter sequence after the silent warp; this script does not recreate it.
.equ FLAG_BEAT_RIVAL_IN_OAKS_LAB, 0x0258
.equ FLAG_HIDE_OAK_IN_HIS_LAB, 0x002B
.equ FLAG_HIDE_OAK_IN_PALLET_TOWN, 0x002C
.equ FLAG_DONT_TRANSITION_MUSIC, 0x4001
.equ VAR_MAP_SCENE_PALLET_TOWN_OAK, 0x4050
.equ VAR_MAP_SCENE_PALLET_TOWN_PROFESSOR_OAKS_LAB, 0x4055
.equ SPECIAL_HEAL_PLAYER_PARTY, 0x000
.equ SPECIAL_SPAWN_CAMERA_OBJECT, 0x114
.equ SPECIAL_REMOVE_CAMERA_OBJECT, 0x115
.equ SE_WARP_IN, 0x28
.equ MUS_HEAL, 0x100
.equ MAP_GROUP_PALLET_TOWN, 4
.equ MAP_NUM_PALLET_TOWN_PROFESSOR_OAKS_LAB, 3
.equ LOCALID_MOM, 1

.global EventScript_TalkToMom
.global EventScript_TalkToMomExitBlock

EventScript_TalkToMom:
    lock
    faceplayer
    checkflag FLAG_BEAT_RIVAL_IN_OAKS_LAB
    if TRUE _goto EventScript_TalkToMomHeal

    msgbox gText_TalkToMomMagicTrick MSG_NORMAL
    closemessage
    waitdooranim
    special SPECIAL_SPAWN_CAMERA_OBJECT
    applymovement PLAYER Movement_TalkToMomPlayerSpin
    waitmovement 0
    playse SE_WARP_IN
    applymovement PLAYER Movement_TalkToMomPlayerWarpOut
    waitmovement 0
    special SPECIAL_REMOVE_CAMERA_OBJECT
    setvar VAR_MAP_SCENE_PALLET_TOWN_PROFESSOR_OAKS_LAB 1
    clearflag FLAG_HIDE_OAK_IN_HIS_LAB
    setvar VAR_MAP_SCENE_PALLET_TOWN_OAK 1
    setflag FLAG_HIDE_OAK_IN_PALLET_TOWN
    setflag FLAG_DONT_TRANSITION_MUSIC
    warpmuted MAP_GROUP_PALLET_TOWN MAP_NUM_PALLET_TOWN_PROFESSOR_OAKS_LAB 0xFF 9 6
    waitstate
    release
    end

@ Preserve pret's post-rival Mom text and out-of-center healing semantics.
EventScript_TalkToMomHeal:
    msgbox gText_TalkToMomHealBefore MSG_NORMAL
    closemessage
    fadescreen FADEOUT_BLACK
    playfanfare MUS_HEAL
    waitfanfare
    special SPECIAL_HEAL_PLAYER_PARTY
    fadescreen FADEIN_BLACK
    msgbox gText_TalkToMomHealAfter MSG_NORMAL
    release
    end

@ Cyan's trigger prevents an early exit by moving the player one tile right.
EventScript_TalkToMomExitBlock:
    lockall
    msgbox gText_TalkToMomComeHere MSG_NORMAL
    closemessage
    applymovement PLAYER Movement_TalkToMomExitRight
    waitmovement PLAYER
    releaseall
    end

Movement_TalkToMomPlayerSpin:
    .byte look_up, pause_vshort, look_left, pause_vshort
    .byte look_down, pause_vshort, look_right, pause_vshort, end_m

Movement_TalkToMomPlayerWarpOut:
    .byte look_up, disable_anim
    .byte slide_up, slide_up, slide_up, slide_up, slide_up, end_m

Movement_TalkToMomExitRight:
    .byte walk_right, end_m
