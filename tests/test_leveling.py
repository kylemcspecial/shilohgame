"""Tests for XP, leveling, move learning, and party switching in battle."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()

from src.monsters.monster import Monster, load_species, load_moves
from src.monsters import leveling
from src.battle.scene import BattleScene
from src.battle import battle as battle_mod


class FakeGame:
    """Minimal stand-in for Game with just a world.party."""

    class world:
        party = []

    class input:
        pressed = set()
        held = set()


def mon(sid, level):
    return Monster(sid, level, load_species(), load_moves())


def test_xp_for_defeat_scales():
    assert leveling.xp_for_defeat(5, 1) < leveling.xp_for_defeat(5, 3)
    assert leveling.xp_for_defeat(3, 1) < leveling.xp_for_defeat(6, 1)


def test_xp_to_next_grows():
    assert leveling.xp_to_next(1) < leveling.xp_to_next(10)


def test_grant_xp_level_up():
    m = mon("fernpup", 5)
    events = leveling.grant_xp(m, leveling.xp_to_next(5) + 1)
    assert m.level == 6
    assert any(e["type"] == "level_up" for e in events)
    assert m.max_hp > 22 + 10


def test_grant_xp_multi_level():
    m = mon("mossrat", 2)
    leveling.grant_xp(m, 500)
    assert m.level > 3
    assert m.xp >= 0


def test_level_cap():
    m = mon("mossrat", 49)
    leveling.grant_xp(m, 99999)
    assert m.level == leveling.LEVEL_CAP


def test_move_learning_from_pool():
    m = mon("fernpup", 3)
    events = leveling.grant_xp(m, leveling.xp_to_next(3) + 1)
    learned = [e for e in events if e["type"] == "learned_move"]
    assert learned, f"expected a learned move at level 4, got {events}"
    assert learned[0]["move"] == "leaf_rip"
    assert "leaf_rip" in [mv["id"] for mv in m.moves]


def test_no_duplicate_move_learning():
    m = mon("fernpup", 3)
    leveling.grant_xp(m, leveling.xp_to_next(3) + 1)
    ids = [mv["id"] for mv in m.moves]
    assert len(ids) == len(set(ids))


def test_battle_win_grants_xp():
    pygame.init()
    game = FakeGame()
    party = [mon("fernpup", 5), mon("brookfin", 4)]
    game.world.party = party
    battle = BattleScene(game, party[0], mon("mossrat", 3), inventory=None)
    battle.intro_timer = 0
    battle.enemy_mon.hp = 0
    battle._check_outcome()
    assert battle.outcome == "won"
    assert party[0].xp > 0
    assert any("grew to level" in msg or "won" in msg for msg in battle.messages)


def test_battle_switch_goes_first():
    pygame.init()
    game = FakeGame()
    party = [mon("fernpup", 5), mon("brookfin", 4)]
    game.world.party = party
    battle = BattleScene(game, party[0], mon("mossrat", 3), inventory=None)
    battle.intro_timer = 0
    enemy_hp_before = battle.enemy_mon.hp
    battle._do_switch(party[1])
    assert battle.player_mon is party[1]
    # switching gives the enemy a free attack; it may have dealt damage
    assert battle.player_mon.hp <= party[1].max_hp


def test_forced_switch_on_faint():
    pygame.init()
    game = FakeGame()
    party = [mon("fernpup", 5), mon("brookfin", 4)]
    game.world.party = party
    battle = BattleScene(game, party[0], mon("mossrat", 3), inventory=None)
    battle.intro_timer = 0
    battle.player_mon.hp = 0
    battle._check_outcome()
    assert battle.force_switch is True
    assert battle.finished is False
    battle._do_switch(party[1])
    assert battle.player_mon is party[1]
    assert battle.force_switch is False


def test_all_faint_loses_battle():
    pygame.init()
    game = FakeGame()
    party = [mon("fernpup", 5)]
    game.world.party = party
    battle = BattleScene(game, party[0], mon("mossrat", 3), inventory=None)
    battle.intro_timer = 0
    battle.player_mon.hp = 0
    battle._check_outcome()
    assert battle.outcome == "lost"
    assert battle.finished
