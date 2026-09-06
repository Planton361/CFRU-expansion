#!/usr/bin/env python3
"""Fail-closed source-table checks for M-004 renewable hidden items."""

from pathlib import Path
import re


SOURCE = Path(__file__).resolve().parents[1] / "src" / "renewable_hidden_items.c"

EXPECTED_GROUPS = {
    "MAP_ROUTE_20": "FALSE",
    "MAP_ROUTE_21_A": "FALSE",
    "MAP_UNDERGROUND_PATH_NORTH_SOUTH_TUNNEL": "TRUE",
    "MAP_UNDERGROUND_PATH_EAST_WEST_TUNNEL": "TRUE",
    "MAP_SEVEN_ISLAND_TANOBY_RUINS": "TRUE",
    "MAP_MT_MOON_B1F": "FALSE",
    "MAP_THREE_ISLAND_BERRY_FOREST": "TRUE",
    "MAP_ONE_ISLAND_TREASURE_BEACH": "TRUE",
    "MAP_THREE_ISLAND_BOND_BRIDGE": "TRUE",
    "MAP_FOUR_ISLAND": "TRUE",
    "MAP_FIVE_ISLAND_MEMORIAL_PILLAR": "TRUE",
    "MAP_FIVE_ISLAND_RESORT_GORGEOUS": "TRUE",
    "MAP_SIX_ISLAND_OUTCAST_ISLAND": "TRUE",
    "MAP_SIX_ISLAND_GREEN_PATH": "TRUE",
    "MAP_SEVEN_ISLAND_TRAINER_TOWER": "TRUE",
}

