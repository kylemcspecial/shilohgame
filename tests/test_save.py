"""Tests for the Healing Lodge, faint penalty, and three-slot save/load."""
import json
import os
from unittest import mock

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pytest

import pygame

from src.monsters.monster import Monster, load_species, load_moves
from src.save import save_game, load_game, serialize, apply_save, SLOT_COUNT, slot_path


@pytest.fixture
def temp_saves(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    return tmp_path


@pytest.fixture
def world(temp_saves):
    pygame.init()
    from src.engine.game import Game

    game = Game()
    game.world.save_slot = 1
    return game.world


def test_save_dir_uses_env(temp_saves):
    from src.save import save_dir

    assert str(temp_saves) in save_dir()


def test_serialize_roundtrip_fields(world):
    world.coins = 123
    world.battles_won = 4
    world.party[0].hp = 3
    data = serialize(world)
    assert data["coins"] == 123
    assert data["battles_won"] == 4
    assert data["party"][0]["hp"] == 3
    assert data["zone_id"] == "hunters_rest"


def test_save_and_load_slot(world, temp_saves):
    world.coins = 77
    save_game(world, 0)
    assert os.path.exists(slot_path(0))
    data = load_game(0)
    assert data is not None
    assert data["coins"] == 77
    assert load_game(1) is None
    assert load_game(2) is None


def test_load_corrupt_save_returns_none(world, temp_saves):
    save_game(world, 0)
    with open(slot_path(0), "w") as f:
        f.write("{not json!!")
    assert load_game(0) is None


def test_load_missing_fields_returns_none(world, temp_saves):
    save_game(world, 0)
    with open(slot_path(0)) as f:
        data = json.load(f)
    del data["party"]
    with open(slot_path(0), "w") as f:
        json.dump(data, f)
    assert load_game(0) is None


def test_apply_save_restores_state(world, temp_saves):
    from src.items.inventory import Inventory

    world.party.append(Monster("brookfin", 4, load_species(), load_moves()))
    world.party[1].hp = 5
    world.coins = 55
    world.battles_won = 2
    save_game(world, 1)

    world.coins = 0
    world.battles_won = 0
    world.party[1].hp = 1
    data = load_game(1)
    apply_save(world, data)
    assert world.coins == 55
    assert world.battles_won == 2
    assert world.party[1].hp == 5
    assert world.party[1].name == "Brookfin"
    assert world.zone_id == "hunters_rest"


def test_three_slots_exist(world, temp_saves):
    for slot in range(SLOT_COUNT):
        save_game(world, slot)
        assert load_game(slot) is not None


def test_healing_lodge_full_heal(world):
    mon = world.party[0]
    mon.hp = 1
    mon.moves[0]["pp"] = 0
    world._heal_party()
    assert mon.hp == mon.max_hp
    assert mon.moves[0]["pp"] == mon.moves[0]["data"]["pp"]


def test_faint_penalty_returns_home_and_costs_coins(world):
    world.coins = 100
    world.switch_zone("whispering_pines", 3, 2)
    world.party[0].hp = 0
    world.heal_and_revive()
    assert world.zone_id == "hunters_rest"
    assert world.coins == 75  # lost 25% (capped at 50)
    assert world.party[0].hp == world.party[0].max_hp


def test_interact_facing_lodge_heals(world):
    mon = world.party[0]
    mon.hp = 2
    world.player.tile_x, world.player.tile_y = 16, 3
    world.player.facing = "up"
    world._interact()
    assert mon.hp == mon.max_hp
    assert world.message


def test_end_battle_loss_triggers_revive(world):
    from src.battle.scene import BattleScene
    from src.engine.game import Game

    game = world.game
    world.coins = 40
    battle = BattleScene(game, world.party[0], Monster("mossrat", 9))
    battle.intro_timer = 0
    battle.player_mon.hp = 0
    battle._check_outcome()
    game.scene = battle
    game.end_battle()
    assert world.coins == 30
    assert world.party[0].hp == world.party[0].max_hp
    assert game.scene is game.world
