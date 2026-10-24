"""Tests for monster data, battle logic, and the Whispering Pines zone."""
import os
import random

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()

from src.monsters.monster import Monster, load_species, load_moves, load_type_chart, roll_wild
from src.battle import battle as battle_mod
from src.world.tiles import TileMap
from src.world.scene import load_zones


class DeterministicRng:
    def __init__(self, value=0.9):
        self.value = value

    def uniform(self, a, b):
        return self.value

    def randint(self, a, b):
        return a

    def random(self):
        return self.value


def test_species_data_complete():
    species = load_species()
    moves = load_moves()
    for sid, s in species.items():
        assert s["name"] and s["types"] and s["base_stats"]
        assert 1 <= s["tier"] <= 4
        assert 1 <= len(s["moves"]) <= 4
        for mid in s["moves"]:
            assert mid in moves


def test_monster_stats_and_faint():
    mon = Monster("fernpup", 5)
    assert mon.max_hp == 22 + 10
    assert not mon.fainted
    mon.hp = 0
    assert mon.fainted


def test_damage_formula_and_effectiveness():
    atk = Monster("fernpup", 5)
    defn = Monster("brookfin", 5)
    chart = load_type_chart()
    dealt, mult = battle_mod.damage(
        atk, defn, load_moves()["leaf_rip"], chart, rng=DeterministicRng(1.0)
    )
    assert dealt >= 1
    # leaf beats water: super effective
    assert mult == 2.0


def test_type_multiplier_neutral_and_weak():
    chart = load_type_chart()
    assert battle_mod.type_multiplier("ember", ["stone"], chart) == 0.5
    assert battle_mod.type_multiplier("leaf", ["stone"], chart) == 2.0
    assert battle_mod.type_multiplier("ember", ["frost"], chart) == 2.0
    assert battle_mod.type_multiplier("frost", ["stone"], chart) == 1.0
    assert battle_mod.type_multiplier("stone", ["leaf"], chart) == 0.5


def test_turn_order_speed_and_ties():
    fast = Monster("fangmoth", 5)
    slow = Monster("mossrat", 5)
    assert battle_mod.goes_first(fast, slow, rng=DeterministicRng(1.0))
    assert not battle_mod.goes_first(slow, fast, rng=DeterministicRng(0.0))
    same_a = Monster("mossrat", 5)
    same_b = Monster("mossrat", 5)
    assert battle_mod.goes_first(same_a, same_b, rng=DeterministicRng(0.1))
    assert not battle_mod.goes_first(same_a, same_b, rng=DeterministicRng(0.9))


def test_run_chance():
    fast = Monster("fangmoth", 5)
    slow = Monster("mossrat", 5)
    assert battle_mod.run_chance(fast, slow)
    assert battle_mod.run_chance(slow, fast, rng=DeterministicRng(1.0)) is False


def test_apply_move_reduces_hp_and_pp():
    atk = Monster("fernpup", 5)
    defn = Monster("mossrat", 5)
    chart = load_type_chart()
    move = atk.moves[0]
    before_hp = defn.hp
    events, messages = battle_mod.apply_move(atk, defn, move, chart, rng=DeterministicRng(1.0))
    assert "damage" in events
    assert defn.hp < before_hp
    assert move["pp"] == move["data"]["pp"] - 1
    assert messages


def test_apply_move_defensive_brace():
    mon = Monster("fernpup", 5)
    foe = Monster("mossrat", 5)
    chart = load_type_chart()
    before = mon.defense
    events, _ = battle_mod.apply_move(mon, foe, mon.moves[1], chart, rng=DeterministicRng(1.0))
    assert "defense_up" in events
    assert mon.defense > before
    assert foe.hp == foe.max_hp


def test_apply_move_miss():
    atk = Monster("fernpup", 5)
    defn = Monster("mossrat", 5)
    chart = load_type_chart()
    move = atk.moves[0]
    events, messages = battle_mod.apply_move(atk, defn, move, chart, rng=AlwaysMissRng())
    assert events == ["missed"]
    assert defn.hp == defn.max_hp


class AlwaysMissRng:
    def randint(self, a, b):
        return 999  # above any accuracy

    def uniform(self, a, b):
        return 1.0


def test_whispering_pines_zone():
    zones = load_zones()["zones"]
    wp = zones["whispering_pines"]
    tm = TileMap(wp)
    assert tm.name == "Whispering Pines"
    assert tm.width == 20 and tm.height == 15
    assert "encounters" in wp
    assert all(sid in load_species() for sid in wp["encounters"])
    lo, hi = wp["encounter_levels"]
    assert lo <= hi


def test_warps_valid_and_reachable():
    zones = load_zones()["zones"]
    for zone in zones.values():
        tm = TileMap(zone)
        for w in tm.warps:
            assert not tm.is_solid(w["x"], w["y"])
            target = TileMap(zones[w["zone"]])
            assert not target.is_solid(w["tx"], w["ty"])


def test_warp_lookup():
    zones = load_zones()["zones"]
    hr = TileMap(zones["hunters_rest"])
    warp = hr.warp_at(5, 12)
    assert warp is not None and warp["zone"] == "whispering_pines"
    assert hr.warp_at(2, 2) is None


def test_tall_grass_in_pines():
    zones = load_zones()["zones"]
    tm = TileMap(zones["whispering_pines"])
    grass_tiles = [
        (x, y)
        for y in range(tm.height)
        for x in range(tm.width)
        if tm.is_tall_grass(x, y)
    ]
    assert len(grass_tiles) > 10


def test_roll_wild_species_in_table():
    zones = load_zones()["zones"]
    wp = zones["whispering_pines"]
    for _ in range(30):
        mon = roll_wild(wp)
        assert mon.species_id in wp["encounters"]
        lo, hi = wp["encounter_levels"]
        assert lo <= mon.level <= hi