EXPECTED_TIERS = {
    "sRoute20Uncommon": ["HIDDEN_ITEM_ROUTE20_STARDUST"],
    "sRoute21NorthUncommon": ["HIDDEN_ITEM_ROUTE21_NORTH_PEARL"],
    "sUndergroundNorthSouthRare": ["HIDDEN_ITEM_UNDERGROUND_PATH_NORTH_SOUTH_TUNNEL_ETHER"],
    "sUndergroundNorthSouthUncommon": [
        "HIDDEN_ITEM_UNDERGROUND_PATH_NORTH_SOUTH_TUNNEL_POTION",
        "HIDDEN_ITEM_UNDERGROUND_PATH_NORTH_SOUTH_TUNNEL_ANTIDOTE",
        "HIDDEN_ITEM_UNDERGROUND_PATH_NORTH_SOUTH_TUNNEL_PARALYZE_HEAL",
        "HIDDEN_ITEM_UNDERGROUND_PATH_NORTH_SOUTH_TUNNEL_AWAKENING",
        "HIDDEN_ITEM_UNDERGROUND_PATH_NORTH_SOUTH_TUNNEL_BURN_HEAL",
        "HIDDEN_ITEM_UNDERGROUND_PATH_NORTH_SOUTH_TUNNEL_ICE_HEAL",
    ],
    "sUndergroundEastWestRare": ["HIDDEN_ITEM_UNDERGROUND_PATH_EAST_WEST_TUNNEL_ETHER"],
    "sUndergroundEastWestUncommon": [
        "HIDDEN_ITEM_UNDERGROUND_PATH_EAST_WEST_TUNNEL_POTION",
        "HIDDEN_ITEM_UNDERGROUND_PATH_EAST_WEST_TUNNEL_ANTIDOTE",
        "HIDDEN_ITEM_UNDERGROUND_PATH_EAST_WEST_TUNNEL_PARALYZE_HEAL",
        "HIDDEN_ITEM_UNDERGROUND_PATH_EAST_WEST_TUNNEL_AWAKENING",
        "HIDDEN_ITEM_UNDERGROUND_PATH_EAST_WEST_TUNNEL_BURN_HEAL",
        "HIDDEN_ITEM_UNDERGROUND_PATH_EAST_WEST_TUNNEL_ICE_HEAL",
    ],
    "sTanobyRuinsRare": [
        "HIDDEN_ITEM_SEVEN_ISLAND_TANOBY_RUINS_HEART_SCALE_4",
        "HIDDEN_ITEM_SEVEN_ISLAND_TANOBY_RUINS_HEART_SCALE",
        "HIDDEN_ITEM_SEVEN_ISLAND_TANOBY_RUINS_HEART_SCALE_2",
        "HIDDEN_ITEM_SEVEN_ISLAND_TANOBY_RUINS_HEART_SCALE_3",
    ],
    "sMtMoonRare": [
        "HIDDEN_ITEM_MT_MOON_B1F_TINY_MUSHROOM",
        "HIDDEN_ITEM_MT_MOON_B1F_TINY_MUSHROOM_2",
        "HIDDEN_ITEM_MT_MOON_B1F_TINY_MUSHROOM_3",
        "HIDDEN_ITEM_MT_MOON_B1F_BIG_MUSHROOM",
        "HIDDEN_ITEM_MT_MOON_B1F_BIG_MUSHROOM_2",
        "HIDDEN_ITEM_MT_MOON_B1F_BIG_MUSHROOM_3",
    ],
    "sMtMoonUncommon": [
        "HIDDEN_ITEM_MT_MOON_B1F_TINY_MUSHROOM",
        "HIDDEN_ITEM_MT_MOON_B1F_TINY_MUSHROOM_2",
        "HIDDEN_ITEM_MT_MOON_B1F_TINY_MUSHROOM_3",
    ],
    "sBerryForestRare": [
        "HIDDEN_ITEM_THREE_ISLAND_BERRY_FOREST_BLUK_BERRY",
        "HIDDEN_ITEM_THREE_ISLAND_BERRY_FOREST_WEPEAR_BERRY",
        "HIDDEN_ITEM_THREE_ISLAND_BERRY_FOREST_ORAN_BERRY",
        "HIDDEN_ITEM_THREE_ISLAND_BERRY_FOREST_CHERI_BERRY",
        "HIDDEN_ITEM_THREE_ISLAND_BERRY_FOREST_ASPEAR_BERRY",
        "HIDDEN_ITEM_THREE_ISLAND_BERRY_FOREST_PERSIM_BERRY",
        "HIDDEN_ITEM_THREE_ISLAND_BERRY_FOREST_PINAP_BERRY",
        "HIDDEN_ITEM_THREE_ISLAND_BERRY_FOREST_LUM_BERRY",
    ],
    "sBerryForestUncommon": [
        "HIDDEN_ITEM_THREE_ISLAND_BERRY_FOREST_BLUK_BERRY",
        "HIDDEN_ITEM_THREE_ISLAND_BERRY_FOREST_WEPEAR_BERRY",
        "HIDDEN_ITEM_THREE_ISLAND_BERRY_FOREST_ORAN_BERRY",
        "HIDDEN_ITEM_THREE_ISLAND_BERRY_FOREST_CHERI_BERRY",
        "HIDDEN_ITEM_THREE_ISLAND_BERRY_FOREST_ASPEAR_BERRY",
        "HIDDEN_ITEM_THREE_ISLAND_BERRY_FOREST_PERSIM_BERRY",
        "HIDDEN_ITEM_THREE_ISLAND_BERRY_FOREST_PINAP_BERRY",
    ],
    "sBerryForestCommon": [
        "HIDDEN_ITEM_THREE_ISLAND_BERRY_FOREST_RAZZ_BERRY",
        "HIDDEN_ITEM_THREE_ISLAND_BERRY_FOREST_NANAB_BERRY",
        "HIDDEN_ITEM_THREE_ISLAND_BERRY_FOREST_CHESTO_BERRY",
        "HIDDEN_ITEM_THREE_ISLAND_BERRY_FOREST_PECHA_BERRY",
        "HIDDEN_ITEM_THREE_ISLAND_BERRY_FOREST_RAWST_BERRY",
    ],
    "sTreasureBeachRare": [
        "HIDDEN_ITEM_ONE_ISLAND_TREASURE_BEACH_ULTRA_BALL",
        "HIDDEN_ITEM_ONE_ISLAND_TREASURE_BEACH_ULTRA_BALL_2",
        "HIDDEN_ITEM_ONE_ISLAND_TREASURE_BEACH_STAR_PIECE",
        "HIDDEN_ITEM_ONE_ISLAND_TREASURE_BEACH_BIG_PEARL",
    ],
    "sTreasureBeachUncommon": [
        "HIDDEN_ITEM_ONE_ISLAND_TREASURE_BEACH_STARDUST",
        "HIDDEN_ITEM_ONE_ISLAND_TREASURE_BEACH_STARDUST_2",
        "HIDDEN_ITEM_ONE_ISLAND_TREASURE_BEACH_PEARL",
        "HIDDEN_ITEM_ONE_ISLAND_TREASURE_BEACH_PEARL_2",
        "HIDDEN_ITEM_ONE_ISLAND_TREASURE_BEACH_ULTRA_BALL",
        "HIDDEN_ITEM_ONE_ISLAND_TREASURE_BEACH_ULTRA_BALL_2",
    ],
    "sTreasureBeachCommon": [
        "HIDDEN_ITEM_ONE_ISLAND_TREASURE_BEACH_ULTRA_BALL",
        "HIDDEN_ITEM_ONE_ISLAND_TREASURE_BEACH_ULTRA_BALL_2",
    ],
    "sBondBridgeUncommon": [
        "HIDDEN_ITEM_THREE_ISLAND_BOND_BRIDGE_PEARL",
        "HIDDEN_ITEM_THREE_ISLAND_BOND_BRIDGE_STARDUST",
    ],
    "sFourIslandUncommon": ["HIDDEN_ITEM_FOUR_ISLAND_PEARL"],
    "sFourIslandCommon": ["HIDDEN_ITEM_FOUR_ISLAND_ULTRA_BALL"],
    "sMemorialPillarRare": ["HIDDEN_ITEM_FIVE_ISLAND_MEMORIAL_PILLAR_BIG_PEARL"],
    "sResortGorgeousRare": [
        "HIDDEN_ITEM_FIVE_ISLAND_RESORT_GORGEOUS_NEST_BALL",
        "HIDDEN_ITEM_FIVE_ISLAND_RESORT_GORGEOUS_STAR_PIECE",
    ],
    "sResortGorgeousUncommon": [
        "HIDDEN_ITEM_FIVE_ISLAND_RESORT_GORGEOUS_STARDUST",
        "HIDDEN_ITEM_FIVE_ISLAND_RESORT_GORGEOUS_STARDUST_2",
    ],
    "sOutcastIslandRare": [
        "HIDDEN_ITEM_SIX_ISLAND_OUTCAST_ISLAND_STAR_PIECE",
        "HIDDEN_ITEM_SIX_ISLAND_OUTCAST_ISLAND_NET_BALL",
    ],
    "sGreenPathCommon": ["HIDDEN_ITEM_SIX_ISLAND_GREEN_PATH_ULTRA_BALL"],
    "sTrainerTowerRare": ["HIDDEN_ITEM_SEVEN_ISLAND_TRAINER_TOWER_BIG_PEARL"],
    "sTrainerTowerUncommon": ["HIDDEN_ITEM_SEVEN_ISLAND_TRAINER_TOWER_PEARL"],
}

