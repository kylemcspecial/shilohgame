"""Tests for visual polish: unique monster sprites, crisp fonts, slim player."""
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame

pygame.init()

from src.battle.mon_sprites import build_monster_sprite
from src.monsters.monster import load_species
from src.world.player import Player


def test_every_species_has_a_sprite():
    for sid, species in load_species().items():
        sprite = build_monster_sprite(sid, species["types"])
        assert sprite.get_size() == (32, 32), sid


def test_species_sprites_are_unique():
    """Different species must not render identically (the old color-blob bug)."""
    species = load_species()
    seen = {}
    for sid, s in species.items():
        sprite = build_monster_sprite(sid, s["types"])
        buf = pygame.image.tostring(sprite, "RGBA")
        assert buf not in seen, f"{sid} renders identically to {seen[buf]}"
        seen[buf] = sid


def test_sprite_varies_across_types():
    leaf = build_monster_sprite("mossrat", ["leaf"])
    water = build_monster_sprite("brookfin", ["water"])
    assert pygame.image.tostring(leaf, "RGBA") != pygame.image.tostring(water, "RGBA")


def test_sprite_cached_per_species():
    s = load_species()["mossrat"]
    assert build_monster_sprite("mossrat", ["leaf"]) is build_monster_sprite("mossrat", ["leaf"])


def test_crisp_font_renders_legibly():
    from src.engine.fonts import get_font

    font = get_font(8)
    surf = font.render("Fierce Monster Hunter 123", False, (255, 255, 255))
    w, h = font.size("Fierce Monster Hunter 123")
    assert surf.get_size() == (w, h)
    assert w > 0 and h >= 8


def test_crisp_font_survives_pygame_quit():
    from src.engine.fonts import get_font

    font = get_font(8)
    pygame.quit()
    pygame.init()
    surf = font.render("still alive", False, (255, 255, 255))
    assert surf.get_width() > 0


def test_player_sprite_smaller_than_tile():
    player = Player(2, 2)
    surf = player._sprites["down"][0]
    width = {x for y in range(16) for x in range(16) if surf.get_at((x, y))[3] > 0}
    height = {y for y in range(16) for x in range(16) if surf.get_at((x, y))[3] > 0}
    assert len(width) <= 12, "player should be slimmer than the full 16px tile"
    assert max(height) <= 15
