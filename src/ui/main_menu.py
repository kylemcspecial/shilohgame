"""Title screen: New Game, Continue, Options, Quit (spec 11)."""
import pygame

from ..engine.constants import SCREEN_W, SCREEN_H, BLACK, WHITE
from ..engine import input as input_mod
from ..engine.fonts import get_font

_MENU = ("New Game", "Continue", "Options", "Quit")


class MainMenuScene:
    """Shown at boot; hands control back to the Game with a chosen action."""

    def __init__(self, game):
        self.game = game
        self.font_big = get_font(16)
        self.font = get_font(8)
        self.index = 0
        self.done = False
        self.action = None  # "new", "continue", "quit", or ("load", slot)
        self.options_menu = False
        self.option_index = 0
        self.continue_menu = False
        self.continue_index = 0
        self._continue_slots = None
        self._flash = None
        self._flash_timer = 0.0

    # ------------------------------------------------------------- helpers

    def _slot_summaries(self):
        """(slot, label) per slot: play time and party count, or Empty."""
        from ..save import load_game, SLOT_COUNT

        if self._continue_slots is None:
            self._continue_slots = []
            for slot in range(SLOT_COUNT):
                data = load_game(slot)
                if data is None:
                    self._continue_slots.append((slot, None))
                else:
                    minutes = int(data.get("play_time", 0) // 60)
                    self._continue_slots.append(
                        (slot, f"Slot {slot + 1}: {len(data['party'])} monsters, {minutes}m")
                    )
        return self._continue_slots

    def _refresh_slots(self):
        self._continue_slots = None

    # --------------------------------------------------------------- input

    def update(self, dt):
        pressed = self.game.input.pressed
        if self._flash_timer > 0:
            self._flash_timer -= dt
            if self._flash_timer <= 0:
                self._flash = None

        if self.continue_menu:
            self._update_continue(pressed)
            return
        if self.options_menu:
            self._update_options(pressed)
            return

        if input_mod.UP in pressed:
            self.index = (self.index - 1) % len(_MENU)
        elif input_mod.DOWN in pressed:
            self.index = (self.index + 1) % len(_MENU)
        elif input_mod.CONFIRM in pressed:
            self._choose(_MENU[self.index])

    def _update_continue(self, pressed):
        from ..save import SLOT_COUNT

        if input_mod.UP in pressed:
            self.continue_index = (self.continue_index - 1) % SLOT_COUNT
        elif input_mod.DOWN in pressed:
            self.continue_index = (self.continue_index + 1) % SLOT_COUNT
        elif input_mod.CONFIRM in pressed:
            slot, label = self._slot_summaries()[self.continue_index]
            if label is None:
                self._flash = "That slot is empty!"
                self._flash_timer = 1.5
            else:
                self.action = ("load", slot)
                self.done = True
        elif input_mod.CANCEL in pressed:
            self.continue_menu = False

    def _update_options(self, pressed):
        if input_mod.CONFIRM in pressed or input_mod.CANCEL in pressed:
            self.options_menu = False
            return
        options = self._option_rows()
        if input_mod.UP in pressed:
            self.option_index = (self.option_index - 1) % len(options)
        elif input_mod.DOWN in pressed:
            self.option_index = (self.option_index + 1) % len(options)
        elif input_mod.LEFT in pressed or input_mod.RIGHT in pressed:
            self._adjust_option(options[self.option_index][0],
                                1 if input_mod.RIGHT in pressed else -1)

    def _option_rows(self):
        audio = self.game.audio
        day_night = getattr(self.game, "day_night_enabled", True)
        return (
            ("music", f"Music Volume: {int(audio.music_volume * 10)}"),
            ("sfx", f"SFX Volume:   {int(audio.sfx_volume * 10)}"),
            ("fullscreen", f"Fullscreen:   {'On' if self.game.fullscreen else 'Off'}"),
            ("day_night", f"Day/Night:    {'On' if day_night else 'Off'}"),
        )

    def _adjust_option(self, key, direction):
        audio = self.game.audio
        if key == "day_night":
            self.game.day_night_enabled = not getattr(
                self.game, "day_night_enabled", True
            )
            return
        if key == "music":
            audio.music_volume = min(1.0, max(0.0, audio.music_volume + 0.1 * direction))
        elif key == "sfx":
            audio.sfx_volume = min(1.0, max(0.0, audio.sfx_volume + 0.1 * direction))
        elif key == "fullscreen":
            self.game.toggle_fullscreen()

    def _choose(self, choice):
        self.game.audio.confirm()
        if choice == "New Game":
            self.action = "new"
            self.done = True
        elif choice == "Continue":
            self.continue_menu = True
            self.continue_index = 0
        elif choice == "Options":
            self.options_menu = True
            self.option_index = 0
        elif choice == "Quit":
            self.action = "quit"
            self.done = True

    def toggle_pause(self):
        pass

    # ----------------------------------------------------------------- gfx

    def draw(self, surface):
        surface.fill((16, 24, 40))
        title = self.font_big.render("FIERCE MONSTER HUNTER", False, WHITE)
        surface.blit(title, ((SCREEN_W - title.get_width()) // 2, 18))
        sub = self.font.render("A tiny retro monster-catching RPG", False, WHITE)
        surface.blit(sub, ((SCREEN_W - sub.get_width()) // 2, 36))

        if self.continue_menu:
            self._draw_continue(surface)
            return
        if self.options_menu:
            self._draw_options(surface)
            return

        y = 64
        for i, option in enumerate(_MENU):
            label = self.font.render(option, False, WHITE)
            surface.blit(label, (SCREEN_W // 2 - 20, y))
            if i == self.index:
                x = SCREEN_W // 2 - 28
                pygame.draw.polygon(
                    surface, WHITE, [(x - 6, y + 3), (x - 1, y + 6), (x - 6, y + 9)]
                )
            y += 14

        if self._flash:
            flash = self.font.render(self._flash, False, WHITE, BLACK)
            surface.blit(flash, ((SCREEN_W - flash.get_width()) // 2, SCREEN_H - 30))

    def _draw_continue(self, surface):
        rect = pygame.Rect(30, 54, SCREEN_W - 60, 52)
        pygame.draw.rect(surface, BLACK, rect)
        pygame.draw.rect(surface, WHITE, rect, 1)
        for i, (slot, label) in enumerate(self._slot_summaries()):
            text = label if label else f"Slot {slot + 1}: Empty"
            label_r = self.font.render(text, False, WHITE if label else (110, 110, 110), BLACK)
            y = rect.y + 4 + i * 15
            surface.blit(label_r, (rect.x + 12, y))
            if i == self.continue_index:
                pygame.draw.polygon(
                    surface, WHITE,
                    [(rect.x + 4, y + 3), (rect.x + 9, y + 6), (rect.x + 4, y + 9)],
                )

    def _draw_options(self, surface):
        rect = pygame.Rect(30, 54, SCREEN_W - 60, 52)
        pygame.draw.rect(surface, BLACK, rect)
        pygame.draw.rect(surface, WHITE, rect, 1)
        for i, (_, text) in enumerate(self._option_rows()):
            label = self.font.render(text, False, WHITE, BLACK)
            y = rect.y + 4 + i * 15
            surface.blit(label, (rect.x + 12, y))
            if i == self.option_index:
                pygame.draw.polygon(
                    surface, WHITE,
                    [(rect.x + 4, y + 3), (rect.x + 9, y + 6), (rect.x + 4, y + 9)],
                )
