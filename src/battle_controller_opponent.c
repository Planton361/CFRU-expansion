#include "defines.h"
#include "defines_battle.h"
#include "../include/battle_anim.h"
#include "../include/event_data.h"
#include "../include/pokeball.h"
#include "../include/random.h"
#include "../include/constants/trainers.h"

#include "../include/new/ai_util.h"
#include "../include/new/ai_master.h"
#include "../include/new/ai_standard.h"
#include "../include/new/ai_ironmon.h"
#include "../include/new/ai_switching.h"
#include "../include/new/ai_opponent_replacement.h"
#include "../include/new/battle_controller_opponent.h"
#include "../include/new/battle_start_turn_start.h"
#include "../include/new/battle_util.h"
#include "../include/new/frontier.h"
#include "../include/new/mega.h"
#include "../include/new/move_menu.h"
#include "../include/new/multi.h"
#include "../include/new/switching.h"
#include "../include/naming_screen.h"
#include "../include/new/terastallization.h"
#include "../include/new/util.h"

/*
battle_controller_opponent.c
	handles the functions responsible for the user moving between battle menus, choosing moves, etc.
*/

//This file's functions:
static void TryRechoosePartnerMove(u16 chosenMove);
static bool8 OpponentProfileReplacementIndexIsUsable(u8 chosenMonId);
static u8 LoadCorrectTrainerPicId(void);
#ifdef CFRU_AI_TEST_TRACE
u8 OpponentAI_TestLastBufferMismatch;
u8 OpponentAI_TestLastBoundedFallback;
struct OpponentAIDispatchTrace OpponentAI_DispatchTrace;
extern int StandardAI_TestLastPolicyRc;
extern int IronmonAI_TestLastPolicyRc;

static void OpponentAI_CaptureDispatchEntry(void)
{
	struct OpponentAIDispatchTrace *trace = &OpponentAI_DispatchTrace;
	u8 i, bank = gActiveBattler;
	Memset(trace, 0, sizeof(*trace));
	trace->rawProfile = VarGet(VAR_TRAINER_AI_PROFILE);
	trace->profile = GetTrainerAIProfile();
	trace->trainerId = gTrainerBattleOpponent_A;
	trace->battleFlags = gBattleTypeFlags;
	trace->exclusionBits = gBattleTypeFlags & (BATTLE_TYPE_DOUBLE | BATTLE_TYPE_LINK
		| BATTLE_TYPE_OAK_TUTORIAL | BATTLE_TYPE_MULTI | BATTLE_TYPE_SAFARI
		| BATTLE_TYPE_ROAMER | BATTLE_TYPE_EREADER_TRAINER
		| BATTLE_TYPE_SCRIPTED_WILD_1 | BATTLE_TYPE_SCRIPTED_WILD_2
		| BATTLE_TYPE_LEGENDARY_FRLG | BATTLE_TYPE_TRAINER_TOWER
		| BATTLE_TYPE_TWO_OPPONENTS | BATTLE_TYPE_INGAME_PARTNER
		| BATTLE_TYPE_POKE_DUDE | BATTLE_TYPE_OLD_MAN | BATTLE_TYPE_FRONTIER
		| BATTLE_TYPE_SHADOW_WARRIOR | BATTLE_TYPE_DYNAMAX
		| BATTLE_TYPE_KYOGRE_GROUDON | BATTLE_TYPE_REGI | BATTLE_TYPE_GHOST
		| BATTLE_TYPE_RING_CHALLENGE | BATTLE_TYPE_MOCK_BATTLE
		| BATTLE_TYPE_BENJAMIN_BUTTERFREE | BATTLE_TYPE_CAMOMONS
		| BATTLE_TYPE_MEGA_BRAWL);
	trace->raid = IsRaidBattle();
	trace->inverse = IsInverseBattle();
	trace->frontierTrainer = IsFrontierTrainerId(gTrainerBattleOpponent_A);
	trace->standardSupported = StandardAI_IsSupportedBattle();
	trace->ironmonSupported = IronmonAI_IsSupportedBattle();
	trace->activeBattler = bank;
	trace->bankAttacker = gBankAttacker;
	trace->bankTarget = gBankTarget;
	trace->selectedSlot = trace->emittedSlot = 0xFF;
	trace->policyRc = -1;
	if (bank >= MAX_BATTLERS_COUNT || gNewBS == NULL)
		return;
	trace->publicPlayerSpecies = gNewBS->ai.standardDisplayedSpecies[FOE(bank)];
	trace->publicOpponentSpecies = gNewBS->ai.standardDisplayedSpecies[bank];
	trace->defenseStage = gBattleMons[FOE(bank)].statStages[STAT_STAGE_DEF - 1];
	for (i = 0; i < MAX_MON_MOVES; ++i)
		trace->moves[i] = gBattleMons[bank].moves[i];
}
#endif

#ifdef TRAINER_AI_RUNTIME_DISPATCH_TRACE
static bool8 OpponentNormalizeSupportedMoveInfo(struct ChooseMoveStruct *moveInfo, u8 bank);
/* The marker is deliberately outside the fair-support gate: a rejected gate
 * is one of the states it must expose. Normal builds contain none of this. */
