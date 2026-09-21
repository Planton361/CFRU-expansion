#!/usr/bin/env python3
"""Compile and run CFRU Ironmon policy parity against accepted Workspace v3."""

from __future__ import annotations

import hashlib
import math
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = ROOT.parents[1]
HOST_ROOT = WORKSPACE / "07_scripts"
EXPECTED_DIGESTS = {
    "uniform_legal": "71fc84c8fd3e219c4e364ecd506127303ac8524a73d47a39999be384efbc95a7",
    "standard": "227ecebc2b937671cc4f2fbab1694abf1b7c186f7e455ed7daf22014b62d0a85",
    "ironmon_smart": "0a637d0bc42cb2e37701bbfa33677ae95c878b1f9a67ec55a60e15a4fbdb85d7",
}


EFFECTS = {
    None: "STANDARD_EFFECT_NONE",
    "accuracy_down": "STANDARD_EFFECT_ACCURACY_DOWN",
    "sand_attack": "STANDARD_EFFECT_SAND_ATTACK",
    "smokescreen": "STANDARD_EFFECT_SMOKESCREEN",
    "speed_down": "STANDARD_EFFECT_SPEED_DOWN",
    "string_shot": "STANDARD_EFFECT_STRING_SHOT",
    "attack_up": "STANDARD_EFFECT_ATTACK_UP",
    "damage": "STANDARD_EFFECT_DAMAGE",
    "major_status": "STANDARD_EFFECT_MAJOR_STATUS",
    "toxic": "STANDARD_EFFECT_TOXIC",
    "leech_seed": "STANDARD_EFFECT_LEECH_SEED",
    "yawn": "STANDARD_EFFECT_YAWN",
    "recovery": "STANDARD_EFFECT_RECOVERY",
    "protect": "STANDARD_EFFECT_PROTECT",
    "field": "STANDARD_EFFECT_FIELD",
    "setup": "STANDARD_EFFECT_SETUP",
    "residual_combo": "STANDARD_EFFECT_RESIDUAL_COMBO",
    "unsupported_effect": "STANDARD_EFFECT_UNSUPPORTED",
}
TACTICS = {
    name: "IRONMON_TACTICAL_" + token
    for name, token in {
        "damage": "DAMAGE", "two_hko": "TWO_HKO", "speed_plan": "SPEED_PLAN",
        "setup_plan": "SETUP_PLAN", "residual": "RESIDUAL", "recovery": "RECOVERY",
        "field": "FIELD", "protect": "PROTECT", "pivot": "PIVOT", "switch": "SWITCH",
        "forced_replacement": "FORCED_REPLACEMENT", "fallback": "FALLBACK",
        "unsupported": "UNSUPPORTED",
    }.items()
}
REPEAT_REASONS = {
    None: "IRONMON_REPEAT_NONE",
    "certified_order_threshold": "IRONMON_REPEAT_ORDER_THRESHOLD",
    "ko_or_2hko_threshold": "IRONMON_REPEAT_KO_OR_2HKO_THRESHOLD",
    "survival_threshold": "IRONMON_REPEAT_SURVIVAL_THRESHOLD",
    "net_positive_recovery": "IRONMON_REPEAT_NET_POSITIVE_RECOVERY",
    "residual_win_line": "IRONMON_REPEAT_RESIDUAL_WIN_LINE",
}
THRESHOLDS = {
    "forced_replacement": "IRONMON_THRESHOLD_FORCED_REPLACEMENT",
    "emergency": "IRONMON_THRESHOLD_EMERGENCY",
    "no_eligible_switch": "IRONMON_THRESHOLD_NO_ELIGIBLE_SWITCH",
    "below_12": "IRONMON_THRESHOLD_BELOW_12",
    "random_12_19": "IRONMON_THRESHOLD_RANDOM_12_19",
    "at_least_20": "IRONMON_THRESHOLD_AT_LEAST_20",
}
ADMITTED = {
    "stay": "IRONMON_ADMITTED_STAY",
    "forced_replacement": "IRONMON_ADMITTED_FORCED_REPLACEMENT",
    "emergency_switch": "IRONMON_ADMITTED_EMERGENCY_SWITCH",
    "voluntary_switch": "IRONMON_ADMITTED_VOLUNTARY_SWITCH",
}


def run(command: list[str]) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


