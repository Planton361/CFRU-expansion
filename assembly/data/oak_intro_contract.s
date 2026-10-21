.cpu arm7tdmi
.syntax unified
.thumb
.text

@ Existing functionrewrites entry symbols are defined ONLY here.
@ Thumb-1 ABI: r0 taskId unchanged, r1 descriptor, r3 actual C consumer.
@ Push 8 bytes; local BL supplies a Thumb return to +10; BX r3 interworks.
@ Return through saved caller LR, including its instruction-set state.

.align 2
.global CreateOakIntroPokemonSprite
.type CreateOakIntroPokemonSprite, %function
.thumb_func
CreateOakIntroPokemonSprite:
    push {r4, lr}                    @ +0
    ldr r1, .Loak_sprite_descriptor    @ +2, PC+16 -> +20
    ldr r3, .Loak_sprite_consumer      @ +4, PC+16 -> +24
    bl .Loak_sprite_call              @ +6 -> +16
    pop {r4}                         @ +10
    pop {r0}                         @ +12, void return
    bx r0                            @ +14
.Loak_sprite_call:
    bx r3                            @ +16
    nop                              @ +18
.Loak_sprite_descriptor:
    .word gOakIntroContract           @ +20
.Loak_sprite_consumer:
    .word OakIntroSpriteConsumer                  @ +24, linker Thumb relocation
.Loak_sprite_end:
.if (.Loak_sprite_call - CreateOakIntroPokemonSprite) != 16
.error "Oak sprite call offset drift"
.endif
.if (.Loak_sprite_descriptor - CreateOakIntroPokemonSprite) != 20
.error "Oak sprite descriptor literal drift"
.endif
.if (.Loak_sprite_consumer - CreateOakIntroPokemonSprite) != 24
.error "Oak sprite consumer literal drift"
.endif
.if (.Loak_sprite_end - CreateOakIntroPokemonSprite) != 28
.error "Oak sprite bridge size drift"
.endif
.size CreateOakIntroPokemonSprite, .Loak_sprite_end - CreateOakIntroPokemonSprite

.align 2
.global Task_OakSpeech_IsInhabitedFarAndWide
.type Task_OakSpeech_IsInhabitedFarAndWide, %function
.thumb_func
Task_OakSpeech_IsInhabitedFarAndWide:
    push {r4, lr}                    @ +0
    ldr r1, .Loak_cry_descriptor    @ +2, PC+16 -> +20
    ldr r3, .Loak_cry_consumer      @ +4, PC+16 -> +24
    bl .Loak_cry_call              @ +6 -> +16
    pop {r4}                         @ +10
    pop {r0}                         @ +12, void return
    bx r0                            @ +14
.Loak_cry_call:
    bx r3                            @ +16
    nop                              @ +18
.Loak_cry_descriptor:
    .word gOakIntroContract           @ +20
.Loak_cry_consumer:
    .word OakIntroCryConsumer                  @ +24, linker Thumb relocation
.Loak_cry_end:
.if (.Loak_cry_call - Task_OakSpeech_IsInhabitedFarAndWide) != 16
.error "Oak cry call offset drift"
.endif
.if (.Loak_cry_descriptor - Task_OakSpeech_IsInhabitedFarAndWide) != 20
.error "Oak cry descriptor literal drift"
.endif
.if (.Loak_cry_consumer - Task_OakSpeech_IsInhabitedFarAndWide) != 24
.error "Oak cry consumer literal drift"
.endif
.if (.Loak_cry_end - Task_OakSpeech_IsInhabitedFarAndWide) != 28
.error "Oak cry bridge size drift"
.endif
.size Task_OakSpeech_IsInhabitedFarAndWide, .Loak_cry_end - Task_OakSpeech_IsInhabitedFarAndWide

