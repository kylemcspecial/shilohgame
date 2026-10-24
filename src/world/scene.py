"""Overworld scene: draws the zone, moves the player, shows a HUD."""
import json
import os

import pygame

from ..engine.constants import SCREEN_W, SCREEN_H, TILE_SIZE, BLACK, WHITE
from ..engine import input as input_mod
from ..world.tiles import TileMap, Tileset
from ..world.player import Player, camera_offset

_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data")


def load_zones():
    with open(os.path.join(_DATA_DIR, "zones.json")) as f:
        return json.load(f)


class WorldScene:
    def __init__(self, game):
        self.game = game
        zones = load_zones()
        self.zones = zones["zones"]
        self.tileset = Tileset()
        self.zone_id = zones["start_zone"]
        self.tile_map = TileMap(self.zones[self.zone_id])
        start = self.tile_map.player_start or (2, 2)
        self.player = Player(*start)
        self.paused = False
        self.font = pygame.font.Font(pygame.font.get_default_font(), 8)
        self.zone_banner_timer = 2.0

    @property
    def zone_name(self):
        return self.zones[self.zone_id]["name"]

    def toggle_pause(self):
        self.paused = not self.paused

    def update(self, dt):
        if self.paused:
            return
        self.player.update(dt, self.tile_map, self.game.input.held)
        if self.zone_banner_timer > 0:
            self.zone_banner_timer -= dt

    def draw(self, surface):
        surface.fill(BLACK)
        cam_x, cam_y = camera_offset(
            self.player.px, self.player.py, self.tile_map.width, self.tile_map.height
        )

        x0 = cam_x // TILE_SIZE
        y0 = cam_y // TILE_SIZE
        x1 = min(self.tile_map.width, x0 + SCREEN_W // TILE_SIZE + 2)
        y1 = min(self.tile_map.height, y0 + SCREEN_H // TILE_SIZE + 2)

        for ty in range(y0, y1):
            for tx in range(x0, x1):
                tile = self.tileset.render(self.tile_map.tile_at(tx, ty))
                surface.blit(tile, (tx * TILE_SIZE - cam_x, ty * TILE_SIZE - cam_y))

        self.player.draw(surface, cam_x, cam_y)
        self._draw_hud(surface)

        if self.zone_banner_timer > 0:
            self._draw_banner(surface, self.zone_name)
        if self.paused:
            self._draw_pause(surface)

    def _draw_hud(self, surface):
        label = self.font.render(self.zone_name, False, WHITE, BLACK)
        surface.blit(label, (2, 2))

    def _draw_banner(self, surface, text):
        width = 140
        x = (SCREEN_W - width) // 2
        rect = pygame.Rect(x, 60, width, 24)
        pygame.draw.rect(surface, BLACK, rect)
        pygame.draw.rect(surface, WHITE, rect, 1)
        label = self.font.render(text, False, WHITE, BLACK)
        surface.blit(label, (x + (width - label.get_width()) // 2, 68))

    def _draw_pause(self, surface):
        rect = pygame.Rect(60, 40, 120, 80)
        pygame.draw.rect(surface, BLACK, rect)
        pygame.draw.rect(surface, WHITE, rect, 1)
        title = self.font.render("PAUSED", False, WHITE, BLACK)
        surface.blit(title, (rect.centerx - title.get_width() // 2, 50))
        hint = self.font.render("Esc to resume", False, WHITE, BLACK)
        surface.blit(hint, (rect.centerx - hint.get_width() // 2, 90))
