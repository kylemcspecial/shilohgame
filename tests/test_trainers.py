"""Tests for trainers, the Emmett arc, zone connections, and towns."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()

from src.world.scene import load_zones
from src.world.tiles import TileMap
from src.world.trainers import TrainerState, trainers_in_zone, load_trainers
from src.battle.scene import TrainerBattle
from src.monsters.monster import Monster, load_species, load_moves
from src.battle import battle as battle_mod


class FakeGame:
    class world:
        party = []

    class input:
        pressed = set()
        held = set()


def test_all_zones_valid():
    zones = load_zones()["zones"]
    for zid, z in zones.items():
        tm = TileMap(z)
        assert len(z["tiles"]) == z["height"], zid
        for row in z["tiles"]:
            assert len(row) == z["width"], (zid, row)
        for w in tm.warps:
            target = TileMap(zones[w["zone"]])
            assert not target.is_solid(w["tx"], w["ty"])


def test_required_zone_count():
    zones = load_zones()["zones"]
    forests = [z for z in zones.values() if "encounters" in z]
    towns = [z for z in zones.values() if any("H" in row for row in z["tiles"])]
    assert len(forests) >= 4, "spec: minimum 4 forest zones"
    assert len(towns) >= 3, "spec: minimum 3 towns"
    for town in towns:
        tm = TileMap(town)
        lodge = any(
            tm.tile_at(x, y) == "H"
            for y in range(tm.height) for x in range(tm.width)
        )
        shop = any(
            tm.tile_at(x, y) == "S"
            for y in range(tm.height) for x in range(tm.width)
        )
        assert lodge and shop, f"{town['name']} needs a Healing Lodge and Trap Shop"


def test_zone_chain_reaches_emberfern():
    """Warps must connect Hunter's Rest to Emberfern Glade."""
    zones = load_zones()["zones"]
    seen = {"hunters_rest"}
    frontier = ["hunters_rest"]
    while frontier:
        zid = frontier.pop()
        for w in zones[zid].get("warps", []):
            if w["zone"] not in seen:
                seen.add(w["zone"])
                frontier.append(w["zone"])
    assert "emberfern_glade" in seen
    assert "pineroot_crossing" in seen and "fernfall" in seen
    assert "mossy_hollow" in seen and "thornwood_ridge" in seen


def test_trainer_data_valid():
    species = load_species()
    for tid, t in load_trainers()["trainers"].items():
        assert t["name"] and t["intro"] and t["defeat"]
        assert t["reward"] >= 0
        assert len(t["team"]) >= 1
        for member in t["team"]:
            assert member["species"] in species
            assert member["level"] >= 1


def test_trainer_positions_walkable():
    zones = load_zones()["zones"]
    for tid, t in load_trainers()["trainers"].items():
        tm = TileMap(zones[t["zone"]])
        assert not tm.is_solid(t["x"], t["y"]), (tid, t["zone"])


def test_emmett_arc_gating():
    state = TrainerState()
    data = load_trainers()["trainers"]
    assert not state.can_challenge("emmett_2", data["emmett_2"])
    assert not state.can_challenge("emmett_3", data["emmett_3"])
    assert state.can_challenge("emmett_1", data["emmett_1"])
    state.record_win("emmett_1")
    assert state.can_challenge("emmett_2", data["emmett_2"])
    assert not state.can_challenge("emmett_3", data["emmett_3"])
    state.record_win("emmett_2")
    assert state.can_challenge("emmett_3", data["emmett_3"])


def test_trainer_rebattle_cooldown():
    state = TrainerState()
    data = load_trainers()["trainers"]
    state.record_start("pineroot_scout")
    state.record_win("pineroot_scout")
    assert not state.can_challenge("pineroot_scout", data["pineroot_scout"])
    state.last_battled["pineroot_scout"] -= 1000.0  # simulate time passing
    assert state.can_challenge("pineroot_scout", data["pineroot_scout"])


def test_trainer_battle_blocks_run_and_catch():
    pygame.init()
    game = FakeGame()
    game.world.party = [Monster("fernpup", 10, load_species(), load_moves())]
    data = load_trainers()["trainers"]["pineroot_scout"]
    battle = TrainerBattle(game, game.world.party[0], "pineroot_scout", data)
    battle.intro_timer = 0
    battle._choose("Run")
    assert "can't run" in battle.messages[-1]
    battle._choose("Catch")
    assert "can't catch" in battle.messages[-1]
    assert not battle.finished


def test_trainer_battle_sends_next_monster():
    pygame.init()
    game = FakeGame()
    game.world.party = [Monster("fernpup", 20, load_species(), load_moves())]
    data = load_trainers()["trainers"]["pineroot_scout"]
    battle = TrainerBattle(game, game.world.party[0], "pineroot_scout", data)
    battle.intro_timer = 0
    first = battle.enemy_mon
    battle.enemy_mon.hp = 0
    battle._check_outcome()
    assert battle.enemy_mon is not first
    assert not battle.finished
    assert "sent out" in battle.messages[-1]


def test_trainer_battle_win_grants_coins_and_flag():
    pygame.init()
    game = FakeGame()
    game.world.party = [Monster("fernpup", 30, load_species(), load_moves())]
    data = load_trainers()["trainers"]["pineroot_scout"]
    battle = TrainerBattle(game, game.world.party[0], "pineroot_scout", data)
    battle.intro_timer = 0
    for m in battle.team:
        m.hp = 0
    battle.enemy_mon = battle.team[0]
    battle._check_outcome()
    assert battle.outcome == "trainer_won"
    assert battle.finished
    assert any("coins" in msg for msg in battle.messages)


def test_trainers_in_zone_lookup():
    pine = trainers_in_zone("pineroot_crossing")
    assert any(tid == "pineroot_scout" for tid, _ in pine)
    hr = trainers_in_zone("hunters_rest")
    assert any(tid == "emmett_1" for tid, _ in hr)