static bool8 OpponentHandleOakDispatchMarker(struct ChooseMoveStruct *moveInfo)
{
	u8 slot;
	u8 target;
	u8 bank = gActiveBattler;
	u16 publicSpecies;
	u16 move;

	if (gTrainerBattleOpponent_A != TRAINER_RIVAL_OAKS_LAB_SQUIRTLE
		|| !(gBattleTypeFlags & BATTLE_TYPE_TRAINER)
		|| (gBattleTypeFlags & (BATTLE_TYPE_DOUBLE | BATTLE_TYPE_LINK
			| BATTLE_TYPE_MULTI | BATTLE_TYPE_TWO_OPPONENTS))
		|| bank >= MAX_BATTLERS_COUNT || SIDE(bank) != B_SIDE_OPPONENT
		|| gNewBS == NULL || gBattleMons[bank].species != SPECIES_SQUIRTLE
		|| gBattleMons[bank].moves[0] != MOVE_TACKLE
		|| gBattleMons[bank].moves[1] != MOVE_TAILWHIP
		|| gBattleMons[bank].moves[2] != MOVE_WATERGUN
		|| gBattleMons[bank].moves[3] != MOVE_NONE
		|| gBattleResults.battleTurnCounter > 2)
		return FALSE;

	if (gBattleResults.battleTurnCounter == 0)
		slot = IronmonAI_IsSupportedBattle() ? 2
			: StandardAI_IsSupportedBattle() ? 0 : 1;
	else if (gBattleResults.battleTurnCounter == 1)
	{
		enum TrainerAIProfile profile = GetTrainerAIProfile();
		slot = profile == TRAINER_AI_PROFILE_IRONMON_SMART ? 2
			: profile == TRAINER_AI_PROFILE_STANDARD ? 0 : 1;
	}
	else
	{
		publicSpecies = gNewBS->ai.standardDisplayedSpecies[FOE(bank)];
		slot = publicSpecies == SPECIES_CHARMANDER ? 2
			: publicSpecies == SPECIES_NONE ? 0 : 1;
	}

	/* A restriction or exhausted PP makes the proposed marker illegal. Let the
	 * ordinary controller handle that state instead of emitting a false code. */
	if (!gBattleMons[bank].pp[slot]
		|| (CheckMoveLimitations(bank, 0, 0xFF) & gBitTable[slot]))
		return FALSE;

	OpponentNormalizeSupportedMoveInfo(moveInfo, bank);
	move = gBattleMons[bank].moves[slot];
	target = gBattleMoves[move].target;
	gBankAttacker = bank;
	gBankTarget = target & (MOVE_TARGET_USER | MOVE_TARGET_USER_OR_PARTNER)
		? bank : FOE(bank);
	gBattleStruct->chosenMovePositions[bank] = slot;
	gBattleStruct->moveTarget[bank] = gBankTarget;
	gChosenMovesByBanks[bank] = move;
	EmitMoveChosen(1, slot, gBankTarget, 0, 0, 0, FALSE, 0);
#ifdef CFRU_AI_TEST_TRACE
	OpponentAI_DispatchTrace.adapter = 3;
	OpponentAI_DispatchTrace.selectedSlot = slot;
	OpponentAI_DispatchTrace.selectedMove = move;
	OpponentAI_DispatchTrace.emittedSlot = slot;
	OpponentAI_DispatchTrace.emittedMove = move;
#endif
	OpponentBufferExecCompleted();
	return TRUE;
}
#endif

static bool8 OpponentNormalizeSupportedMoveInfo(struct ChooseMoveStruct *moveInfo,
	u8 bank)
{
	u8 i;
	for (i = 0; i < MAX_MON_MOVES; ++i)
		if (moveInfo->moves[i] != gBattleMons[bank].moves[i])
		{
			u8 j;
			/* The fair adapters rank gBattleMons slots. Restore the controller's
			 * local view from that same authoritative own-move array before any
			 * slot index is emitted. */
			for (j = 0; j < MAX_MON_MOVES; ++j)
				moveInfo->moves[j] = gBattleMons[bank].moves[j];
			return TRUE;
		}
	return FALSE;
}

static u8 OpponentResolveSupportedAIMoveSlot(struct ChooseMoveStruct *moveInfo,
	u8 bank, u8 chosenMovePos)
{
	if (chosenMovePos >= MAX_MON_MOVES
		|| moveInfo->moves[chosenMovePos] != gBattleMons[bank].moves[chosenMovePos]
		|| moveInfo->moves[chosenMovePos] == MOVE_NONE)
	{
		/* Do not turn a sentinel/non-move/slot mismatch into literal slot 0.
		 * Ask the source adapter for a bounded own-move emergency slot; when no
		 * move is legal it returns an occupied slot for engine Struggle logic. */
		chosenMovePos = StandardAI_ChooseEmergencyMoveSlot(bank);
#ifdef CFRU_AI_TEST_TRACE
		OpponentAI_TestLastBoundedFallback = TRUE;
#endif
	}
	if (moveInfo->moves[chosenMovePos] != gBattleMons[bank].moves[chosenMovePos])
	{
		u8 i;
		for (i = 0; i < MAX_MON_MOVES; ++i)
			moveInfo->moves[i] = gBattleMons[bank].moves[i];
	}
	return chosenMovePos;
}

