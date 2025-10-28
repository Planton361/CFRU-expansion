.thumb
.align 2

.include "../xse_commands.s"
.include "../xse_defines.s"
.include "../asm_defines.s"

.global EventScriptP_ViridianCity_Youngster
.global EventScriptP_ViridianCity_YoungMan
.global EventScriptP_ViridianCity_YoungLady


.macro resetvar var
setvar \var 0
.endm

@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
EventScriptP_ViridianCity_Youngster:
    lock
    faceplayer
    additem ITEM_LEFTOVERS 1

    @ Relatable Mons
    setvar 0x8000 MOVE_AURASPHERE
    setvar 0x8001 MOVE_DAZZLINGGLEAM
    setvar 0x8002 MOVE_THUNDERWAVE
    setvar 0x8003 MOVE_MOONLIGHT
    setvar 0x8004 NATURE_MODEST
    setvar 0x8005 NOT_SHINY
    setvar 0x8006 16
    setvar 0x8007 16
    setvar 0x8008 16
    setvar 0x8009 16
    setvar 0x800A 16
    setvar 0x800B 16
    givepokemon SPECIES_TOGETIC 26 ITEM_LEFTOVERS 0 1 10

    @ Set-Up Gyarados
    setvar 0x8000 MOVE_WATERFALL
    setvar 0x8001 MOVE_ICEFANG
    setvar 0x8002 MOVE_DRAGONDANCE
    setvar 0x8003 MOVE_EARTHQUAKE
    setvar 0x8004 NATURE_ADAMANT
    setvar 0x8005 IS_SHINY
    setvar 0x8006 16
    setvar 0x8007 16
    setvar 0x8008 16
    setvar 0x8009 16
    setvar 0x800A 16
    setvar 0x800B 16
    givepokemon SPECIES_GYARADOS 26 ITEM_LEFTOVERS 0 1 5

    setflag 0x82F
    @ Mega Blaziken
    setvar 0x8000 MOVE_BLAZEKICK
    setvar 0x8001 MOVE_SKYUPPERCUT
    setvar 0x8002 MOVE_THUNDERPUNCH
    setvar 0x8003 MOVE_SWORDSDANCE
    setvar 0x8004 NATURE_ADAMANT
    setvar 0x8005 NOT_SHINY
    setvar 0x8006 31
    setvar 0x8007 31
    setvar 0x8008 31
    setvar 0x8009 31
    setvar 0x800A 31
    setvar 0x800B 31
    givepokemon SPECIES_BLAZIKEN 40 ITEM_LEFTOVERS 0 9

    @ Meganium
    setvar 0x8000 MOVE_SEEDBOMB
    setvar 0x8001 MOVE_SYNTHESIS
    setvar 0x8002 MOVE_TOXIC
    setvar 0x8003 MOVE_PROTECT
    setvar 0x8004 NATURE_TIMID
    setvar 0x8005 NOT_SHINY
    setvar 0x8006 31
    setvar 0x8007 31
    setvar 0x8008 31
    setvar 0x8009 31
    setvar 0x800A 31
    setvar 0x800B 31
    givepokemon SPECIES_BULBASAUR 3 ITEM_LEFTOVERS 0 9

    additem ITEM_MEGA_RING 1
    msgbox gText_ViridianCity_Youngster MSG_NORMAL
    release
    end

@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
EventScriptP_ViridianCity_YoungMan:
    lock
    faceplayer

    setflag 0xA09 @ Sabotage Battle
    additem ITEM_SUPER_POTION 0x1
    trainerbattle0 0 329 0 gText_ViridianCity_BattleStart gText_ViridianCity_BattleEnd
    msgbox gText_ViridianCity_BattleOver MSG_NORMAL

    release
    end

@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
