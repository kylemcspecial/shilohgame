import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import pygame
import pytest

pygame.init()
pygame.joystick.init()

from src.world.tiles import TileMap
from src.world.scene import load_zones


@pytest.fixture(scope="module")
def zone_data():
    return load_zones()["zones"]["hunters_rest"]


@pytest.fixture
def tile_map(zone_data):
    return TileMap(zone_data)


def test_map_dimensions(tile_map):
    assert tile_map.width == 20
    assert tile_map.height == 15


def test_player_start_found(tile_map):
    assert tile_map.player_start == (3, 4)
    assert not tile_map.is_solid(*tile_map.player_start)


def test_solidity(tile_map):
    assert tile_map.is_solid(0, 0)          # tree border
    assert tile_map.is_solid(10, 5)         # house wall
    assert not tile_map.is_solid(5, 5)      # road
    assert not tile_map.is_solid(2, 1)      # grass
    assert not tile_map.is_solid(5, 12)     # door


def test_tall_grass(tile_map):
    assert tile_map.is_tall_grass(2, 2)
    assert not tile_map.is_tall_grass(3, 2)


def test_out_of_bounds_is_solid(tile_map):
    assert tile_map.is_solid(-1, 0)
    assert tile_map.is_solid(0, 99)
    assert tile_map.is_solid(99, 99)


def test_player_steps_and_collides(tile_map):
    from src.world.player import Player

    player = Player(1, 1)
    assert player.try_step(0, -1, tile_map) is False   # tree border above
    assert (player.tile_x, player.tile_y) == (1, 1)
    assert player.try_step(0, 1, tile_map) is True     # grass below
    assert (player.tile_x, player.tile_y) == (1, 2)
