.thumb
.align 2

.include "../xse_commands.s"
.include "../xse_defines.s"
.include "../asm_defines.s"

.global EventScript_ViridianForest_Nurse

EventScript_ViridianForest_Nurse:
    lock
    faceplayer
    callasm ViridianForest_IsPoisonInParty
    compare LASTRESULT TRUE
    if TRUE _goto EventScript_ViridianForest_NurseCantHealPoison

    msgbox gText_ViridianForest_NurseHealAsk MSG_YESNO
    compare LASTRESULT YES
    if TRUE _goto EventScript_ViridianForest_NurseHeal

    msgbox gText_ViridianForest_NurseNo MSG_NORMAL
    release
    end

EventScript_ViridianForest_NurseHeal:
    special 0x0 @ HealPlayerParty
    playse 0x1 @ SE_USE_ITEM
    waitse
    msgbox gText_ViridianForest_NurseHealed MSG_NORMAL
    release
    end

EventScript_ViridianForest_NurseCantHealPoison:
    msgbox gText_ViridianForest_NurseCantHealPoison MSG_NORMAL
    release
    end