bool8 OpponentHandleSupportedAIMoveChoice(struct ChooseMoveStruct *moveInfo)
{
	u8 chosenMovePos;
	if (IronmonAI_IsSupportedBattle())
	{
		u8 target;
		bool8 bufferMismatch = OpponentNormalizeSupportedMoveInfo(moveInfo, gActiveBattler);
#ifdef CFRU_AI_TEST_TRACE
		OpponentAI_TestLastBufferMismatch = bufferMismatch;
		OpponentAI_TestLastBoundedFallback = FALSE;
#endif
		BattleAI_SetupAIData(0xF);
		chosenMovePos = IronmonAI_ChooseMoveOrAction();
#ifdef CFRU_AI_TEST_TRACE
		OpponentAI_DispatchTrace.adapter = 2;
		OpponentAI_DispatchTrace.policyRc = IronmonAI_TestLastPolicyRc;
		OpponentAI_DispatchTrace.selectedSlot = chosenMovePos;
		OpponentAI_DispatchTrace.selectedMove = chosenMovePos < MAX_MON_MOVES
			? gBattleMons[gActiveBattler].moves[chosenMovePos] : MOVE_NONE;
#endif
		chosenMovePos = OpponentResolveSupportedAIMoveSlot(moveInfo, gActiveBattler,
			chosenMovePos);
		target = gBattleMoves[moveInfo->moves[chosenMovePos]].target;
		gBankTarget = target & (MOVE_TARGET_USER | MOVE_TARGET_USER_OR_PARTNER)
			? gActiveBattler : FOE(gActiveBattler);
		gBattleStruct->chosenMovePositions[gActiveBattler] = chosenMovePos;
		gBattleStruct->moveTarget[gActiveBattler] = gBankTarget;
		gChosenMovesByBanks[gActiveBattler] = moveInfo->moves[chosenMovePos];
		EmitMoveChosen(1, chosenMovePos, gBankTarget, 0, 0, 0, FALSE, 0);
#ifdef CFRU_AI_TEST_TRACE
		OpponentAI_DispatchTrace.emittedSlot = chosenMovePos;
		OpponentAI_DispatchTrace.emittedMove = moveInfo->moves[chosenMovePos];
#endif
		OpponentBufferExecCompleted();
		return TRUE;
	}

	if (StandardAI_IsSupportedBattle())
	{
		u8 target;
		bool8 bufferMismatch = OpponentNormalizeSupportedMoveInfo(moveInfo, gActiveBattler);
#ifdef CFRU_AI_TEST_TRACE
		OpponentAI_TestLastBufferMismatch = bufferMismatch;
		OpponentAI_TestLastBoundedFallback = FALSE;
#endif
		BattleAI_SetupAIData(0xF);
		chosenMovePos = StandardAI_ChooseMoveOrAction();
#ifdef CFRU_AI_TEST_TRACE
		OpponentAI_DispatchTrace.adapter = 1;
		OpponentAI_DispatchTrace.policyRc = StandardAI_TestLastPolicyRc;
		OpponentAI_DispatchTrace.selectedSlot = chosenMovePos;
		OpponentAI_DispatchTrace.selectedMove = chosenMovePos < MAX_MON_MOVES
			? gBattleMons[gActiveBattler].moves[chosenMovePos] : MOVE_NONE;
#endif
		chosenMovePos = OpponentResolveSupportedAIMoveSlot(moveInfo, gActiveBattler,
			chosenMovePos);
		target = gBattleMoves[moveInfo->moves[chosenMovePos]].target;
		gBankTarget = target & (MOVE_TARGET_USER | MOVE_TARGET_USER_OR_PARTNER)
			? gActiveBattler : FOE(gActiveBattler);
		gBattleStruct->chosenMovePositions[gActiveBattler] = chosenMovePos;
		gBattleStruct->moveTarget[gActiveBattler] = gBankTarget;
		gChosenMovesByBanks[gActiveBattler] = moveInfo->moves[chosenMovePos];
		/* Keep fair profiles out of legacy prediction and gimmick routing. */
		EmitMoveChosen(1, chosenMovePos, gBankTarget, 0, 0, 0, FALSE, 0);
#ifdef CFRU_AI_TEST_TRACE
		OpponentAI_DispatchTrace.emittedSlot = chosenMovePos;
		OpponentAI_DispatchTrace.emittedMove = moveInfo->moves[chosenMovePos];
#endif
		OpponentBufferExecCompleted();
		return TRUE;
	}

	return FALSE;
}

