"""Tests for M12: postgame leaders, legendary shrine, dex, map, move hints,
text speed."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()

import pytest

from src.engine.game import Game
from src.battle.scene import TrainerBattle, BattleScene
from src.monsters.monster import Monster, load_species, load_moves
from src.world.trainers import load_trainers


@pytest.fixture
def game(tmp_path):
    os.environ["XDG_DATA_HOME"] = str(tmp_path)
    return Game()


def mon(sid, level):
    return Monster(sid, level, load_species(), load_moves())


ALL_BADGES = ["fenwick", "boulder", "ivy", "hazel", "rex", "bram", "pyra"]


# ------------------------------------------------- postgame leader rematches

def test_postgame_leader_rematch_at_45(game):
    trainer = load_trainers()["trainers"]["fenwick"]
    for tid in ALL_BADGES:
        game.world.trainer_state.defeated[tid] = True
    assert "ember_crown" in game.world.badge_ids
    battle = TrainerBattle(game, mon("fernpup", 45), "fenwick", trainer)
    assert [m.level for m in battle.team] == [20, 20, 21], "Ember Crown rematches at +12"
    # no crown: normal +3 rematch
    game2 = Game()
    game2.world.trainer_state.defeated["fenwick"] = True
    battle2 = TrainerBattle(game2, mon("fernpup", 20), "fenwick", trainer)
    assert [m.level for m in battle2.team] == [11, 11, 12]


def test_postgame_levels_capped_at_50(game):
    trainer = load_trainers()["trainers"]["pyra"]
    for tid in ALL_BADGES:
        game.world.trainer_state.defeated[tid] = True
    battle = TrainerBattle(game, mon("fernpup", 45), "pyra", trainer)
    assert all(m.level <= 50 for m in battle.team)


# ------------------------------------------------------------ legendary shrine

def test_shrine_data_valid():
    import json

    zones = json.load(open("data/zones.json"))["zones"]
    shrine = zones["emberfern_glade"]["legendary_shrine"]
    assert zones["emberfern_glade"]["tiles"][shrine["y"]][shrine["x"]] == "L"
    species = load_species()
    for sid in shrine["species"]:
        assert species[sid]["tier"] == 4
    assert shrine["requires_badge"] == "ember_crown"


def test_shrine_locked_without_crown(game):
    world = game.world
    world.switch_zone("emberfern_glade", 9, 11)
    handled = world._try_shrine(9, 12)
    assert handled is True
    assert "Ember Crown" in world.message
    assert game.scene is world, "no battle without the crown"


def test_shrine_starts_legendary_battle_with_crown(game):
    world = game.world
    for tid in ALL_BADGES:
        world.trainer_state.defeated[tid] = True
    world.switch_zone("emberfern_glade", 9, 11)
    import json

    shrine = json.load(open("data/zones.json"))["zones"]["emberfern_glade"]["legendary_shrine"]
    handled = world._try_shrine(9, 12)
    assert handled is True
    assert game.scene is not world, "battle starts with the crown"
    battle = game.scene
    assert battle.enemy_mon.species_id in shrine["species"]
    assert battle.enemy_mon.species["tier"] == 4


# ---------------------------------------------------------------------- dex

def test_dex_registers_seen_and_caught(game):
    world = game.world
    enemy = mon("mossrat", 5)
    world.dex_register(enemy)
    assert world.dex_seen == ["mossrat"] and world.dex_caught == []
    world.dex_register(enemy, caught=True)
    assert "mossrat" in world.dex_caught
    # re-registering does not duplicate
    world.dex_register(enemy, caught=True)
    assert world.dex_caught.count("mossrat") == 1


def test_dex_battle_hooks(game):
    world = game.world
    enemy = mon("chirrel", 4)
    battle = BattleScene(game, mon("fernpup", 6), enemy)
    battle.intro_timer = 0.01
    battle.update(1 / 60)  # drains intro, registers seen
    assert "chirrel" in world.dex_seen
    assert "chirrel" not in world.dex_caught
    # the catch path registers caught (via end-of-battle handling)
    world.dex_register(mon("dewvole", 4), caught=True)
    assert "dewvole" in world.dex_caught


def test_dex_persists(game):
    world = game.world
    world.dex_register(mon("mossrat", 5), caught=True)
    from src.save import serialize, apply_save

    data = serialize(world)
    assert data["dex_seen"] == ["mossrat"] and data["dex_caught"] == ["mossrat"]
    apply_save(world, data)
    assert world.dex_seen == ["mossrat"] and world.dex_caught == ["mossrat"]


def test_dex_screen_draws(game):
    world = game.world
    world.dex_register(mon("mossrat", 5), caught=True)
    world.dex_menu = True
    world.dex_index = 0
    world.draw(game.buffer)  # must not crash


def test_map_screen_draws(game):
    world = game.world
    world.map_menu = True
    world.draw(game.buffer)
    world.trainer_state.defeated["fenwick"] = True
    world.draw(game.buffer)  # OK! status path


# ---------------------------------------------------------------- move hints

def test_move_hint_marking(game):
    from src.battle import battle as battle_mod
    from src.monsters.monster import load_type_chart

    chart = load_type_chart()
    # leaf move vs water enemy: super effective
    mult = battle_mod.type_multiplier("leaf", ["water"], chart)
    assert mult > 1.0
    # stone vs stone: neutral
    assert battle_mod.type_multiplier("stone", ["stone"], chart) == 1.0


def test_move_menu_with_hints_draws(game):
    battle = BattleScene(game, mon("fernpup", 6), mon("brookfin", 5))
    battle.intro_timer = 0
    battle.move_menu = True
    battle.draw(game.buffer)  # must not crash; hints rendered


# -------------------------------------------------------------- text speed

def test_text_speed_speeds_advance(game):
    game.message_speed = 4
    battle = BattleScene(game, mon("fernpup", 6), mon("mossrat", 5))
    battle.intro_timer = 0
    battle._confirmed = True
    battle._append_messages(["one", "two", "three", "four", "five"])
    # _read sits on the first appended line (index 1 of 6 total)
    assert battle.message_index == 1
    # default speed 2: one press advances two lines
    game.message_speed = 2
    battle._advance_message()
    assert battle.message_index == 3
    # fast: 4 per press, clamped at the final pending line (index 5)
    game.message_speed = 4
    battle._advance_message()
    assert battle.message_index == 5
    assert battle.message_index == len(battle.messages) - 1


def test_options_include_text_speed():
    from src.ui.main_menu import MainMenuScene

    class StubGame:
        class audio:
            music_volume = 0.5
            sfx_volume = 0.5

        fullscreen = False
        day_night_enabled = True
        message_speed = 2

    menu = MainMenuScene(StubGame())
    rows = menu._option_rows()
    assert any("Text Speed" in label for _, label in rows)
    assert "Normal" in dict(rows)["text_speed"]