def load_host():
    if not (HOST_ROOT / "ai_policy/fixtures/ironmon_fixtures.json").is_file():
        raise SystemExit("accepted Workspace #515 host corpus is unavailable")
    sys.path.insert(0, str(HOST_ROOT))
    from ai_policy.schema import load_fixtures
    from ai_policy.runner import run_all, run_fixture
    from ai_policy.tests.test_ironmon_policy import MANDATORY_TAGS
    return load_fixtures, run_all, run_fixture, MANDATORY_TAGS


def verify_digests(load_fixtures, run_all, mandatory_tags: set[str]) -> list[dict]:
    paths = {
        "uniform_legal": HOST_ROOT / "ai_policy/fixtures/synthetic_fixtures.json",
        "standard": HOST_ROOT / "ai_policy/fixtures/standard_fixtures.json",
        "ironmon_smart": HOST_ROOT / "ai_policy/fixtures/ironmon_fixtures.json",
    }
    ironmon = []
    for policy, path in paths.items():
        fixtures = load_fixtures(path)
        digest = hashlib.sha256(b"".join(r.line for r in run_all(fixtures, policy, 0))).hexdigest()
        assert digest == EXPECTED_DIGESTS[policy], (policy, digest)
        print(f"{policy} accepted host digest: {digest}")
        if policy == "ironmon_smart":
            ironmon = fixtures
            tags = {
                tag
                for fixture in fixtures
                for tag in fixture["expected"]["coverage_tags"]
            }
            assert not mandatory_tags - tags, sorted(mandatory_tags - tags)
            assert "switch_candidate_min_advantage" in tags
            print(
                "ironmon mandatory coverage tags: "
                f"{len(mandatory_tags)}/{len(mandatory_tags)} PASS; "
                f"accepted corpus unique tags={len(tags)}"
            )
    return ironmon


def c_bool(value) -> str:
    return "1" if value else "0"


def endpoint_map(fixture: dict) -> dict[str, int]:
    values = set()
    for action in fixture["candidates"]:
        values.update(v for v in (action["switch_from"], action["switch_to"]) if v)
    for decision in fixture["policy_memory"]["decisions"]:
        values.update(v for v in (decision["switch_from"], decision["switch_to"]) if v)
    return {value: i for i, value in enumerate(sorted(values))}