void OpponentHandleChooseMove(void)
{
	u8 chosenMovePos;
	struct ChooseMoveStruct* moveInfo = (struct ChooseMoveStruct*)(&gBattleBufferA[gActiveBattler][4]);
#ifdef CFRU_AI_TEST_TRACE
	OpponentAI_CaptureDispatchEntry();
#endif
#ifdef TRAINER_AI_RUNTIME_DISPATCH_TRACE
	if (OpponentHandleOakDispatchMarker(moveInfo))
		return;
#endif
	if (OpponentHandleSupportedAIMoveChoice(moveInfo))
		return;

#ifdef CFRU_AI_TEST_TRACE
	/* The host suite tests the exact supported outer route. Unsupported-profile
	 * routing is separately exercised without pulling all legacy controller I/O. */
	return;
#else

	if ((gBattleTypeFlags & (BATTLE_TYPE_TRAINER | BATTLE_TYPE_OAK_TUTORIAL | BATTLE_TYPE_SAFARI | BATTLE_TYPE_ROAMER))
	#ifdef FLAG_SMART_WILD
	||  FlagGet(FLAG_SMART_WILD)
	#endif
	#ifdef VAR_GAME_DIFFICULTY //Wild Pokemon are smart in expert mode
	||  IsGameDifficultyExpert()
	#endif
	|| (gBattleTypeFlags & BATTLE_TYPE_SHADOW_WARRIOR)
	|| (!(gBattleTypeFlags & BATTLE_TYPE_TRAINER) && WildMonIsSmart(gActiveBattler))
	|| (IsRaidBattle() && gRaidBattleStars >= 6))
	{
		if (RAID_BATTLE_END)
			goto CHOOSE_DUMB_MOVE;

		BattleAI_SetupAIData(0xF);
		chosenMovePos = BattleAI_ChooseMoveOrAction();

		switch (chosenMovePos) {
			case AI_CHOICE_WATCH:
				EmitTwoReturnValues(1, ACTION_WATCHES_CAREFULLY, 0);
				break;

			case AI_CHOICE_FLEE:
				EmitTwoReturnValues(1, ACTION_RUN, 0);
				break;

			case 6:
				EmitTwoReturnValues(1, 15, gBankTarget);
				break;

			default: ;
				u16 chosenMove = moveInfo->moves[chosenMovePos];
				u8 moveTarget = GetBaseMoveTarget(chosenMove, gActiveBattler);

				if (moveTarget & MOVE_TARGET_USER)
				{
					gBankTarget = gActiveBattler;
				}
				else if (moveTarget & MOVE_TARGET_USER_OR_PARTNER)
				{
					if (SIDE(gBankTarget) != SIDE(gActiveBattler))
						gBankTarget = gActiveBattler;
				}
				else if (moveTarget & MOVE_TARGET_BOTH)
				{
					if (SIDE(gActiveBattler) == B_SIDE_PLAYER)
					{
						gBankTarget = GetBattlerAtPosition(B_POSITION_OPPONENT_LEFT);
						if (gAbsentBattlerFlags & gBitTable[gBankTarget])
							gBankTarget = GetBattlerAtPosition(B_POSITION_OPPONENT_RIGHT);
					}
					else
					{
						gBankTarget = GetBattlerAtPosition(B_POSITION_PLAYER_LEFT);
						if (gAbsentBattlerFlags & gBitTable[gBankTarget])
							gBankTarget = GetBattlerAtPosition(B_POSITION_PLAYER_RIGHT);
					}
				}

				//You get 1 of 3 of the following gimmicks per Pokemon
				if (moveInfo->possibleZMoves[chosenMovePos]) //Checked first b/c Rayquaza can do all 3
				{
					u8 foe = gBankTarget;

					if (IS_SINGLE_BATTLE)
					{
						if (gActiveBattler == gBankTarget)
							foe = FOE(gActiveBattler); //Use actual enemy in calc

						//Allows for fresh calc factoring in foe move prediction
						ClearShouldAIUseZMoveByMoveAndMovePos(gActiveBattler, foe, chosenMovePos);
					}

					if (ShouldAIUseZMoveByMoveAndMovePos(gActiveBattler, foe, moveInfo->moves[chosenMovePos], chosenMovePos))
						gNewBS->zMoveData.toBeUsed[gActiveBattler] = TRUE;
				}
				else if (moveInfo->canMegaEvolve)
				{
					if (!ShouldAIDelayMegaEvolution(gActiveBattler, gBankTarget, chosenMove, FALSE, TRUE))
					{
						if (moveInfo->megaVariance != MEGA_VARIANT_ULTRA_BURST)
							gNewBS->megaData.chosen[gActiveBattler] = TRUE;
						else if (moveInfo->megaVariance == MEGA_VARIANT_ULTRA_BURST)
							gNewBS->ultraData.chosen[gActiveBattler] = TRUE;
					}
				}
				else if (moveInfo->possibleMaxMoves[chosenMovePos]) //Handles the "Can I Dynamax" checks
				{
					if (ShouldAIDynamax(gActiveBattler))
						gNewBS->dynamaxData.toBeUsed[gActiveBattler] = TRUE;
				}
				//For Terastallization
				else if (moveInfo->canTera) // For Terastallization
				{
					if (!ShouldAIDelayTerastallization(gActiveBattler, gBankTarget, chosenMove, FALSE, TRUE))
						gNewBS->teraData.chosen[gActiveBattler] = TRUE;
				}
				//This is handled again later, but it's only here to help with the case of choosing Helping Hand when the partner is switching out.
				gBattleStruct->chosenMovePositions[gActiveBattler] = chosenMovePos;
				gBattleStruct->moveTarget[gActiveBattler] = gBankTarget;
				gChosenMovesByBanks[gActiveBattler] = chosenMove;
				TryRemovePartnerDoublesKillingScoreComplete(gActiveBattler, gBankTarget, chosenMove, moveTarget, TRUE); //Allow the partner to choose a new target if its best move was this target

				EmitMoveChosen(1, chosenMovePos, gBankTarget, gNewBS->megaData.chosen[gActiveBattler], gNewBS->ultraData.chosen[gActiveBattler], gNewBS->zMoveData.toBeUsed[gActiveBattler], gNewBS->dynamaxData.toBeUsed[gActiveBattler], gNewBS->teraData.chosen[gActiveBattler]); // For Terastallization
				TryRechoosePartnerMove(moveInfo->moves[chosenMovePos]);
				break;
		}

		OpponentBufferExecCompleted();
	}
	else
	{
		CHOOSE_DUMB_MOVE: ;
		u16 move;
		do
		{
			chosenMovePos = Random() & 3;
			move = moveInfo->moves[chosenMovePos];
		} while (move == MOVE_NONE);

		if (GetBaseMoveTarget(move, gActiveBattler) & (MOVE_TARGET_USER_OR_PARTNER | MOVE_TARGET_USER))
			EmitMoveChosen(1, chosenMovePos, gActiveBattler, 0, 0, 0, FALSE, 0); // For Terastallization
		else if (IS_DOUBLE_BATTLE)
			EmitMoveChosen(1, chosenMovePos, GetBattlerAtPosition(Random() & 2), 0, 0, 0, FALSE, 0); // For Terastallization
		else
			EmitMoveChosen(1, chosenMovePos, FOE(gActiveBattler), 0, 0, 0, FALSE, 0); // For Terastallization

		OpponentBufferExecCompleted();
	}
#endif
}

#define STATE_BEFORE_ACTION_CHOSEN 0
static void TryRechoosePartnerMove(u16 chosenMove)
{
	u32 speedCalcBank = SpeedCalc(gActiveBattler);
	u32 speedCalcPartner = SpeedCalc(PARTNER(gActiveBattler));

	if (speedCalcBank < speedCalcPartner //Second to choose action on either side
	|| (speedCalcBank == speedCalcPartner && (GetBattlerPosition(gActiveBattler) & BIT_SIDE) == B_FLANK_RIGHT)) //Same speed and second mon on side
	{
		switch (gChosenMovesByBanks[PARTNER(gActiveBattler)]) {
			case MOVE_HELPINGHAND:
				if (chosenMove == MOVE_NONE || SPLIT(chosenMove) == SPLIT_STATUS)
				{
					struct ChooseMoveStruct moveInfo;
					gChosenMovesByBanks[gActiveBattler] = chosenMove;

					u8 backup = gActiveBattler;
					gActiveBattler = PARTNER(gActiveBattler);
					ForceCompleteDamageRecalculation(gActiveBattler);
					EmitChooseMove(0, (IS_DOUBLE_BATTLE) != 0, FALSE, &moveInfo); //Rechoose partner move
					MarkBufferBankForExecution(gActiveBattler);
					gActiveBattler = backup;
				}
				break;
		}
	}
	else if (!IsBankIncapacitated(gActiveBattler) //The first Pokemon will actually attack
	&& (chosenMove == MOVE_FUSIONFLARE || chosenMove == MOVE_FUSIONBOLT)) //The first Pokemon chose one of these moves
	{
		u8 partner = PARTNER(gActiveBattler);
		u8 foe1 = FOE(gActiveBattler);

		//Force recalculation since Fusion moves are now twice as strong
		if (chosenMove == MOVE_FUSIONFLARE)
		{
			u8 movePos = FindMovePositionInMoveset(MOVE_FUSIONBOLT, partner);
			if (movePos < MAX_MON_MOVES)
				ForceSpecificDamageRecalculation(partner, foe1, movePos);
		}
		else //Fusion Bolt
		{
			u8 movePos = FindMovePositionInMoveset(MOVE_FUSIONFLARE, partner);
			if (movePos < MAX_MON_MOVES)
				ForceSpecificDamageRecalculation(partner, foe1, movePos);
		}
	}
}

