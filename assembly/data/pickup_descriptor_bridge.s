.cpu arm7tdmi
.syntax unified
.thumb
.text
.align 2
.global atkE5_pickupitemcalculation
.type atkE5_pickupitemcalculation, %function
.thumb_func
atkE5_pickupitemcalculation:
    @ ABI v1: 28 bytes, 4-aligned. E5 remains a void(void) Thumb command.
    @ Preserve the caller's LR and 8-byte stack alignment; r0 is the ONLY
    @ descriptor argument used by the C consumer. No compiler literal search.
    push {r4, lr}                   @ +0
    ldr r0, .Lpickup_descriptor      @ +2, PC+16 -> +20
    ldr r3, .Lpickup_consumer        @ +4, PC+16 -> +24
    bl .Lpickup_call                @ +6, local Thumb-1 call -> +16
    pop {r4}                        @ +10
    pop {r0}                        @ +12, saved LR (void return)
    bx r0                           @ +14, preserves caller state
.Lpickup_call:
    bx r3                           @ +16, C Thumb function, returns to +10
    nop                             @ +18, word alignment
.Lpickup_descriptor:
    .word gPickupDescriptor          @ +20, the same r0 seen by the consumer
.Lpickup_consumer:
    .word PickupItemCalculation      @ +24, linker supplies Thumb bit
.Lpickup_end:
.if (.Lpickup_call - atkE5_pickupitemcalculation) != 16
.error "Pickup ABI v1 call offset drift"
.endif
.if (.Lpickup_descriptor - atkE5_pickupitemcalculation) != 20
.error "Pickup ABI v1 descriptor offset drift"
.endif
.if (.Lpickup_consumer - atkE5_pickupitemcalculation) != 24
.error "Pickup ABI v1 consumer offset drift"
.endif
.if (.Lpickup_end - atkE5_pickupitemcalculation) != 28
.error "Pickup ABI v1 bridge size drift"
.endif
.size atkE5_pickupitemcalculation, .Lpickup_end - atkE5_pickupitemcalculation
