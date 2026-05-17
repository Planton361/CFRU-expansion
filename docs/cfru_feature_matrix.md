# CFRU Gen9 Randomizer Feature Matrix

Scope: current `compat/firered-gen9-randomizer` source configuration. This is a ROM-free source review only; it does not prove runtime behavior in a built ROM.

Current stable randomizer path:

- UPR-FVX Wild Standard/Fallback.
- Trainer Pokemon core.
- Pokemon Movesets Random completely.
- Ogerpon learnset, sprite, and palette fixes.
- GUI-4B local smoke passed.

Known boundary: UPR-FVX Standard/Fallback Wild currently does not model CFRU Day/Night headers, swarms, DexNav, raids, or other special-wild systems.

Recommendations use:

- `keep`: keep for the current build unless a later targeted scope changes it.
- `disable for randomizer run`: likely should be disabled or neutralized for a normal randomized walkthrough.
- `investigate later`: separate technical scope needed before changing.
- `do not touch`: engine-critical or high-risk; leave alone without a dedicated migration.

## Debug Features

| Name | File | Current status/value | Meaning | Randomizer impact | Risk | Recommendation |
| --- | --- | --- | --- | --- | --- | --- |
| `DEBUG_QUICK_BATTLES` | `src/config.h` | commented | Ends battles quickly after choosing the first attack. | Would invalidate normal battle and trainer smoke behavior. | High if enabled for real play. | keep disabled |
| `DEBUG_MEGA` | `src/config.h` | commented | Allows Mega Evolution without normal gating. | Can mask item/flag gating issues. | Medium. | keep disabled |
| `DEBUG_HMS` | `src/config.h` | commented | Allows HM use from party screen regardless of normal gates. | Can hide progression and HM compatibility bugs. | Medium. | keep disabled |
| `DEBUG_OBEDIENCE` | `src/config.h` | commented | Disables traded Pokemon obedience issues. | Changes walkthrough difficulty and obedience tests. | Low to medium. | keep disabled |
| `DEBUG_DYNAMAX` | `src/config.h` | commented | Allows Dynamax without a Dynamax Band in Dynamax battles. | Can hide Dynamax gating issues. | Medium. | keep disabled |
| `DEBUG_AI_CHOICES` | `src/config.h` | commented | Removes frame-based randomness from AI choices. | Useful for deterministic AI diagnosis, not normal play. | Low for diagnosis, medium for normal play. | investigate later |
| `DEBUG_TERASTAL` | `src/config.h` | commented | Allows Terastallization without normal Tera Orb gating. | Can hide Tera gating issues. | Medium. | keep disabled |
| `VAR_DEBUG_MENU_SET_CUSTOM_VAR` / `VAR_DEBUG_MENU_SET_CUSTOM_VAR_VALUE` | `src/config.h` | `0x5158`, `0x5159` | Vars used by the debug menu custom-var option. | No direct UPR-FVX impact unless scripts expose debug menu. | Low if unused; medium if exposed. | investigate later |
| `FLAG_SANDBOX_MODE` | `src/config.h` | `0xA0D` | Sandbox/debug-style runtime flag. | Could bypass intended walkthrough constraints if set. | Medium. | investigate later |

## Wild Encounter Features

