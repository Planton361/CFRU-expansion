.align 2
.thumb

.include "../xse_commands.s"
.include "../xse_defines.s"
.include "../asm_defines.s"

@ BPRE's HM05/Flash item and the original Route 2 aide's award flag.
.equ ITEM_HM05, 343
.equ FLAG_GOT_HM05, 0x23B
.equ LOCALID_ROUTE10_HIKER, 11

.global EventScript_Route10HM05
EventScript_Route10HM05:
    lock
    faceplayer
    checkflag FLAG_GOT_HM05
    if TRUE _goto EventScript_Route10HM05Done
    msgbox gText_Route10HM05 MSG_NORMAL
    checkitemspace ITEM_HM05 1
    compare LASTRESULT FALSE
    if equal _goto EventScript_Route10HM05NoRoom
    obtainitem ITEM_HM05 1
    compare LASTRESULT FALSE
    if equal _goto EventScript_Route10HM05Release
    setflag FLAG_GOT_HM05
    msgbox gText_Route10HM05Explain MSG_NORMAL
EventScript_Route10HM05Done:
    closemessage
    removeobject LOCALID_ROUTE10_HIKER
EventScript_Route10HM05Release:
    release
    end

EventScript_Route10HM05NoRoom:
    msgbox gText_Route10HM05NoRoom MSG_NORMAL
    goto EventScript_Route10HM05Release
