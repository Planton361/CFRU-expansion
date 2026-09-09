.align 2
.thumb

.include "../xse_commands.s"
.include "../xse_defines.s"
.include "../asm_defines.s"

@ M-007: bounded Faster FireRed parcel handoff. The values below are BPRE
@ source constants confirmed against pret's map, flag, var, and special tables.
.equ FLAG_HIDE_OAK_PALLET_TOWN_BALL_CUTSCENE, 0x0152
.equ FLAG_HIDE_ROUTE1_MART_CLERK_CUTSCENE, 0x0153
.equ FLAG_SYS_POKEDEX_GET, 0x0829
.equ VAR_MAP_SCENE_VIRIDIAN_CITY_OLD_MAN, 0x4051
.equ VAR_MAP_SCENE_ROUTE22, 0x4054
.equ VAR_MAP_SCENE_PALLET_TOWN_PROFESSOR_OAKS_LAB, 0x4055
.equ VAR_MAP_SCENE_VIRIDIAN_CITY_MART, 0x4057
.equ VAR_MAP_SCENE_PALLET_TOWN_RIVALS_HOUSE, 0x4058
.equ VAR_MAP_SCENE_POKEMON_CENTER_TEALA, 0x407C
.equ VAR_TEMP_1, 0x4001
.equ LOCALID_ROUTE1_MART_CLERK, 3
.equ LOCALID_PALLET_PARCEL_OAK, 4
.equ SPECIAL_SET_UNLOCKED_POKEDEX_FLAGS, 0x181
.equ face_down_fast, 0x04

.global EventScript_M007NoOp
.global EventScript_M007Route1ClerkTrigger10
.global EventScript_M007Route1ClerkTrigger11
.global EventScript_M007Route1ClerkTrigger12
.global EventScript_M007Route1ClerkTrigger13
.global EventScript_M007PalletOakTrigger12
.global EventScript_M007PalletOakTrigger13

@ The source-map templates use NULL scripts; this harmless source-owned end
@ lets the existing fail-closed object overlay carry an explicit script symbol.
EventScript_M007NoOp:
    end

EventScript_M007Route1ClerkTrigger10:
    lockall
    applymovement LOCALID_ROUTE1_MART_CLERK Movement_M007Route1ClerkApproach10
    waitmovement LOCALID_ROUTE1_MART_CLERK
    goto EventScript_M007Route1ClerkHandoff

EventScript_M007Route1ClerkTrigger11:
    lockall
    applymovement LOCALID_ROUTE1_MART_CLERK Movement_M007Route1ClerkApproach11
    waitmovement LOCALID_ROUTE1_MART_CLERK
    goto EventScript_M007Route1ClerkHandoff

EventScript_M007Route1ClerkTrigger12:
    lockall
    applymovement LOCALID_ROUTE1_MART_CLERK Movement_M007Route1ClerkApproach12
    waitmovement LOCALID_ROUTE1_MART_CLERK
    goto EventScript_M007Route1ClerkHandoff

EventScript_M007Route1ClerkTrigger13:
    lockall
    applymovement LOCALID_ROUTE1_MART_CLERK Movement_M007Route1ClerkApproach13
    waitmovement LOCALID_ROUTE1_MART_CLERK
    goto EventScript_M007Route1ClerkHandoff

EventScript_M007Route1ClerkHandoff:
    textcolor BLUE
    msgbox gText_M007Route1ClerkParcel MSG_NORMAL
    closemessage
    @ Scene 1 disables the vanilla Mart's scene-0 parcel handoff before the
    @ item is awarded, so that duplicate handoff cannot become reachable.
    setvar VAR_MAP_SCENE_VIRIDIAN_CITY_MART 1
    obtainitem ITEM_OAKS_PARCEL 1
    closemessage
    applymovement LOCALID_ROUTE1_MART_CLERK Movement_M007Route1ClerkLeave
    waitmovement LOCALID_ROUTE1_MART_CLERK
    removeobject LOCALID_ROUTE1_MART_CLERK
    fadedefaultbgm
    setflag FLAG_HIDE_ROUTE1_MART_CLERK_CUTSCENE
    clearflag FLAG_HIDE_OAK_PALLET_TOWN_BALL_CUTSCENE
    setvar VAR_MAP_SCENE_PALLET_TOWN_PROFESSOR_OAKS_LAB 5
    releaseall
    end

