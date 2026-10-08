.thumb
.text
.align 2
.global gEvolutionFriendshipContract
.type gEvolutionFriendshipContract, %object

/* v1: retained by the ordinary assembly glob/linker .text path.
 * GetEvolutionTargetSpecies reads threshold through its volatile declaration.
 * The consumer relocation binds discovery to the unchanged live hook.
 */
gEvolutionFriendshipContract:
.ascii "CFRUEVO1"
.word gEvolutionFriendshipContract
.word GetEvolutionTargetSpecies
.hword 1                      @ version
.hword 32                     @ record size
.hword 28                     @ threshold offset
.hword 1                      @ threshold width
.hword 220                    @ default threshold
.hword 160                    @ optional easier threshold
.byte 220                     @ live threshold; the only patchable byte
.byte 0                       @ reserved
.hword 0                      @ reserved
.size gEvolutionFriendshipContract, .-gEvolutionFriendshipContract
