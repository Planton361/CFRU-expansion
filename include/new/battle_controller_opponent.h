#pragma once

/**
 * \file battle_controller_opponent.h
 * \brief Contains functions relating the controller of the opponent in battles.
 *		  Includes things such as move choosing, trainer sliding, mon choosing,
 *		  and loading the correct trainer picture.
 */

//Exported Functions
/*NONE*/

struct ChooseMoveStruct;
bool8 OpponentHandleSupportedAIMoveChoice(struct ChooseMoveStruct *moveInfo);

#ifdef CFRU_AI_TEST_TRACE
struct OpponentAIDispatchTrace
{
	u16 rawProfile, trainerId, publicPlayerSpecies, publicOpponentSpecies;
	u16 moves[MAX_MON_MOVES], selectedMove, emittedMove;
	u32 battleFlags, exclusionBits;
	s16 policyRc;
	u8 profile, standardSupported, ironmonSupported;
	u8 raid, inverse, frontierTrainer;
	u8 activeBattler, bankAttacker, bankTarget, defenseStage;
	u8 adapter, selectedSlot, emittedSlot;
	u8 resolvedBeforeMarker, adapterFailureReason;
	u8 controllerBufferMismatch, boundedFallback, diagnosticClass;
};
extern struct OpponentAIDispatchTrace OpponentAI_DispatchTrace;
#endif

//Functions hooked in
void OpponentHandleChooseMove(void);
void OpponentHandleDrawTrainerPic(void);
void OpponentHandleTrainerSlide(void);
void OpponentHandleChoosePokemon(void);

//Exported Constants
#define AI_CHOICE_FLEE 4
#define AI_CHOICE_WATCH 5
