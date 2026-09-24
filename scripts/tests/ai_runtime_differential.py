#!/usr/bin/env python3
"""Compare live CFRU adapter facts/decisions with accepted Workspace host policy.

The C harness emits observations from production adapters and source move
tables. This script gives those exact public facts to the accepted Python
floor and policies. It does not mutate host policy or accepted digests.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = ROOT.parents[1]
sys.path.insert(0, str(WORKSPACE / "07_scripts"))

from ai_policy.floor import apply_common_floor  # noqa: E402
from ai_policy.ironmon import choose_ironmon  # noqa: E402
from ai_policy.memory import consecutive_successes  # noqa: E402
from ai_policy.rng import XorShift32  # noqa: E402
from ai_policy.standard import choose_standard  # noqa: E402


FAMILIES = (
    None, "accuracy_down", "speed_down", "attack_up", "defense_up", "speed_up",
    "special_attack_up", "special_defense_up", "accuracy_up", "attack_down",
    "defense_down", "special_attack_down", "special_defense_down", "evasion_up",
    "evasion_down", "sand_attack", "smokescreen", "string_shot",
    "speed_down", "damage", "major_status", "toxic", "leech_seed", "yawn",
    "recovery", "protect", "field", "setup", "residual_combo", "unsupported",
)
TACTICAL = (
    "damage", "two_hko", "speed_plan", "setup_plan", "residual", "recovery",
    "field", "protect", "pivot", "switch", "forced_replacement", "fallback",
    "unsupported",
)
REPEAT_REASONS = (
    None, "certified_order_threshold", "ko_or_2hko_threshold",
    "survival_threshold", "net_positive_recovery", "residual_win_line",
)
BOOL_FIELDS = (
    "legal", "productive", "known_no_effect", "pure_status", "robust_safe_ko",
    "redundant_status", "positive_marginal_exception", "switch_legal",
    "entry_survives", "forced", "standard_switch_emergency",
)
TRANSFER_FIELDS = (
    "expected_damage", "opponent_hp_fraction_lost", "known_no_effect",
    "immediate_future_gain", "legal", "productive", "stat_stage_before",
    "stat_stage_after", "effect_family", "robust_safe_ko", "pure_status",
)


def parse_trace(binary: Path) -> list[dict]:
    lines = subprocess.check_output([str(binary), "--differential"], cwd=ROOT, text=True)
    cases: list[dict] = []
    current: dict | None = None
    for line in lines.splitlines():
        row = json.loads(line)
        if row["type"] == "case":
            current = {"header": row, "memory": [], "responses": [],
                       "candidates": [], "ironmon_candidates": [], "branches": []}
            cases.append(current)
        else:
            assert current is not None
            key = {"memory": "memory", "response": "responses",
                   "candidate": "candidates", "ironmon_candidate": "ironmon_candidates",
                   "branch": "branches"}[row["type"]]
            current[key].append(row)
    return cases


def memory_of(case: dict) -> dict:
    return {"decisions": [{
        "kind": "move" if row["kind"] == 0 else "switch",
        "effect_family": FAMILIES[row["effect_family"]],
        "success": bool(row["success"]), "forced": bool(row["forced"]),
        "switch_from": None if row["switch_from"] == 255 else str(row["switch_from"]),
        "switch_to": None if row["switch_to"] == 255 else str(row["switch_to"]),
    } for row in case["memory"]]}


def action_of(row: dict) -> dict:
    action = {key: row[key] for key in (
        "stat_stage_before", "stat_stage_after", "expected_damage", "fallback_cost",
        "net_faints", "opponent_hp_fraction_lost", "own_hp_fraction_lost",
        "immediate_future_gain", "entry_cost", "repeat_cost", "uncertainty_cost",
    )}
    action.update({key: bool(row[key]) for key in BOOL_FIELDS})
    # The accepted host schema predates the source adapter's explicit UNKNOWN
    # admission bit. The host floor's productive input represents both a
    # measured positive result and a legal potentially productive unknown.
    action["productive"] |= bool(row["unknown_potentially_productive"])
    action.update({
        "id": str(row["id"]),
        "kind": "move" if row["kind"] == 0 else "switch",
        "effect_family": FAMILIES[row["effect_family"]],
        "switch_from": None if row["switch_from"] == 255 else str(row["switch_from"]),
        "switch_to": None if row["switch_to"] == 255 else str(row["switch_to"]),
    })
    return action


def check_transfer(case: dict, actions: list[dict], memory: dict) -> None:
    for source, host in zip(case["candidates"], actions):
        for field in TRANSFER_FIELDS:
            if field == "effect_family":
                assert host[field] == FAMILIES[source[field]], (case["header"]["name"], field)
            elif field == "productive":
                assert host[field] == bool(source[field] or source["unknown_potentially_productive"])
            else:
                assert host[field] == source[field], (case["header"]["name"], field)
        repeat = consecutive_successes(memory["decisions"], host["effect_family"])
        if case["header"]["name"] == "accuracy_third" and source["id"] < 2:
            assert repeat == 2
        if source["move"] and source["mechanics_class"] == 3:
            assert source["mechanics_reason"] != 0
            if source["legal"] and source["unknown_potentially_productive"]:
                assert not source["expected_damage"] and not source["productive"]
        elif source["move"] and source["mechanics_reason"] == 0:
            assert source["mechanics_class"] in (0, 1, 2)


def response_model(case: dict) -> dict:
    rows = case["responses"]
    known = [row for row in rows if row["id"] != 65535]
    unknown = any(row["id"] == 65535 for row in rows)
    factor = 3 if known and unknown else 1
    moves = [str(row["id"]) for row in known]
    return {"revealed_moves": moves,
            "move_counts": {str(row["id"]): row["weight"] // factor - 1 for row in known},
            "unknown_move_slots": 1 if unknown else 0,
            "opponent_switch_weight": 0}


def check_case(case: dict) -> dict[str, int]:
    header = case["header"]
    name = header["name"]
    memory = memory_of(case)
    actions = [action_of(row) for row in case["candidates"]]
    assert len(actions) == header["count"]
    assert len(memory["decisions"]) == header["memory_count"]
    check_transfer(case, actions, memory)
    rng = XorShift32(header["pre"])

    if header["profile"] == "standard":
        observation = {"candidates": actions}
        floor = apply_common_floor(observation, memory)
        result = choose_standard(observation, floor, memory, rng)
        diagnostics = {item["action_id"]: item for item in result.diagnostics}
        for row in case["candidates"]:
            ident = str(row["id"])
            host = diagnostics[ident]
            assert host["standard_eligible"] == bool(row["standard_eligible"]), (name, ident, "admission")
            assert host["utility_total"] == row["utility_total"], (name, ident, "utility")
            assert host["near_best"] == bool(row["near_best"]), (name, ident, "near_best")
            assert host["selected"] == bool(row["selected"]), (name, ident, "selected")
        assert floor.no_productive_action == bool(header["fallback"]), name
    else:
        assert len(case["ironmon_candidates"]) == len(actions)
        model = response_model(case)
        by_id = {row["id"]: row for row in case["ironmon_candidates"]}
        for action in actions:
            details = by_id[int(action["id"])]
            action.update({
                "tactical_class": TACTICAL[details["tactical_class"]],
                "ironmon_switch_emergency": bool(details["ironmon_switch_emergency"]),
                "stay_defensible": bool(details["stay_defensible"]),
                "repeat_exception_reason": REPEAT_REASONS[details["repeat_exception_reason"]],
                "public_threat_changed": bool(details["public_threat_changed"]),
                "regenerator_only": bool(details["regenerator_only"]),
                "progress_after_loop_cost": details["progress_after_loop_cost"],
                "responses": [{key: str(row[key]) if key == "response_id" and row[key] != 65535
                               else "UNKNOWN" if key == "response_id" else row[key]
                               for key in ("response_id", "net_faints", "opponent_hp_fraction_lost",
                                           "own_hp_fraction_lost", "future_gain_undiscounted", "entry_cost")}
                              for row in case["branches"] if row["candidate_id"] == int(action["id"])],
            })
        observation = {"candidates": actions, "response_model": model}
        floor = apply_common_floor(observation, memory)
        result = choose_ironmon(observation, floor, memory, rng)
        expected_weights = {row["response_id"]: row["weight"] for row in result.response_weights}
        source_weights = {"UNKNOWN" if row["id"] == 65535 else str(row["id"]): row["weight"]
                          for row in case["responses"]}
        assert expected_weights == source_weights, (name, "response weights")
        diagnostics = {item["action_id"]: item for item in result.diagnostics}
        for row in case["ironmon_candidates"]:
            ident = str(row["id"])
            host = diagnostics[ident]
            for field in ("ironmon_eligible", "near_best", "utility_total", "repeat_count",
                          "repeat_cost", "uncertainty_cost"):
                assert host[field] == row[field], (name, ident, field, host[field], row[field])
        assert {ident for ident in result.near_best_ids} == {
            str(row["id"]) for row in case["ironmon_candidates"] if row["near_best"]}
    assert result.selected_action_id == str(header["selected"]), (name, "selection")
    assert rng.draw_count == header["draws"], (name, "draws")
    assert rng.state == header["post"], (name, "RNG post-state")
    chosen = next(row for row in case["candidates"] if row["id"] == header["selected"])
    chosen_score = diagnostics[str(chosen["id"])]["utility_total"]
    epsilon = 8 if header["profile"] == "standard" else 4
    superior_supported = [row for row in case["candidates"]
                          if row["mechanics_reason"] == 0 and row["legal"]
                          and diagnostics[str(row["id"])]["utility_total"] > chosen_score + epsilon]
    missed_ko = bool(any(row["robust_safe_ko"] and row["legal"] for row in case["candidates"])
                     and not chosen["robust_safe_ko"])
    below_epsilon = bool(not diagnostics[str(chosen["id"])]["near_best"])
    third_repeat = bool(chosen["pure_status"] and
                        consecutive_successes(memory["decisions"],
                                              FAMILIES[chosen["effect_family"]]) >= 2
                        and not chosen["positive_marginal_exception"])
    metrics = {
        "illegal_or_no_effect": int(bool((not chosen["legal"] or chosen["known_no_effect"])
                                        and any(row["legal"] and row["productive"]
                                                for row in case["candidates"]))),
        "missed_robust_ko": int(missed_ko),
        "third_harmful_repeat": int(third_repeat),
        "below_epsilon": int(below_epsilon),
        "unsupported_below_superior": int(bool(chosen["mechanics_class"] == 3
                                               and superior_supported)),
        "fallback": int(bool(header["fallback"])),
    }
    print(f"differential {name}: {header['profile']} candidates={len(actions)} "
          f"selected={result.selected_action_id} draws={rng.draw_count} "
          f"post={rng.state:08x} PASS")
    return metrics


def run(binary: Path) -> None:
    cases = parse_trace(binary)
    assert {case["header"]["name"] for case in cases} == {
        "rival", "near_best", "accuracy_first", "accuracy_second",
        "accuracy_third", "unsupported_fixed", "known_immunity", "all_futile",
        "secondary_damage", "priority_ko",
    }
    totals = {key: 0 for key in ("illegal_or_no_effect", "missed_robust_ko",
                                "third_harmful_repeat", "below_epsilon",
                                "unsupported_below_superior", "fallback")}
    for case in cases:
        for key, value in check_case(case).items():
            totals[key] += value
    assert all(value == 0 for key, value in totals.items() if key != "fallback")
    assert totals["fallback"] == 1
    print("runtime quality counts:", " ".join(f"{key}={value}" for key, value in totals.items()),
          "fallback_reason=NO_PRODUCTIVE_ACTION")
    print(f"production-vs-Workspace-host differential: {len(cases)} states PASS")


if __name__ == "__main__":
    run(Path(sys.argv[1]))
