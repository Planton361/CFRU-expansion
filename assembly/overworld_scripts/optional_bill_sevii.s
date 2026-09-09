.align 2
.thumb

.include "../xse_commands.s"
.include "../xse_defines.s"
.include "../asm_defines.s"

@ M-008: BPRE Cinnabar Island scene-1 bypass. These constants are verified
@ against the current CFRU BPRE headers and pret's Cinnabar source map.
.equ LOCALID_CINNABAR_BILL, 3
.equ VAR_MAP_SCENE_CINNABAR_ISLAND, 0x4071
.equ FLAG_HIDE_CINNABAR_POKECENTER_BILL, 0x00A2

.global EventScript_M008BillWaitInPokeCenter

@ Replace only the automatic outdoor Bill scene. The existing Cinnabar
@ Pokemon Center Bill remains the original interactive Yes/No travel script.
EventScript_M008BillWaitInPokeCenter:
    lockall
    removeobject LOCALID_CINNABAR_BILL
    setvar VAR_MAP_SCENE_CINNABAR_ISLAND 2
    clearflag FLAG_HIDE_CINNABAR_POKECENTER_BILL
    releaseall
    end