.align 2
.global gOakIntroContract
.type gOakIntroContract, %object
gOakIntroContract:
    .ascii "CFROAK01"                 @ 0
    .word gOakIntroContract            @ 8: self, not a copied marker
    .hword 1                          @ 12: version
    .hword 96                         @ 14: descriptor size
    .word 1                           @ 16: CFRU/DPE native profile
    .hword 1440                       @ 20: table capacity
    .hword 29                         @ 22: default Nidoran F
    .hword 92                         @ 24: writable selector offset
    .hword 2                          @ 26: selector width
    .word gOakIntroEligibility         @ 28: immutable policy owner
    .hword 180                        @ 32: bitmap bytes
    .hword 1                          @ 34: policy version
    .word CreateOakIntroPokemonSprite  @ 36: Thumb bridge
    .word OakIntroSpriteConsumer       @ 40: Thumb C consumer
    .word Task_OakSpeech_IsInhabitedFarAndWide @ 44: Thumb bridge
    .word OakIntroCryConsumer          @ 48: Thumb C consumer
    .word 0x08000128                   @ 52: front table repoint slot
    .word 0x08000130                   @ 56: normal palette repoint slot
    .hword 8                          @ 60: complete front row stride
    .hword 8                          @ 62: complete normal palette stride
    .hword 28                         @ 64: bridge bytes
    .hword 20                         @ 66: descriptor literal offset
    .hword 24                         @ 68: consumer literal offset
    .hword 4                          @ 70: pointer width
    .space 20, 0                      @ 72: reserved, immutable zero
.Loak_selected_species:
    .hword 29                         @ 92: ONLY future UPR mutable field
    .hword 0                          @ 94: reserved, immutable zero
.Loak_contract_end:
.if (.Loak_selected_species - gOakIntroContract) != 92
.error "Oak selector offset drift"
.endif
.if (.Loak_contract_end - gOakIntroContract) != 96
.error "Oak descriptor size drift"
.endif
.size gOakIntroContract, .Loak_contract_end - gOakIntroContract

@ DPE d887185de1f6ae6a78e85c4311bbadde17041d00 public source + asset names.
@ LSB-first, bit i selects native ID i; NOT a blanket valid-ID range.
@ See docs/testing/oak-intro-abi-v1.md and reproducible public-source test.
.align 2
.global gOakIntroEligibility
.type gOakIntroEligibility, %object
gOakIntroEligibility:
    .byte 0xfe, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff @ slots 0..95
    .byte 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff @ slots 96..191
    .byte 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x0f, 0x00, 0x00, 0xe0, 0xff @ slots 192..287
    .byte 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff @ slots 288..383
    .byte 0xfd, 0xff, 0xff, 0xeb, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff @ slots 384..479
    .byte 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff @ slots 480..575
    .byte 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff @ slots 576..671
    .byte 0xff, 0xff, 0xff, 0xff, 0xfb, 0x3f, 0x00, 0x00, 0xfd, 0x03, 0xdf, 0xff @ slots 672..767
    .byte 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xdf, 0x21, 0xff, 0xff, 0xff @ slots 768..863
    .byte 0x1f, 0x00, 0x00, 0x00, 0x00, 0x00, 0x80, 0xff, 0xff, 0xff, 0xff, 0xff @ slots 864..959
    .byte 0xff, 0xff, 0xff, 0x7f, 0xff, 0xff, 0xff, 0xff, 0xff, 0xaf, 0x78, 0x00 @ slots 960..1055
    .byte 0x00, 0xfe, 0xfe, 0xfd, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff @ slots 1056..1151
    .byte 0xff, 0xff, 0xff, 0xff, 0x7f, 0xfe, 0x0b, 0xff, 0xfb, 0x6f, 0xff, 0xff @ slots 1152..1247
    .byte 0xff, 0x0f, 0x00, 0x00, 0x00, 0xc0, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff @ slots 1248..1343
    .byte 0xff, 0xbf, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xc3, 0x9f @ slots 1344..1439
.Loak_eligibility_end:
.if (.Loak_eligibility_end - gOakIntroEligibility) != 180
.error "Oak eligibility size drift"
.endif
.size gOakIntroEligibility, .Loak_eligibility_end - gOakIntroEligibility
