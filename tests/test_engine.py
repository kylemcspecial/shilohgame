"""Regression checks for controller lifecycle and game cleanup."""
import os
from unittest.mock import Mock

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')

import pygame
import pytest

from src.engine.input import Input, RIGHT
from src.engine.game import Game


@pytest.fixture
def pygame_runtime():
    pygame.init()
    yield
    pygame.quit()


def test_controller_lifecycle_uses_instance_ids(monkeypatch, pygame_runtime):
    stick = Mock()
    stick.get_instance_id.return_value = 42
    stick.get_numaxes.return_value = 1
    stick.get_axis.return_value = 1.0
    stick.get_numhats.return_value = 0
    stick.get_numbuttons.return_value = 0
    monkeypatch.setattr(pygame.joystick, 'get_count', lambda: 1)
    monkeypatch.setattr(pygame.joystick, 'Joystick', lambda index: stick)
    controls = Input()
    assert list(controls._joysticks) == [42]
    controls.update([])
    assert RIGHT in controls.held
    assert controls.held_set is controls.held
    stick.get_axis.assert_called_once_with(0)
    stick.get_axis.side_effect = pygame.error('Joystick not initialized')
    controls.update([pygame.event.Event(pygame.JOYDEVICEREMOVED, instance_id=42)])
    assert not controls.held
    stick.quit.assert_called_once()
    stick.get_axis.side_effect = None
    controls.update([pygame.event.Event(pygame.JOYDEVICEADDED, device_index=0)])
    assert list(controls._joysticks) == [42]
    assert RIGHT in controls.held


def test_window_close_releases_pygame(pygame_runtime):
    game = Game()
    pygame.event.post(pygame.event.Event(pygame.QUIT))
    game.run()
    assert not game.running
    assert not pygame.get_init()


def test_render_failure_releases_pygame(monkeypatch, pygame_runtime):
    game = Game()
    def fail(surface):
        raise RuntimeError('render failed')
    monkeypatch.setattr(game.scene, 'draw', fail)
    with pytest.raises(RuntimeError, match='render failed'):
        game.run()
    assert not pygame.get_init()


def test_fullscreen_round_trip(pygame_runtime):
    game = Game()
    original_size = game.screen.get_size()
    game.toggle_fullscreen()
    assert game.fullscreen
    assert game.screen.get_flags() & pygame.FULLSCREEN
    game.toggle_fullscreen()
    assert not game.fullscreen
    assert not game.screen.get_flags() & pygame.FULLSCREEN
    assert game.screen.get_size() == original_size


def test_failed_fullscreen_change_preserves_state(monkeypatch, pygame_runtime):
    game = Game()
    screen = game.screen
    def fail(*args):
        raise pygame.error('display unavailable')
    monkeypatch.setattr(pygame.display, 'set_mode', fail)
    with pytest.raises(pygame.error, match='display unavailable'):
        game.toggle_fullscreen()
    assert not game.fullscreen
    assert game.screen is screen