| Name | File | Current status/value | Meaning | Randomizer impact | Risk | Recommendation |
| --- | --- | --- | --- | --- | --- | --- |
| `FLAG_POKEMON_RANDOMIZER` | `src/config.h`, `src/build_pokemon.c` | `0x940` | Runtime flag that randomizes Pokemon species created by CFRU. | Separate from UPR-FVX ROM rewrite path; can stack unexpected runtime randomization on top of UPR-FVX output. | High if enabled during UPR-FVX randomized run. | disable for randomizer run unless specifically testing CFRU runtime randomizer |
| `NUM_SPECIES_RANDOMIZER` | `src/config.h`, `src/build_pokemon.c` | `NUM_SPECIES` | Species count used by CFRU runtime species randomizer. | If `FLAG_POKEMON_RANDOMIZER` is set, this controls the runtime random pool size. | Medium; wrong count can select invalid species. | keep, but avoid runtime randomizer for normal run |
| `FLAG_WILD_CUSTOM_MOVES` | `src/config.h`, `src/wild_encounter.c` | `0x90B` | Lets scripts assign custom wild Pokemon moves. | Can override randomized learnset assumptions for special/scripted encounters. | Medium. | investigate later |
| `FLAG_SMART_WILD` | `src/config.h`, `src/wild_encounter.c` | `0x90C` | Makes a specific wild battle use smarter AI; cleared after battle. | Changes battle difficulty independently of UPR-FVX. | Low to medium. | keep |
| `WILD_ALWAYS_SMART` | `src/config.h` | defined | Makes all wild Pokemon act smartly. | Normal wild encounters may be harder than expected; not a species-randomization blocker. | Medium for difficulty tuning. | investigate later |
| `FLAG_SCALE_WILD_POKEMON_LEVELS` | `src/config.h`, `src/wild_encounter.c` | `0x90D` | Scales random wild Pokemon to the lowest party level when flag is set. | Runtime level scaling can conflict with UPR-FVX randomized levels and tracker assumptions. | Medium to high if scripts set it. | investigate later |
| `FLAG_DOUBLE_WILD_BATTLE` | `src/config.h`, `src/wild_encounter.c` | `0x910` | Forces or enables double wild battles. | UPR-FVX Standard/Fallback evidence does not cover wild double battle behavior. | Medium. | investigate later |
| `WILD_DOUBLE_RANDOM_CHANCE` | `src/config.h`, `src/wild_encounter.c` | `50` | Chance for wild double battle in special grass/Sweet Scent paths. | Special-wild behavior outside current UPR-FVX scope. | Medium. | investigate later |
| `FLAG_NO_RANDOM_WILD_ENCOUNTERS` | `src/config.h`, `src/wild_encounter.c` | `0x911` | Disables random wild encounters when set. | Can make local smoke appear encounter-free despite valid tables. | Medium for testing. | keep, but verify scripts do not set it unexpectedly |
| `BIKE_ENCOUNTER_PERCENT` | `src/config.h` | `60` | Encounter-rate multiplier while biking. | Does not change species tables, only encounter frequency. | Low. | keep |
| `SWEET_SCENT_ONLY_IN_CLEAR_WEATHER` | `src/config.h`, `src/wild_encounter.c` | defined | Blocks Sweet Scent wild encounters in non-clear weather. | Affects encounter test setup. | Low. | keep |
| `SWEET_SCENT_WILD_DOUBLE_BATTLES` | `src/config.h`, `src/wild_encounter.c` | defined | Sweet Scent may trigger double wild battles. | Outside current Standard/Fallback scope. | Medium. | investigate later |

## Swarm/DayNight/Special-Wild

