.align 2
.thumb

.include "../xse_commands.s"
.include "../xse_defines.s"

@ #595: pinned pret BPRE ChoseStarter 0x08169C74 + 1 + 3 + 8.
@ Resume at the original call RestorePrevTextColor, after only the flavor.
.equ ChoseStarter_RestoreAndAward, 0x08169C80

.global EventScript_ChoseStarterNoFlavor
EventScript_ChoseStarterNoFlavor:
    erasemonpic
    removeobject LASTTALKED
    goto ChoseStarter_RestoreAndAward