#define STATE_WAIT_ACTION_CONFIRMED 4
bool8 ShouldAIChooseAction(u8 position)
{
	//Try prioritizing AI mons in order from fastest to slowest (gets better calcs)
	u8 bank = GetBattlerAtPosition(position);
	u8 partner = GetBattlerAtPosition(BATTLE_PARTNER(position));

	if (gBattleTypeFlags & BATTLE_TYPE_MULTI
	|| gBattleStruct->field_91 & gBitTable[partner] //Only mon on side
	|| gBattleCommunication[partner] == STATE_WAIT_ACTION_CONFIRMED) //Partner already chose action
		return TRUE;

	if (!(gBattleTypeFlags & BATTLE_TYPE_LINK) //Vs AI
	&& IS_DOUBLE_BATTLE
	&& (SIDE(bank) == B_SIDE_OPPONENT || IsMockBattle())) //AI controlled side
	{
		u32 speedCalcBank = SpeedCalc(bank);
		u32 speedCalcPartner = SpeedCalc(partner);

		if (speedCalcBank > speedCalcPartner) //This mon would probably hit before partner
			return TRUE;
		else if (speedCalcBank == speedCalcPartner //Speed tie
		&& (position & BIT_FLANK) == B_FLANK_LEFT) //Then assume left slot would move first
			return TRUE;
	}
	else if ((position & BIT_FLANK) == B_FLANK_LEFT) //Left slot
		return TRUE;

	return FALSE;
}

void OpponentHandleDrawTrainerPic(void)
{
	u32 trainerPicId = LoadCorrectTrainerPicId();
	s16 xPos;

	if (gBattleTypeFlags & (BATTLE_TYPE_MULTI | BATTLE_TYPE_TWO_OPPONENTS))
	{
		if ((GetBattlerPosition(gActiveBattler) & BIT_FLANK) != 0) // second mon
			xPos = 152;
		else // first mon
			xPos = 200;
	}
	else
	{
		xPos = 176;
	}

	DecompressTrainerFrontPic(trainerPicId, gActiveBattler); //0x80346C4
	SetMultiuseSpriteTemplateToTrainerBack(trainerPicId, GetBattlerPosition(gActiveBattler));
	gBattlerSpriteIds[gActiveBattler] = CreateSprite(&gMultiuseSpriteTemplate[0],
											   xPos,
											   (8 - gTrainerFrontPicCoords[trainerPicId].coords) * 4 + 40,
											   GetBattlerSpriteSubpriority(gActiveBattler));

	gSprites[gBattlerSpriteIds[gActiveBattler]].pos2.x = -240;
	gSprites[gBattlerSpriteIds[gActiveBattler]].data[0] = 3; //2; //Speed scrolling in
	gSprites[gBattlerSpriteIds[gActiveBattler]].oam.paletteNum = IndexOfSpritePaletteTag(gTrainerFrontPicPaletteTable[trainerPicId].tag);
	gSprites[gBattlerSpriteIds[gActiveBattler]].data[5] = gSprites[gBattlerSpriteIds[gActiveBattler]].oam.tileNum;
	gSprites[gBattlerSpriteIds[gActiveBattler]].oam.tileNum = GetSpriteTileStartByTag(gTrainerFrontPicTable[trainerPicId].tag);
	gSprites[gBattlerSpriteIds[gActiveBattler]].oam.affineParam = trainerPicId;
	gSprites[gBattlerSpriteIds[gActiveBattler]].callback = SpriteCB_TrainerSlideIn;

	gBattlerControllerFuncs[gActiveBattler] = CompleteOnBattlerSpriteCallbackDummy;
}

void OpponentHandleTrainerSlide(void)
{

	u32 trainerPicId = LoadCorrectTrainerPicId();

	DecompressTrainerFrontPic(trainerPicId, gActiveBattler);
	SetMultiuseSpriteTemplateToTrainerBack(trainerPicId, GetBattlerPosition(gActiveBattler));
	gBattlerSpriteIds[gActiveBattler] = CreateSprite(&gMultiuseSpriteTemplate[0], 176, (8 - gTrainerFrontPicCoords[trainerPicId].coords) * 4 + 40, 30);

	gSprites[gBattlerSpriteIds[gActiveBattler]].pos2.x = 96;
	gSprites[gBattlerSpriteIds[gActiveBattler]].pos1.x += 32;
	gSprites[gBattlerSpriteIds[gActiveBattler]].data[0] = -2;
	gSprites[gBattlerSpriteIds[gActiveBattler]].oam.paletteNum = IndexOfSpritePaletteTag(gTrainerFrontPicPaletteTable[trainerPicId].tag);
	gSprites[gBattlerSpriteIds[gActiveBattler]].data[5] = gSprites[gBattlerSpriteIds[gActiveBattler]].oam.tileNum;
	gSprites[gBattlerSpriteIds[gActiveBattler]].oam.tileNum = GetSpriteTileStartByTag(gTrainerFrontPicTable[trainerPicId].tag);
	gSprites[gBattlerSpriteIds[gActiveBattler]].oam.affineParam = trainerPicId;
	gSprites[gBattlerSpriteIds[gActiveBattler]].callback = SpriteCB_TrainerSlideIn;

	gBattlerControllerFuncs[gActiveBattler] = CompleteOnBankSpriteCallbackDummy2;
}

static bool8 OpponentProfileReplacementIndexIsUsable(u8 chosenMonId)
{
	u8 firstId, lastId;
	u8 battlerIn1, battlerIn2;
	struct Pokemon* party;

	if (SIDE(gActiveBattler) != B_SIDE_OPPONENT)
		return FALSE;

	party = LoadPartyRange(gActiveBattler, &firstId, &lastId);
	if (party != gEnemyParty)
		return FALSE;

	if (IS_DOUBLE_BATTLE)
	{
		battlerIn1 = gActiveBattler;
		if (gAbsentBattlerFlags & gBitTable[PARTNER(gActiveBattler)])
			battlerIn2 = gActiveBattler;
		else
			battlerIn2 = PARTNER(battlerIn1);
	}
	else
	{
		battlerIn1 = gActiveBattler;
		battlerIn2 = gActiveBattler;
	}

	return OpponentReplacementIndexIsUsable(party, gEnemyParty, firstId, lastId, chosenMonId,
		gBattlerPartyIndexes[battlerIn1], gBattlerPartyIndexes[battlerIn2]);
}

