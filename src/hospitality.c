#include "defines.h"
#include "defines_battle.h"
#include "../include/new/hospitality.h"
#include "../include/new/battle_util.h"
#include "../include/new/battle_script_util.h"
#include "../include/new/dynamax.h"
#include "../include/new/util.h"

extern const u8 BattleScript_Hospitality[];

// The byte is shared, not the effect: only these forms implement Hospitality.
bool8 SpeciesHasHospitality(u16 species)
{
	return species == SPECIES_SINISTCHA || species == SPECIES_SINISTCHA_MASTERPIECE;
}

// Called only by entry state machines, after ordinary switch-in abilities.
// Each caller advances its cursor before yielding to the healing script.
bool8 TryActivateHospitality(u8 bank)
{
	u8 partner;
	u16 healing;

	if (!IS_DOUBLE_BATTLE || bank >= gBattlersCount
	|| (gAbsentBattlerFlags & gBitTable[bank]) || !BATTLER_ALIVE(bank)
	|| !SpeciesHasHospitality(SPECIES(bank)) || ABILITY(bank) != ABILITY_HOSPITALITY)
		return FALSE;

	partner = PARTNER(bank);
	if (partner >= gBattlersCount || (gAbsentBattlerFlags & gBitTable[partner])
	|| !BATTLER_ALIVE(partner) || BATTLER_MAX_HP(partner) || IsHealBlocked(partner))
		return FALSE;

	healing = MathMax(1, GetBaseMaxHP(partner) / 4);
	healing = MathMin(healing, gBattleMons[partner].maxHP - gBattleMons[partner].hp);
	gBattleMoveDamage = -((s32) healing);
	gBattleScripting.bank = bank;
	gBankTarget = partner;
	gLastUsedAbility = ABILITY_HOSPITALITY;
	BattleScriptPushCursorAndCallback(BattleScript_Hospitality);
	return TRUE;
}
