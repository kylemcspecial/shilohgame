"""Tests for the optional audio system and Pi-target performance."""
import os
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()


def test_audio_degrades_gracefully():
    """Audio must never break the game when no device exists."""
    from src.engine.audio import Audio

    audio = Audio(sfx_volume=0.7, music_volume=0.5)
    audio.confirm()
    audio.hit()
    audio.faint()
    audio.catch_success()
    audio.catch_fail()
    audio.level_up()
    audio.heal()
    assert isinstance(audio.sfx_volume, float)


def test_audio_volume_zero_is_silent():
    from src.engine.audio import Audio

    audio = Audio(sfx_volume=0.0, music_volume=0.0)
    audio.confirm()
    audio.hit()
    assert audio.sfx_volume == 0.0


def test_tone_samples_shape():
    import numpy as np

    from src.engine.audio import _tone_samples

    stereo = _tone_samples(440, 0.1, 0.5)
    assert stereo is not None
    assert stereo.shape[1] == 2
    assert stereo.shape[0] > 0
    assert stereo.dtype == np.int16


def test_game_loop_renders_fast_headless():
    """Spec target: 30 FPS minimum. Headless render of world + battle frames
    should each complete well under the 33ms frame budget."""
    from src.engine.game import Game
    from src.battle.scene import BattleScene
    from src.monsters.monster import Monster, load_species, load_moves

    game = Game()
    game.input.pressed = set()
    game.input.held = set()

    times = []
    for _ in range(60):
        start = time.perf_counter()
        game.world.update(1 / 60)
        game.world.draw(game.buffer)
        times.append(time.perf_counter() - start)
    avg_ms = sum(times) / len(times) * 1000
    assert avg_ms < 33.0, f"world frame avg {avg_ms:.1f}ms exceeds 33ms budget"

    battle = BattleScene(
        game,
        Monster("fernpup", 5, load_species(), load_moves()),
        Monster("mossrat", 3, load_species(), load_moves()),
        inventory=game.world.inventory,
    )
    battle.intro_timer = 0
    times = []
    for _ in range(60):
        start = time.perf_counter()
        battle.update(1 / 60)
        battle.draw(game.buffer)
        times.append(time.perf_counter() - start)
    avg_ms = sum(times) / len(times) * 1000
    assert avg_ms < 33.0, f"battle frame avg {avg_ms:.1f}ms exceeds 33ms budget"