| Name | File | Current status/value | Meaning | Randomizer impact | Risk | Recommendation |
| --- | --- | --- | --- | --- | --- | --- |
| `SWARM_CHANCE` | `src/config.h`, `src/wild_encounter.c` | `50` | Percent chance that the active route swarm replaces a land encounter. | Directly explains Route 1 Frigibax despite UPR-FVX Route 1 log showing other Standard/Fallback species. | High for normal randomized walkthrough consistency. | disable for randomizer run or neutralize swarms in a targeted follow-up |
| `gSwarmTable` | `src/Tables/wild_encounter_tables.c` | Route 1 entry with `SPECIES_FRIGIBAX` | Defines possible swarm species and map sections. | UPR-FVX currently does not read/write it; active swarms can leak non-randomized species into play. | High for current Frigibax issue. | disable for randomizer run |
| `VAR_SWARM_INDEX` | `src/config.h`, `src/wild_encounter.c` | `0x5008` | Runtime var for current swarm index or override. | If valid, selects an entry in `gSwarmTable`. | Medium. | investigate later |
| `VAR_SWARM_DAILY_EVENT` | `src/config.h`, `src/wild_encounter.c` | `0x5009` | Daily event state for swarm update. | Swarm selection can change by day/time/player ID depending on build settings. | Medium. | investigate later |
| `SWARM_CHANGE_HOURLY` | `src/Tables/wild_encounter_tables.c`, `src/wild_encounter.c` | not defined in reviewed config | Optional hourly swarm rotation table. | If enabled later, special-wild species can change by hour. | Medium. | keep disabled |
| `TIME_ENABLED` | `src/config.h`, `src/wild_encounter.c`, `src/dns.c` | defined | Enables RTC/time-based systems, including Day/Night wild header selection. | UPR-FVX Standard/Fallback does not model CFRU time-specific wild headers. | High for special-wild coverage; broad engine impact if disabled. | investigate later |
| `TIME_MORNING_START` / `TIME_DAY_START` / `TIME_EVENING_START` / `TIME_NIGHT_START` | `src/config.h` | `4`, `8`, `17`, `20` | Time windows used by Day/Night systems. | Changes which special wild table is selected when `TIME_ENABLED` is active. | Low by itself, medium with populated headers. | keep |
| `DNS_IN_BATTLE` | `src/config.h`, `src/dns.c`, `src/battle_terrain.c` | defined | Enables Day/Night visuals in battle. | Visual/background behavior, not UPR-FVX species writer scope. | Low to medium. | keep |
| `gWildMonMorningHeaders` | `src/Tables/wild_encounter_tables.c`, `src/wild_encounter.c` | defined, currently empty sentinel unless `FIRERED_GEN9_ENABLE_ROUTE1_CUSTOM_WILD` is enabled | Morning-specific wild table headers. | Not read/written by UPR-FVX Standard/Fallback. | Medium if populated. | investigate later |
| `gWildMonDayHeaders` | `src/Tables/wild_encounter_tables.c`, `src/wild_encounter.c` | defined, empty sentinel | Day-specific wild table headers. | Not read/written by UPR-FVX Standard/Fallback. | Medium if populated. | investigate later |
| `gWildMonEveningHeaders` | `src/Tables/wild_encounter_tables.c`, `src/wild_encounter.c` | defined, empty sentinel | Evening-specific wild table headers. | Not read/written by UPR-FVX Standard/Fallback. | Medium if populated. | investigate later |
| `gWildMonNightHeaders` | `src/Tables/wild_encounter_tables.c`, `src/wild_encounter.c` | defined, empty sentinel | Night-specific wild table headers. | Not read/written by UPR-FVX Standard/Fallback. | Medium if populated. | investigate later |
| `FIRERED_GEN9_ENABLE_ROUTE1_CUSTOM_WILD` | `src/Tables/wild_encounter_tables.c` | `0` | Local compile switch for custom Route 1 morning wild table example. | Currently off; not source of Route 1 Frigibax. | Low while off. | keep |
| `DEXNAV_POKEMON_MOVE_IN_CAVES_WATER` | `src/config.h`, `src/dexnav.c` | defined | DexNav overworld movement in caves/water. | DexNav is special-wild/outside current UPR-FVX scope. | Medium for DexNav testing. | investigate later |
| DexNav search chances | `include/new/dexnav_config.h` | defined numeric thresholds | Controls egg move, hidden ability, potential star chances by search level. | DexNav can surface special species/moves/abilities independent of Standard/Fallback tables. | Medium. | investigate later |
| Raid encounters | `src/Tables/raid_encounters.h`, `src/config.h` | tables present; `DYNAMAX_FEATURE` defined | Raid species/levels are table-driven special encounters. | Outside current UPR-FVX Wild Standard/Fallback scope. | Medium to high if used in walkthrough. | investigate later |

## Trainer/Battle Features