void OpponentHandleChoosePokemon(void)
{
	u8 chosenMonId;
	bool8 profileReplacement = FALSE;

	if (IronmonAI_IsSupportedBattle())
	{
		chosenMonId = gBattleStruct->switchoutIndex[SIDE(gActiveBattler)];
		if (chosenMonId >= PARTY_SIZE)
			chosenMonId = IronmonAI_ChooseReplacement();

		if (OpponentProfileReplacementIndexIsUsable(chosenMonId))
		{
			gBattleStruct->switchoutIndex[SIDE(gActiveBattler)] = PARTY_SIZE;
			gBattleStruct->monToSwitchIntoId[gActiveBattler] = chosenMonId;
			EmitChosenMonReturnValue(1, chosenMonId, 0);
			OpponentBufferExecCompleted();
			return;
		}

		/* A bad preselected target or policy result uses the established CFRU
		 * forced-replacement path below. Never emit its sentinel or bad index. */
		profileReplacement = TRUE;
		gBattleStruct->switchoutIndex[SIDE(gActiveBattler)] = PARTY_SIZE;
	}

	if (StandardAI_IsSupportedBattle())
	{
		chosenMonId = gBattleStruct->switchoutIndex[SIDE(gActiveBattler)];
		if (chosenMonId >= PARTY_SIZE)
			chosenMonId = StandardAI_ChooseReplacement();

		if (OpponentProfileReplacementIndexIsUsable(chosenMonId))
		{
			gBattleStruct->switchoutIndex[SIDE(gActiveBattler)] = PARTY_SIZE;
			gBattleStruct->monToSwitchIntoId[gActiveBattler] = chosenMonId;
			EmitChosenMonReturnValue(1, chosenMonId, 0);
			OpponentBufferExecCompleted();
			return;
		}

		/* A bad preselected target or policy result uses the established CFRU
		 * forced-replacement path below. Never emit its sentinel or bad index. */
		profileReplacement = TRUE;
		gBattleStruct->switchoutIndex[SIDE(gActiveBattler)] = PARTY_SIZE;
	}

	if (gBattleStruct->switchoutIndex[SIDE(gActiveBattler)] == PARTY_SIZE)
	{
		u8 battlerIn1, battlerIn2, firstId, lastId;
		struct Pokemon* party = LoadPartyRange(gActiveBattler, &firstId, &lastId);

		if (IS_DOUBLE_BATTLE)
		{
			battlerIn1 = gActiveBattler; //The dead mon
			if (gAbsentBattlerFlags & gBitTable[PARTNER(gActiveBattler)])
				battlerIn2 = gActiveBattler;
			else
				battlerIn2 = PARTNER(battlerIn1);
		}
		else
		{
			battlerIn1 = gActiveBattler;
			battlerIn2 = gActiveBattler;
		}

		if (profileReplacement)
		{
			if (gNewBS->inPivotingMove //TODO: Add logic for Baton Pass
			&& gNewBS->ai.pivotTo[gActiveBattler] != PARTY_SIZE //Set at some point before
			&& gNewBS->ai.pivotTo[gActiveBattler] != battlerIn1 //Hasn't been switched in, in the mean time
			&& gNewBS->ai.pivotTo[gActiveBattler] != battlerIn2
			&& OpponentReplacementIndexIsUsable(party, gEnemyParty, firstId, lastId,
				gNewBS->ai.pivotTo[gActiveBattler], gBattlerPartyIndexes[battlerIn1],
				gBattlerPartyIndexes[battlerIn2]))
			{
				chosenMonId = gNewBS->ai.pivotTo[gActiveBattler];
			}
			else
			{
				if (!OpponentReplacementIndexIsUsable(party, gEnemyParty, firstId, lastId,
					gNewBS->ai.bestMonIdToSwitchInto[gActiveBattler][0],
					gBattlerPartyIndexes[battlerIn1], gBattlerPartyIndexes[battlerIn2]))
					CalcMostSuitableMonToSwitchInto();

				chosenMonId = GetMostSuitableMonToSwitchInto();
			}

			if (!OpponentReplacementIndexIsUsable(party, gEnemyParty, firstId, lastId, chosenMonId,
				gBattlerPartyIndexes[battlerIn1], gBattlerPartyIndexes[battlerIn2]))
				chosenMonId = OpponentReplacementFindFirstUsable(party, gEnemyParty, firstId, lastId,
					gBattlerPartyIndexes[battlerIn1], gBattlerPartyIndexes[battlerIn2]);
		}
		else
		{
			if (gNewBS->inPivotingMove //TODO: Add logic about switching if actually Baton Pass
			&& gNewBS->ai.pivotTo[gActiveBattler] != PARTY_SIZE //Set at some point before
			&& gNewBS->ai.pivotTo[gActiveBattler] != battlerIn1 //Hasn't been switched in, in the mean time
			&& gNewBS->ai.pivotTo[gActiveBattler] != battlerIn2
			&& party[gNewBS->ai.pivotTo[gActiveBattler]].hp != 0) //Still alive
			{
				chosenMonId = gNewBS->ai.pivotTo[gActiveBattler];
			}
			else
			{
				if (gNewBS->ai.bestMonIdToSwitchInto[gActiveBattler][0] == PARTY_SIZE
				|| GetMonData(&party[gNewBS->ai.bestMonIdToSwitchInto[gActiveBattler][0]], MON_DATA_HP, NULL) == 0 //Best mon is dead
				|| gNewBS->ai.bestMonIdToSwitchInto[gActiveBattler][0] == gBattlerPartyIndexes[battlerIn1]
				|| gNewBS->ai.bestMonIdToSwitchInto[gActiveBattler][0] == gBattlerPartyIndexes[battlerIn2]) //The best mon is already in
					CalcMostSuitableMonToSwitchInto();

				chosenMonId = GetMostSuitableMonToSwitchInto();
			}

			if (chosenMonId >= PARTY_SIZE
			|| chosenMonId < firstId || chosenMonId >= lastId) //Trying to pick from partner's team
			{
				for (chosenMonId = firstId; chosenMonId < lastId; ++chosenMonId)
				{
					if (party[chosenMonId].species != SPECIES_NONE
					&& party[chosenMonId].hp != 0
					&& !GetMonData(&party[chosenMonId], MON_DATA_IS_EGG, 0)
					&& chosenMonId != gBattlerPartyIndexes[battlerIn1]
					&& chosenMonId != gBattlerPartyIndexes[battlerIn2])
						break;
				}
			}
		}
	}
	else
	{
		chosenMonId = gBattleStruct->switchoutIndex[SIDE(gActiveBattler)];
		gBattleStruct->switchoutIndex[SIDE(gActiveBattler)] = PARTY_SIZE;
	}

	/* The engine should not ask for a replacement after the opponent's final
	 * mon faints. Fail closed if a profile path is nevertheless entered then. */
	if (profileReplacement && !OpponentProfileReplacementIndexIsUsable(chosenMonId))
	{
		gBattleStruct->monToSwitchIntoId[gActiveBattler] = PARTY_SIZE;
		OpponentBufferExecCompleted();
		return;
	}

	RemoveBestMonToSwitchInto(gActiveBattler);
	gBattleStruct->monToSwitchIntoId[gActiveBattler] = chosenMonId;
	EmitChosenMonReturnValue(1, chosenMonId, 0);
	OpponentBufferExecCompleted();
	TryRechoosePartnerMove(MOVE_NONE);
}