EXPECTED_GROUP_TIERS = {
    "MAP_ROUTE_20": ("sNoRenewableItems", "sRoute20Uncommon", "sNoRenewableItems"),
    "MAP_ROUTE_21_A": ("sNoRenewableItems", "sRoute21NorthUncommon", "sNoRenewableItems"),
    "MAP_UNDERGROUND_PATH_NORTH_SOUTH_TUNNEL": ("sUndergroundNorthSouthRare", "sUndergroundNorthSouthUncommon", "sNoRenewableItems"),
    "MAP_UNDERGROUND_PATH_EAST_WEST_TUNNEL": ("sUndergroundEastWestRare", "sUndergroundEastWestUncommon", "sNoRenewableItems"),
    "MAP_SEVEN_ISLAND_TANOBY_RUINS": ("sTanobyRuinsRare", "sNoRenewableItems", "sNoRenewableItems"),
    "MAP_MT_MOON_B1F": ("sMtMoonRare", "sMtMoonUncommon", "sNoRenewableItems"),
    "MAP_THREE_ISLAND_BERRY_FOREST": ("sBerryForestRare", "sBerryForestUncommon", "sBerryForestCommon"),
    "MAP_ONE_ISLAND_TREASURE_BEACH": ("sTreasureBeachRare", "sTreasureBeachUncommon", "sTreasureBeachCommon"),
    "MAP_THREE_ISLAND_BOND_BRIDGE": ("sNoRenewableItems", "sBondBridgeUncommon", "sNoRenewableItems"),
    "MAP_FOUR_ISLAND": ("sNoRenewableItems", "sFourIslandUncommon", "sFourIslandCommon"),
    "MAP_FIVE_ISLAND_MEMORIAL_PILLAR": ("sMemorialPillarRare", "sNoRenewableItems", "sNoRenewableItems"),
    "MAP_FIVE_ISLAND_RESORT_GORGEOUS": ("sResortGorgeousRare", "sResortGorgeousUncommon", "sNoRenewableItems"),
    "MAP_SIX_ISLAND_OUTCAST_ISLAND": ("sOutcastIslandRare", "sNoRenewableItems", "sNoRenewableItems"),
    "MAP_SIX_ISLAND_GREEN_PATH": ("sNoRenewableItems", "sNoRenewableItems", "sGreenPathCommon"),
    "MAP_SEVEN_ISLAND_TRAINER_TOWER": ("sTrainerTowerRare", "sTrainerTowerUncommon", "sNoRenewableItems"),
}


