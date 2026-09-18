#!/usr/bin/env python3
"""Exact accepted-source union and fail-closed integration checks; no ROM input."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "827fa1ef04bd43e5c6bad5c47f7d8690ea6823ec"
PREMIER = "d8468e1d12dbe33f646e2778bbde51ece7010a73"
LEARNSETS = "c483410d44c1b592e8039e631556cadab2352b3a"
WORKSPACE = "ddd26b17d1ecae80a26943b76ed51b93e70e692c"
PREFLIGHT = "scripts/check_hidden_item_sparkle.py"
PREMIER_FILES = {"docs/M-013.md", PREFLIGHT, "scripts/check_premier_bonus.py",
                 "scripts/tests/m013_premier_host.c", "src/item.c"}
LEARNSET_FILES = {"docs/coherent-learnset-consumers.jsonl", "docs/coherent-learnsets-closure.md",
                 "docs/coherent-learnsets-provenance.json", "scripts/check_coherent_learnsets.py",
                 PREFLIGHT, "src/Tables/level_up_learnsets.c"}
INTEGRATION_FILES = {"scripts/check_m013_coherent_integration.py", "docs/M-013-coherent-integration.md"}
ENTRY = ("    # Combined candidate: exact accepted source union before input access.\n"
         "    from check_m013_coherent_integration import check_source_contract as check_integration\n"
         "    check_integration()\n")


def require(condition, message):
    if not condition:
        raise ValueError("M-013/coherent integration fail-closed: " + message)


def git(*args, root=ROOT):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True)


def source(revision, path):
    return git("show", revision + ":" + path)


def read(path):
    # Preserve line endings too: accepted-source equality is byte-exact UTF-8.
    return (ROOT / path).read_bytes().decode("utf-8")


def combined_preflight():
    """Keep all #48 checks, splice the exact #45 boundary/allowlist addition.

    This is a literal composition, not an acceptance of arbitrary callback or
    learnset edits. The independent accepted source files are pinned below too.
    """
    premier = source(PREMIER, PREFLIGHT)
    coherent = source(LEARNSETS, PREFLIGHT)
    end = "    changed = set(git("
    start = "    # M-013 is an independent, bounded successor."
    require(premier.count(start) == 1 and premier.count(end) == 1, "Premier preflight anchor drift")
    addition = premier[premier.index(start):premier.index(end)]
    old_tail = '"scripts/tests/m009_sparkle_host.c"}'
    require(addition.count(old_tail) == 1, "Premier allowlist anchor drift")
    addition = addition.replace(old_tail,
        '"scripts/tests/m009_sparkle_host.c",\n'
        '               "src/Tables/level_up_learnsets.c", "scripts/check_coherent_learnsets.py",\n'
        '               "scripts/check_m013_coherent_integration.py"}')
    start = "    allowed = {"
    require(coherent.count(start) == 1 and coherent.count(end) == 1, "Coherent preflight anchor drift")
    result = coherent[:coherent.index(start)] + addition + coherent[coherent.index(end):]
    anchor = "def check_source_contract():\n"
    require(result.count(anchor) == 1, "Preflight entry anchor drift")
    return result.replace(anchor, anchor + ENTRY, 1)


def expected_sources():
    for revision, files in ((PREMIER, PREMIER_FILES), (LEARNSETS, LEARNSET_FILES)):
        require(git("merge-base", BASE, revision).strip() == BASE, "Candidate not based on canonical pilot")
        require(set(git("diff", "--name-only", BASE, revision).splitlines()) == files,
                "Accepted candidate file set differs from reviewed set")
    expected = {path: source(PREMIER, path) for path in PREMIER_FILES - {PREFLIGHT}}
    expected.update({path: source(LEARNSETS, path) for path in LEARNSET_FILES - {PREFLIGHT}})
    expected[PREFLIGHT] = combined_preflight()
    # These canonical owners are also checked before input access. M-009 checks
    # insertion's exact M-001..M-008 contract and all preserved frame owners.
    for path in ("scripts/insert.py", "hooks", "functionrewrites", "bytereplacement",
                 "src/config.h", "src/learn_move.c", "include/new/learn_move.h",
                 "include/constants/species.h", "include/constants/moves.h",
                 "src/m009_overworld_frame.c", "src/hidden_item_sparkle.c"):
        expected[path] = source(BASE, path)
    return expected


def validate(reader, changed, expected):
    allowed = PREMIER_FILES | LEARNSET_FILES | INTEGRATION_FILES
    require(set(changed) == allowed, "Unapproved/missing changed path: " + str(sorted(set(changed) ^ allowed)))
    for path, contents in expected.items():
        require(reader(path) == contents, "Not exact accepted/combined source: " + path)


def changed_paths():
    return set(git("diff", "--name-only", BASE).splitlines()) | set(
        git("ls-files", "--others", "--exclude-standard").splitlines())


def check_source_contract():
    validate(read, changed_paths(), expected_sources())
    print("PASS: exact #45 + #48 source union; only deliberate combined preflight/test/documentation additions")


def check_rejections():
    expected = expected_sources()
    changed = changed_paths()
    cases = [
        ("Premier divisor", "src/item.c", lambda s: s.replace("(u16)tItemCount / 10", "(u16)tItemCount / 9", 1)),
        ("Premier re-entry", "src/item.c", lambda s: s.replace("\t\t\treturn;\n\t\t}\n\t\t#endif\n\n\t\t#ifdef ENABLE_MULTIPLE_PURCHASE_REWARDS", "\t\t\t/* missing return */\n\t\t}\n\t\t#endif\n\n\t\t#ifdef ENABLE_MULTIPLE_PURCHASE_REWARDS", 1)),
        ("learnset row", "src/Tables/level_up_learnsets.c", lambda s: s.replace("MOVE_SCRATCH", "MOVE_NONE", 1)),
        ("form re-sharing", "src/Tables/level_up_learnsets.c", lambda s: s.replace("[SPECIES_PICHU_SPIKY] = sPichuSpikyLevelUpLearnset", "[SPECIES_PICHU_SPIKY] = sPichuLevelUpLearnset", 1)),
        ("Dada null", "src/Tables/level_up_learnsets.c", lambda s: s.replace("\t[SPECIES_ZARUDE_DADA] = sZarudeLevelUpLearnset,\n", "", 1)),
        ("reference relabel", "docs/coherent-learnsets-provenance.json", lambda s: s.replace("b1156ff19204e48089e2384eb2c9c1a8004f57ce", "UNKNOWN", 1)),
        ("learnset guard bypass", PREFLIGHT, lambda s: s.replace("    check_learnsets()\n", "", 1)),
        ("Premier boundary bypass", PREFLIGHT, lambda s: s.replace("    require(item.replace(body(item, callback)", "    require(True or item.replace(body(item, callback)", 1)),
        ("integration guard bypass", PREFLIGHT, lambda s: s.replace(ENTRY, "", 1)),
        ("insertion preflight bypass", "scripts/insert.py", lambda s: s.replace("    check_source_contract()\n", "", 1)),
        ("guard weakening", "scripts/check_coherent_learnsets.py", lambda s: s.replace("len(changed) == 820", "True", 1)),
        ("host weakening", "scripts/check_premier_bonus.py", lambda s: s.replace('"-fsanitize=undefined,bounds",', "", 1)),
    ]
    for label, path, mutate in cases:
        modified = mutate(expected[path])
        require(modified != expected[path], "Invalid mutation fixture: " + label)
        try:
            validate(lambda p: modified if p == path else read(p), changed, expected)
        except ValueError:
            continue
        raise AssertionError("Invalid integration accepted: " + label)
    try:
        validate(read, changed | {"src/unapproved_engine.c"}, expected)
    except ValueError:
        pass
    else:
        raise AssertionError("Unapproved source path accepted")
    print(f"PASS: {len(cases) + 1} integration mutations rejected (callback/data/pointers/provenance/guards/scope)")


def check_workspace_replay(workspace, data):
    """Reuse the accepted helper unchanged; point only CFRU reads at this tree."""
    script_dir = workspace / "07_scripts/data_audit"
    require(git("rev-parse", "HEAD", root=workspace).strip() == WORKSPACE, "Unexpected workspace helper revision")
    require(not git("diff", "HEAD", "--", "07_scripts/data_audit", root=workspace).strip(), "Modified accepted helper inputs")
    require(not git("ls-files", "--others", "--exclude-standard", "07_scripts/data_audit", root=workspace).strip(), "Untracked helper inputs")
    sys.path.insert(0, str(script_dir))
    import showdown_pokemon_data_sync as sync
    import showdown_pinned_closure as closure
    # DPE remains read-only at its canonical pin through the accepted workspace.
    old_root = sync.CFRU_ROOT
    sync.CFRU_ROOT = ROOT
    sync.CFRU_LEARNSETS = ROOT / "src/Tables/level_up_learnsets.c"
    # The accepted constants parser derives component labels and relative paths
    # from its original workspace layout. Keep that parser unchanged; prove its
    # CFRU header inputs identical to this integration before reusing them.
    for paths in sync.mapping.LOCAL_HEADERS.values():
        for path in paths:
            if path.is_relative_to(old_root):
                require((ROOT / path.relative_to(old_root)).read_bytes() == path.read_bytes(),
                        "Accepted helper constant input differs from integration: " + path.name)
    reference = json.loads(closure.REFERENCE.read_text())
    closure.verify_reference(data, reference)
    closure.verify_component_inputs(reference)
    closure.verify_candidate(data, reference)
    first, _ = closure.build_inventory(data, reference)
    second, _ = closure.build_inventory(data, reference)
    require(closure.serialize_inventory(first, True) == closure.serialize_inventory(second, True), "Nondeterministic helper replay")
    require(closure.serialize_inventory(first, True) == (workspace / "docs/audits/coherent-learnsets-candidate-2026-09-15.jsonl").read_text(),
            "Integration inventory differs from accepted #48 inventory")
    require(first["summary"]["counts"] == json.loads(read("docs/coherent-learnsets-provenance.json"))["inventory_counts"],
            "Inventory counts drifted")
    print("PASS: unchanged accepted helper, exact replay and two identical full inventories matching #48")
    print(json.dumps(first["summary"]["counts"], sort_keys=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, help="Read-only accepted Workspace #493 checkout at the locked revision")
    parser.add_argument("--showdown-data-dir", type=Path, help="Read-only pinned public Showdown data directory")
    args = parser.parse_args()
    require(bool(args.workspace) == bool(args.showdown_data_dir), "Replay needs both workspace and Showdown data paths")
    check_source_contract()
    check_rejections()
    if args.workspace:
        check_workspace_replay(args.workspace.resolve(), args.showdown_data_dir.resolve())


if __name__ == "__main__":
    main()