static u8 LoadCorrectTrainerPicId(void)
{
    u8 trainerPicId;
    u8 position = GetBattlerPosition(gActiveBattler);

    if (gTrainerBattleOpponent_A == TRAINER_SECRET_BASE)
    {
        trainerPicId = GetSecretBaseTrainerPicIndex();
    }
    else if (gBattleTypeFlags & BATTLE_TYPE_FRONTIER
          || (position == B_POSITION_OPPONENT_LEFT && IsFrontierTrainerId(gTrainerBattleOpponent_A))
          || (position == B_POSITION_OPPONENT_RIGHT && IsFrontierTrainerId(gTrainerBattleOpponent_B)))
    {
        if (IsTwoOpponentBattle()
         || ((gBattleTypeFlags & BATTLE_TYPE_LINK) && (gBattleTypeFlags & BATTLE_TYPE_MULTI)))
        {
            if (position == B_POSITION_OPPONENT_LEFT)
                trainerPicId = GetFrontierTrainerFrontSpriteId(gTrainerBattleOpponent_A, 0);
            else
                trainerPicId = GetFrontierTrainerFrontSpriteId(gTrainerBattleOpponent_B, 1);
        }
        else
        {
            trainerPicId = GetFrontierTrainerFrontSpriteId(gTrainerBattleOpponent_A, 0);
        }
    }
    else if (gBattleTypeFlags & BATTLE_TYPE_TRAINER_TOWER)
    {
        trainerPicId = GetTrainerTowerTrainerPicIndex(); // 0x815DA3C
    }
    else if (gBattleTypeFlags & BATTLE_TYPE_EREADER_TRAINER)
    {
        trainerPicId = GetEreaderTrainerFrontSpriteId(); // 0x80E7420
    }
    else if (gBattleTypeFlags & BATTLE_TYPE_TWO_OPPONENTS)
    {
        if (position == B_POSITION_OPPONENT_LEFT)
        {
            trainerPicId = gTrainers[gTrainerBattleOpponent_A].trainerPic;
        }
        else
        {
            trainerPicId = gTrainers[gTrainerBattleOpponent_B].trainerPic;
        }
    }
    else
    {
        trainerPicId = gTrainers[gTrainerBattleOpponent_A].trainerPic;
    }

    return trainerPicId;
}

void SpriteCB_SlideInTrainer(struct Sprite* sprite)
{
    if (!(gIntroSlideFlags & 1))
    {
        sprite->pos2.x += sprite->data[0];
		
		if (sprite->data[0] > 0) //Positive
		{
			if (sprite->pos2.x > 0)
			{
				sprite->callback = SpriteCallbackDummy;
				sprite->pos2.x = 0;
			}
		}
		else //Negative
		{
			if (sprite->pos2.x < 0)
			{
				sprite->callback = SpriteCallbackDummy;
				sprite->pos2.x = 0;
			}
		}
    }
}

#define sBattler data[0]
void SpriteCB_WildMon(struct Sprite *sprite)
{
	u32 selectedPalettes = 0x10000 << sprite->oam.paletteNum;

    sprite->callback = (void*) (0x8011D94 | 1); //SpriteCB_MoveWildMonToRight
    StartSpriteAnimIfDifferent(sprite, 0);
    if (!BeginNormalPaletteFade(selectedPalettes, 0, 10, 10, RGB(8, 8, 8))) //If a fade is already in progress,
		gPaletteFade_selectedPalettes |= selectedPalettes; //Then add second mon in wild doubles to the palettes to fade
}

void SpriteCB_WildMonShowHealthbox(struct Sprite *sprite)
{
    if (sprite->animEnded)
    {
		u32 selectedPalettes = 0x10000 << sprite->oam.paletteNum;

        StartHealthboxSlideIn(sprite->sBattler);
        SetHealthboxSpriteVisible(gHealthboxSpriteIds[sprite->sBattler]);
        sprite->callback = SpriteCallbackDummy;
        StartSpriteAnimIfDifferent(sprite, 0);
        if (!BeginNormalPaletteFade(selectedPalettes, 0, 10, 0, RGB(8, 8, 8))) //If a fade is already in progress,
			gPaletteFade_selectedPalettes |= selectedPalettes; //Then add second mon in wild doubles to the palettes to unfade
    }
}
#undef sBattler

