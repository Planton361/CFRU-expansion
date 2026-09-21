#include "../../include/new/ai_standard_mechanics.h"

static uint32_t Min(uint32_t a, uint32_t b) { return a < b ? a : b; }
static uint32_t Max(uint32_t a, uint32_t b) { return a > b ? a : b; }

uint32_t StandardMechanicsStage(uint32_t value, uint8_t stage)
{
	if (stage > 12) stage = 12;
	return Max(1, stage >= 6 ? value * (stage - 4) / 2 : value * 2 / (8 - stage));
}

uint32_t StandardMechanicsSpeed(uint16_t base, uint8_t level, uint8_t stage, uint8_t high)
{
	uint32_t value = ((2 * base + (high ? 94 : 0)) * level / 100 + 5);
	return StandardMechanicsStage(value * (high ? 110 : 90) / 100, stage);
}

/* build_pokemon.c CALC_STAT: IV 0..31, EV/4 0..63, nature 90..110%. */
static uint32_t Defense(const struct StandardMechanicsInput* s, uint8_t high)
{
	if (s->known_defense) return StandardMechanicsStage(s->known_defense, s->defense_stage);
	uint32_t value = ((2 * s->base_defense + (high ? 94 : 0)) * s->target_level / 100 + 5);
	value = value * (high ? 110 : 90) / 100;
	return StandardMechanicsStage(value, s->defense_stage);
}

/* damage_calc.c CalculateBaseDamage, neutral ordinary single-hit subset.
 * Keep the engine's integer division order; never call its global/RNG graph. */
static uint32_t Damage(const struct StandardMechanicsInput* s, uint32_t defense, uint8_t roll)
{
	/* Validated below: level<=100, power<=150, raw attack<=2048, stage<=12.
	 * Maximum initial product = 42*150*8192 = 51,609,600. At defense=1,
	 * after /50+2, STAB and three 2x factors, the largest roll numerator
	 * is 1,238,632,800. Every intermediate fits uint32 without reordering. */
	uint32_t d = ((2 * s->level / 5 + 2) * (uint32_t)s->power
		* StandardMechanicsStage(s->attack, s->attack_stage) / Max(1, defense)) / 50 + 2;
	unsigned i;
	if (s->own_burn) d /= 2;
	if (s->stab) d = d * 15 / 10;
	for (i = 0; i < 3; ++i) d = d * s->effectiveness[i] / 10;
	d = d * roll / 100;
	return d > 65535 ? 65535 : Max(1, (uint32_t)d);
}

