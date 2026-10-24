"""New-game intro: name the hunter, name the rival, pick a starter monster.

On-screen keyboard entry (arrow keys + confirm), so it works with the same
input mapping as the rest of the game, including gamepads.
"""
import string

import pygame

from ..engine.constants import SCREEN_W, SCREEN_H, BLACK, WHITE
from ..engine import input as input_mod
from ..engine.fonts import get_font

_ROWS = (
    tuple(string.ascii_uppercase),
    tuple(string.ascii_lowercase),
    ("0", "1", "2", "3", "4", "5", "6", "7", "8", "9"),
    ("-", "!", "?", ".", "DEL", "END"),
)

_STARTERS = (
    ("fernpup", "Fernpup", "Leaf", (90, 185, 90)),
    ("brookfin", "Brookfin", "Water", (85, 135, 235)),
    ("kindlekit", "Kindlekit", "Ember", (245, 120, 60)),
)

_MAX_NAME = 8


class IntroScene:
    """Three-step setup shown before a new game starts."""

    def __init__(self, game):
        self.game = game
        self.font = get_font(8)
        self.font_big = get_font(16)
        self.done = False
        self.result = None  # {"player": str, "rival": str, "starter": species_id}
        self.step = 0  # 0 hunter name, 1 rival name, 2 starter
        self.names = ["", ""]
        self.row = 0
        self.col = 0
        self.starter_index = 0
        self.flash = ""

    # ------------------------------------------------------------- input

    def _typing_active(self):
        return self.step in (0, 1)

    def _current_rows(self):
        return _ROWS

    def update(self, dt):
        pressed = self.game.input.pressed
        if self.step == 2:
            if input_mod.LEFT in pressed or input_mod.UP in pressed:
                self.starter_index = (self.starter_index - 1) % len(_STARTERS)
            elif input_mod.RIGHT in pressed or input_mod.DOWN in pressed:
                self.starter_index = (self.starter_index + 1) % len(_STARTERS)
            elif input_mod.CONFIRM in pressed:
                self.result = {
                    "player": self.names[0] or "Hunter",
                    "rival": self.names[1] or "Emmett",
                    "starter": _STARTERS[self.starter_index][0],
                }
                self.done = True
                self.game.audio.confirm()
            elif input_mod.CANCEL in pressed:
                self.step = 1
            return

        rows = self._current_rows()
        if input_mod.UP in pressed:
            self.row = (self.row - 1) % len(rows)
            self.col = min(self.col, len(rows[self.row]) - 1)
        elif input_mod.DOWN in pressed:
            self.row = (self.row + 1) % len(rows)
            self.col = min(self.col, len(rows[self.row]) - 1)
        elif input_mod.LEFT in pressed:
            self.col = (self.col - 1) % len(rows[self.row])
        elif input_mod.RIGHT in pressed:
            self.col = (self.col + 1) % len(rows[self.row])
        elif input_mod.CONFIRM in pressed:
            key = rows[self.row][self.col]
            if key == "END":
                if not self.names[self.step]:
                    self.flash = "Type a name first!"
                    return
                self.game.audio.confirm()
                self.step += 1
                self.row = self.col = 0
                self.flash = ""
            elif key == "DEL":
                self.names[self.step] = self.names[self.step][:-1]
            elif len(self.names[self.step]) < _MAX_NAME:
                self.names[self.step] += key
                self.flash = ""

    # --------------------------------------------------------------- gfx

    def draw(self, surface):
        surface.fill(BLACK)
        if self.step == 2:
            self._draw_starter(surface)
        else:
            self._draw_name_entry(surface)

    def _title(self, surface, text):
        label = self.font_big.render(text, False, WHITE, BLACK)
        surface.blit(label, ((SCREEN_W - label.get_width()) // 2, 10))

    def _draw_name_entry(self, surface):
        who = "What is your name, hunter?" if self.step == 0 else "What is your rival's name?"
        self._title(surface, who)
        name = self.names[self.step] or "..."
        box = pygame.Rect(60, 32, SCREEN_W - 120, 16)
        pygame.draw.rect(surface, BLACK, box)
        pygame.draw.rect(surface, WHITE, box, 1)
        label = self.font_big.render(name, False, WHITE, BLACK)
        surface.blit(label, (box.centerx - label.get_width() // 2, box.y + 3))

        rows = self._current_rows()
        y = 60
        for r, row in enumerate(rows):
            x = (SCREEN_W - sum(self.font.size(k)[0] + 6 for k in row)) // 2
            for c, key in enumerate(row):
                color = WHITE
                if r == self.row and c == self.col:
                    color = (255, 230, 120)
                label = self.font.render(key, False, color, BLACK)
                surface.blit(label, (x, y))
                if r == self.row and c == self.col:
                    pygame.draw.polygon(
                        surface, (255, 230, 120),
                        [(x, y + 10), (x + 4, y + 13), (x, y + 16)],
                    )
                x += self.font.size(key)[0] + 6
            y += 20

        hint = self.font.render("Arrows move, Z picks, END when done", False,
                                (150, 150, 150), BLACK)
        surface.blit(hint, ((SCREEN_W - hint.get_width()) // 2, SCREEN_H - 14))
        if self.flash:
            flash = self.font.render(self.flash, False, (255, 120, 120), BLACK)
            surface.blit(flash, ((SCREEN_W - flash.get_width()) // 2, SCREEN_H - 26))

    def _draw_starter(self, surface):
        self._title(surface, "Pick your partner!")
        from ..battle.mon_sprites import build_monster_sprite

        for i, (sid, name, type_name, color) in enumerate(_STARTERS):
            x = 30 + i * 65
            rect = pygame.Rect(x, 44, 56, 66)
            pygame.draw.rect(surface, BLACK, rect)
            pygame.draw.rect(
                surface, (255, 230, 120) if i == self.starter_index else WHITE, rect, 1
            )
            sprite = pygame.transform.scale(
                build_monster_sprite(sid, [type_name.lower()]), (48, 48)
            )
            surface.blit(sprite, (x + 4, rect.y + 4))
            label = self.font.render(name, False, WHITE, BLACK)
            surface.blit(label, (x + (56 - label.get_width()) // 2, rect.bottom - 22))
            tlabel = self.font.render(type_name, False, color, BLACK)
            surface.blit(tlabel, (x + (56 - tlabel.get_width()) // 2, rect.bottom - 10))

        hint = self.font.render("Arrows choose, Z confirms", False,
                                (150, 150, 150), BLACK)
        surface.blit(hint, ((SCREEN_W - hint.get_width()) // 2, SCREEN_H - 14))
