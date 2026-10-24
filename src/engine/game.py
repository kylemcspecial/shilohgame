"""Core game loop: window, integer scaling, scene management."""
import os

import pygame

from ..engine.constants import SCREEN_W, SCREEN_H, FPS
from ..engine import input as input_mod
from ..engine.audio import Audio
from ..world.scene import WorldScene


class Game:
    """Owns the window, the clock, and the active scene."""

    def __init__(self):
        pygame.init()
        pygame.joystick.init()
        pygame.display.set_caption("Fierce Monster Hunter")
        self.fullscreen = False
        self.screen = pygame.display.set_mode((SCREEN_W * 3, SCREEN_H * 3), pygame.SCALED)
        self.buffer = pygame.Surface((SCREEN_W, SCREEN_H))
        self.clock = pygame.time.Clock()
        self.input = input_mod.Input()
        self.audio = Audio()
        self.running = True
        self.world = WorldScene(self)
        self.scene = self.world
        self.font = pygame.font.Font(pygame.font.get_default_font(), 8)

    def start_battle(self, battle_scene):
        self.scene = battle_scene

    def end_battle(self):
        battle = self.scene
        if battle is not self.world:
            caught = getattr(battle, "caught_monster", None)
            if caught is not None:
                self.world.monsters_caught += 1
                if len(self.world.party) < 6:
                    self.world.party.append(caught)
                else:
                    self.world.storage.append(caught)
            if getattr(battle, "outcome", None) == "won":
                self.world.battles_won += 1
            elif getattr(battle, "outcome", None) == "trainer_won":
                self.world.battles_won += 1
                tid = getattr(battle, "trainer_id", None)
                if tid is not None:
                    self.world.trainer_state.record_win(tid)
                    self.world.coins += battle.trainer["reward"]
                if self.world.save_slot is not None:
                    from ..save import save_game

                    save_game(self.world, self.world.save_slot)
            elif getattr(battle, "outcome", None) == "lost":
                self.world.heal_and_revive()
        self.scene = self.world

    def toggle_fullscreen(self):
        fullscreen = not self.fullscreen
        flags = pygame.SCALED | (pygame.FULLSCREEN if fullscreen else 0)
        screen = pygame.display.set_mode((SCREEN_W * 3, SCREEN_H * 3), flags)
        self.screen = screen
        self.fullscreen = fullscreen

    def quit(self):
        self.running = False

    def run(self, title=True):
        try:
            if title:
                self._run_title_loop()
            while self.running:
                events = pygame.event.get()
                for event in events:
                    if event.type == pygame.QUIT:
                        self.quit()
                        return
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                        self.toggle_fullscreen()

                self.input.update(events)
                if input_mod.PAUSE in self.input.pressed:
                    self.scene.toggle_pause()

                dt = self.clock.tick(FPS) / 1000.0
                self.scene.update(dt)
                self.scene.draw(self.buffer)

                pygame.transform.scale(self.buffer, self.screen.get_size(), self.screen)
                pygame.display.flip()

                if getattr(self.scene, "exit_to_title", False):
                    self._run_title_loop()
        finally:
            pygame.quit()

    def _run_title_loop(self):
        """Show the main menu until New Game/Continue/Quit is chosen."""
        from ..ui.main_menu import MainMenuScene

        menu = MainMenuScene(self)
        while self.running and not menu.done:
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    self.quit()
                    return
                if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                    self.toggle_fullscreen()

            self.input.update(events)
            dt = self.clock.tick(FPS) / 1000.0
            menu.update(dt)
            menu.draw(self.buffer)

            pygame.transform.scale(self.buffer, self.screen.get_size(), self.screen)
            pygame.display.flip()

            if menu.action == "quit":
                self.quit()
                return

        if menu.action == "new":
            self._new_game()
        elif isinstance(menu.action, tuple) and menu.action[0] == "load":
            self._load_game(menu.action[1])

    def _new_game(self):
        """Fresh world, back to the game loop."""
        from ..world.scene import WorldScene

        self.world = WorldScene(self)
        self.scene = self.world
        self.world.save_slot = None

    def _load_game(self, slot):
        from ..save import load_game, apply_save

        data = load_game(slot)
        if data is None:
            self._new_game()
            return
        apply_save(self.world, data)
        self.world.save_slot = slot
        self.scene = self.world


def main():
    os.environ.setdefault("SDL_VIDEO_CENTERED", "1")
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
