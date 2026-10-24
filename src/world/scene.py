"""Overworld scene: draws the zone, moves the player, shows a HUD."""
import json
import os

import pygame

from ..engine.constants import SCREEN_W, SCREEN_H, TILE_SIZE, BLACK, WHITE
from ..engine import input as input_mod
from ..engine.fonts import get_font
from ..world.tiles import TileMap, Tileset
from ..world.player import Player, camera_offset
from ..world.encounters import EncounterTracker
from ..monsters.monster import Monster, load_species, load_moves, roll_wild
from ..items.inventory import Inventory
from ..world.trainers import TrainerState, trainers_in_zone, load_trainers

_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data")


def _reset_battle_boosts(mon):
    """Full restore: HP, PP, and any in-battle stat boosts (brace stacks)."""
    mon.hp = mon.max_hp
    mon.brace_stacks = 0
    mon.defense = mon.species["base_stats"]["defense"] + mon.level // 2
    for mv in mon.moves:
        mv["pp"] = mv["data"]["pp"]

ENCOUNTER_RATE = 0.125  # ~1 in 8 steps in tall grass

# Zone progression chain: zone -> (next zone, leader guarding the exit to it).
# Forward exits are badge-gated; going back is always allowed.
_ZONE_CHAIN = {
    "whispering_pines": ("pineroot_crossing", "fenwick"),
    "pineroot_crossing": ("mossy_hollow", "boulder"),
    "mossy_hollow": ("fernfall", "ivy"),
    "fernfall": ("thornwood_ridge", "hazel"),
    "thornwood_ridge": ("mossy_hollow_gate", "rex"),
    "mossy_hollow_gate": ("emberfern_glade", "bram"),
}


def load_zones():
    with open(os.path.join(_DATA_DIR, "zones.json")) as f:
        return json.load(f)