EventScript_M007PalletOakTrigger12:
    lockall
    setvar VAR_TEMP_1 0
    applymovement LOCALID_PALLET_PARCEL_OAK Movement_M007PalletOakApproach12
    waitmovement LOCALID_PALLET_PARCEL_OAK
    goto EventScript_M007PalletOakHandoff

EventScript_M007PalletOakTrigger13:
    lockall
    setvar VAR_TEMP_1 1
    applymovement LOCALID_PALLET_PARCEL_OAK Movement_M007PalletOakApproach13
    waitmovement LOCALID_PALLET_PARCEL_OAK
    goto EventScript_M007PalletOakHandoff

EventScript_M007PalletOakHandoff:
    textcolor BLUE
    msgbox gText_M007PalletOakHandoff MSG_NORMAL
    closemessage
    textcolor BLACK
    removeitem ITEM_OAKS_PARCEL 1
    @ Match the normal BPRE parcel completion path. Do not enable the National
    @ Dex here: that remains the project's existing later-game policy.
    setflag FLAG_SYS_POKEDEX_GET
    special SPECIAL_SET_UNLOCKED_POKEDEX_FLAGS
    obtainitem ITEM_POKE_BALL 5
    setvar VAR_MAP_SCENE_POKEMON_CENTER_TEALA 1
    closemessage
    compare VAR_TEMP_1 0
    if equal _call EventScript_M007PalletOakLeave12
    compare VAR_TEMP_1 1
    if equal _call EventScript_M007PalletOakLeave13
    setvar VAR_MAP_SCENE_PALLET_TOWN_PROFESSOR_OAKS_LAB 6
    setvar VAR_MAP_SCENE_VIRIDIAN_CITY_MART 2
    @ Faster FireRed intentionally skips the Old Man tutorial and uses scene 2.
    setvar VAR_MAP_SCENE_VIRIDIAN_CITY_OLD_MAN 2
    setvar VAR_MAP_SCENE_PALLET_TOWN_RIVALS_HOUSE 1
    setvar VAR_MAP_SCENE_ROUTE22 1
    setflag FLAG_HIDE_OAK_PALLET_TOWN_BALL_CUTSCENE
    releaseall
    end

EventScript_M007PalletOakLeave12:
    applymovement LOCALID_PALLET_PARCEL_OAK Movement_M007PalletOakLeave12
    waitmovement LOCALID_PALLET_PARCEL_OAK
    removeobject LOCALID_PALLET_PARCEL_OAK
    return

EventScript_M007PalletOakLeave13:
    applymovement LOCALID_PALLET_PARCEL_OAK Movement_M007PalletOakLeave13
    waitmovement LOCALID_PALLET_PARCEL_OAK
    removeobject LOCALID_PALLET_PARCEL_OAK
    return

Movement_M007Route1ClerkApproach10:
    .byte run_left, run_left, run_left, face_down_fast, end_m

Movement_M007Route1ClerkApproach11:
    .byte run_left, run_left, face_down_fast, end_m

Movement_M007Route1ClerkApproach12:
    .byte run_left, face_down_fast, end_m

Movement_M007Route1ClerkApproach13:
    .byte face_down_fast, end_m

Movement_M007Route1ClerkLeave:
    .byte run_up, run_up, run_up, run_up, run_up, run_up, end_m

Movement_M007PalletOakApproach12:
    .byte run_up, run_up, run_up, run_up, run_up
    .byte run_right, run_up, run_up, end_m

Movement_M007PalletOakApproach13:
    .byte run_up, run_up, run_up, run_up, run_up
    .byte run_right, run_right, run_up, run_up, end_m

Movement_M007PalletOakLeave12:
    .byte run_down, run_down, run_left, run_down, run_down
    .byte run_down, run_down, run_down, end_m

Movement_M007PalletOakLeave13:
    .byte run_down, run_down, run_left, run_left, run_down
    .byte run_down, run_down, run_down, run_down, run_down, end_m