def main() -> None:
    source = SOURCE.read_text(encoding="utf-8")

    for map_name, guaranteed in EXPECTED_GROUPS.items():
        row = "{ " + map_name + ", " + guaranteed + ","
        if source.count(row) != 1:
            raise SystemExit("expected exactly one table row: " + row)

    if source.count("{ MAP_") != len(EXPECTED_GROUPS):
        raise SystemExit("renewable table contains an unexpected map group")

    for tier_name, expected_flags in EXPECTED_TIERS.items():
        match = re.search(
            r"static const u8 " + tier_name + r"\[\] = \{(.*?)\};",
            source,
            flags=re.DOTALL,
        )
        if match is None:
            raise SystemExit("missing tier: " + tier_name)
        actual_flags = re.findall(r"HIDDEN_ITEM_[A-Z0-9_]+", match.group(1))
        if actual_flags != expected_flags:
            raise SystemExit("unexpected flags in " + tier_name)

    for map_name, expected_tiers in EXPECTED_GROUP_TIERS.items():
        match = re.search(
            r"\{ " + map_name + r", (?:TRUE|FALSE), \{ ([^}]*) \} \}",
            source,
        )
        if match is None:
            raise SystemExit("missing group tiers for " + map_name)
        actual_tiers = tuple(re.findall(r"s[A-Za-z0-9_]+", match.group(1)))
        if actual_tiers != expected_tiers:
            raise SystemExit("unexpected tiers for " + map_name)

    required_fragments = (
        "#define RENEWABLE_ITEM_STEP_LIMIT 1500",
        "VarSet(VAR_RENEWABLE_ITEM_STEP_COUNTER, 0);",
        "u16 randomValue = Random() % 100;",
        "if (group->guaranteeItem && flags[0] == NO_RENEWABLE_ITEM)",
        "flags = GetFirstPopulatedTier(group);",
    )
    for fragment in required_fragments:
        if fragment not in source:
            raise SystemExit("missing required source behavior: " + fragment)

    print("Renewable hidden item source-table check passed.")


if __name__ == "__main__":
    main()
