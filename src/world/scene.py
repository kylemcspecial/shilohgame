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
from ..world.trainers import TrainerState, trainers_in_zone, load_trainers

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
        self.pause_index = 0
        self.save_menu = False
        self.save_index = 0
        self.card_menu = False
        self.trainer_state = TrainerState()
        self.trainers_data = load_trainers()
        self.encounters = EncounterTracker(ENCOUNTER_RATE)
        self.inventory = Inventory({"basic_trap": 5, "potion_s": 3, "berry": 2})
        species_table = load_species()
        move_table = load_moves()
        self.party = [Monster("fernpup", 5, species_table, move_table)]
        self.storage = []
        self.coins = 60
        self.battles_won = 0
        self.monsters_caught = 0
        self.play_time = 0.0
        self.message = None
        self.message_timer = 0.0
        self.save_slot = None

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

    def _open_shop(self):
        """Face the Trap Shop and confirm to buy a Basic Trap (20 coins)."""
        if self.coins >= 20:
            self.coins -= 20
            self.inventory.add("basic_trap")
            self._flash("Bought a Basic Trap! (20 coins)")
        else:
            self._flash("Not enough coins for a trap!")

    def _heal_party(self):
        """Full party heal, free, and auto-save to the current slot."""
        from ..save import save_game

        for mon in self.party + self.storage:
            mon.hp = mon.max_hp
            for mv in mon.moves:
                mv["pp"] = mv["data"]["pp"]
        self._flash("Your monsters are fully healed! Game saved.")
        if self.save_slot is not None:
            save_game(self, self.save_slot)

    def _flash(self, text):
        self.message = text
        self.message_timer = 2.5

    def heal_and_revive(self):
        """Called after a total-party faint: warp home, heal, small coin loss."""
        loss = max(0, min(self.coins // 4, 50))
        self.coins -= loss
        hr = TileMap(self.zones["hunters_rest"])
        start = hr.player_start or (3, 4)
        self.switch_zone("hunters_rest", *start)
        for mon in self.party + self.storage:
            mon.hp = mon.max_hp
            for mv in mon.moves:
                mv["pp"] = mv["data"]["pp"]
        self._flash(f"You rushed to the Healing Lodge! Lost {loss} coins.")

    def _on_step(self):
        """Called each time the player finishes a step onto a new tile."""
        warp = self.tile_map.warp_at(self.player.tile_x, self.player.tile_y)
        if warp is not None:
            self.switch_zone(warp["zone"], warp["tx"], warp["ty"])
            return
        zone = self.zones[self.zone_id]
        self._check_trainer_sight()
        if "encounters" in zone and self.tile_map.is_tall_grass(
            self.player.tile_x, self.player.tile_y
        ):
            if self.encounters.should_trigger():
                from ..battle.scene import BattleScene

                enemy = roll_wild(zone, party=self.party)
                self.game.start_battle(
                    BattleScene(self.game, self.party[0], enemy, inventory=self.inventory)
                )

    def _trainer_at(self, tx, ty):
        for tid, t in trainers_in_zone(self.zone_id):
            if t["x"] == tx and t["y"] == ty:
                return tid, t
        return None

    def _check_trainer_sight(self):
        """Start a trainer battle when the player steps adjacent to a trainer."""
        found = self._trainer_at(self.player.tile_x, self.player.tile_y)
        if found is None:
            for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                found = self._trainer_at(self.player.tile_x + dx, self.player.tile_y + dy)
                if found is not None:
                    break
        if found is None:
            return
        tid, trainer = found
        if not self.trainer_state.can_challenge(tid, trainer):
            return
        if self.trainer_state.defeated.get(tid) and not trainer.get("rival"):
            pass  # cooldown handled by can_challenge
        self.trainer_state.record_start(tid)
        from ..battle.scene import TrainerBattle

        self.game.start_battle(
            TrainerBattle(self.game, self.party[0], tid, trainer, inventory=self.inventory)
        )

    def _interact(self):
        """Confirm while facing a building: heal at the Lodge, rest and save at home."""
        dx, dy = {
            "up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0),
        }[self.player.facing]
        tx, ty = self.player.tile_x + dx, self.player.tile_y + dy
        if self.tile_map.is_healing_lodge(tx, ty):
            self._heal_party()
        elif self.tile_map.tile_at(tx, ty) == "S":
            self._open_shop()
        elif self.tile_map.tile_at(tx, ty) == "#":
            from ..save import save_game

            if self.save_slot is not None:
                save_game(self, self.save_slot)
                self._flash("You rested at home. Game saved!")
            else:
                self._flash("Home sweet home!")

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

        if input_mod.CONFIRM in self.game.input.pressed:
            self._interact()

        self.play_time += dt
        if self.message_timer > 0:
            self.message_timer -= dt
            if self.message_timer <= 0:
                self.message = None

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
        if self.message:
            self._draw_flash(surface)
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
        if self.card_menu:
            if input_mod.CONFIRM in pressed or input_mod.CANCEL in pressed:
                self.card_menu = False
            return
        if self.save_menu:
            self._draw_save_menu(surface)
            return
        if self.card_menu:
            self._draw_trainer_card(surface)
            return
        if self.party_menu:
            self._draw_party(surface)
            return
        title = self.font.render("PAUSED", False, WHITE, BLACK)
        surface.blit(title, (rect.centerx - title.get_width() // 2, 46))
        for i, option in enumerate(self._PAUSE_MENU):
            label = self.font.render(option, False, WHITE, BLACK)
            y = 60 + i * 12
            surface.blit(label, (rect.centerx - label.get_width() // 2 + 6, y))
            if i == self.pause_index:
                x = rect.centerx - label.get_width() // 2 - 4
                pygame.draw.polygon(
                    surface, WHITE, [(x - 6, y + 3), (x - 1, y + 6), (x - 6, y + 9)]
                )

    def _draw_save_menu(self, surface):
        """Three-slot save picker drawn over the pause box."""
        from ..save import SLOT_COUNT

        rect = pygame.Rect(60, 40, 120, 80)
        for i in range(SLOT_COUNT):
            label = self.font.render(f"Slot {i + 1}", False, WHITE, BLACK)
            y = 52 + i * 12
            surface.blit(label, (rect.centerx - 20, y))
            if i == self.save_index:
                pygame.draw.polygon(
                    surface, WHITE,
                    [(rect.centerx - 28, y + 3), (rect.centerx - 23, y + 6),
                     (rect.centerx - 28, y + 9)],
                )

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

    _PAUSE_MENU = ("Monsters", "Trainer Card", "Save", "Close")

    def _update_pause_menu(self):
        """Handle input while the pause menu is open."""
        pressed = self.game.input.pressed
        if self.card_menu:
            if input_mod.CONFIRM in pressed or input_mod.CANCEL in pressed:
                self.card_menu = False
            return
        if self.save_menu:
            from ..save import save_game, load_game, SLOT_COUNT

            if input_mod.UP in pressed:
                self.save_index = (self.save_index - 1) % SLOT_COUNT
            elif input_mod.DOWN in pressed:
                self.save_index = (self.save_index + 1) % SLOT_COUNT
            elif input_mod.CONFIRM in pressed:
                save_game(self, self.save_index)
                self.save_slot = self.save_index
                self.save_menu = False
                self.paused = False
                self._flash(f"Saved to slot {self.save_index + 1}!")
            elif input_mod.CANCEL in pressed:
                self.save_menu = False
            return
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
        if input_mod.UP in pressed:
            self.pause_index = (self.pause_index - 1) % len(self._PAUSE_MENU)
        elif input_mod.DOWN in pressed:
            self.pause_index = (self.pause_index + 1) % len(self._PAUSE_MENU)
        elif input_mod.CONFIRM in pressed:
            choice = self._PAUSE_MENU[self.pause_index]
            if choice == "Monsters":
                self.party_menu = True
                self.party_index = 0
            elif choice == "Trainer Card":
                self.card_menu = True
            elif choice == "Save":
                self.save_menu = True
                self.save_index = 0
            elif choice == "Close":
                self.paused = False


    def _draw_flash(self, surface):
        lines = [self.message[i:i+34] for i in range(0, len(self.message), 34)][:2]
        rect = pygame.Rect(0, SCREEN_H - 14 - 10 * len(lines), SCREEN_W, 10 * len(lines) + 4)
        pygame.draw.rect(surface, BLACK, rect)
        pygame.draw.rect(surface, WHITE, rect, 1)
        for i, line in enumerate(lines):
            label = self.font.render(line, False, WHITE, BLACK)
            surface.blit(label, (rect.x + 3, rect.y + 2 + i * 10))

    def _draw_trainer_card(self, surface):
        """Trainer card: play time, battles won, monsters caught, coins (spec 11)."""
        minutes = int(self.play_time // 60)
        lines = [
            "TRAINER CARD",
            f"Battles Won: {self.battles_won}",
            f"Monsters Caught: {self.monsters_caught}",
            f"Coins: {self.coins}",
            f"Play Time: {minutes}m",
        ]
        rect = pygame.Rect(30, 20, SCREEN_W - 60, 12 * len(lines) + 8)
        pygame.draw.rect(surface, BLACK, rect)
        pygame.draw.rect(surface, WHITE, rect, 1)
        for i, line in enumerate(lines):
            label = self.font.render(line, False, WHITE, BLACK)
            surface.blit(label, (rect.x + 6, rect.y + 4 + i * 12))