| Name | File | Current status/value | Meaning | Randomizer impact | Risk | Recommendation |
| --- | --- | --- | --- | --- | --- | --- |
| `EXPAND_TRAINERS` | `src/config.h`, `src/Tables/trainer_data.c`, `src/Tables/trainer_parties.h`, `repoints`, `src/build_pokemon.c` | defined | Enables expanded/editable trainer data. | Expected by current Trainer Pokemon core compatibility. | High if disabled. | keep |
| `TRAINERS_WITH_EVS` | `src/config.h`, `src/Tables/trainers_with_evs_table.h`, `src/build_pokemon.c` | defined | Enables trainer EV data hack. | UPR-FVX Trainer Pokemon core may preserve or interact with richer trainer data; changes difficulty. | Medium. | investigate later |
| `STANDARD_IV` | `src/config.h`, `src/build_pokemon.c` | `10` | Default IV value for random trainer-owned Pokemon. | Affects trainer difficulty independent of species randomization. | Low to medium. | keep |
| `FLAG_SCALE_TRAINER_LEVELS` | `src/config.h`, `src/build_pokemon.c` | `0x90E` | Runtime flag to scale trainer Pokemon levels to the highest party level. | Can conflict with UPR-FVX trainer level output and Ironmon-style expectations. | High if scripts set it. | investigate later |
| `OPEN_WORLD_TRAINERS` | `src/config.h`, `src/build_pokemon.c` | commented, warning says not to use with `EXPAND_TRAINERS` | Uses party-level based trainer teams. | Would bypass normal trainer table assumptions. | High. | keep disabled |
| `VAR_GAME_DIFFICULTY` | `src/config.h`, `src/build_pokemon.c` | `0x5157` | Difficulty var that affects trainer friendship, EVs, IVs, AI style, and other scaling decisions. | Can change trainer behavior even when species are randomized. | Medium. | investigate later |
| `WILD_ALWAYS_SMART` | `src/config.h`, `src/Battle_AI/ai_master.c`, `src/battle_controller_opponent.c` | defined | All wild Pokemon use smarter AI. | Changes randomizer run difficulty. | Medium. | investigate later |
| `OKAY_WITH_AI_SUICIDE` | `src/config.h` | defined | Allows AI to use self-KO moves. | Changes trainer/wild battle behavior. | Low to medium. | keep |
| `TEAM_PREVIEW_TRIGGER` / `FLAG_IN_BATTLE_TEAM_PREVIEW` | `src/config.h` | defined, `0xA00` | Adds team preview trigger. | QoL/difficulty information; can reveal randomized trainer teams. | Low. | keep |
| `ENCOUNTER_MUSIC_BY_CLASS` | `src/config.h` | defined | Trainer-spot music based on trainer class. | No species impact. | Low. | keep |
| `MEGA_EVOLUTION_FEATURE` | `src/config.h`, `src/mega.c`, `assembly/hooks/mega_hooks.s` | defined | Enables Mega Evolution systems. | Generally compatible but broad battle-system surface. | Medium. | keep |
| `DYNAMAX_FEATURE` | `src/config.h`, `src/dynamax.c`, `src/move_menu.c`, `src/Tables/battle_moves.c` | defined | Enables Dynamax and Raid Battles. | Raid/special battles are outside current randomizer evidence. | Medium to high for special encounter scope. | investigate later |
| `TERASTAL_FEATURE` | `src/config.h`, `src/terastallization.c`, `src/move_menu.c` | defined | Enables Terastallization. | Battle-system feature; not covered by current randomizer scope. | Medium. | investigate later |
| `FLAG_TERA_BATTLE` | `src/config.h` | `0xA08` | Enables Tera in a trainer battle command. | Script-gated battle feature independent of UPR-FVX trainer randomization. | Medium. | investigate later |
| `FLAG_DYNAMAX_BATTLE` / `FLAG_RAID_BATTLE` | `src/config.h`, `src/dynamax.c` | `0x918`, `0x919` | Runtime flags for Dynamax and raids. | Raids are special encounter scope, not Standard/Fallback wild. | Medium to high. | investigate later |

## Moves/TMs/Tutors

