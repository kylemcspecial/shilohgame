"""Battle scene: intro, message log, and a Fight/Run command menu."""
import math

import pygame

from ..engine.constants import SCREEN_W, SCREEN_H, BLACK, WHITE
from ..engine.fonts import get_font
from ..engine import input as input_mod
from ..battle import battle as battle_mod
from ..battle import catch as catch_mod
from ..battle import mon_sprites
from ..monsters.monster import Monster, load_species, load_moves, load_type_chart
from ..monsters import leveling

_MENU = ("Fight", "Bag", "Catch", "Switch", "Run")


class BattleScene:
    """Turn-based wild battle with a player monster and a wild monster."""

    def __init__(self, game, player_monster, enemy_monster, inventory=None):
        self.game = game
        self.player_mon = player_monster
        self.enemy_mon = enemy_monster
        self.inventory = inventory
        self.type_chart = load_type_chart()
        self.font = get_font(8)
        self.menu_index = 0
        self.messages = [f"A wild {enemy_monster.name} appeared!"]
        self._read = 0
        self._confirmed = False
        self.finished = False
        self.outcome = None
        self.intro_timer = 1.0
        self.caught_monster = None
        self.trap_menu = False
        self.trap_index = 0
        self.bag_menu = False
        self.bag_index = 0
        self.shake_timer = 0.0
        self.party = list(getattr(game.world, "party", [player_monster]))
        self.participants = [player_monster]  # monsters that fought in this battle
        self.switch_menu = False
        self.switch_index = 0
        self.force_switch = False
        self.move_menu = False
        self.move_index = 0
        self.coins_won = 0

    def _append_messages(self, new_messages):
        """Append messages; nothing appended may be skipped.

        `_read` is the index of the line currently displayed and `_confirmed`
        marks that the player acted on it (a new command). Only then does the
        display move to the first new message; chained appends within one
        action (e.g. catch failure followed by the enemy's attack) stay put
        so each line waits for its own confirm.
        """
        if not new_messages:
            return
        first_new = len(self.messages)
        self.messages.extend(new_messages)
        if self._confirmed:
            self._read = first_new
            self._confirmed = False

    @property
    def message_index(self):
        """Index of the message currently displayed."""
        return min(self._read, len(self.messages) - 1)

    def _advance_message(self):
        if self._read < len(self.messages) - 1:
            self._read += 1
            return True
        return False

    def _xp_messages(self, xp):
        """Apply XP and build level-up/evolution/learned-move messages.

        The active monster gets full XP; other battle participants that
        are still standing get half (rounded down, min 1 when xp > 0).
        """
        messages = []
        for mon in self.participants:
            if mon is self.player_mon:
                share = xp
            elif mon.fainted:
                continue
            else:
                share = max(1, xp // 2) if xp > 0 else 0
            if share <= 0:
                continue
            name_before = mon.name
            events = leveling.grant_xp(mon, share)
            for event in events:
                if event["type"] == "level_up":
                    self.game.audio.level_up()
                    messages.append(f"{name_before} grew to level {event['level']}!")
                elif event["type"] == "evolved":
                    messages.append(
                        f"What? {mon.pre_evolution_name} evolved into {mon.name}!"
                    )
                elif event["type"] == "learned_move":
                    move_name = load_moves()[event["move"]]["name"]
                    messages.append(f"{mon.name} learned {move_name}!")
        return messages

    # ------------------------------------------------------------------ input

    def update(self, dt):
        if self.shake_timer > 0:
            self.shake_timer -= dt
        if self.intro_timer > 0:
            self.intro_timer -= dt
            return

        pressed = self.game.input.pressed
        has_pending = self.message_index < len(self.messages) - 1
        if has_pending:
            if input_mod.CONFIRM in pressed or input_mod.CANCEL in pressed:
                self._advance_message()
            return
        if self.force_switch and not self.switch_menu:
            self.switch_menu = True
            self.switch_index = 0
            return
        if self.move_menu:
            moves = self.player_mon.moves
            if not moves:
                self.move_menu = False
            elif input_mod.UP in pressed:
                self.move_index = (self.move_index - 1) % len(moves)
            elif input_mod.DOWN in pressed:
                self.move_index = (self.move_index + 1) % len(moves)
            elif input_mod.CONFIRM in pressed:
                chosen = moves[self.move_index]
                self.move_menu = False
                if chosen["pp"] <= 0:
                    # Out of PP: pass the turn (a struggle) so the enemy attacks
                    # and the battle can still resolve toward defeat/revival.
                    self._confirmed = True
                    self._append_messages([
                        f"{chosen['data']['name']} has no PP left!",
                        f"{self.player_mon.name} can only struggle!",
                    ])
                    self._take_turn(None)
                else:
                    self._take_turn(chosen)
            elif input_mod.CANCEL in pressed:
                self.move_menu = False
            return
        if self.switch_menu:
            living = self._switchable()
            if not living:
                self.switch_menu = False
                self.force_switch = False
            elif input_mod.UP in pressed or input_mod.LEFT in pressed:
                self.switch_index = (self.switch_index - 1) % len(living)
            elif input_mod.DOWN in pressed or input_mod.RIGHT in pressed:
                self.switch_index = (self.switch_index + 1) % len(living)
            elif input_mod.CONFIRM in pressed:
                self._do_switch(living[self.switch_index])
            elif input_mod.CANCEL in pressed and not self.force_switch:
                self.switch_menu = False
            return
        if self.trap_menu:
            available = self.inventory.traps()
            if not available:
                self.trap_menu = False
            elif input_mod.UP in pressed or input_mod.LEFT in pressed:
                self.trap_index = (self.trap_index - 1) % len(available)
            elif input_mod.DOWN in pressed or input_mod.RIGHT in pressed:
                self.trap_index = (self.trap_index + 1) % len(available)
            elif input_mod.CONFIRM in pressed:
                self._choose_trap(self.trap_index)
            elif input_mod.CANCEL in pressed:
                self.trap_menu = False
            return
        if self.bag_menu:
            available = self.inventory.usables()
            if not available:
                self.bag_menu = False
            elif input_mod.UP in pressed or input_mod.LEFT in pressed:
                self.bag_index = (self.bag_index - 1) % len(available)
            elif input_mod.DOWN in pressed or input_mod.RIGHT in pressed:
                self.bag_index = (self.bag_index + 1) % len(available)
            elif input_mod.CONFIRM in pressed:
                self._use_item(available[self.bag_index][0], available[self.bag_index][1])
            elif input_mod.CANCEL in pressed:
                self.bag_menu = False
            return
        if self.finished:
            if input_mod.CONFIRM in pressed or input_mod.CANCEL in pressed:
                self.game.end_battle()
            return

        if input_mod.UP in pressed or input_mod.LEFT in pressed:
            self.menu_index = (self.menu_index - 1) % len(_MENU)
        elif input_mod.DOWN in pressed or input_mod.RIGHT in pressed:
            self.menu_index = (self.menu_index + 1) % len(_MENU)
        elif input_mod.CONFIRM in pressed:
            self._choose(_MENU[self.menu_index])

    def toggle_pause(self):
        pass

    def _choose(self, command):
        self._confirmed = True
        if command == "Run":
            self._try_run()
            return
        if command == "Switch":
            living = [m for m in self.party if not m.fainted and m is not self.player_mon]
            if not living:
                self._append_messages(["No other monsters to send out!"])
                return
            self.switch_menu = True
            self.switch_index = 0
            return
        if command == "Catch":
            if not self.inventory.traps():
                self._append_messages(["You have no traps left!"])
                return
            self.trap_menu = True
            self.trap_index = 0
            return
        if command == "Bag":
            if not self.inventory.usables():
                self._append_messages(["Your bag is empty!"])
                return
            self.bag_menu = True
            self.bag_index = 0
            return
        self.move_menu = True
        self.move_index = 0

    def _choose_trap(self, index):
        self._confirmed = True
        available = self.inventory.traps()
        if not available or index >= len(available):
            self.trap_menu = False
            return
        item_id, item = available[index]
        self.trap_menu = False
        if not catch_mod.is_weak_enough(self.enemy_mon):
            self._append_messages(["It's too strong to catch yet!"])
            return
        self.inventory.remove(item_id)
        self.shake_timer = 1.2
        success, chance = catch_mod.attempt_catch(
            self.enemy_mon, item["catch_bonus"], self.player_mon.level
        )
        if success:
            self.game.audio.catch_success()
            self.caught_monster = self.enemy_mon
            catch_messages = [f"Gotcha! {self.enemy_mon.name} was caught!"]
            xp = leveling.xp_for_defeat(
                self.enemy_mon.level, self.enemy_mon.species["tier"], self.player_mon.level
            )
            catch_messages.extend(self._xp_messages(xp))
            self._append_messages(catch_messages)
            self.outcome = "caught"
            self.finished = True
        else:
            self.game.audio.catch_fail()
            self._append_messages(["Oh no! It broke free!"])
            self._enemy_free_attack()

    def _use_item(self, item_id, item):
        """Use a potion or berry on the active monster; enemy gets a free attack."""
        self._confirmed = True
        self.bag_menu = False
        target = self.player_mon
        if item["kind"] == "potion":
            healed = min(item["heal"], target.max_hp - target.hp)
            if healed <= 0:
                self._append_messages([f"{target.name} is already at full health!"])
                return
            self.inventory.remove(item_id)
            target.hp += healed
            self.game.audio.heal()
            self._append_messages([
                f"You used a {item['name']}!",
                f"{target.name} recovered {healed} HP!",
            ])
        elif item["kind"] == "berry":
            low_pp = [mv for mv in target.moves if mv["pp"] < mv["data"]["pp"]]
            if not low_pp:
                self._append_messages([f"{target.name} has full PP already!"])
                return
            self.inventory.remove(item_id)
            for mv in low_pp:
                mv["pp"] = min(mv["data"]["pp"], mv["pp"] + item["pp_restore"])
            self.game.audio.heal()
            self._append_messages([
                f"You used a {item['name']}!",
                f"{target.name} feels refreshed!",
            ])
        else:
            return
        self._enemy_free_attack()

    def _take_turn(self, player_move):
        player_first = battle_mod.goes_first(self.player_mon, self.enemy_mon)
        order = (
            (self.player_mon, self.enemy_mon, player_move),
            (self.enemy_mon, self.player_mon, self._enemy_move()),
        )
        if not player_first:
            order = (order[1], order[0])

        messages = []
        for attacker, defender, move in order:
            if self.player_mon.fainted or self.enemy_mon.fainted:
                break
            if move is None:
                if attacker is self.player_mon:
                    messages.append(f"{attacker.name} has no moves left!")
                    attacker.hp = max(0, attacker.hp - 1)
                    messages.append(f"{attacker.name} struggles and hurts itself!")
                continue
            _, new = battle_mod.apply_move(attacker, defender, move, self.type_chart)
            messages.extend(new)

        self._append_messages(messages or ["Nothing happened!"])
        self._check_outcome()

    def _enemy_move(self):
        import random

        usable = self.enemy_mon.usable_moves()
        return random.choice(usable) if usable else None

    def _switchable(self):
        return [m for m in self.party if not m.fainted and m is not self.player_mon]

    def _next_living_party_member(self):
        for m in self.party:
            if not m.fainted and m is not self.player_mon:
                return m
        return None

    def _do_switch(self, new_mon):
        """Switch active monster; voluntary switching gives the enemy a free attack."""
        self._confirmed = True
        if new_mon not in self.participants:
            self.participants.append(new_mon)
        forced = self.force_switch
        self.player_mon = new_mon
        self.switch_menu = False
        self.force_switch = False
        self._append_messages([f"Go, {new_mon.name}!"])
        if (
            not forced
            and not self.finished
            and not self.player_mon.fainted
            and not self.enemy_mon.fainted
        ):
            self._enemy_free_attack()

    def _try_run(self):
        if battle_mod.run_chance(self.player_mon, self.enemy_mon):
            self._append_messages(["Got away safely!"])
            self.outcome = "ran"
            self.finished = True
        else:
            self._append_messages(["Couldn't get away!"])
            self._enemy_free_attack()

    def _enemy_free_attack(self):
        """The wild monster attacks after a failed catch or run attempt."""
        move = self._enemy_move()
        if move is None:
            return
        _, new = battle_mod.apply_move(self.enemy_mon, self.player_mon, move, self.type_chart)
        self._append_messages(new)
        self._check_outcome()

    def _check_outcome(self):
        if self.enemy_mon.fainted:
            self.game.audio.hit()
            outcome_messages = [f"The wild {self.enemy_mon.name} fainted!"]
            xp = leveling.xp_for_defeat(
                self.enemy_mon.level, self.enemy_mon.species["tier"], self.player_mon.level
            )
            outcome_messages.extend(self._xp_messages(xp))
            coins = 2 * self.enemy_mon.level + 3 * (self.enemy_mon.species["tier"] - 1)
            outcome_messages.append(f"You found {coins} coins!")
            self.coins_won = coins
            outcome_messages.append("You won the battle!")
            self._append_messages(outcome_messages)
            self.outcome = "won"
            self.finished = True
        elif self.player_mon.fainted:
            if self._next_living_party_member() is not None:
                self._append_messages([
                    f"{self.player_mon.name} fainted!",
                    "Send out another monster?",
                ])
                self.force_switch = True
                return
            self._append_messages([
                f"{self.player_mon.name} fainted!",
                "You hurried back home...",
            ])
            self.outcome = "lost"
            self.finished = True

    # ------------------------------------------------------------------- gfx

    def draw(self, surface):
        surface.fill((40, 60, 90))
        if self.intro_timer > 0:
            self._draw_intro(surface)
            return
        self._draw_mon(surface, self.enemy_mon, (SCREEN_W - 52, 14), back=False)
        self._draw_mon(surface, self.player_mon, (14, SCREEN_H - 66), back=True)
        self._draw_shake(surface)
        self._draw_hp_box(surface, self.enemy_mon, (SCREEN_W - 92, 46))
        self._draw_hp_box(surface, self.player_mon, (4, SCREEN_H - 88))
        self._draw_message(surface)
        if self.finished:
            return
        if self.move_menu:
            self._draw_move_menu(surface)
            return
        if self.switch_menu or self.trap_menu or self.bag_menu:
            if self.switch_menu:
                self._draw_switch_menu(surface)
            elif self.trap_menu:
                self._draw_trap_menu(surface)
            else:
                self._draw_bag_menu(surface)
        elif self.message_index >= len(self.messages) - 1:
            self._draw_menu(surface)

    def _draw_intro(self, surface):
        label = self.font.render("A wild monster draws near!", False, WHITE, BLACK)
        surface.blit(label, ((SCREEN_W - label.get_width()) // 2, SCREEN_H // 2 - 4))

    def _draw_mon(self, surface, mon, pos, back):
        """Unique per-species sprite with outline, idle bob, and shadow."""
        x, y = pos
        bob = int(pygame.time.get_ticks() / 400) % 2
        if not back:
            y += bob
        sprite = mon_sprites.build_monster_sprite(mon.species_id, mon.types)
        if getattr(mon, "shiny", False):
            sprite = sprite.copy()
            overlay = pygame.Surface(sprite.get_size(), pygame.SRCALPHA)
            overlay.fill((255, 215, 80, 70))
            sprite.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
            now = pygame.time.get_ticks() / 150
            spark = int(now) % 3
            for i in range(4):
                angle = now + i * 1.6
                sx = 16 + int(12 * math.cos(angle))
                sy = 16 + int(12 * math.sin(angle))
                if i % 3 == spark:
                    pygame.draw.circle(sprite, (255, 250, 200), (sx, sy), 1)
        shadow = pygame.Surface((32, 5), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (16, 16, 24, 90), (4, 0, 24, 5))
        surface.blit(shadow, (x + 2, y + 30))
        surface.blit(sprite, (x, y))

    def _draw_hp_box(self, surface, mon, pos):
        x, y = pos
        rect = pygame.Rect(x, y, 88, 24)
        pygame.draw.rect(surface, BLACK, rect)
        pygame.draw.rect(surface, WHITE, rect, 1)
        name = self.font.render(mon.name, False, WHITE, BLACK)
        surface.blit(name, (x + 2, y + 2))
        level = self.font.render(f"L{mon.level}", False, WHITE, BLACK)
        surface.blit(level, (x + rect.w - level.get_width() - 2, y + 2))
        from ..world.gfx import PALETTES

        ui = PALETTES["ui"]
        frac = mon.hp / mon.max_hp
        bar_color = ui["hp_hi"] if frac > 0.5 else ui["hp_mid"] if frac > 0.2 else ui["hp_low"]
        pygame.draw.rect(surface, (60, 60, 60), (x + 2, y + 14, 84, 6))
        bar_w = int(84 * frac)
        if bar_w > 0:
            pygame.draw.rect(surface, bar_color, (x + 2, y + 14, bar_w, 6))
            pygame.draw.line(surface, tuple(min(255, c + 60) for c in bar_color),
                             (x + 2, y + 14), (x + 1 + bar_w, y + 14), 1)

    def _draw_message(self, surface):
        rect = pygame.Rect(0, SCREEN_H - 26, SCREEN_W, 26)
        pygame.draw.rect(surface, BLACK, rect)
        pygame.draw.rect(surface, WHITE, rect, 1)
        text = self.messages[self.message_index]
        lines = textwrap_lines(text, self.font, rect.w - 8)
        for i, line in enumerate(lines[:2]):
            label = self.font.render(line, False, WHITE)
            surface.blit(label, (rect.x + 4, rect.y + 4 + i * 10))

    def _draw_menu(self, surface):
        row_h = 11
        height = row_h * len(_MENU) + 3
        width = max(58, max(self.font.size(option)[0] + 14 for option in _MENU))
        rect = pygame.Rect(SCREEN_W - width, SCREEN_H - height - 2, width, height)
        rect.y = SCREEN_H - height - 2
        pygame.draw.rect(surface, BLACK, rect)
        pygame.draw.rect(surface, WHITE, rect, 1)
        for i, option in enumerate(_MENU):
            color = WHITE
            label = self.font.render(option, False, color, BLACK)
            y = rect.y + 2 + i * row_h
            surface.blit(label, (rect.x + 10, y))
            if i == self.menu_index:
                pygame.draw.polygon(
                    surface,
                    WHITE,
                    [(rect.x + 3, y + 4), (rect.x + 8, y + 7), (rect.x + 3, y + 10)],
                )

    def _draw_move_menu(self, surface):
        """Move picker: name, type, PP; greyed out at 0 PP."""
        moves = self.player_mon.moves
        row_h = 11
        rect = pygame.Rect(4, SCREEN_H - 26 - row_h * len(moves) - 2, 150,
                           row_h * len(moves) + 4)
        pygame.draw.rect(surface, BLACK, rect)
        pygame.draw.rect(surface, WHITE, rect, 1)
        for i, mv in enumerate(moves):
            has_pp = mv["pp"] > 0
            color = WHITE if has_pp else (110, 110, 110)
            label = self.font.render(
                f"{mv['data']['name']} {mv['data']['type'][:3].upper()} PP{mv['pp']}",
                False, color, BLACK,
            )
            y = rect.y + 2 + i * row_h
            surface.blit(label, (rect.x + 10, y))
            if i == self.move_index:
                pygame.draw.polygon(
                    surface, WHITE,
                    [(rect.x + 3, y + 3), (rect.x + 8, y + 6), (rect.x + 3, y + 9)],
                )

    def _draw_switch_menu(self, surface):
        living = self._switchable()
        if not living:
            return
        row_h = 11
        rect = pygame.Rect(4, 20, 100, row_h * len(living) + 2)
        pygame.draw.rect(surface, BLACK, rect)
        pygame.draw.rect(surface, WHITE, rect, 1)
        for i, mon in enumerate(living):
            label = self.font.render(f"{mon.name} L{mon.level}", False, WHITE, BLACK)
            y = rect.y + 1 + i * row_h
            surface.blit(label, (rect.x + 10, y))
            if i == self.switch_index:
                pygame.draw.polygon(
                    surface, WHITE,
                    [(rect.x + 3, y + 4), (rect.x + 8, y + 7), (rect.x + 3, y + 10)],
                )

    def _draw_trap_menu(self, surface):
        available = self.inventory.traps()
        rect = pygame.Rect(SCREEN_W - 84, SCREEN_H - 26 - 11 * len(available), 84, 11 * len(available) + 2)
        pygame.draw.rect(surface, BLACK, rect)
        pygame.draw.rect(surface, WHITE, rect, 1)
        for i, (item_id, item) in enumerate(available):
            label = self.font.render(
                f"{item['name']} x{self.inventory.count(item_id)}", False, WHITE, BLACK
            )
            y = rect.y + 1 + i * 11
            surface.blit(label, (rect.x + 10, y))
            if i == self.trap_index:
                pygame.draw.polygon(
                    surface, WHITE,
                    [(rect.x + 3, y + 4), (rect.x + 8, y + 7), (rect.x + 3, y + 10)],
                )

    def _draw_bag_menu(self, surface):
        """Bag picker: potions and berries with counts, drawn like the trap menu."""
        available = self.inventory.usables()
        rect = pygame.Rect(
            SCREEN_W - 84, SCREEN_H - 26 - 11 * len(available), 84, 11 * len(available) + 2
        )
        pygame.draw.rect(surface, BLACK, rect)
        pygame.draw.rect(surface, WHITE, rect, 1)
        for i, (item_id, item) in enumerate(available):
            label = self.font.render(
                f"{item['name']} x{self.inventory.count(item_id)}", False, WHITE, BLACK
            )
            y = rect.y + 1 + i * 11
            surface.blit(label, (rect.x + 10, y))
            if i == self.bag_index:
                pygame.draw.polygon(
                    surface, WHITE,
                    [(rect.x + 3, y + 4), (rect.x + 8, y + 7), (rect.x + 3, y + 10)],
                )

    def _draw_shake(self, surface):
        """Draw a wobbling trap over the enemy monster while shaking."""
        if self.shake_timer <= 0:
            return
        wobble = math.sin(pygame.time.get_ticks() / 60.0) * 3
        x = SCREEN_W - 52 + 16 + wobble
        y = 14 + 16
        pygame.draw.circle(surface, (180, 60, 50), (int(x), int(y)), 8)
        pygame.draw.circle(surface, (240, 180, 120), (int(x), int(y - 4)), 4)


def move_name(move_id):
    return load_moves()[move_id]["name"]


def _darken(color):
    return tuple(c // 2 for c in color)


class TrainerBattle(BattleScene):
    """Battle vs a trainer's team: no running, no catching, coins on win."""

    def __init__(self, game, player_monster, trainer_id, trainer_data, inventory=None):
        from ..monsters.monster import Monster, load_species, load_moves

        species, moves = load_species(), load_moves()
        rematch = bool(trainer_data.get("leader")) and bool(
            getattr(getattr(game, "world", None), "trainer_state", None)
            and game.world.trainer_state.defeated.get(trainer_id)
        )
        level_boost = 3 if rematch else 0
        self.team = [
            Monster(t["species"], min(50, t["level"] + level_boost), species, moves)
            for t in trainer_data["team"]
        ]
        super().__init__(game, player_monster, self.team[0], inventory=inventory)
        self.trainer_id = trainer_id
        self.trainer = trainer_data
        if trainer_data.get("rival"):
            rival_name = getattr(getattr(game, "world", None), "rival_name", None) or "Emmett"
            trainer_data = dict(trainer_data)
            trainer_data["name"] = rival_name
            trainer_data["intro"] = trainer_data["intro"].replace("squirt", "friend")
            trainer_data["defeat"] = trainer_data["defeat"].replace("squirt", "friend")
            self.trainer = trainer_data
        self.badge_won = trainer_data.get("badge") if trainer_data.get("leader") else None
        if rematch:
            self.badge_won = None  # badge already earned; rematch is for XP
        self.messages = [
            f"{trainer_data['name']} wants to battle!",
            f"\"{trainer_data['intro']}\"",
            f"{trainer_data['name']} sent out {self.team[0].name}!",
        ]
        self._read = 0
        self._confirmed = False

    def _choose(self, command):
        self._confirmed = True
        if command == "Run":
            self._append_messages(["You can't run from a trainer battle!"])
            return
        if command == "Catch":
            self._append_messages(["You can't catch another trainer's monster!"])
            return
        super()._choose(command)

    def _check_outcome(self):
        if self.enemy_mon.fainted:
            remaining = [m for m in self.team if not m.fainted and m is not self.enemy_mon]
            if remaining:
                self._append_messages([
                    f"{self.trainer['name']}'s {self.enemy_mon.name} fainted!",
                    f"{self.trainer['name']} sent out {remaining[0].name}!",
                ])
                self.enemy_mon = remaining[0]
                return
            from ..monsters import leveling

            strongest = max(m.level for m in self.team)
            xp = int(
                1.5 * leveling.xp_for_defeat(
                    strongest, max(m.species["tier"] for m in self.team),
                    self.player_mon.level,
                )
            )
            outcome_messages = [f"{self.enemy_mon.name} fainted!"]
            outcome_messages.extend(self._xp_messages(xp))
            outcome_messages.append(f"\"{self.trainer['defeat']}\"")
            outcome_messages.append(f"You got {self.trainer['reward']} coins!")
            self._append_messages(outcome_messages)
            self.outcome = "trainer_won"
            self.finished = True
        elif self.player_mon.fainted:
            if self._next_living_party_member() is not None:
                self._append_messages([
                    f"{self.player_mon.name} fainted!",
                    "Send out another monster?",
                ])
                self.force_switch = True
                return
            self._append_messages([
                f"{self.player_mon.name} fainted!",
                "You hurried back home...",
            ])
            self.outcome = "lost"
            self.finished = True


def textwrap_lines(text, font, max_width):
    words = text.split()
    lines, current = [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if font.size(candidate)[0] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines
