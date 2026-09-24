#!/usr/bin/env python3
"""Audit Standard/Ironmon controller replacement emissions and fallback routing."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def fail(message: str) -> None:
    raise SystemExit(message)


def main() -> int:
    controller = (ROOT / "src/battle_controller_opponent.c").read_text(encoding="utf-8")
    chooser = controller.split("void OpponentHandleChoosePokemon(void)", 1)[1].split(
        "static u8 LoadCorrectTrainerPicId(void)", 1
    )[0]
    validator = controller.split(
        "static bool8 OpponentProfileReplacementIndexIsUsable(u8 chosenMonId)", 1
    )[1].split("void OpponentHandleChoosePokemon(void)", 1)[0]

    if "party != gEnemyParty" not in validator:
        fail("profile replacement must require the opponent-owned party")
    if "OpponentReplacementIndexIsUsable(party, gEnemyParty" not in validator:
        fail("profile replacement must use the tested range/state validator")

    ironmon = chooser.split("if (IronmonAI_IsSupportedBattle())", 1)[1].split(
        "if (StandardAI_IsSupportedBattle())", 1
    )[0]
    standard = chooser.split("if (StandardAI_IsSupportedBattle())", 1)[1].split(
        "if (gBattleStruct->switchoutIndex[SIDE(gActiveBattler)] == PARTY_SIZE)", 1
    )[0]

    for name, block, chooser_name in (
        ("Ironmon", ironmon, "IronmonAI_ChooseReplacement()"),
        ("Standard", standard, "StandardAI_ChooseReplacement()"),
    ):
        if chooser_name not in block:
            fail(f"{name} replacement chooser disappeared")
        gate = block.find("if (OpponentProfileReplacementIndexIsUsable(chosenMonId))")
        emit = block.find("EmitChosenMonReturnValue(1, chosenMonId, 0)")
        if gate < 0 or emit < 0 or gate > emit:
            fail(f"{name} chosen index is emitted without the shared validity gate")
        if "profileReplacement = TRUE;" not in block:
            fail(f"{name} invalid selection does not fall through to CFRU replacement")

    if "GetMostSuitableMonToSwitchInto()" not in chooser:
        fail("profile failure no longer reaches the established CFRU selection path")
    if "OpponentReplacementFindFirstUsable(party, gEnemyParty" not in chooser:
        fail("legacy selection lacks a safe in-range fallback scan")
    if "profileReplacement && !OpponentProfileReplacementIndexIsUsable(chosenMonId)" not in chooser:
        fail("profile path can emit when no live replacement exists")
    no_candidate = chooser.find("profileReplacement && !OpponentProfileReplacementIndexIsUsable(chosenMonId)")
    final_emit = chooser.find("EmitChosenMonReturnValue(1, chosenMonId, 0)", no_candidate)
    if no_candidate < 0 or final_emit < 0:
        fail("final profile emission lacks fail-closed end-of-battle gate")
    if chooser.find("OpponentBufferExecCompleted();", no_candidate) > final_emit:
        fail("no-candidate path must complete without emitting an invalid index")

    print("opponent replacement controller routing/ownership/emission audit: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