| Name | File | Current status/value | Meaning | Randomizer impact | Risk | Recommendation |
| --- | --- | --- | --- | --- | --- | --- |
| `EXPAND_MOVESETS` | `src/config.h`, `src/learn_move.c`, `src/Tables/level_up_learnsets.c`, `repoints` | defined | Uses expanded level-up learnsets through CFRU/DPE table handling. | Required for current Gen9 learnset and UPR-FVX moveset randomization compatibility. | High if disabled. | keep |
| `EXPANDED_TMSHMS` | `src/config.h`, `src/item.c`, `assembly/hooks/tmhm_hooks.s` | defined | Expands TM/HM count beyond vanilla 50/8. | UPR-FVX TM/HM support must match this expanded table shape. | High if changed without coordinated randomizer support. | keep |
| `EXPANDED_MOVE_TUTORS` | `src/config.h`, `src/learn_move.c`, `src/item.c`, `hooks` | defined | Expands move tutor count. | UPR-FVX tutor support depends on table shape and configured counts. | High if changed without coordinated randomizer support. | keep |
| `NUM_TMS` | `src/config.h` | `120` | Number of TMs. | Must match UPR-FVX TM writer expectations. | High if changed. | keep |
| `NUM_HMS` | `src/config.h` | `8` | Number of HMs. | Affects TM/HM compatibility table shape. | Medium. | keep |
| `NUM_MOVE_TUTORS` | `src/config.h` | `152` with note saying DPE should use `128` | Number of tutor moves. | Potential mismatch risk with DPE/randomizer expectations; requires confirmation before tutor randomization scope. | High. | investigate later |
| `LAST_TOTAL_TUTOR_NUM` | `src/config.h` | `161` | Should equal `NUM_MOVE_TUTORS - 1 + 9`. | Build/runtime table arithmetic risk if inconsistent. | High. | investigate later |
| `DELETABLE_HMS` | `src/config.h` | defined | Allows deleting HMs without Move Deleter. | QoL, no direct species impact. | Low. | keep |
| `REUSABLE_TMS` | `src/config.h` | defined | TMs are reusable if item metadata is configured correctly. | Randomized TM output remains reusable. | Low to medium if item metadata mismatches. | keep |
| `TMS_BEFORE_HMS` | `src/config.h` | commented | Changes TM/HM bag order. | UI/order only; could confuse assumptions if tools expect order. | Low. | keep disabled |
| `FLAG_MOVE_RELEARNER_IGNORE_LEVEL` | `src/config.h`, `src/learn_move.c` | `0x916` | Move relearner shows all level-up moves to `MAX_LEVEL` when flag is set. | Can expose randomized future moves earlier. | Medium. | investigate later |
| `FLAG_EGG_MOVE_RELEARNER` | `src/config.h`, `src/learn_move.c` | `0x917` | Move relearner loads egg moves when flag is set. | Egg moves are separate randomizer scope. | Medium. | investigate later |
| `EXPAND_MOVE_REMINDER_DESCRIPTION` | `src/config.h`, `src/learn_move.c` | defined | Five-line move reminder descriptions. | UI-only for learn move path. | Low. | keep |
| `FATHER_PASSES_TMS` | `src/config.h` | defined | Fathers can pass known TMs through breeding. | Breeding move inheritance may reflect randomized TMs. | Low to medium. | investigate later |

## Save/Engine Critical Features

