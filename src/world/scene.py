"""Overworld scene: draws the zone, moves the player, shows a HUD."""
import json
import os

import pygame

from ..engine.constants import SCREEN_W, SCREEN_H, TILE_SIZE, BLACK, WHITE
from ..engine import input as input_mod
from ..world.tiles import TileMap, Tileset
from ..world.player import Player, camera_offset
from ..world.encounters import EncounterTracker
from ..monsters.monster import Monster, load_species, load_moves, roll_wild
from ..items.inventory import Inventory

_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data")

ENCOUNTER_RATE = 0.125  # ~1 in 8 steps in tall grass


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
        self.party_menu = False
        self.party_index = 0
        self.encounters = EncounterTracker(ENCOUNTER_RATE)
        self.inventory = Inventory({"basic_trap": 5, "potion_s": 3, "berry": 2})
        species_table = load_species()
        move_table = load_moves()
        self.party = [Monster("fernpup", 5, species_table, move_table)]
        self.storage = []

    def switch_zone(self, zone_id, tx, ty):
        self.zone_id = zone_id
        self.tile_map = TileMap(self.zones[zone_id])
        self.player.tile_x, self.player.tile_y = tx, ty
        self.player.px, self.player.py = tx * TILE_SIZE, ty * TILE_SIZE
        self.player.moving = False
        self.zone_banner_timer = 2.0

    @property
    def zone_name(self):
        return self.zones[self.zone_id]["name"]

    def toggle_pause(self):
        if self.game.scene is not self:
            return
        self.paused = not self.paused
        self.party_menu = False
        self.party_index = 0

    def _on_step(self):
        """Called each time the player finishes a step onto a new tile."""
        warp = self.tile_map.warp_at(self.player.tile_x, self.player.tile_y)
        if warp is not None:
            self.switch_zone(warp["zone"], warp["tx"], warp["ty"])
            return
        zone = self.zones[self.zone_id]
        if "encounters" in zone and self.tile_map.is_tall_grass(
            self.player.tile_x, self.player.tile_y
        ):
            if self.encounters.should_trigger():
                from ..battle.scene import BattleScene

                enemy = roll_wild(zone)
                self.game.start_battle(
                    BattleScene(self.game, self.party[0], enemy, inventory=self.inventory)
                )

    def update(self, dt):
        if self.paused:
            self._update_pause_menu()
            return
        was_moving = self.player.moving
        self.player.update(dt, self.tile_map, self.game.input.held)
        if self.zone_banner_timer > 0:
            self.zone_banner_timer -= dt

        if was_moving and not self.player.moving:
            self._on_step()

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
        if self.party_menu:
            self._draw_party(surface)

    def _draw_party(self, surface):
        """Party list in the pause menu; confirm swaps to the front slot."""
        rect = pygame.Rect(8, 8, SCREEN_W - 16, 11 * len(self.party) + 4)
        pygame.draw.rect(surface, BLACK, rect)
        pygame.draw.rect(surface, WHITE, rect, 1)
        for i, mon in enumerate(self.party):
            hp = f"{mon.hp}/{mon.max_hp}"
            label = self.font.render(f"{mon.name} L{mon.level} {hp}", False, WHITE, BLACK)
            y = rect.y + 2 + i * 11
            surface.blit(label, (rect.x + 10, y))
            if i == self.party_index:
                pygame.draw.polygon(
                    surface, WHITE,
                    [(rect.x + 3, y + 3), (rect.x + 8, y + 6), (rect.x + 3, y + 9)],
                )

    def _update_pause_menu(self):
        """Handle input while the pause menu is open."""
        pressed = self.game.input.pressed
        if self.party_menu:
            if input_mod.UP in pressed:
                self.party_index = (self.party_index - 1) % len(self.party)
            elif input_mod.DOWN in pressed:
                self.party_index = (self.party_index + 1) % len(self.party)
            elif input_mod.CONFIRM in pressed and len(self.party) > 1:
                self.party[0], self.party[self.party_index] = (
                    self.party[self.party_index], self.party[0],
                )
                self.party_index = 0
            elif input_mod.CANCEL in pressed:
                self.party_menu = False
            return
        if input_mod.CONFIRM in pressed:
            self.party_menu = True
            self.party_index = 0

