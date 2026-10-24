"""Battle scene: intro, message log, and a Fight/Run command menu."""
import math

import pygame

from ..engine.constants import SCREEN_W, SCREEN_H, BLACK, WHITE
from ..engine import input as input_mod
from ..battle import battle as battle_mod
from ..battle import catch as catch_mod
from ..monsters.monster import Monster, load_species, load_moves, load_type_chart
from ..monsters import leveling

_MENU = ("Fight", "Catch", "Switch", "Run")
_TRAP_MENU_ITEMS = ["Basic Trap", "Stout Trap", "High Trap", "Ultra Trap"]


class BattleScene:
    """Turn-based wild battle with a player monster and a wild monster."""

    def __init__(self, game, player_monster, enemy_monster, inventory=None):
        self.game = game
        self.player_mon = player_monster
        self.enemy_mon = enemy_monster
        self.inventory = inventory
        self.type_chart = load_type_chart()
        self.font = pygame.font.Font(pygame.font.get_default_font(), 8)
        self.menu_index = 0
        self.messages = [f"A wild {enemy_monster.name} appeared!"]
        self.message_index = 0
        self.finished = False
        self.outcome = None
        self.intro_timer = 1.0
        self.caught_monster = None
        self.trap_menu = False
        self.trap_index = 0
        self.shake_timer = 0.0
        self.party = list(getattr(game.world, "party", [player_monster]))
        self.switch_menu = False
        self.switch_index = 0
        self.force_switch = False

    # ------------------------------------------------------------------ input

    def update(self, dt):
        if self.intro_timer > 0:
            self.intro_timer -= dt
            return

        pressed = self.game.input.pressed
        if self.force_switch and not self.switch_menu:
            self.switch_menu = True
            self.switch_index = 0
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
        if self.message_index < len(self.messages) - 1:
            if input_mod.CONFIRM in pressed or input_mod.CANCEL in pressed:
                self.message_index += 1
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
        if command == "Run":
            self._try_run()
            return
        if command == "Switch":
            living = [m for m in self.party if not m.fainted and m is not self.player_mon]
            if not living:
                self.messages.append("No other monsters to send out!")
                self.message_index = len(self.messages) - 1
                return
            self.switch_menu = True
            self.switch_index = 0
            return
        if command == "Catch":
            if not self.inventory.traps():
                self.messages.append("You have no traps left!")
                self.message_index = len(self.messages) - 1
                return
            self.trap_menu = True
            self.trap_index = 0
            return
        self._take_turn(self.player_mon.usable_moves()[0] if self.player_mon.usable_moves() else None)

    def _choose_trap(self, index):
        available = self.inventory.traps()
        if not available or index >= len(available):
            self.trap_menu = False
            return
        item_id, item = available[index]
        self.trap_menu = False
        if not catch_mod.is_weak_enough(self.enemy_mon):
            self.messages.append("It's too strong to catch yet!")
            self.message_index = len(self.messages) - 1
            return
        self.inventory.remove(item_id)
        self.shake_timer = 1.2
        success, chance = catch_mod.attempt_catch(
            self.enemy_mon, item["catch_bonus"], self.player_mon.level
        )
        if success:
            self.caught_monster = self.enemy_mon
            self.messages.append(f"Gotcha! {self.enemy_mon.name} was caught!")
            self.message_index = len(self.messages) - 1
            self.outcome = "caught"
            self.finished = True
        else:
            self.messages.append("Oh no! It broke free!")
            self.message_index = len(self.messages) - 1
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
                continue
            _, new = battle_mod.apply_move(attacker, defender, move, self.type_chart)
            messages.extend(new)

        self.messages.extend(messages or ["Nothing happened!"])
        self.message_index = len(self.messages) - 1
        self._check_outcome()

    def _enemy_move(self):
        usable = self.enemy_mon.usable_moves()
        return usable[0] if usable else None

    def _switchable(self):
        return [m for m in self.party if not m.fainted and m is not self.player_mon]

    def _next_living_party_member(self):
        for m in self.party:
            if not m.fainted and m is not self.player_mon:
                return m
        return None

    def _do_switch(self, new_mon):
        """Switch active monster; switching always goes before the enemy attack."""
        self.player_mon = new_mon
        self.switch_menu = False
        self.force_switch = False
        self.messages.append(f"Go, {new_mon.name}!")
        self.message_index = len(self.messages) - 1
        if not self.finished and not self.player_mon.fainted and not self.enemy_mon.fainted:
            self._enemy_free_attack()

    def _try_run(self):
        if battle_mod.run_chance(self.player_mon, self.enemy_mon):
            self.messages.append("Got away safely!")
            self.outcome = "ran"
            self.finished = True
        else:
            self.messages.append("Couldn't get away!")
            self._enemy_free_attack()
            self._check_outcome()

    def _enemy_free_attack(self):
        """The wild monster attacks after a failed catch or run attempt."""
        move = self._enemy_move()
        if move is None:
            return
        _, new = battle_mod.apply_move(self.enemy_mon, self.player_mon, move, self.type_chart)
        self.messages.extend(new)
        self.message_index = len(self.messages) - 1
        self._check_outcome()

    def _check_outcome(self):
        if self.enemy_mon.fainted:
            self.messages.append(f"The wild {self.enemy_mon.name} fainted!")
            xp = leveling.xp_for_defeat(self.enemy_mon.level, self.enemy_mon.species["tier"])
            events = leveling.grant_xp(self.player_mon, xp)
            for event in events:
                if event["type"] == "level_up":
                    self.messages.append(f"{self.player_mon.name} grew to level {event['level']}!")
                elif event["type"] == "learned_move":
                    move_name = load_moves()[event["move"]]["name"]
                    self.messages.append(f"{self.player_mon.name} learned {move_name}!")
            self.messages.append("You won the battle!")
            self.outcome = "won"
            self.finished = True
        elif self.player_mon.fainted:
            if self._next_living_party_member() is not None:
                self.messages.append(f"{self.player_mon.name} fainted!")
                self.messages.append("Send out another monster?")
                self.force_switch = True
                return
            self.messages.append(f"{self.player_mon.name} fainted!")
            self.messages.append("You hurried back home...")
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
        if not self.finished and self.message_index >= len(self.messages) - 1:
            if self.switch_menu:
                self._draw_switch_menu(surface)
            elif self.trap_menu:
                self._draw_trap_menu(surface)
            else:
                self._draw_menu(surface)

    def _draw_intro(self, surface):
        label = self.font.render("A wild monster draws near!", False, WHITE, BLACK)
        surface.blit(label, ((SCREEN_W - label.get_width()) // 2, SCREEN_H // 2 - 4))

    def _draw_mon(self, surface, mon, pos, back):
        size = 32
        x, y = pos
        if back:
            x += math.sin(pygame.time.get_ticks() / 200.0) * 0  # stable; kept simple
        sprite = pygame.Surface((size, size), pygame.SRCALPHA)
        color = _MON_COLORS.get(mon.types[0], (200, 200, 200))
        pygame.draw.ellipse(sprite, color, (0, 8, 32, 24))
        pygame.draw.circle(sprite, _darken(color), (16, 10), 10)
        pygame.draw.circle(sprite, WHITE, (12, 8), 2)
        pygame.draw.circle(sprite, WHITE, (20, 8), 2)
        pygame.draw.circle(sprite, BLACK, (12, 8), 1)
        pygame.draw.circle(sprite, BLACK, (20, 8), 1)
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
        frac = mon.hp / mon.max_hp
        bar_color = (80, 200, 80) if frac > 0.5 else (240, 200, 60) if frac > 0.2 else (220, 60, 60)
        pygame.draw.rect(surface, (60, 60, 60), (x + 2, y + 14, 84, 6))
        pygame.draw.rect(surface, bar_color, (x + 2, y + 14, int(84 * frac), 6))

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
        rect = pygame.Rect(SCREEN_W - 64, SCREEN_H - 26, 64, 37)
        pygame.draw.rect(surface, BLACK, rect)
        pygame.draw.rect(surface, WHITE, rect, 1)
        for i, option in enumerate(_MENU):
            color = WHITE
            label = self.font.render(option, False, color, BLACK)
            y = rect.y + 2 + i * 11
            surface.blit(label, (rect.x + 10, y))
            if i == self.menu_index:
                pygame.draw.polygon(
                    surface,
                    WHITE,
                    [(rect.x + 3, y + 4), (rect.x + 8, y + 7), (rect.x + 3, y + 10)],
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

    def _draw_shake(self, surface):
        """Draw a wobbling trap over the enemy monster while shaking."""
        if self.shake_timer <= 0:
            return
        self.shake_timer -= 1 / 60.0
        wobble = math.sin(pygame.time.get_ticks() / 60.0) * 3
        x = SCREEN_W - 52 + 16 + wobble
        y = 14 + 16
        pygame.draw.circle(surface, (180, 60, 50), (int(x), int(y)), 8)
        pygame.draw.circle(surface, (240, 180, 120), (int(x), int(y - 4)), 4)


_MON_COLORS = {
    "leaf": (80, 180, 80),
    "water": (80, 130, 230),
    "storm": (240, 220, 110),
    "frost": (170, 220, 240),
    "stone": (150, 140, 120),
    "ember": (240, 120, 60),
}


def move_name(move_id):
    return load_moves()[move_id]["name"]


def _darken(color):
    return tuple(c // 2 for c in color)


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