| Name | File | Current status/value | Meaning | Randomizer impact | Risk | Recommendation |
| --- | --- | --- | --- | --- | --- | --- |
| `SAVE_BLOCK_EXPANSION` | `src/config.h`, `hooks`, `src/save.c`, `src/scripting.c`, `src/read_keys.c` | defined | Enables expanded save-block storage and related hooks. Comment warns disabling requires manual hook removal and breaks features. | Engine-critical. Randomizer compatibility assumes current build layout. | Very high if changed. | do not touch |
| `EVOS_PER_MON` | `src/config.h` | `16` | Max evolutions per species; note says DPE has 16. | UPR-FVX evolution parsing/writing expects expanded DPE shape. | High. | keep |
| `KANTO_DEX_COUNT` / `NATIONAL_DEX_COUNT` | `src/config.h` | `151`, `1025` | Dex count constants. | Impacts Pokedex limits and Gen9 availability. | High if changed. | keep |
| `MAX_LEVEL` | `src/config.h`, `asm_defines.s` | `100` in both | Max Pokemon level; comment says keep ASM in sync. | Level randomization/scaling depends on consistent max. | High if mismatched. | keep |
| `EV_CAP` | `src/config.h`, `asm_defines.s` | `252` in both | EV cap; comment says keep ASM in sync. | Trainer EV behavior and stat math. | Medium. | keep |
| `EXPANDED_TEXT_BUFFERS` | `src/config.h`, `repoints` | defined | Expands scripting string buffers. | Supports broader scripting/UI text. | Medium if disabled. | keep |
| `EXPANDED_NEW_ITEMS` | `src/config.h`, `src/item.c`, `src/Tables/item_tables.c` | defined | Expands items table and adds new items through Gen9. | Item randomization and held-item pools depend on expanded IDs. | High if changed. | keep |
| `PALETTE_SWAPPER` | `src/config.h`, `assembly/hooks`, `src/dynamic_ow_pals.c` | defined | Dynamic overworld palette system. | Not directly UPR-FVX, but tied to sprite/palette compatibility. | Medium. | keep |
| `NEW_BATTLE_BACKGROUNDS` | `src/config.h`, `src/Tables/battle_background_tables.c`, `src/battle_terrain.c` | defined | Dynamic battle background tables. | Visual/battle intro behavior; not species randomization. | Medium. | keep |
| `repoints` | `repoints` | active pointer manifest | Repoints core tables including `gLevelUpLearnsets`, `gTrainers`, trainer class names, experience, text, item and type tables. | Randomizer compatibility depends on where tables are repointed and how UPR-FVX locates/writes them. | High. | do not touch |
| `repointall` | `repointall` | active pointer-all manifest | Repoints tables such as `gBattleMoves`, move names, abilities, item data, and movement tables. | Broad engine table layout impact. | High. | do not touch |
| `hooks` | `hooks`, `assembly/hooks/*` | active hook manifest | Installs save, item, trainer, tutor, prebattle, palette, Mega, PC, and other hooks. | Broad runtime behavior; changing hooks can invalidate current compatibility baseline. | High. | do not touch |

## QoL Features

| Name | File | Current status/value | Meaning | Randomizer impact | Risk | Recommendation |
| --- | --- | --- | --- | --- | --- | --- |
| `FLAG_EXP_SHARE` | `src/config.h` | `0x906` | Runtime flag for Gen6+ Exp Share. | Difficulty/progression impact only. | Low to medium. | keep |
| `FLAG_AUTO_RUN` | `src/config.h` | `0x914` | Enables auto-run by L button; note says L=A will not work if used. | QoL input behavior. | Low. | keep |
| `FLAG_RUNNING_ENABLED` | `src/config.h` | `0x82F` | Running requires this flag; if commented, running shoes from start. | Progression/QoL. | Low. | keep |
| `BW_REPEL_SYSTEM` | `src/config.h` | defined | Prompt to reuse repel when it expires. | QoL only. | Low. | keep |
| `AUTO_NAMING_SCREEN_SWAP` | `src/config.h` | defined | Naming screens auto-swap to lower-case. | QoL only. | Low. | keep |
| `CAN_RUN_IN_BUILDINGS` | `src/config.h` | defined | Allows running indoors. | QoL only. | Low. | keep |
| `SELECT_FROM_PC` | `src/config.h`, `hooks`, `src/scripting.c` | defined | Select-from-PC hack. | QoL/storage behavior, not randomization. | Medium due hooks. | keep |
| `FLAG_FOLLOWER_POKEMON` | `src/config.h`, `src/follow_me.c`, `src/follower_mon.c` | `0x4BD` | Enables follower Pokemon behavior. | Sprite/palette stress path; Ogerpon assets now fixed but broad Gen9 follower scope is not UPR-FVX proof. | Medium. | investigate later |
| `POISON_1_HP_SURVIVAL` | `src/config.h` | defined | Poison leaves Pokemon at 1 HP in overworld. | QoL/progression. | Low. | keep |
| `FR_PRE_BATTLE_MUGSHOT_STYLE` | `src/config.h` | defined | FR Elite Four/Champion mugshot style. | Visual only. | Low. | keep |
| `TEAM_PREVIEW_TRIGGER` | `src/config.h` | defined | L-trigger team preview. | Can reveal randomized teams but does not break them. | Low. | keep |
| `LAST_USED_BALL_TRIGGER` | `src/config.h` | defined | L-trigger last-used ball. | QoL only. | Low. | keep |
| `TAKE_WILD_MON_ITEM_ON_CAPTURE` | `src/config.h` | defined | Captured wild held items may be placed in bag. | Interacts with randomized held items if enabled later. | Low to medium. | keep |
| `FLAG_NUZLOCKE`, `FLAG_HARD_LEVEL_CAP`, `FLAG_KEPT_LEVEL_CAP_ON` | `src/config.h` | defined runtime flags | Optional challenge-mode runtime flags. | Can strongly change walkthrough rules if scripts set them. | Medium. | investigate later |

