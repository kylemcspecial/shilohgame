"""Regression tests for the second bugfix pass (PR #10)."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()

from src.engine.game import Game
from src.battle.scene import BattleScene
from src.monsters.monster import Monster, load_species, load_moves
from src.monsters import leveling
from src.world.tiles import Tileset
from src.world.scene import load_zones


def mon(sid, level):
    return Monster(sid, level, load_species(), load_moves())


def test_shake_timer_decrements_in_update_not_draw(tmp_path):
    game = Game()
    os.environ["XDG_DATA_HOME"] = str(tmp_path)
    battle = BattleScene(game, mon("fernpup", 5), mon("mossrat", 3))
    battle.intro_timer = 0
    battle.shake_timer = 1.0
    for _ in range(10):
        battle.draw(game.buffer)
    assert battle.shake_timer == 1.0, "draw() must not advance animation time"
    battle.update(1 / 60)
    assert battle.shake_timer < 1.0


def test_forced_switch_no_free_attack(tmp_path):
    """A faint-forced switch must not give the enemy a free hit (review #10)."""
    os.environ["XDG_DATA_HOME"] = str(tmp_path)
    game = Game()
    party = [mon("mossrat", 5), mon("brookfin", 5)]
    game.world.party = party
    battle = BattleScene(game, party[0], mon("fernpup", 8))
    battle.intro_timer = 0
    party[0].hp = 0
    battle._check_outcome()
    assert battle.force_switch
    hp_before = party[1].hp
    battle._do_switch(party[1])
    assert party[1].hp == hp_before, "forced switch must not trigger a free enemy attack"


def test_voluntary_switch_still_gives_free_attack(tmp_path):
    os.environ["XDG_DATA_HOME"] = str(tmp_path)
    game = Game()
    party = [mon("mossrat", 5), mon("brookfin", 5)]
    game.world.party = party
    battle = BattleScene(game, party[0], mon("fernpup", 8))
    battle.intro_timer = 0
    hp_before = party[1].hp
    battle._do_switch(party[1])
    assert party[1].hp <= hp_before, "voluntary switch should let the enemy attack"


def test_npc_tile_renders_distinct():
    tileset = Tileset()
    npc = tileset.render("N")
    grass = tileset.render(".")
    assert npc.get_size() == (16, 16)
    assert npc.get_at((8, 10)) != grass.get_at((8, 10)), "NPC tile must be visible"


def test_npc_tiles_exist_in_towns():
    zones = load_zones()["zones"]
    npc_zones = [
        z for z in zones.values() if any("N" in row for row in z["tiles"])
    ]
    assert len(npc_zones) >= 3


def test_levelup_message_uses_pre_evolution_name(tmp_path):
    """Level-up line should name the monster as it was at that level."""
    os.environ["XDG_DATA_HOME"] = str(tmp_path)
    game = Game()
    # mossrat at 15 near the level threshold: one win levels it to 16 and evolves it
    m = mon("mossrat", 15)
    m.xp = leveling.xp_to_next(15) - 1
    game.world.party = [m]
    battle = BattleScene(game, m, mon("mossrat", 20))
    battle.intro_timer = 0
    battle.enemy_mon.hp = 0
    battle._check_outcome()
    level_lines = [msg for msg in battle.messages if "grew to level" in msg]
    assert level_lines, battle.messages
    assert "Mossrat grew to level 16" in level_lines[0]
    assert any("evolved into" in msg for msg in battle.messages)


def test_save_menu_no_unused_import_regression(tmp_path):
    src = open("src/world/scene.py").read()
    assert "load_game, SLOT_COUNT" not in src
