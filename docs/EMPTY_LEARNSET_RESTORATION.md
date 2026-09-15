# Restore five accidentally empty active learnsets

Status: source candidate, not runtime accepted. Stacked on M-013; no engine mechanic change.

## Evidence and bounded decision

At the canonical pilot CFRU pin `827fa1ef04bd43e5c6bad5c47f7d8690ea6823ec`,
`src/Tables/level_up_learnsets.c` contains only `LEVEL_UP_END` in the Pikachu,
Rotom, Necrozma, Zacian and Zamazenta named tables. Thirty-one existing
species/form pointers share those five tables. DPE's `EXPAND_LEARNSETS` is
disabled at its pin `22ffa27ad09cfacbca841d90e6cbe31e6f9b7fdc`, so the empty
CFRU tables are the active pilot source, not unused copies.

Classification: **DATA_BUG**. The smallest source-backed repair restores exactly
those five blocks from tracked CFRU revision
`53273184bab06f91cdc3ad6e0e5af4a8ba41591a` (before the data-sync change), retaining
all pointer bindings and other tables byte-for-byte. Restored move counts are
18 / 16 / 19 / 14 / 14 respectively. No DPE, randomizer, battle logic or form
transition changes are included. The empty sentinel `sEmptyMoveset` is preserved.

This repairs lost data; it does **not** certify that the historical moves are the
final Scarlet/Violet authority. The approved upstream raw dataset/snapshot is
not tracked in this workspace. Exact modern-data parity therefore remains
UNKNOWN; an external snapshot is not invented or fetched as part of this fix.
Shared-form synchronization is a plausible cause of the empties, not a proven
cause without that original input dataset.

## Verification

- `python3 scripts/check_restored_learnsets.py`: PASS, exact five-block source
  restoration, no unrelated edits, 31 unchanged pointer bindings, valid levels
  and move symbols, no other named empty tables.
- Existing M-009 source contract, eight rejection mutations and host algorithm:
  PASS. Its fail-closed change allowlist now explicitly runs the restoration
  contract; frame/scanner checks are unchanged.
- `python3 scripts/check_premier_bonus.py`: PASS, inherited M-013 host regression.
- ARM compiler `-fsyntax-only` on the complete learnset translation unit: PASS.
- `git diff --check`: PASS.
- Clean full `python3 scripts/build.py` attempted in a fresh source worktree:
  all C/assembly/string/image stages completed, then stopped at audio because
  `wav2agb` is missing. `mid2agb` is also not installed. Full link/build is NOT
  certified; no ROM insertion or protected artifact was accessed.

## User-only gates

1. Review M-013 first. This branch is stacked on its candidate so both bounded
   extensions of the M-009 preflight coexist. After M-013 is merged by the user,
   retarget/rebase this draft to the compatibility branch; never merge the
   experimental M-011 mechanic work.
2. Complete a clean/full source build with the approved existing toolchain.
3. On a user-owned integrated test build, check each of the five base species at
   level 1 and across one later restored level boundary: legal nonempty starting
   moves, exactly the expected move-learning prompt, no invalid move/name/crash.
4. Check a shared-form representative per family where the existing engine makes
   that form safely accessible. This tests shared data, not new transformation
   mechanics. Do not force unsupported forms or assert missing mechanics work.
5. Recheck party/PC summary and save/reload, plus unmodified and randomized
   movesets. UPR's asset/learnset gates may admit these species after this repair;
   repeat the expanded-pool smoke on the final integrated source pins.

STOP on an invalid ID, empty legal moveset, crash, corrupted UI, lost unrelated
moves, or a source mismatch. Provide only sanitized steps/IDs/text results; do
not attach ROMs, saves, emulator states, generated builds or private addresses.