## Randomizer-Related Flags

| Name | File | Current status/value | Meaning | Randomizer impact | Risk | Recommendation |
| --- | --- | --- | --- | --- | --- | --- |
| `FLAG_POKEMON_RANDOMIZER` | `src/config.h`, `src/build_pokemon.c` | `0x940` | CFRU runtime species randomizer flag. | Do not mix with UPR-FVX ROM-level species randomization for normal walkthrough unless intentionally testing stacked behavior. | High. | disable for randomizer run |
| `FLAG_POKEMON_LEARNSET_RANDOMIZER` | `src/config.h`, `src/build_pokemon.c` | `0x941` | CFRU runtime learnset randomizer flag. | Can conflict with UPR-FVX Pokemon Movesets Random completely output. | High. | disable for randomizer run |
| `FLAG_ABILITY_RANDOMIZER` | `src/config.h` | `0x942` | CFRU runtime ability randomizer flag. | Can conflict with UPR-FVX ability randomization if used later. | High. | disable for randomizer run |
| `NUM_SPECIES_RANDOMIZER` | `src/config.h` | `NUM_SPECIES` | Runtime randomizer species range. | Matters only when CFRU runtime species randomizer flag is set. | Medium. | keep |
| `FLAG_TEMP_DISABLE_RANDOMIZER` | `src/build_pokemon.c` reference only | not defined in reviewed `src/config.h` | Conditional hook used in trainer growth logic if defined. | No current effect unless defined elsewhere. | Low. | keep disabled |
| `FLAG_SCALE_WILD_POKEMON_LEVELS` | `src/config.h`, `src/wild_encounter.c` | `0x90D` | Runtime wild level scaling. | Can override randomizer-selected wild levels. | Medium to high. | investigate later |
| `FLAG_SCALE_TRAINER_LEVELS` | `src/config.h`, `src/build_pokemon.c` | `0x90E` | Runtime trainer level scaling. | Can override randomizer-selected trainer levels. | Medium to high. | investigate later |
| `FLAG_HIDDEN_ABILITY` | `src/config.h`, `src/build_pokemon.c` | `0x90F` | Generated wild/gift Pokemon use hidden ability when set. | Can alter ability assumptions. | Medium. | investigate later |
| `FLAG_GIGANTAMAXABLE` | `src/config.h`, `src/build_pokemon.c` | `0x928` | Generated wild/gift Pokemon get Gigantamax bit. | Dynamax/Gigantamax outside current randomizer scope. | Medium. | investigate later |

## Features/Settings Outside `config.h`

