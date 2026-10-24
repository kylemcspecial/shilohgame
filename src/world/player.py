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
        self._sprites = self._build_all_sprites()

    def _build_all_sprites(self):
        """4 directions x 2 walk frames, SNES-style with outline and shading."""
        return {facing: [self._build_sprite(facing, step) for step in (0, 1)]
                for facing in ("down", "up", "left", "right")}

    def _build_sprite(self, facing, step):
        """Slim hunter, sized like the town NPCs (about 10x14 in a 16px tile)."""
        outline = (28, 24, 40)
        surface = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
        # leg offsets per walk frame
        leg_a, leg_b = ((2, 0) if step == 0 else (0, 2))
        # boots
        pygame.draw.rect(surface, (80, 52, 30), (6, 13 + leg_a // 2, 2, 2 - leg_a // 2))
        pygame.draw.rect(surface, (80, 52, 30), (9, 13 + leg_b // 2, 2, 2 - leg_b // 2))
        # tunic (blue with bevel shading), slim
        pygame.draw.rect(surface, outline, (5, 7, 7, 6))
        pygame.draw.rect(surface, (64, 104, 200), (6, 8, 5, 4))
        pygame.draw.line(surface, (120, 160, 230), (6, 8), (10, 8), 1)
        pygame.draw.line(surface, (36, 64, 140), (6, 12), (10, 12), 1)
        # belt
        pygame.draw.rect(surface, (180, 140, 60), (6, 11, 5, 1))
        # arms
        arm_y = 8 if step == 0 else 9
        pygame.draw.rect(surface, outline, (4, arm_y, 1, 3))
        pygame.draw.rect(surface, (64, 104, 200), (4, arm_y + 1, 1, 2))
        pygame.draw.rect(surface, outline, (12, arm_y, 1, 3))
        pygame.draw.rect(surface, (64, 104, 200), (12, arm_y + 1, 1, 2))
        # head with hair
        pygame.draw.rect(surface, outline, (5, 2, 7, 5))
        pygame.draw.rect(surface, (255, 222, 180), (6, 3, 5, 4))
        pygame.draw.rect(surface, (120, 72, 32), (5, 2, 7, 2))  # hair cap
        # face detail per direction
        if facing == "down":
            pygame.draw.rect(surface, (28, 28, 40), (7, 4, 1, 1))
            pygame.draw.rect(surface, (28, 28, 40), (9, 4, 1, 1))
        elif facing == "left":
            pygame.draw.rect(surface, (28, 28, 40), (6, 4, 1, 1))
        elif facing == "right":
            pygame.draw.rect(surface, (28, 28, 40), (10, 4, 1, 1))
        # up: hair covers face, no eyes
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
        import math

        frame = 0
        if self.moving:
            frame = int(self.step_count + pygame.time.get_ticks() / 150) % 2
        sprite = self._sprites[self.facing][frame]
        # soft shadow
        shadow = pygame.Surface((TILE_SIZE, 4), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (16, 16, 24, 90), (3, 0, 10, 4))
        surface.blit(shadow, (round(self.px - camera_x) + 1, round(self.py - camera_y) + 13))
        surface.blit(sprite, (round(self.px - camera_x), round(self.py - camera_y)))


def camera_offset(player_px, player_py, map_width, map_height):
    """Integer pixel offset of the camera (floats break tile-range math)."""
    player_px = int(player_px)
    player_py = int(player_py)
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
    return int(cam_x), int(cam_y)
