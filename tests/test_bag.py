"""Tests for the Bag: potions heal HP, berries restore PP, shop stocks them."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()

from src.engine.game import Game
from src.battle.scene import BattleScene, _MENU
from src.items.inventory import Inventory
from src.monsters.monster import Monster, load_species, load_moves
from src.world.scene import WorldScene


def mon(sid, level):
    return Monster(sid, level, load_species(), load_moves())


def make_battle(tmp_path, inventory=None):
    os.environ["XDG_DATA_HOME"] = str(tmp_path)
    game = Game()
    battle = BattleScene(
        game, mon("fernpup", 5), mon("mossrat", 3), inventory=inventory
    )
    battle.intro_timer = 0
    battle._enemy_free_attack = lambda: None  # isolate item effects from enemy turns
    return battle


def test_usables_list_only_owned_consumables():
    inv = Inventory({"potion_s": 2, "berry": 1, "basic_trap": 3})
    usables = inv.usables()
    ids = [iid for iid, _ in usables]
    assert ids == ["potion_s", "berry"]
    assert all(item["kind"] in ("potion", "berry") for _, item in usables)


def test_bag_command_in_battle_menu():
    assert "Bag" in _MENU


def test_use_potion_heals_and_consumes(tmp_path):
    inv = Inventory({"potion_s": 2})
    battle = make_battle(tmp_path, inventory=inv)
    battle.player_mon.hp = battle.player_mon.max_hp - 10
    hp_before = battle.player_mon.hp
    battle._use_item("potion_s", inv.items["potion_s"])
    assert inv.count("potion_s") == 1
    assert battle.player_mon.hp == hp_before + 10
    assert not battle.bag_menu


def test_potion_at_full_health_not_consumed(tmp_path):
    inv = Inventory({"potion_s": 1})
    battle = make_battle(tmp_path, inventory=inv)
    battle.player_mon.hp = battle.player_mon.max_hp
    battle._use_item("potion_s", inv.items["potion_s"])
    assert inv.count("potion_s") == 1
    assert "full health" in battle.messages[-1]


def test_use_berry_restores_pp(tmp_path):
    inv = Inventory({"berry": 1})
    battle = make_battle(tmp_path, inventory=inv)
    moves = battle.player_mon.moves
    for mv in moves:
        mv["pp"] = 0
    battle._use_item("berry", inv.items["berry"])
    assert inv.count("berry") == 0
    assert all(mv["pp"] == 5 for mv in moves)


def test_berry_at_full_pp_not_consumed(tmp_path):
    inv = Inventory({"berry": 1})
    battle = make_battle(tmp_path, inventory=inv)
    battle._use_item("berry", inv.items["berry"])
    assert inv.count("berry") == 1
    assert "full PP" in battle.messages[-1]


def test_bag_command_opens_menu(tmp_path):
    inv = Inventory({"potion_s": 1})
    battle = make_battle(tmp_path, inventory=inv)
    battle._choose("Bag")
    assert battle.bag_menu
    assert battle.bag_index == 0


def test_bag_empty_shows_message(tmp_path):
    battle = make_battle(tmp_path, inventory=Inventory())
    battle._choose("Bag")
    assert not battle.bag_menu
    assert battle.messages[-1] == "Your bag is empty!"


def test_shop_stocks_consumables():
    items = WorldScene._SHOP_ITEMS
    assert "potion_s" in items and "potion_m" in items and "berry" in items


def test_starting_inventory_has_bag_items():
    inv = Inventory({"basic_trap": 5, "potion_s": 3, "berry": 2})
    assert inv.usables()


def test_brace_stacks_reset_on_level_up():
    """Codex review on PR #17: leveling rebuilds defense, so brace stacks must reset."""
    from src.monsters import leveling

    species = load_species()
    moves = load_moves()
    mon = Monster("fernpup", 5, species, moves)
    mon.brace_stacks = 2
    mon.xp = leveling.xp_to_next(5)
    events = leveling.grant_xp(mon, 1)
    assert any(e["type"] == "level_up" for e in events)
    assert mon.brace_stacks == 0
    assert mon.defense == species["fernpup"]["base_stats"]["defense"] + mon.level // 2


def test_brace_stacks_reset_on_evolution():
    """Evolution rebuilds stats in place; stale brace stacks must not survive."""
    from src.monsters import leveling

    species = load_species()
    evo = species["mossrat"].get("evolve_into")
    assert evo, "mossrat must have an evolution for this test"
    mon = Monster("mossrat", evo["level"], species, load_moves())
    mon.brace_stacks = 2
    result = leveling.check_evolution(mon)
    assert result is not None
    assert mon.brace_stacks == 0


def test_zero_pp_choice_advances_turn(tmp_path):
    """Codex review on PR #17: a 0-PP move pick must struggle and advance the turn."""
    battle = make_battle(tmp_path, inventory=Inventory({"potion_s": 1}))
    for mv in battle.player_mon.moves:
        mv["pp"] = 0
    battle.move_menu = True
    battle.move_index = 0
    turns = []
    battle._take_turn = lambda move: turns.append(move)
    battle.update(1 / 60)  # no pending messages, intro done
    battle.game.input.pressed = {"confirm"}
    battle.update(1 / 60)
    assert turns == [None], "0-PP confirm must pass the turn via _take_turn(None)"
    assert not battle.move_menu
    assert any("can only struggle" in m for m in battle.messages)