| Name | File | Current status/value | Meaning | Randomizer impact | Risk | Recommendation |
| --- | --- | --- | --- | --- | --- | --- |
| DexNav config | `include/new/dexnav_config.h` | active numeric thresholds | Search timeout, proximity, egg move chance, hidden ability chance, and potential star chance tables. | DexNav can generate encounters and metadata outside UPR-FVX Standard/Fallback. | Medium. | investigate later |
| `gSwarmTable` Route 1 Frigibax | `src/Tables/wild_encounter_tables.c` | active entry | Route 1 swarm species is `SPECIES_FRIGIBAX`. | Current cause candidate for Route 1 Frigibax after UPR-FVX Standard/Fallback randomization. | High. | disable for randomizer run |
| Day/Night header tables | `src/Tables/wild_encounter_tables.c` | defined, currently empty sentinel in default branch path | Time-specific wild headers. | UPR-FVX does not read/write them yet. | Medium if populated. | investigate later |
| Level-up learnset table | `src/Tables/level_up_learnsets.c` | active `gLevelUpLearnsets` | Gen9 level-up learnset data. | UPR-FVX Learnsets path depends on valid expanded table and runtime pointer. | High. | keep |
| Trainer tables | `src/Tables/trainer_data.c`, `src/Tables/trainer_parties.h`, `src/Tables/trainers_with_evs_table.h` | active with `EXPAND_TRAINERS` and `TRAINERS_WITH_EVS` | Trainer metadata, parties, and EV extension data. | Current Trainer Pokemon core scope depends on preserving table shape. | High. | keep |
| Battle move table | `src/Tables/battle_moves.c` | active with Dynamax conditionals | Move definitions and special move forms. | Move randomization support later must preserve table format and special move IDs. | Medium. | keep |
| Item tables | `src/Tables/item_tables.c`, `src/item.c` | active with expanded items/TMs/tutors | Item definitions and TM/tutor item behavior. | Items/Moves/Abilities randomizer scope must match expanded item IDs. | Medium to high. | investigate later |
| Raid encounter tables | `src/Tables/raid_encounters.h` | active source table | Raid species/levels by map section. | Special-wild encounter source not covered by Standard/Fallback. | Medium. | investigate later |
| `asm_defines.s` mirrored constants | `asm_defines.s` | `MAX_LEVEL 100`, `EV_CAP 252` | ASM constants that must stay in sync with `src/config.h`. | Desync can create runtime stat/level inconsistencies. | High. | do not touch without paired update |
| `repoints` manifest | `repoints` | active | Source of table pointer repoints. | UPR-FVX compatibility depends on stable repointed table locations and generated pointer artifacts. | High. | do not touch |
| `repointall` manifest | `repointall` | active | Repoints all pointers found at specified locations. | Broad engine pointer rewrite behavior. | High. | do not touch |
| `hooks` and `assembly/hooks/*` | `hooks`, `assembly/hooks` | active | Hook installation for expanded save, items, trainers, tutors, prebattle, palettes, Mega, PC, and other systems. | Changing hooks is not a documentation-only randomizer scope. | High. | do not touch |

## Normal Randomizer Walkthrough Defaults

Recommended for the current normal UPR-FVX walkthrough:

- Keep `EXPAND_MOVESETS`, `EXPANDED_TMSHMS`, `EXPANDED_MOVE_TUTORS`, `SAVE_BLOCK_EXPANSION`, `EXPAND_TRAINERS`, `MEGA_EVOLUTION_FEATURE`, `TERASTAL_FEATURE`, and `DYNAMAX_FEATURE` as-is until each has a targeted support decision.
- Do not enable CFRU runtime randomizer flags (`FLAG_POKEMON_RANDOMIZER`, `FLAG_POKEMON_LEARNSET_RANDOMIZER`, `FLAG_ABILITY_RANDOMIZER`) during normal UPR-FVX-randomized runs.
- Disable or neutralize swarms for normal randomized runs because `gSwarmTable` currently contains Route 1 `SPECIES_FRIGIBAX` and UPR-FVX does not randomize that table.
- Treat Day/Night headers, DexNav, raids, double wild battles, and other special-wild systems as separate later scopes.
- Do not touch `SAVE_BLOCK_EXPANSION`, `repoints`, `repointall`, or hook manifests without a dedicated engine migration plan.