def build_case(fixture: dict, run_fixture) -> str:
    result = run_fixture(fixture, "ironmon_smart", 0)
    trace = result.trace
    ironmon = trace["ironmon_policy"]
    actions = fixture["candidates"]
    id_map = {name: i for i, name in enumerate(sorted(a["id"] for a in actions))}
    endpoints = endpoint_map(fixture)
    response_rows = ironmon["response_weights"]
    response_ids = {
        row["response_id"]: (65535 if row["response_id"] == "UNKNOWN" else i + 1)
        for i, row in enumerate(response_rows)
    }
    diagnostics = {row["action_id"]: row for row in ironmon["candidate_diagnostics"]}
    arb = ironmon["switch_arbitration"]
    rng = trace["policy_rng"]

    lines = [f'{{.name="{fixture["fixture_id"]}",', ".observation={"]
    lines.append(f".response_count={len(response_rows)},.responses={{")
    for row in response_rows:
        lines.append(f'{{.id={response_ids[row["response_id"]]},.weight={row["weight"]}u}},')
    lines.append(f"}},.count={len(actions)},.candidates={{")
    for action in actions:
        floor = [
            f'.id={id_map[action["id"]]}',
            f'.kind={"STANDARD_POLICY_SWITCH" if action["kind"] == "switch" else "STANDARD_POLICY_MOVE"}',
            f'.legal={c_bool(action["legal"])}', f'.productive={c_bool(action["productive"])}',
            f'.known_no_effect={c_bool(action["known_no_effect"])}',
            f'.pure_status={c_bool(action["pure_status"])}',
            f'.robust_safe_ko={c_bool(action["robust_safe_ko"])}',
            f'.redundant_status={c_bool(action["redundant_status"])}',
            f'.stat_stage_before={action["stat_stage_before"]}',
            f'.stat_stage_after={action["stat_stage_after"]}',
            f'.effect_family={EFFECTS[action["effect_family"]]}',
            f'.positive_marginal_exception={c_bool(action["positive_marginal_exception"])}',
            f'.expected_damage={action["expected_damage"]}',
            f'.switch_legal={c_bool(action["switch_legal"])}',
            f'.entry_survives={c_bool(action["entry_survives"])}',
            f'.forced={c_bool(action["forced"])}', f'.fallback_cost={action["fallback_cost"]}',
            f'.switch_from={endpoints.get(action["switch_from"], 255)}',
            f'.switch_to={endpoints.get(action["switch_to"], 255)}',
        ]
        branches = {row["response_id"]: row for row in action["responses"]}
        lines.append("{.floor={" + ",".join(floor) + "},")
        lines.append(f'.tactical_class={TACTICS[action["tactical_class"]]},')
        lines.append(f'.ironmon_switch_emergency={c_bool(action["ironmon_switch_emergency"])},')
        lines.append(f'.stay_defensible={c_bool(action["stay_defensible"])},')
        lines.append(f'.repeat_exception_reason={REPEAT_REASONS[action["repeat_exception_reason"]]},')
        lines.append(f'.public_threat_changed={c_bool(action["public_threat_changed"])},')
        lines.append(f'.regenerator_only={c_bool(action["regenerator_only"])},')
        lines.append(f'.progress_after_loop_cost={action["progress_after_loop_cost"]},')
        lines.append(f'.response_count={len(response_rows)},.responses={{')
        for rr in response_rows:
            branch = branches[rr["response_id"]]
            lines.append("{" + ",".join((
                f'.response_id={response_ids[rr["response_id"]]}',
                f'.net_faints={branch["net_faints"]}',
                f'.opponent_hp_fraction_lost={branch["opponent_hp_fraction_lost"]}',
                f'.own_hp_fraction_lost={branch["own_hp_fraction_lost"]}',
                f'.future_gain_undiscounted={branch["future_gain_undiscounted"]}',
                f'.entry_cost={branch["entry_cost"]}',
            )) + "},")
        lines.append("}},")
    lines.append("}},")
    model = fixture["public_state"]["response_model"]
    revealed = sorted(model["revealed_moves"])
    move_values = [response_ids[move] for move in revealed] + [0] * (4 - len(revealed))
    count_values = [model["move_counts"][move] for move in revealed] + [0] * (4 - len(revealed))
    lines.append(".revealed_moves={" + ",".join(map(str, move_values)) + "},")
    lines.append(".move_counts={" + ",".join(map(str, count_values)) + "},")
    lines.append(f'.unknown_slots={model["unknown_move_slots"]},')
    decisions = fixture["policy_memory"]["decisions"]
    lines.append(f".memory={{.count={len(decisions)},.decisions={{")
    for decision in decisions:
        lines.append("{" + ",".join((
            f'.kind={"STANDARD_POLICY_SWITCH" if decision["kind"] == "switch" else "STANDARD_POLICY_MOVE"}',
            f'.effect_family={EFFECTS[decision["effect_family"]]}',
            f'.success={c_bool(decision["success"])}', f'.forced={c_bool(decision["forced"])}',
            f'.switch_from={endpoints.get(decision["switch_from"], 255)}',
            f'.switch_to={endpoints.get(decision["switch_to"], 255)}',
        )) + "},")
    lines.append("}},")
    lines.append(f'.seed={rng["pre_state"]}u,.selected_id={id_map[trace["selected_action_id"]]},')
    lines.append(f'.best_score={ironmon["best_score"]},')
    eligible_mask = sum(1 << i for i, a in enumerate(actions) if diagnostics[a["id"]]["ironmon_eligible"])
    near_mask = sum(1 << i for i, a in enumerate(actions) if diagnostics[a["id"]]["near_best"])
    lines.append(f'.admitted_pool={eligible_mask},.near_best_pool={near_mask},')
    lines.append(f'.threshold={THRESHOLDS[arb["threshold_class"]]},')
    lines.append(f'.admitted={ADMITTED[arb["admitted_tactical_class"]]},')
    lines.append(f'.admission_result={c_bool(arb["admission_rng"]["admitted"])},')
    lines.append(f'.admission_draws={arb["admission_rng"]["draw_count"]},')
    lines.append(f'.total_draws={rng["draw_count"]},.rng_post={rng["post_state"]}u,')
    lines.append(f'.admission_pre={arb["admission_rng"]["pre_state"]}u,')
    lines.append(f'.admission_post={arb["admission_rng"]["post_state"]}u,')
    best_stay = arb["best_stay"]
    best_switch = arb["best_switch"]
    lines.append(f'.best_stay_id={255 if best_stay is None else id_map[best_stay["action_id"]]},')
    lines.append(f'.best_switch_id={255 if best_switch is None else id_map[best_switch["action_id"]]},')
    lines.append(f'.best_stay_score={0 if best_stay is None else best_stay["score"]},')
    lines.append(f'.best_switch_score={0 if best_switch is None else best_switch["score"]},')
    lines.append(f'.switch_advantage={0 if arb["advantage"] is None else arb["advantage"]},')
    selected_adv = arb["selected_candidate_advantage"]
    lines.append(f'.selected_advantage={"INT32_MIN" if selected_adv is None else selected_adv},')
    lines.append(".diagnostics={")
    for action in actions:
        d = diagnostics[action["id"]]
        lines.append("{" + ",".join((
            f'.utility={d["utility_total"]}', f'.expected={d["expected_before_uncertainty"]}',
            f'.repeat_count={d["repeat_count"]}', f'.repeat_cost={d["repeat_cost"]}',
            f'.loop_cost={d["loop_cost"]}', f'.uncertainty={d["uncertainty_cost"]}',
            f'.threshold_eligible={c_bool(d["switch_threshold_eligible"])}',
            f'.switch_advantage={"INT32_MIN" if d["switch_advantage"] is None else d["switch_advantage"]}',
        )) + "},")
    lines.append("}},")
    return "".join(lines)