void StandardMechanicsDamage(const struct StandardMechanicsInput* s,
	struct StandardPolicyCandidate* c, struct StandardDamageEnvelope* e)
{
	uint32_t dmin, dmax, estimate, accuracy, hp_estimate, maxhp;
	struct StandardMechanicsInput critical = *s;
	unsigned i;
	/* Clear padding too: deterministic bytewise host/adapter evidence. */
	for (i = 0; i < sizeof(*e); ++i) ((uint8_t*)e)[i] = 0;
	c->expected_damage = c->opponent_hp_fraction_lost = c->net_faints = c->robust_safe_ko = 0;
	c->survival_to_act = s->can_act_safely;
	c->productive = c->unknown_potentially_productive = 0;
	if (s->known_immunity)
	{
		c->known_no_effect = 1;
		c->productive = 0;
		return;
	}
	if (!s->supported_damage || !s->power || s->power > 150
		|| !s->level || s->level > 100 || !s->target_level || s->target_level > 100
		|| s->attack > 2048 || s->base_defense > 255 || s->base_hp > 255
		|| s->attack_stage > 12 || s->defense_stage > 12
		|| s->accuracy > 100 || s->accuracy_stage > 12 || s->evasion_stage > 12
		|| s->effectiveness[0] > 20 || s->effectiveness[1] > 20 || s->effectiveness[2] > 20)
	{
		e->uncertain = 1;
		e->maximum = 65535;
		c->unknown_potentially_productive = 1;
		return; /* Unsupported effects receive no invented positive value. */
	}
	e->max_hp_minimum = s->shedinja ? 1 : 2 * s->base_hp * s->target_level / 100 + s->target_level + 10;
	e->max_hp_maximum = s->shedinja ? 1 : (2 * s->base_hp + 94) * s->target_level / 100 + s->target_level + 10;
	/* Quantized display interval, including the minimum one-pixel convention. */
	if (s->hp_pixels <= 48)
	{
		e->hp_minimum = s->hp_pixels <= 1 ? 1 : Max(1, e->max_hp_minimum * s->hp_pixels / 48);
		e->hp_maximum = Min(e->max_hp_maximum, (e->max_hp_maximum * (s->hp_pixels + 1) + 47) / 48);
	}
	else
	{
		e->hp_minimum = 1;
		e->hp_maximum = e->max_hp_maximum;
	}
	if (s->known_max_hp)
	{
		e->max_hp_minimum = e->max_hp_maximum = s->known_max_hp;
		e->hp_minimum = e->hp_maximum = s->known_hp;
	}
	dmin = Damage(s, Defense(s, 1), 85);
	/* Critical damage ignores unfavorable attacker / favorable defender stages. */
	if (critical.attack_stage < 6) critical.attack_stage = 6;
	if (critical.defense_stage > 6) critical.defense_stage = 6;
	dmax = Damage(&critical, Defense(&critical, 0), 100);
	estimate = Damage(s, (Defense(s, 0) + Defense(s, 1)) / 2, 93);
	accuracy = s->accuracy == 0 ? 100 : s->accuracy;
	if (s->accuracy != 0)
	{
		int stage = (int)s->accuracy_stage - (int)s->evasion_stage;
		if (stage < -6) stage = -6;
		if (stage > 6) stage = 6;
		accuracy = Min(100, stage >= 0 ? accuracy * (3 + stage) / 3 : accuracy * 3 / (3 - stage));
	}
	c->accuracy = accuracy;
	/* A nominal neutral estimate is useful for ranking, not a guarantee. Unknown
	 * ability/item/field modifiers widen the COMPLETE envelope to [0,65535].
	 * No probability for a hidden ability/item is invented. */
	e->uncertain = !s->certified_modifiers;
	e->minimum = s->certified_modifiers && accuracy == 100 ? dmin : 0;
	e->maximum = s->certified_modifiers ? Min(65535, dmax * 3) : 65535; /* includes critical hits */
	e->estimate = estimate;
	e->possible_ko = e->maximum >= e->hp_minimum;
	c->expected_damage = estimate * accuracy / 100;
	maxhp = (e->max_hp_minimum + e->max_hp_maximum) / 2;
	hp_estimate = (e->hp_minimum + e->hp_maximum) / 2;
	c->opponent_hp_fraction_lost = Min(256, Min(c->expected_damage, hp_estimate) * 256 / Max(1, maxhp));
	c->productive = c->expected_damage != 0;
	/* Relative cost preserves damage ordering and avoids a fixed -8 bias on
	 * every ordinary attack; nominal utility is explicitly uncertainty-priced. */
	c->uncertainty_cost = e->uncertain ? c->opponent_hp_fraction_lost * 20 / 256 : 0;
	c->robust_safe_ko = s->can_act_safely && s->hp_pixels <= 48
		&& e->minimum >= e->hp_maximum && e->minimum != 0;
	c->net_faints = c->robust_safe_ko ? 1 : 0;
}

void StandardMechanicsAccuracy(struct StandardPolicyCandidate* c)
{
	unsigned before = c->stat_stage_before, after = c->stat_stage_after;
	unsigned old_hit, new_hit;
	if (before > 12 || after > before) return;
	/* One future 100-accuracy exposure, upper bounded by one HP bar. The
	 * drop in hit rate has diminishing returns: 100->75->60->50... . */
	old_hit = before >= 6 ? 100 : 300 / (9 - before);
	new_hit = after >= 6 ? 100 : 300 / (9 - after);
	c->immediate_future_gain = Min(40, old_hit - new_hit);
	c->productive = before != after && old_hit != new_hit;
	c->uncertainty_cost = c->productive ? c->immediate_future_gain / 2 : 0;
}

void StandardMechanicsQualifySwitches(struct StandardPolicyObservation* o)
{
	unsigned i;
	uint8_t productive_stay = 0;
	for (i = 0; i < o->count; ++i)
	{
		const struct StandardPolicyCandidate* c = &o->candidates[i];
		if (c->kind == STANDARD_POLICY_MOVE && c->legal
			&& (c->productive || c->unknown_potentially_productive)
			&& !c->known_no_effect && !c->redundant_status)
			productive_stay = 1;
	}
	for (i = 0; i < o->count; ++i)
	{
		struct StandardPolicyCandidate* c = &o->candidates[i];
		if (c->kind == STANDARD_POLICY_SWITCH)
			c->standard_switch_emergency = !c->forced && !productive_stay
				&& c->legal && c->switch_legal && c->entry_survives && c->productive;
	}
}
