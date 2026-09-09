.align 2
.thumb

.include "../xse_commands.s"
.include "../xse_defines.s"
.include "../asm_defines.s"

.global EventScript_OaksLabPotion

EventScript_OaksLabPotion:
	finditem ITEM_POTION 1
	end