def generate_harness(fixtures: list[dict], run_fixture) -> str:
    cases = "\n".join(build_case(fixture, run_fixture) for fixture in fixtures)
    fixture_indexes = {fixture["fixture_id"]: i for i, fixture in enumerate(fixtures)}

    def sequence(fixture_id: str) -> tuple[str, list[int]]:
        fixture = fixtures[fixture_indexes[fixture_id]]
        action_ids = sorted(a["id"] for a in fixture["candidates"])
        action_map = {name: i for i, name in enumerate(action_ids)}
        rows = []
        counts = [0] * len(action_ids)
        for replicate in range(1024):
            result = run_fixture(fixture, "ironmon_smart", replicate)
            selected = action_map[result.trace["selected_action_id"]]
            counts[selected] += 1
            arb = result.trace["ironmon_policy"]["switch_arbitration"]["admission_rng"]
            rng = result.trace["policy_rng"]
            rows.append("{" + ",".join((
                f'{rng["pre_state"]}u', f'{rng["post_state"]}u', str(selected),
                str(arb["draw_count"]), str(rng["draw_count"]),
                c_bool(arb["admitted"]),
            )) + "}")
        return ",".join(rows), counts

    switch_sequence, switch_counts = sequence("ironmon_switch_candidates_12_8")
    equal_sequence, equal_counts = sequence("ironmon_equal_four")
    deterministic_sequence, deterministic_counts = sequence("ironmon_switch_candidates_20_16")
    print("accepted +12/+8 host sequence admit/reject:",
          sum(switch_counts[1:]), switch_counts[0])
    total = sum(switch_counts)
    admission_entropy = -sum(
        (count / total) * math.log2(count / total)
        for count in (sum(switch_counts[1:]), switch_counts[0]) if count
    )
    print(f"accepted +12/+8 normalized admission entropy: {admission_entropy:.6f}")
    print("accepted equal-four host counts:", equal_counts)
    total = sum(equal_counts)
    equal_entropy = -sum(
        (count / total) * math.log2(count / total)
        for count in equal_counts if count
    ) / math.log2(len(equal_counts))
    print(f"accepted equal-four normalized entropy: {equal_entropy:.6f}")
    print("accepted +20/+16 host counts:", deterministic_counts)
    return f'''#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include "new/ai_ironmon_policy.h"

struct ExpectedDiagnostic {{ int32_t utility, expected, switch_advantage; uint8_t repeat_count, repeat_cost, loop_cost, uncertainty, threshold_eligible; }};
struct Case {{ const char *name; struct IronmonPolicyObservation observation; uint16_t revealed_moves[4], move_counts[4]; uint8_t unknown_slots; struct StandardPolicyMemory memory; uint32_t seed;
 uint8_t selected_id; int32_t best_score; uint16_t admitted_pool, near_best_pool; uint8_t threshold, admitted, admission_result, admission_draws, total_draws;
 uint32_t rng_post, admission_pre, admission_post; uint8_t best_stay_id, best_switch_id; int32_t best_stay_score, best_switch_score, switch_advantage, selected_advantage;
 struct ExpectedDiagnostic diagnostics[IRONMON_POLICY_MAX_CANDIDATES]; }};
static struct Case cases[] = {{
{cases}
}};
struct Sequence {{ uint32_t seed, post; uint8_t selected, admission_draws, total_draws, admitted; }};
static const struct Sequence switch_sequence[1024] = {{{switch_sequence}}};
static const struct Sequence equal_sequence[1024] = {{{equal_sequence}}};
static const struct Sequence deterministic_sequence[1024] = {{{deterministic_sequence}}};
#define CHECK(expr) do {{ if (!(expr)) {{ fprintf(stderr, "FAIL %s line %d: %s\\n", c->name, __LINE__, #expr); return 1; }} }} while (0)
int main(void) {{
 unsigned n, i, admitted=0, rejected=0; struct IronmonPolicyResponse responses[5]; uint8_t response_count; struct Case *c=&cases[0];
 uint16_t moves[4]={{20,10,0,0}}, counts[4]={{1,3,0,0}};
 CHECK(IronmonPolicyBuildResponses(moves,counts,2,responses,&response_count)==0);
 CHECK(response_count==3 && responses[0].id==10 && responses[0].weight==12 && responses[1].id==20 && responses[1].weight==6 && responses[2].id==65535 && responses[2].weight==6);
 for (n=0;n<sizeof(cases)/sizeof(cases[0]);++n) {{
  struct IronmonPolicyResult r; uint32_t seed; c=&cases[n]; seed=c->seed;
  CHECK(IronmonPolicyBuildResponses(c->revealed_moves,c->move_counts,c->unknown_slots,responses,&response_count)==0);
  CHECK(response_count==c->observation.response_count);
  for(i=0;i<response_count;++i) CHECK(responses[i].id==c->observation.responses[i].id && responses[i].weight==c->observation.responses[i].weight);
  CHECK(IronmonPolicyChoose(&c->observation,&c->memory,&seed,&r)==0);
  CHECK(r.selected_id==c->selected_id); CHECK(r.best_score==c->best_score);
  CHECK(r.admitted_pool==c->admitted_pool); CHECK(r.near_best_pool==c->near_best_pool);
  CHECK(r.threshold_class==c->threshold); CHECK(r.admitted_class==c->admitted);
  CHECK(r.admission_result==c->admission_result); CHECK(r.admission_draws==c->admission_draws);
  CHECK(r.total_draws==c->total_draws); CHECK(r.rng_post==c->rng_post && seed==c->rng_post);
  CHECK(r.admission_rng_pre==c->admission_pre); CHECK(r.admission_rng_post==c->admission_post);
  CHECK(r.best_stay_id==c->best_stay_id); CHECK(r.best_switch_id==c->best_switch_id);
  CHECK(r.best_stay_score==c->best_stay_score); CHECK(r.best_switch_score==c->best_switch_score);
  CHECK(r.switch_advantage==c->switch_advantage); CHECK(r.selected_switch_advantage==c->selected_advantage);
  for(i=0;i<c->observation.count;++i) {{
   struct ExpectedDiagnostic *e=&c->diagnostics[i]; struct IronmonPolicyDiagnostic *d=&r.diagnostics[i];
   CHECK(d->utility_total==e->utility); CHECK(d->expected_before_uncertainty==e->expected);
   CHECK(d->repeat_count==e->repeat_count); CHECK(d->repeat_cost==e->repeat_cost);
   CHECK(d->loop_cost==e->loop_cost); CHECK(d->uncertainty_cost==e->uncertainty);
   CHECK(d->switch_threshold_eligible==e->threshold_eligible); CHECK(d->switch_advantage==e->switch_advantage);
  }}
 }}
 c=&cases[{fixture_indexes["ironmon_switch_candidates_12_8"]}];
 for(n=0;n<1024;++n) {{ struct IronmonPolicyResult r; uint32_t seed=switch_sequence[n].seed;
  CHECK(IronmonPolicyChoose(&c->observation,&c->memory,&seed,&r)==0);
  CHECK(r.selected_id==switch_sequence[n].selected && seed==switch_sequence[n].post);
  CHECK(r.admission_draws==1 && r.total_draws==1);
  CHECK(r.admission_draws==switch_sequence[n].admission_draws && r.total_draws==switch_sequence[n].total_draws);
  CHECK(r.admission_result==switch_sequence[n].admitted); CHECK(r.selected_id!=2);
  CHECK(r.selected_id==0 || r.selected_id==1);
  if(r.admission_result) ++admitted; else ++rejected;
 }}
 CHECK(admitted>460 && admitted<564); CHECK(admitted+rejected==1024);
 printf("+12/+8 1024-seed admission: admitted=%u rejected=%u; one admission draw; below-threshold selected=0; invalid selected=0; replay=0\\n",admitted,rejected);
 c=&cases[{fixture_indexes["ironmon_equal_four"]}];
 {{ unsigned counts[4]={{0,0,0,0}}; for(n=0;n<1024;++n) {{ struct IronmonPolicyResult r; uint32_t seed=equal_sequence[n].seed;
  CHECK(IronmonPolicyChoose(&c->observation,&c->memory,&seed,&r)==0);
  CHECK(r.selected_id==equal_sequence[n].selected && seed==equal_sequence[n].post);
  CHECK(r.total_draws==equal_sequence[n].total_draws); ++counts[r.selected_id]; }}
  for(i=0;i<4;++i) CHECK(counts[i]>=205 && counts[i]<=307);
  printf("equal-four 1024-seed counts: %u/%u/%u/%u; uniform +/-5pp PASS\\n",counts[0],counts[1],counts[2],counts[3]); }}
 c=&cases[{fixture_indexes["ironmon_switch_candidates_20_16"]}];
 for(n=0;n<1024;++n) {{ struct IronmonPolicyResult r; uint32_t seed=deterministic_sequence[n].seed;
  CHECK(IronmonPolicyChoose(&c->observation,&c->memory,&seed,&r)==0);
  CHECK(r.selected_id==deterministic_sequence[n].selected && seed==deterministic_sequence[n].post);
  CHECK(r.admission_draws==0 && r.selection_draws==1 && r.total_draws==1);
 }}
 c=&cases[{fixture_indexes["ironmon_robust_ko"]}]; {{ struct IronmonPolicyResult r; uint32_t seed=c->seed;
  CHECK(IronmonPolicyChoose(&c->observation,&c->memory,&seed,&r)==0 && r.total_draws==0); }}
 puts("+20/+16 admission-before-selection ordering and singleton zero-draw: PASS");
 {{ struct IronmonPolicyObservation o={{0}}; struct StandardPolicyMemory m={{0}}; struct IronmonPolicyResult r; uint32_t seed=1;
  o.response_count=2; o.responses[0].id=1; o.responses[0].weight=1; o.responses[1].id=2; o.responses[1].weight=1; o.count=1;
  o.candidates[0].floor.id=0; o.candidates[0].floor.legal=1; o.candidates[0].floor.productive=1;
  o.candidates[0].floor.entry_survives=1; o.candidates[0].stay_defensible=1; o.candidates[0].response_count=2;
  o.candidates[0].responses[0]=(struct IronmonPolicyBranch){{1,-1,0,256,-80,INT32_MAX}};
  o.candidates[0].responses[1]=(struct IronmonPolicyBranch){{2,1,256,-256,80,0}};
  CHECK(IronmonPolicyChoose(&o,&m,&seed,&r)==0);
  CHECK(r.diagnostics[0].expected_before_uncertainty==-1073741773);
  CHECK(r.diagnostics[0].uncertainty_cost==25 && r.diagnostics[0].utility_total==-1073741798);
  o.response_count=1; o.responses[0].weight=1; o.candidates[0].response_count=1; seed=1;
  CHECK(IronmonPolicyChoose(&o,&m,&seed,&r)==0 && r.diagnostics[0].utility_total==INT32_MIN);
 }}
 puts("signed weighted arithmetic, toward-zero division, uncertainty cap, int32 saturation: PASS");
 printf("Ironmon C host parity: %zu/63 fixtures PASS at replicate 0\\n",sizeof(cases)/sizeof(cases[0]));
 return 0;
}}
'''


def main() -> int:
    run(["python3", "scripts/tests/audit_ironmon_ai.py"])
    load_fixtures, run_all, run_fixture, mandatory_tags = load_host()
    fixtures = verify_digests(load_fixtures, run_all, mandatory_tags)
    source = generate_harness(fixtures, run_fixture)
    with tempfile.TemporaryDirectory(prefix="cfru-ironmon-ai-") as directory:
        harness = Path(directory) / "ironmon_parity.c"
        binary = Path(directory) / "ironmon_parity"
        harness.write_text(source, encoding="utf-8")
        run(["cc", "-std=c99", "-Wall", "-Wextra", "-Werror", "-Iinclude",
             str(harness), "src/Battle_AI/ai_standard_policy.c",
             "src/Battle_AI/ai_ironmon_policy.c", "-o", str(binary)])
        subprocess.run([str(binary)], cwd=ROOT, check=True)
    print("Ironmon temporary host objects: deleted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
