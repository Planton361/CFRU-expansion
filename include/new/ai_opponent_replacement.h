#pragma once

#include "../pokemon.h"
#include "../constants/species.h"

static inline bool8 OpponentReplacementIndexIsUsable(
	const struct Pokemon* party, const struct Pokemon* expectedParty,
	u8 firstPartyId, u8 lastPartyId,
	u8 candidateId, u8 firstActiveId, u8 secondActiveId)
{
	if (party == 0 || party != expectedParty || firstPartyId >= lastPartyId
		|| lastPartyId > PARTY_SIZE
		|| candidateId < firstPartyId || candidateId >= lastPartyId
		|| candidateId >= PARTY_SIZE
		|| candidateId == firstActiveId || candidateId == secondActiveId)
		return FALSE;

	return party[candidateId].species != SPECIES_NONE
		&& party[candidateId].species != SPECIES_EGG
		&& party[candidateId].hp != 0
		&& !party[candidateId].isEgg;
}

static inline u8 OpponentReplacementFindFirstUsable(
	const struct Pokemon* party, const struct Pokemon* expectedParty,
	u8 firstPartyId, u8 lastPartyId,
	u8 firstActiveId, u8 secondActiveId)
{
	u8 candidateId;

	if (party == 0 || party != expectedParty || firstPartyId >= lastPartyId
		|| lastPartyId > PARTY_SIZE)
		return PARTY_SIZE;

	for (candidateId = firstPartyId; candidateId < lastPartyId; ++candidateId)
		if (OpponentReplacementIndexIsUsable(party, expectedParty, firstPartyId, lastPartyId,
			candidateId, firstActiveId, secondActiveId))
			return candidateId;

	return PARTY_SIZE;
}