class WorldScene:
    def __init__(self, game, intro=None):
        self.game = game
        self.player_name = (intro or {}).get("player", "Hunter")
        self.rival_name = (intro or {}).get("rival", "Emmett")
        starter_id = (intro or {}).get("starter", "fernpup")
        zones = load_zones()
        self.zones = zones["zones"]
        self.tileset = Tileset()
        self.zone_id = zones["start_zone"]
        self.tile_map = TileMap(self.zones[self.zone_id])
        start = self.tile_map.player_start or (2, 2)
        self.player = Player(*start)
        self.paused = False
        self.font = get_font(8)
        self.zone_banner_timer = 2.0
        self.party_menu = False
        self.party_index = 0
        self.pause_index = 0
        self.save_menu = False
        self.save_index = 0
        self.card_menu = False
        self.storage_menu = False
        self.storage_index = 0
        self.shop_menu = False
        self.shop_index = 0
        self._pending_save_message = None
        self.trainer_state = TrainerState()
        self.trainers_data = load_trainers()
        self.encounters = EncounterTracker(ENCOUNTER_RATE)
        self.inventory = Inventory({"basic_trap": 5, "potion_s": 3, "berry": 2})
        species_table = load_species()
        move_table = load_moves()
        self.party = [Monster(starter_id, 5, species_table, move_table)]
        self.storage = []
        self.coins = 60
        self.battles_won = 0
        self.monsters_caught = 0
        self.badges = []
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

    @property
    def player_level(self):
        """Player level from battles won (spec 6.5): 1 level per 2 wins, capped at 50."""
        return min(50, 1 + self.battles_won // 2)

    def toggle_pause(self):
        if self.game.scene is not self:
            return
        self.paused = not self.paused
        self.party_menu = False
        self.party_index = 0
        self.save_menu = False
        self.card_menu = False
        self.pause_index = 0
        if self.shop_menu and self.paused:
            self.shop_menu = False

    _SHOP_ITEMS = (
        "basic_trap", "stout_trap", "high_trap", "ultra_trap",
        "potion_s", "potion_m", "berry",
    )

    def _open_shop(self):
        """Open the Trap Shop menu (traps gated by player level, spec 7.2)."""
        self.shop_menu = True
        self.shop_index = 0

    _BADGE_SHOP_UNLOCKS = {
        "stout_trap": "pine",
        "potion_m": "stone",
        "high_trap": "gale",
        "ultra_trap": "thorn",
    }

    def _shop_available(self):
        """Shop entries with prices; rare stock unlocks by badge, not level."""
        from ..items.inventory import load_items

        items = load_items()
        badges = self.badge_ids
        entries = []
        for item_id in self._SHOP_ITEMS:
            item = items[item_id]
            needed = self._BADGE_SHOP_UNLOCKS.get(item_id)
            entries.append({
                "id": item_id,
                "name": item["name"],
                "cost": item["cost"],
                "unlocked": needed is None or needed in badges,
                "unlock_badge": needed,
            })
        return entries

    @staticmethod
    def _load_trap_unlocks():
        import json as _json

        with open(os.path.join(_DATA_DIR, "items.json")) as f:
            return _json.load(f)["trap_unlocks"]

    def _buy(self, entry):
        if not entry["unlocked"]:
            needed = entry["unlock_badge"]
            badge_name = next(
                (t["badge_name"] for t in self.trainers_data["trainers"].values()
                 if t.get("badge") == needed),
                "a badge",
            )
            self._flash(f"{entry['name']} unlocks with the {badge_name}!")
            return
        if self.coins < entry["cost"]:
            self._flash("Not enough coins!")
            return
        self.coins -= entry["cost"]
        self.inventory.add(entry["id"])
        self.game.audio.confirm()
        self._flash(f"Bought a {entry['name']}! ({entry['cost']} coins)")

    def _update_shop_menu(self):
        pressed = self.game.input.pressed
        entries = self._shop_available()
        if input_mod.UP in pressed:
            self.shop_index = (self.shop_index - 1) % len(entries)
        elif input_mod.DOWN in pressed:
            self.shop_index = (self.shop_index + 1) % len(entries)
        elif input_mod.CONFIRM in pressed:
            self._buy(entries[self.shop_index])
            self.shop_menu = False
        elif input_mod.CANCEL in pressed:
            self.shop_menu = False

    def _draw_shop(self, surface):
        """Trap Shop list with prices and badge locks."""
        entries = self._shop_available()
        row_h = 14
        rect = pygame.Rect(30, 14, SCREEN_W - 60, row_h * len(entries) + 16)
        pygame.draw.rect(surface, BLACK, rect)
        pygame.draw.rect(surface, WHITE, rect, 1)
        title = self.font.render("TRAP SHOP", False, WHITE, BLACK)
        surface.blit(title, (rect.centerx - title.get_width() // 2, rect.y + 3))
        for i, entry in enumerate(entries):
            y = rect.y + 14 + i * row_h
            if entry["unlocked"]:
                status = f"{entry['cost']}c"
            else:
                needed = entry["unlock_badge"]
                status = next(
                    (t["badge_name"].split()[0] for t in self.trainers_data["trainers"].values()
                     if t.get("badge") == needed),
                    "Badge",
                )
            color = WHITE if entry["unlocked"] else (120, 120, 120)
            label = self.font.render(f"{entry['name']} {status}", False, color, BLACK)
            surface.blit(label, (rect.x + 10, y))
            if i == self.shop_index:
                pygame.draw.polygon(
                    surface, WHITE,
                    [(rect.x + 3, y + 3), (rect.x + 8, y + 6), (rect.x + 3, y + 9)],
                )

    def _save_or_pick_slot(self, message):
        """Save to the current slot, or the first free slot on a fresh game.

        If every slot holds a save, open the slot picker instead of silently
        overwriting one — the player must explicitly choose what to replace.
        """
        from ..save import save_game, load_game, SLOT_COUNT

        pending = getattr(self, "_pending_save_message", None)
        if pending is not None:
            # Slot picker was open for this save; the player chose a slot.
            save_game(self, self.save_slot)
            self._pending_save_message = None
            self._flash(f"{pending} (Slot {self.save_slot + 1})")
            return

        if self.save_slot is None:
            free = next((slot for slot in range(SLOT_COUNT) if load_game(slot) is None), None)
            if free is None:
                # All slots occupied: require an explicit choice.
                self._pending_save_message = message
                self.save_menu = True
                self.save_index = 0
                self._flash("All slots full! Pick one to overwrite.")
                return
            self.save_slot = free
        save_game(self, self.save_slot)
        self._flash(f"{message} (Slot {self.save_slot + 1})")

    def _heal_party(self):
        """Full party heal, free, and auto-save (spec 10: lodge always saves)."""
        for mon in self.party + self.storage:
            _reset_battle_boosts(mon)
        self.game.audio.heal()
        self._save_or_pick_slot("Your monsters are fully healed! Game saved.")

    def _flash(self, text):
        self.message = text
        self.message_timer = 2.5

    def on_badge_won(self, badge_id):
        """Award a badge: record it, triple-coin payout, unlock message."""
        if badge_id in getattr(self, "_badges_awarded", ()):
            return
        self._badges_awarded = list(getattr(self, "_badges_awarded", ())) + [badge_id]
        trainer = next(
            t for t in self.trainers_data["trainers"].values()
            if t.get("badge") == badge_id
        )
        self.coins += trainer["reward"] * 3
        self.game.audio.catch_success()
        self._flash(f"You earned the {trainer['badge_name']}! (+{trainer['reward'] * 3} coins)")

    def heal_and_revive(self):
        """Called after a total-party faint: warp home, heal, small coin loss."""
        loss = max(0, min(self.coins // 4, 50))
        self.coins -= loss
        hr = TileMap(self.zones["hunters_rest"])
        start = hr.player_start or (3, 4)
        self.switch_zone("hunters_rest", *start)
        for mon in self.party + self.storage:
            _reset_battle_boosts(mon)
        self._flash(f"You rushed to the Healing Lodge! Lost {loss} coins.")

    def _first_living(self):
        """First non-fainted party member, or None if the whole party is down."""
        for mon in self.party:
            if not mon.fainted:
                return mon
        return None

    def _gate_block(self, warp):
        """Badge-gate forward exits: zone leader must be beaten to pass."""
        chain = _ZONE_CHAIN.get(self.zone_id)
        if chain is None or warp["zone"] != chain[0]:
            return None
        next_zone, leader_id = chain
        if self.trainer_state.defeated.get(leader_id):
            return None
        leader = self.trainers_data["trainers"][leader_id]
        return f"The gate to {self.zones[next_zone]['name']} is sealed! Beat {leader['name']} first!"

    @property
    def badge_ids(self):
        """Badge ids earned, mapped from defeated leader trainers."""
        badges = []
        for tid, t in self.trainers_data["trainers"].items():
            if t.get("leader") and self.trainer_state.defeated.get(tid):
                if t["badge"] not in badges:
                    badges.append(t["badge"])
        return badges

    def _on_step(self):
        """Called each time the player finishes a step onto a new tile."""
        warp = self.tile_map.warp_at(self.player.tile_x, self.player.tile_y)
        if warp is not None:
            blocked = self._gate_block(warp)
            if blocked is not None:
                self._flash(blocked)
                return
            self.switch_zone(warp["zone"], warp["tx"], warp["ty"])
            return
        zone = self.zones[self.zone_id]
        self._check_trainer_sight()
        if self.game.scene is not self:
            return  # a trainer battle started; don't roll a wild encounter over it
        if "encounters" in zone and self.tile_map.is_tall_grass(
            self.player.tile_x, self.player.tile_y
        ):
            if self.encounters.should_trigger():
                lead = self._first_living()
                if lead is None:
                    self.heal_and_revive()
                    return
                from ..battle.scene import BattleScene

                enemy = roll_wild(zone, party=self.party)
                self.game.start_battle(
                    BattleScene(self.game, lead, enemy, inventory=self.inventory)
                )

    def _rival_at(self, tx, ty):
        """Rival trainer standing at (tx, ty), if any."""
        for tid, t in trainers_in_zone(self.zone_id):
            if t.get("rival") and t["x"] == tx and t["y"] == ty:
                return tid, t
        return None

    def _trainer_at(self, tx, ty):
        for tid, t in trainers_in_zone(self.zone_id):
            if t["x"] == tx and t["y"] == ty:
                return tid, t
        return None

    def _leader_at(self, tx, ty):
        """Leader trainer standing at (tx, ty), if any."""
        for tid, t in trainers_in_zone(self.zone_id):
            if t.get("leader") and t["x"] == tx and t["y"] == ty:
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
        if trainer.get("rival") or trainer.get("leader"):
            return  # rivals and leaders are talk-to-battle, never ambushed
        if not self.trainer_state.can_challenge(tid, trainer):
            return
        if self.trainer_state.defeated.get(tid) and not trainer.get("rival"):
            pass  # cooldown handled by can_challenge
        lead = self._first_living()
        if lead is None:
            self.heal_and_revive()
            return
        self.trainer_state.record_start(tid)
        from ..battle.scene import TrainerBattle

        self.game.start_battle(
            TrainerBattle(self.game, lead, tid, trainer, inventory=self.inventory)
        )

    def _interact(self):
        """Confirm while facing a building: heal at the Lodge, rest and save at home."""
        dx, dy = {
            "up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0),
        }[self.player.facing]
        tx, ty = self.player.tile_x + dx, self.player.tile_y + dy
        rival = self._rival_at(tx, ty) or self._leader_at(tx, ty)
        if rival is not None:
            tid, trainer = rival
            if self.trainer_state.can_challenge(tid, trainer):
                self.trainer_state.record_start(tid)
                from ..battle.scene import TrainerBattle

                lead = self._first_living()
                if lead is not None:
                    self.game.start_battle(
                        TrainerBattle(self.game, lead, tid, trainer, inventory=self.inventory)
                    )
                else:
                    self.heal_and_revive()
            else:
                blocked = trainer.get("requires_defeat")
                if blocked and not self.trainer_state.defeated.get(blocked):
                    self._flash(f"{self.rival_name} says: catch me in Fernfall later!")
                elif trainer.get("leader"):
                    self._flash(f"{trainer['name']} says: come back stronger!")
                else:
                    self._flash(f"{self.rival_name} is resting. Try again soon!")
            return
        if self.tile_map.is_healing_lodge(tx, ty):
            self._heal_party()
        elif self.tile_map.tile_at(tx, ty) == "S":
            self._open_shop()
        elif self.tile_map.tile_at(tx, ty) == "#":
            self._save_or_pick_slot("You rested at home. Game saved!")

    def update(self, dt):
        if self.shop_menu:
            self._update_shop_menu()
            return
        if self.save_menu and not self.paused:
            # Slot picker opened by the lodge/home when all slots are full.
            self._update_pause_menu()
            return
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

        x0 = int(cam_x) // TILE_SIZE
        y0 = int(cam_y) // TILE_SIZE
        x1 = min(self.tile_map.width, x0 + SCREEN_W // TILE_SIZE + 2)
        y1 = min(self.tile_map.height, y0 + SCREEN_H // TILE_SIZE + 2)

        for ty in range(y0, y1):
            for tx in range(x0, x1):
                tile = self.tileset.render(self.tile_map.tile_at(tx, ty))
                surface.blit(tile, (tx * TILE_SIZE - cam_x, ty * TILE_SIZE - cam_y))

        self.player.draw(surface, cam_x, cam_y)
        self._draw_trainers(surface, cam_x, cam_y)
        self._draw_hud(surface)

        if self.zone_banner_timer > 0:
            self._draw_banner(surface, self.zone_name)
        if self.message:
            self._draw_flash(surface)
        if self.shop_menu:
            self._draw_shop(surface)
        if self.paused:
            self._draw_pause(surface)

    def _draw_trainers(self, surface, cam_x, cam_y):
        """Draw a marker at each trainer's tile so challenges are visible."""
        for tid, trainer in trainers_in_zone(self.zone_id):
            x = trainer["x"] * TILE_SIZE - cam_x
            y = trainer["y"] * TILE_SIZE - cam_y
            if not self.trainer_state.defeated.get(tid):
                if trainer.get("leader"):
                    color = (200, 50, 200)
                elif trainer.get("rival"):
                    color = (200, 60, 60)
                else:
                    color = (230, 160, 60)
            else:
                color = (110, 110, 110)
            pygame.draw.rect(surface, color, (x + 4, y + 2, 8, 5))
            pygame.draw.rect(surface, (90, 90, 160), (x + 5, y + 7, 6, 6))
            pygame.draw.circle(surface, (255, 220, 180), (x + 8, y + 3), 2)

    def _draw_hud(self, surface):
        """Always-visible HUD: zone, coins, and lead monster HP."""
        zone = self.font.render(self.zone_name, False, WHITE, BLACK)
        surface.blit(zone, (2, 2))
        coins = self.font.render(f"{self.coins}c", False, (255, 230, 140), BLACK)
        surface.blit(coins, (SCREEN_W - coins.get_width() - 2, 2))
        lead = self._first_living() or (self.party[0] if self.party else None)
        if lead is not None:
            hp = self.font.render(f"{lead.name} {lead.hp}/{lead.max_hp}",
                                  False, WHITE, BLACK)
            surface.blit(hp, (2, SCREEN_H - 12))

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
            self._draw_trainer_card(surface)
            return
        if self.save_menu:
            self._draw_save_menu(surface)
            return
        if getattr(self, "storage_menu", False):
            self._draw_storage(surface)
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

    def _draw_storage(self, surface):
        """Storage box list: stored monsters, confirm adds to party."""
        rect = pygame.Rect(8, 8, SCREEN_W - 16, 11 * max(1, len(self.storage)) + 4)
        pygame.draw.rect(surface, BLACK, rect)
        pygame.draw.rect(surface, WHITE, rect, 1)
        if not self.storage:
            label = self.font.render("Storage is empty! X to close.", False, WHITE, BLACK)
            surface.blit(label, (rect.x + 10, rect.y + 4))
            return
        for i, mon in enumerate(self.storage):
            hp = f"{mon.hp}/{mon.max_hp}"
            label = self.font.render(f"{mon.name} L{mon.level} {hp}", False, WHITE, BLACK)
            y = rect.y + 2 + i * 11
            surface.blit(label, (rect.x + 10, y))
            if i == self.storage_index:
                pygame.draw.polygon(
                    surface, WHITE,
                    [(rect.x + 3, y + 3), (rect.x + 8, y + 6), (rect.x + 3, y + 9)],
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

    _PAUSE_MENU = ("Monsters", "Trainer Card", "Storage", "Save", "Close")

    def _update_storage_menu(self):
        """Storage box: swap stored monsters with party members (Fern Badge)."""
        pressed = self.game.input.pressed
        stored = self.storage
        if not stored:
            if input_mod.CONFIRM in pressed or input_mod.CANCEL in pressed:
                self.storage_menu = False
            return
        if input_mod.UP in pressed:
            self.storage_index = (self.storage_index - 1) % len(stored)
        elif input_mod.DOWN in pressed:
            self.storage_index = (self.storage_index + 1) % len(stored)
        elif input_mod.CONFIRM in pressed:
            chosen = stored[self.storage_index]
            if len(self.party) < 6:
                self.storage.pop(self.storage_index)
                self.party.append(chosen)
                self.storage_index = 0
                self.game.audio.confirm()
            else:
                self._flash("Party is full! Move one to storage first.")
        elif input_mod.CANCEL in pressed:
            self.storage_menu = False

    def _update_pause_menu(self):
        """Handle input while the pause menu is open."""
        pressed = self.game.input.pressed
        if self.card_menu:
            if input_mod.CONFIRM in pressed or input_mod.CANCEL in pressed:
                self.card_menu = False
            return
        if self.save_menu:
            from ..save import SLOT_COUNT

            overwriting = getattr(self, "_pending_save_message", None) is not None
            if input_mod.UP in pressed:
                self.save_index = (self.save_index - 1) % SLOT_COUNT
            elif input_mod.DOWN in pressed:
                self.save_index = (self.save_index + 1) % SLOT_COUNT
            elif input_mod.CONFIRM in pressed:
                self.save_slot = self.save_index
                self.save_menu = False
                self.paused = False
                self._save_or_pick_slot("Game saved.")
            elif input_mod.CANCEL in pressed:
                self.save_menu = False
                if overwriting:
                    self._pending_save_message = None
                    self._flash("Save cancelled.")
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
        if getattr(self, "storage_menu", False):
            self._update_storage_menu()
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
            elif choice == "Storage":
                if "fern" in self.badge_ids:
                    self.storage_menu = True
                    self.storage_index = 0
                else:
                    self._flash("Storage unlocks with the Fern Badge!")
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

    _BADGE_ORDER = ("pine", "stone", "fern", "gale", "bloom", "thorn", "ember_crown")
    _BADGE_COLORS = {
        "pine": (90, 185, 90), "stone": (155, 145, 125), "fern": (60, 140, 60),
        "gale": (245, 222, 110), "bloom": (230, 120, 200), "thorn": (180, 60, 60),
        "ember_crown": (245, 120, 60),
    }

    def _draw_trainer_card(self, surface):
        """Trainer card: name, badges, stats (spec 11 + M9)."""
        minutes = int(self.play_time // 60)
        lines = [
            f"{self.player_name}'s CARD",
            f"Rival: {self.rival_name}",
            f"Battles Won: {self.battles_won}",
            f"Monsters Caught: {self.monsters_caught}",
            f"Coins: {self.coins}",
            f"Play Time: {minutes}m",
        ]
        rect = pygame.Rect(30, 16, SCREEN_W - 60, 12 * len(lines) + 22)
        pygame.draw.rect(surface, BLACK, rect)
        pygame.draw.rect(surface, WHITE, rect, 1)
        for i, line in enumerate(lines):
            label = self.font.render(line, False, WHITE, BLACK)
            surface.blit(label, (rect.x + 6, rect.y + 4 + i * 12))
        # badge strip: 7 slots, filled as earned
        earned = set(self.badge_ids)
        bx = rect.x + 6
        by = rect.bottom - 14
        for badge in self._BADGE_ORDER:
            color = self._BADGE_COLORS[badge] if badge in earned else (60, 60, 60)
            pygame.draw.circle(surface, color, (bx + 5, by + 5), 4)
            pygame.draw.circle(
                surface, WHITE if badge in earned else (110, 110, 110), (bx + 5, by + 5), 4, 1
            )
            bx += 24
