.thumb
.align 2

.include "../xse_commands.s"
.include "../xse_defines.s"
.include "../asm_defines.s"

@ M-006: source-backed BPRE/pret/Cyan Player House 1F Mom handoff.
@
@ These values are BPRE script constants confirmed against pret's flags, vars,
@ maps, songs, and specials tables. M-006 owns only the scene-1 Lab handoff;
@ starter selection, Rival selection, and every later Lab scene stay vanilla.
.equ FLAG_BEAT_RIVAL_IN_OAKS_LAB, 0x0258
.equ FLAG_HIDE_OAK_IN_HIS_LAB, 0x002B
.equ FLAG_HIDE_OAK_IN_PALLET_TOWN, 0x002C
.equ FLAG_DONT_TRANSITION_MUSIC, 0x4001
.equ VAR_MAP_SCENE_PALLET_TOWN_OAK, 0x4050
.equ VAR_MAP_SCENE_PALLET_TOWN_PROFESSOR_OAKS_LAB, 0x4055
.equ SPECIAL_HEAL_PLAYER_PARTY, 0x000
.equ MOVEMENT_TYPE_FACE_UP, 0x007
.equ SE_WARP_IN, 0x27
.equ SE_WARP_OUT, 0x28
.equ MUS_HEAL, 0x100
.equ MUS_DUMMY, 0x000
.equ MAP_GROUP_PALLET_TOWN, 4
.equ MAP_NUM_PALLET_TOWN_PROFESSOR_OAKS_LAB, 3
.equ LOCALID_MOM, 1

.global EventScript_TalkToMom
.global EventScript_TalkToMomExitBlock
.global EventScript_M006OaksLabOnWarp
.global EventScript_M006OaksLabChooseStarter

@ xse_defines.s owns BPRE CAMERA_START (0x113) and CAMERA_END (0x114).
EventScript_TalkToMom:
    lock
    faceplayer
    checkflag FLAG_BEAT_RIVAL_IN_OAKS_LAB
    if TRUE _goto EventScript_TalkToMomHeal

    msgbox gText_TalkToMomMagicTrick MSG_NORMAL
    closemessage
    waitdooranim
    special CAMERA_START
    applymovement PLAYER Movement_TalkToMomPlayerSpin
    waitmovement 0
    playse SE_WARP_IN
    applymovement PLAYER Movement_TalkToMomPlayerWarpOut
    waitmovement 0
    special CAMERA_END
    setvar VAR_MAP_SCENE_PALLET_TOWN_PROFESSOR_OAKS_LAB 1
    clearflag FLAG_HIDE_OAK_IN_HIS_LAB
    setvar VAR_MAP_SCENE_PALLET_TOWN_OAK 1
    setflag FLAG_HIDE_OAK_IN_PALLET_TOWN
    setflag FLAG_DONT_TRANSITION_MUSIC
    @ This (9, 6) destination is intentionally coupled to the source-backed
    @ scene-1 Lab OnWarp replacement below, which immediately places PLAYER
    @ at (9, 0) before the custom six-tile entrance movement runs.
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

@ M-006 replaces only the VAR_MAP_SCENE_PALLET_TOWN_PROFESSOR_OAKS_LAB == 1
@ OnWarp entry. This is Cyan's required positioning half of the (9, 6)
@ handoff; other Lab map-script states retain their BPRE pointers.
EventScript_M006OaksLabOnWarp:
    setobjectxy PLAYER 9 0
    setobjectmovementtype PLAYER MOVEMENT_TYPE_FACE_UP
    end

@ Cyan's scene-1 fast path: retain Oak's core selection prompt, but skip the
@ vanilla Oak entrance, eight-tile player walk, and Rival waiting dialogue.
@ Set scene 2 afterward so the original starter-ball scripts take over.
EventScript_M006OaksLabChooseStarter:
    lockall
    textcolor BLUE
    playse SE_WARP_OUT
    special CAMERA_START
    applymovement PLAYER Movement_M006OaksLabPlayerEnter
    waitmovement 0
    special CAMERA_END
    clearflag FLAG_DONT_TRANSITION_MUSIC
    savebgm MUS_DUMMY
    fadedefaultbgm
    waitse
    msgbox gText_M006OaksLabChooseStarter MSG_NORMAL
    closemessage
    setvar VAR_MAP_SCENE_PALLET_TOWN_PROFESSOR_OAKS_LAB 2
    releaseall
    end

@ Cyan PalletTown_ProfessorOaksLab_Movement_PlayerEnter:
@ delay_16, face_up, disable_anim, six slide_down, restore_anim, face_up.
Movement_M006OaksLabPlayerEnter:
    .byte pause_long, look_up, disable_anim
    .byte slide_down, slide_down, slide_down, slide_down, slide_down, slide_down
    .byte enable_anim, look_up, end_m

Movement_TalkToMomPlayerSpin:
    .byte look_up, pause_vshort, look_left, pause_vshort
    .byte look_down, pause_vshort, look_right, pause_vshort, end_m

Movement_TalkToMomPlayerWarpOut:
    .byte look_up, disable_anim
    .byte slide_up, slide_up, slide_up, slide_up, slide_up, slide_up, end_m

Movement_TalkToMomExitRight:
    .byte walk_right, end_m
