# F01/D01 — minimal opening Oak exposition

Contract: [Workspace #592](https://github.com/Planton361/firered-gen9-randomizer-workspace/issues/592).
**CONFIRMED USER DECISION:** retain normal character creation and New Game;
reduce only the opening Oak exposition. **INTENDED IMPLEMENTATION:** this
candidate, pending user-owned runtime checks. No runtime PASS is claimed.

CFRU base: `78478c728501fe8c70bd84e01e51c6334250a6f0`.
Branch: `qol/oak-minimal-exposition`.
Integration target: `compat/firered-gen9-randomizer`.
Source writing uses an isolated, initially clean source-only checkout cloned
from the existing local Git repository, with HEAD verified at the exact base
before branching. The persistent Workspace and dirty CFRU checkout are not
modified. Protected tracked artifacts are excluded from the sparse checkout.

## Source ownership and binding

The structural reference is pret/pokefirered
`e060ab955b5dc9ac1c4904c2cd141683615cf477`, `src/oak_speech.c`,
`src/new_game.c`, and `src/overworld.c`. It supplies lifecycle structure, not a
replacement engine. BPRE addresses are established by that pinned repository's
own source history, not patch binaries, generated builds or unrelated layouts:

- Ancestor `fb7ba2161078a822da9698ef801472baf1ee0ed1`,
  `src/oak_speech.c`: `sub_812F7C0` is the initializer, creating the hidden
  Pokémon sprite/background/Oak/platform, starting BGM and palette fade, then
  assigning `sub_812F880` (the modern `Task_OakSpeech_WelcomeToTheWorld`).
- `sub_812F880` prints the welcome and assigns `sub_812F944` (ThisWorld).
  Its original assembly label is also present in
  `dfc2fa2b393437a471bf815f2c9a7be0bc061021^:asm/oak_speech.s`.
- `sub_812FD78` clears the dialogue, calls `sub_813144C(taskId, 2)`
  (CreateFadeInTask), sets task data[3] to 48, and assigns `sub_812FDC0`
  (AskPlayerGender). The assembly at
  `2f337edf36ded496efd8ec6cc0c35dda10e1bc98^:asm/oak_speech.s`
  independently labels this entry `0x0812FD78` and its next task `0x0812FDC0`.
  The modern source requires data[2] (trainer-picture fade completion) before
  clearing Oak's picture and asking gender.
- The accepted CFRU already owns the intro species sprite and cry through
  `CreateOakIntroPokemonSprite` at `0x08130F2C` and
  `Task_OakSpeech_IsInhabitedFarAndWide` at `0x0812FA78`; both remain unchanged.

The new `functionrewrites` row replaces only `0x0812F880` with the void,
one-argument `Task_OakSpeech_MinimalExposition` (`1 0` wrapper fields).
`BPRE.ld` binds the retained `Task_OakSpeech_FadeOutOak` to `0x0812FD78 | 1`.
The wrapper replaces 20 bytes at the original function entry, wholly within
WelcomeToTheWorld; it does not alter its successor or initializer.

## Old and new transition

Old:

`OakSpeech_Init → WelcomeToTheWorld → ThisWorld → ReleaseNidoranFFromPokeBall
→ IsInhabitedFarAndWide → IStudyPokemon → ReturnNidoranFToPokeBall
→ TellMeALittleAboutYourself → FadeOutOak → AskPlayerGender`.

New:

`OakSpeech_Init → MinimalExposition → original FadeOutOak → AskPlayerGender`.

MinimalExposition waits for the initialization palette fade and idle text
printer, destroys exactly the still-hidden intro Pokémon sprite (data[4]),
then invokes the original FadeOutOak and zeros only the presentation timer
(data[3]). It does not destroy a Poke Ball sprite: the bypassed release/return
steps never created one. The original fade child task still signals completion
in data[2], hides the platform sprites, and gates AskPlayerGender. This avoids
leaving an invisible sprite behind or bypassing required BG/blend/picture state.

Bypassed: welcome, world explanation, inhabitance/study text, Pokémon release,
cry and return presentation, "tell me about yourself", their associated waits,
the post-initialization 80-frame welcome wait, and the extra 48-frame wait after
Oak's fade. The original initializer's pre-initialization delay, allocation,
background load, palette fade, BGM, Oak/platform creation and species loader
remain. Identity-associated presentation and the closing shrink/exit animation
remain; this is a single opening-task change, not a broad intro rewrite.

## Retained lifecycle

- `AskPlayerGender → ShowGenderOptions → HandleGenderInput` still offers BOY
  and GIRL, with the normal ignored B/no-selection input.
- `ClearGenderWindows → LoadPlayerPic → YourNameWhatIsIt
  → FadeOutForPlayerNamingScreen → DoNamingScreen` still opens the free player
  naming screen and preserves default-name initialization.
- `CB2_ReturnFromNamingScreen → ConfirmName → HandleConfirmNameInput`
  preserves confirmation, NO/B retry and resource reconstruction.
- Player confirmation continues through `FadeOutPlayerPic → FadeInRivalPic
  → AskRivalsName → MoveRivalDisplayNameOptions → HandleRivalNameInput`.
  NEW NAME opens the normal free rival naming screen; existing preset choices,
  confirmation and retry remain. D03 rival presentation is unchanged.
- Rival confirmation continues through `FadeOutRivalPic → ReshowPlayersPic
  → LetsGo → FadeOutBGM → SetUpExitAnimation`, normal platform destruction,
  picture shrink/fades, `WaitForFade → FreeResources → CB2_NewGame`.
- FreeResources still frees window buffers, the mon graphics manager and speech
  resources, nulls the pointer, restores text flags and destroys the task.
- `CB2_NewGame → NewGameInitData` still initializes the party/storage/bag/flags,
  preserves the selected rival name, generates Trainer ID through
  `(Random() << 16) | GetGeneratedTrainerIdLower()`, and warps to Player Room.
  CFRU's existing post-init settings hook, native early running, controls-guide
  skip, M-006 Mom/Lab handoff, starter/nickname/Rival/story paths are unchanged.

## Source-only verification

Run from the isolated component checkout:

```sh
python3 scripts/tests/check_oak_minimal_exposition.py --pret-root /path/to/pret-pokefirered
git diff --check
git status --short
git diff --stat
```

The checker reads exact pinned reference Git source objects and checks both
address/source bindings, every skipped opening transition, retained gender,
player/rival naming, defaults/retries, cleanup, New Game and Trainer ID paths.
It restricts the diff to the five listed files and verifies that the linker and
rewrite manifests have only their exact additions. No header, SaveBlock/layout,
settings/running source, story script, DPE, UPR-FVX or Gitlink change is allowed.
These are structural checks, not runtime proof.

Changed files: `src/oak_minimal_exposition.c`, `BPRE.ld`, `functionrewrites`,
`scripts/tests/check_oak_minimal_exposition.py`, this document.

## Targeted user-owned runtime acceptance

Record the exact candidate revision and test configuration. User checks still
required:

1. Fresh New Game: short Oak transition, no opening exposition/Pokémon
   presentation, normal gender prompt; both BOY and GIRL over separate runs.
2. Freely enter distinct valid player/rival names. Test player and rival
   confirmation NO/B retries, rival NEW NAME/preset choices, and empty/default
   naming behavior wherever the existing naming screen supports it.
3. Verify selected gender/name/rival name and generated Trainer ID on identity
   screens; do not expect specific IDs or a guarantee of different IDs per run.
4. Reach Player Room, normal Mom interaction and accepted M-006 Lab handoff.
   Check all starter choices over separate runs, nickname YES/NO, normal Rival
   starter choice and battle continuation, Lab exit and story progression.
5. Save/reload identity and progression; check existing B-running, L Auto-Run,
   settings defaults/persistence and ordinary menus.
6. Observe fade/background/platform cleanup, naming-screen return/retry,
   missing/stray sprites, hangs or resource regressions throughout the flow.

**UNKNOWN:** runtime rendering, cleanup timing and downstream gameplay until
these checks pass. No known product CONFLICT. Random-number consumption/timing
changes when presentation tasks are skipped; the normal Trainer ID generator is
preserved, not any previous run's exact ID.

Protected boundary: no ROM, save, emulator state, build, screenshot, tool binary,
private artifact or secret is read, created or modified. No emulator/randomizer
is run. No Workspace Gitlink changes, merge, or upstream contribution work.
`UPSTREAM_CONTRIBUTION = DEFERRED`.
