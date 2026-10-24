"""Player sprite, movement, and camera-follow logic."""
import pygame

from ..engine.constants import TILE_SIZE, SCREEN_W, SCREEN_H
from ..engine import input as input_mod

_FACING_FROM_DIR = {(0, -1): "up", (0, 1): "down", (-1, 0): "left", (1, 0): "right"}


class Player:
    """Grid-based movement with smooth pixel interpolation between tiles."""

    def __init__(self, tile_x, tile_y):
        self.tile_x = tile_x
        self.tile_y = tile_y
        self.px = tile_x * TILE_SIZE
        self.py = tile_y * TILE_SIZE
        self.moving = False
        self.facing = "down"
        self.step_count = 0
        self.surface = self._build_sprite()

    def _build_sprite(self):
        surface = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
        pygame.draw.rect(surface, (200, 40, 40), (4, 1, 8, 4))
        pygame.draw.rect(surface, (255, 220, 180), (5, 5, 6, 4))
        pygame.draw.rect(surface, (60, 90, 200), (4, 9, 8, 5))
        pygame.draw.rect(surface, (50, 40, 120), (5, 14, 2, 2))
        pygame.draw.rect(surface, (50, 40, 120), (9, 14, 2, 2))
        return surface

    def try_step(self, dx, dy, tile_map):
        nx, ny = self.tile_x + dx, self.tile_y + dy
        self.facing = _FACING_FROM_DIR[(dx, dy)]
        if tile_map.is_solid(nx, ny):
            return False
        self.tile_x, self.tile_y = nx, ny
        self.moving = True
        self.step_count += 1
        return True

    def update(self, dt, tile_map, held=None):
        if self.moving:
            target_x = self.tile_x * TILE_SIZE
            target_y = self.tile_y * TILE_SIZE
            self.px += (target_x - self.px) * min(1, dt * 18)
            self.py += (target_y - self.py) * min(1, dt * 18)
            if abs(target_x - self.px) < 0.5 and abs(target_y - self.py) < 0.5:
                self.px, self.py = target_x, target_y
                self.moving = False
            return

        if held is None:
            return
        if input_mod.UP in held:
            self.try_step(0, -1, tile_map)
        elif input_mod.DOWN in held:
            self.try_step(0, 1, tile_map)
        elif input_mod.LEFT in held:
            self.try_step(-1, 0, tile_map)
        elif input_mod.RIGHT in held:
            self.try_step(1, 0, tile_map)

    def draw(self, surface, camera_x, camera_y):
        surface.blit(self.surface, (round(self.px - camera_x), round(self.py - camera_y)))


def camera_offset(player_px, player_py, map_width, map_height):
    cam_x = player_px - (SCREEN_W - TILE_SIZE) // 2
    cam_y = player_py - (SCREEN_H - TILE_SIZE) // 2
    max_x = map_width * TILE_SIZE - SCREEN_W
    max_y = map_height * TILE_SIZE - SCREEN_H
    if max_x < 0:
        cam_x = max_x // 2
    else:
        cam_x = max(0, min(cam_x, max_x))
    if max_y < 0:
        cam_y = max_y // 2
    else:
        cam_y = max(0, min(cam_y, max_y))
    return cam_x, cam_y
