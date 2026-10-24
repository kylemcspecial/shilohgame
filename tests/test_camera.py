"""Regression test: camera scrolling must not feed floats into tile-range math.

The player's pixel position becomes a float during smooth movement (lerp),
and camera_offset previously returned floats, crashing draw() with
TypeError: 'float' object cannot be interpreted as an integer
the first time the camera scrolled (walking down from spawn).
"""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()

from src.engine.game import Game
from src.world.player import camera_offset


def test_camera_offset_returns_ints():
    for px in (3 * 16, 3 * 16 + 0.37, 100.0, 99.6):
        cam_x, cam_y = camera_offset(px, 64.2, 20, 15)
        assert isinstance(cam_x, int), f"x not int for px={px}: {cam_x}"
        assert isinstance(cam_y, int), f"y not int for px={px}: {cam_y}"


def test_walking_all_directions_renders(tmp_path):
    os.environ["XDG_DATA_HOME"] = str(tmp_path)
    game = Game()
    world = game.world
    game.input.pressed = set()
    # Walk far enough in each direction that the camera scrolls on both axes.
    for direction in ("down", "right", "up", "left", "down"):
        for _ in range(150):
            game.input.held = {direction}
            world.update(1 / 60)
            world.draw(game.buffer)
    game.input.held = set()


def test_walk_triggers_encounter_battle_renders(tmp_path, monkeypatch):
    """A completed grass step must start a wild battle that updates and draws."""
    from src.battle.scene import BattleScene, TrainerBattle

    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    game = Game()
    try:
        world = game.world
        game.input.pressed = set()
        # Enter real encounter grass from the adjacent walkable tile.
        world.switch_zone("whispering_pines", 3, 2)
        assert not world.tile_map.is_solid(3, 2)
        assert world.tile_map.is_tall_grass(4, 2)
        # Guarantee the encounter roll without changing global RNG state.
        world.encounters.rate = 1.0
        game.input.held = {"right"}
        for _ in range(120):
            world.update(1 / 60)
            world.draw(game.buffer)
            if game.scene is not world:
                break

        assert game.scene is not world, "Walking into grass never started a battle"
        battle = game.scene
        assert isinstance(battle, BattleScene)
        assert not isinstance(battle, TrainerBattle)
        assert (world.player.tile_x, world.player.tile_y) == (4, 2)
        game.input.held = set()
        # Draw both the encounter intro and the active battle UI.
        battle.update(1 / 60)
        battle.draw(game.buffer)
        battle.intro_timer = 0
        for _ in range(10):
            battle.update(1 / 60)
            battle.draw(game.buffer)
    finally:
        game.input.held = set()
        pygame.quit()
