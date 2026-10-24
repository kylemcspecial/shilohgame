"""Catching logic: HP threshold, trap tiers, and the catch chance formula."""
import random

CATCH_HP_THRESHOLD = 0.5  # catch only allowed at or below 50% HP
MIN_CATCH_CHANCE = 0.05
MAX_CATCH_CHANCE = 0.95

RARITY_MODIFIERS = {1: 1.0, 2: 0.7, 3: 0.4, 4: 0.15}


def is_weak_enough(monster):
    """Catching is only allowed once the wild monster is at or below 50% HP."""
    return monster.hp / monster.max_hp <= CATCH_HP_THRESHOLD


def catch_chance(monster, trap_bonus, player_best_level, rng=None):
    """Chance to catch a weakened monster, clamped between 5% and 95%."""
    rng = rng or random
    base_rate = 0.5
    rarity = RARITY_MODIFIERS.get(monster.species["tier"], 0.5)
    hp_factor = 1 - monster.hp / monster.max_hp
    level_ratio = min(1.0, player_best_level / max(1, monster.level))
    level_modifier = 0.5 + 0.5 * level_ratio
    chance = base_rate * trap_bonus * hp_factor * rarity * level_modifier
    return max(MIN_CATCH_CHANCE, min(MAX_CATCH_CHANCE, chance))


def attempt_catch(monster, trap_bonus, player_best_level, rng=None):
    """Roll one catch attempt. Returns (success, chance)."""
    rng = rng or random
    if not is_weak_enough(monster):
        return False, 0.0
    chance = catch_chance(monster, trap_bonus, player_best_level, rng=rng)
    return rng.random() < chance, chance