#define sBattler data[6]
void SpriteCB_OpponentMonSendOut_1(struct Sprite* sprite)
{
	sprite->data[0] = 25;
	sprite->data[2] = GetBattlerSpriteCoord(sprite->sBattler, BATTLER_COORD_X_2);
	sprite->data[4] = GetBattlerSpriteCoord(sprite->sBattler, BATTLER_COORD_Y) + 24;
	sprite->data[5] = -30;

	if (IS_DOUBLE_BATTLE && GetBattlerPosition(sprite->sBattler) == B_POSITION_OPPONENT_LEFT)
		sprite->data[0] = 23; //Slightly faster than the second mon

	sprite->oam.affineParam = sprite->sBattler;
	InitAnimArcTranslation(sprite);
	sprite->callback = SpriteCB_PlayerMonSendOut_2;
}
#undef sBattler
extern u8 gBattlerAttacker;
#define gText_BattleYesNoChoice (u8*) 0x83FE791
#define B_WIN_YESNO 14
#define SE_SELECT 5
void Cmd_trygivecaughtmonnick(void)
{
    if (FlagGet(FLAG_NUZLOCKE)) // ⭐ Nuzlocke Mode: Always nickname
    {
        switch (gBattleCommunication[MULTIUSE_STATE])
        {
        case 0:
            GetMonData(&gEnemyParty[gBattlerPartyIndexes[gBattlerAttacker ^ BIT_SIDE]], MON_DATA_NICKNAME, gBattleStruct->caughtMonNick);
            FreeAllWindowBuffers();

            DoNamingScreen(NAMING_SCREEN_CAUGHT_MON, gBattleStruct->caughtMonNick,
                           GetMonData(&gEnemyParty[gBattlerPartyIndexes[gBattlerAttacker ^ BIT_SIDE]], MON_DATA_SPECIES, NULL),
                           GetMonGender(&gEnemyParty[gBattlerPartyIndexes[gBattlerAttacker ^ BIT_SIDE]]),
                           GetMonData(&gEnemyParty[gBattlerPartyIndexes[gBattlerAttacker ^ BIT_SIDE]], MON_DATA_PERSONALITY, NULL),
                           BattleMainCB2);

            gBattleCommunication[MULTIUSE_STATE]++;
            break;
        case 1:
            if (gMain.callback2 == BattleMainCB2 && !gPaletteFade->active)
            {
                SetMonData(&gEnemyParty[gBattlerPartyIndexes[gBattlerAttacker ^ BIT_SIDE]], MON_DATA_NICKNAME, gBattleStruct->caughtMonNick);
                gBattlescriptCurrInstr = T1_READ_PTR(gBattlescriptCurrInstr + 1);
            }
            break;
        }
        return;
    }

    // Default behavior when Nuzlocke is OFF (yes/no choice)
    switch (gBattleCommunication[MULTIUSE_STATE])
    {
    case 0:
        HandleBattleWindow(23, 8, 29, 13, 0);
        BattlePutTextOnWindow(gText_BattleYesNoChoice, B_WIN_YESNO);
        gBattleCommunication[MULTIUSE_STATE]++;
        gBattleCommunication[CURSOR_POSITION] = 0;
        BattleCreateYesNoCursorAt(0);
        break;
    case 1:
        if (JOY_NEW(DPAD_UP) && gBattleCommunication[CURSOR_POSITION] != 0)
        {
            PlaySE(SE_SELECT);
            BattleDestroyYesNoCursorAt(0);
            gBattleCommunication[CURSOR_POSITION] = 0;
            BattleCreateYesNoCursorAt(0);
        }
        if (JOY_NEW(DPAD_DOWN) && gBattleCommunication[CURSOR_POSITION] == 0)
        {
            PlaySE(SE_SELECT);
            BattleDestroyYesNoCursorAt(0);
            gBattleCommunication[CURSOR_POSITION] = 1;
            BattleCreateYesNoCursorAt(1);
        }
        if (JOY_NEW(A_BUTTON))
        {
            PlaySE(SE_SELECT);
            if (gBattleCommunication[CURSOR_POSITION] == 0)
            {
                gBattleCommunication[MULTIUSE_STATE]++;
                BeginFastPaletteFade(3);
            }
            else
            {
                gBattleCommunication[MULTIUSE_STATE] = 4;
            }
        }
        else if (JOY_NEW(B_BUTTON))
        {
            PlaySE(SE_SELECT);
            gBattleCommunication[MULTIUSE_STATE] = 4;
        }
        break;
    case 2:
        if (!gPaletteFade->active)
        {
            GetMonData(&gEnemyParty[gBattlerPartyIndexes[gBattlerAttacker ^ BIT_SIDE]], MON_DATA_NICKNAME, gBattleStruct->caughtMonNick);
            FreeAllWindowBuffers();

            DoNamingScreen(NAMING_SCREEN_CAUGHT_MON, gBattleStruct->caughtMonNick,
                           GetMonData(&gEnemyParty[gBattlerPartyIndexes[gBattlerAttacker ^ BIT_SIDE]], MON_DATA_SPECIES, NULL),
                           GetMonGender(&gEnemyParty[gBattlerPartyIndexes[gBattlerAttacker ^ BIT_SIDE]]),
                           GetMonData(&gEnemyParty[gBattlerPartyIndexes[gBattlerAttacker ^ BIT_SIDE]], MON_DATA_PERSONALITY, NULL),
                           BattleMainCB2);

            gBattleCommunication[MULTIUSE_STATE]++;
        }
        break;
    case 3:
        if (gMain.callback2 == BattleMainCB2 && !gPaletteFade->active)
        {
            SetMonData(&gEnemyParty[gBattlerPartyIndexes[gBattlerAttacker ^ BIT_SIDE]], MON_DATA_NICKNAME, gBattleStruct->caughtMonNick);
            gBattlescriptCurrInstr = T1_READ_PTR(gBattlescriptCurrInstr + 1);
        }
        break;
    case 4:
        if (CalculatePlayerPartyCount() == PARTY_SIZE)
            gBattlescriptCurrInstr += 5;
        else
            gBattlescriptCurrInstr = T1_READ_PTR(gBattlescriptCurrInstr + 1);
        break;
    }
}
