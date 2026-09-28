.align 2
.thumb

.include "../xse_commands.s"
.include "../xse_defines.s"
.include "../asm_defines.s"

@ Public pret source maps Pewter's final object (index 6) to local ID 7.
.equ LOCALID_PEWTER_RUNNING_SHOES_AIDE, 7
.equ VAR_MAP_SCENE_PEWTER_CITY, 0x406C
.equ FLAG_HIDE_PEWTER_CITY_RUNNING_SHOES_GUY, 0x0092

.global EventScript_PewterRunningShoesCleanup
EventScript_PewterRunningShoesCleanup:
    lockall
    setvar VAR_MAP_SCENE_PEWTER_CITY 2
    setflag FLAG_HIDE_PEWTER_CITY_RUNNING_SHOES_GUY
    removeobject LOCALID_PEWTER_RUNNING_SHOES_AIDE
    releaseall
    end
