"""Shared SNES-style palettes and dithering helpers for procedural art.

Every procedural surface must draw its colors from PALETTES so the whole
game keeps a consistent 16-bit look (see data/graphics-spec.md).
"""
import pygame

TILE = 16

PALETTES = {
    "grass": {
        "dark": (44, 96, 44),
        "mid": (68, 132, 60),
        "light": (96, 168, 72),
        "hi": (128, 192, 88),
    },
    "tallgrass": {
        "dark": (36, 88, 40),
        "mid": (56, 128, 52),
        "light": (84, 160, 64),
        "hi": (112, 184, 80),
    },
    "tree": {
        "canopy_dark": (24, 64, 32),
        "canopy_mid": (36, 92, 44),
        "canopy_light": (56, 120, 56),
        "trunk_dark": (56, 40, 24),
        "trunk_mid": (84, 60, 36),
        "trunk_light": (112, 84, 52),
    },
    "road": {
        "dark": (116, 96, 64),
        "mid": (152, 128, 88),
        "light": (184, 160, 112),
        "stone": (196, 176, 130),
    },
    "house": {
        "wall_dark": (150, 100, 68),
        "wall_mid": (190, 138, 92),
        "wall_light": (222, 176, 120),
        "roof_dark": (128, 52, 44),
        "roof_mid": (168, 76, 60),
        "roof_light": (208, 108, 76),
        "door": (92, 60, 36),
    },
    "water": {
        "dark": (32, 60, 128),
        "mid": (52, 96, 172),
        "light": (88, 136, 208),
        "foam": (200, 224, 240),
    },
    "ui": {
        "shadow": (16, 16, 24),
        "frame": (232, 232, 216),
        "hp_hi": (96, 208, 96),
        "hp_mid": (224, 200, 64),
        "hp_low": (216, 72, 64),
    },
}


def dither(surface, rect, color_a, color_b, parity=0):
    """Sparse 2px checker blend of two colors — the cheap '16-bit' look."""
    x0, y0, w, h = rect
    for y in range(y0, y0 + h, 2):
        for x in range(x0 + ((y + parity) % 4 // 2), x0 + w, 4):
            surface.set_at((x, y), color_a if (x + y + parity) % 2 == 0 else color_b)


def bevel(surface, rect, light, dark, width=1):
    """Top/left highlight, bottom/right shadow — instant depth."""
    x, y, w, h = rect
    pygame.draw.line(surface, light, (x, y), (x + w - 1, y), width)
    pygame.draw.line(surface, light, (x, y), (x, y + h - 1), width)
    pygame.draw.line(surface, dark, (x, y + h - 1), (x + w - 1, y + h - 1), width)
    pygame.draw.line(surface, dark, (x + w - 1, y), (x + w - 1, y + h - 1), width)


def vgrad(surface, rect, top_color, bottom_color, steps=4):
    """Vertical gradient in discrete steps (no smooth gradients — SNES palette feel)."""
    x, y, w, h = rect
    step_h = max(1, h // steps)
    for i in range(steps):
        t = i / max(1, steps - 1)
        color = tuple(
            int(top_color[c] + (bottom_color[c] - top_color[c]) * t) for c in range(3)
        )
        pygame.draw.rect(
            surface, color, (x, y + i * step_h, w, min(step_h, h - i * step_h))
        )
