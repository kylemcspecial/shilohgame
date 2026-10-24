"""Tests for catching: HP threshold, catch formula, trap tiers, inventory."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

from src.monsters.monster import Monster, load_species, load_moves
from src.battle import catch as catch_mod
from src.items.inventory import Inventory, load_items


class FixedRng:
    def __init__(self, value):
        self.value = value

    def random(self):
        return self.value


def mon(sid, level, hp_frac=1.0):
    m = Monster(sid, level, load_species(), load_moves())
    m.hp = int(m.max_hp * hp_frac)
    return m


def test_items_data_complete():
    items = load_items()
    for iid, item in items.items():
        assert item["name"] and item["kind"] in ("trap", "potion", "berry", "key")
        if item["kind"] == "trap":
            assert item["catch_bonus"] >= 1.0


def test_trap_tiers_ordered():
    items = load_items()
    tiers = ["basic_trap", "stout_trap", "high_trap", "ultra_trap"]
    bonuses = [items[t]["catch_bonus"] for t in tiers]
    assert bonuses == sorted(bonuses)
    assert bonuses == [1.0, 1.5, 2.0, 3.0]


def test_catch_blocked_above_half_hp():
    monster = mon("mossrat", 3, hp_frac=0.6)
    assert not catch_mod.is_weak_enough(monster)
    success, chance = catch_mod.attempt_catch(monster, 1.0, 5, rng=FixedRng(0.0))
    assert success is False and chance == 0.0


def test_catch_allowed_at_half_hp():
    monster = mon("mossrat", 3, hp_frac=0.5)
    assert catch_mod.is_weak_enough(monster)


def test_catch_chance_clamped():
    weak = mon("mossrat", 2, hp_frac=0.0)
    best = catch_mod.catch_chance(weak, 3.0, 50)
    assert best <= catch_mod.MAX_CATCH_CHANCE
    tough = mon("emberlynx", 10, hp_frac=0.49)
    worst = catch_mod.catch_chance(tough, 1.0, 1)
    assert worst >= catch_mod.MIN_CATCH_CHANCE


def test_catch_chance_factors():
    weak = mon("mossrat", 3, hp_frac=0.1)
    healthier = mon("mossrat", 3, hp_frac=0.45)
    assert catch_mod.catch_chance(weak, 1.0, 5) > catch_mod.catch_chance(healthier, 1.0, 5)
    assert catch_mod.catch_chance(weak, 2.0, 5) > catch_mod.catch_chance(weak, 1.0, 5)
    rare = mon("emberlynx", 3, hp_frac=0.1)
    assert catch_mod.catch_chance(rare, 1.0, 5) < catch_mod.catch_chance(weak, 1.0, 5)


def test_attempt_catch_success_and_failure():
    weak = mon("mossrat", 3, hp_frac=0.1)
    success, chance = catch_mod.attempt_catch(weak, 1.0, 5, rng=FixedRng(0.0))
    assert success and 0.0 < chance <= 0.95
    success, _ = catch_mod.attempt_catch(weak, 1.0, 5, rng=FixedRng(0.999))
    assert not success


def test_inventory_add_remove_counts():
    inv = Inventory({"basic_trap": 2})
    assert inv.count("basic_trap") == 2
    inv.add("basic_trap")
    assert inv.count("basic_trap") == 3
    assert inv.remove("basic_trap")
    assert inv.remove("basic_trap")
    assert inv.remove("basic_trap")
    assert inv.count("basic_trap") == 0
    assert not inv.remove("basic_trap")


def test_inventory_traps_only_owned():
    inv = Inventory({"basic_trap": 1, "potion_s": 3})
    traps = inv.traps()
    assert len(traps) == 1
    assert traps[0][0] == "basic_trap"
