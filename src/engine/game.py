"""Core game loop: window, integer scaling, scene management."""
import os
import sys

import pygame

from ..engine.constants import SCREEN_W, SCREEN_H, FPS, BLACK, WHITE
from ..engine import input as input_mod
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
        self.running = True
        self.scene = WorldScene(self)
        self.font = pygame.font.Font(pygame.font.get_default_font(), 8)

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN | pygame.SCALED)
        else:
            self.screen = pygame.display.set_mode((SCREEN_W * 3, SCREEN_H * 3), pygame.SCALED)

    def quit(self):
        self.running = False

    def run(self):
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
        pygame.quit()


def main():
    os.environ.setdefault("SDL_VIDEO_CENTERED", "1")
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
