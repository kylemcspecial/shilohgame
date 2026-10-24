"""Procedural per-species battle sprites: distinct silhouettes and features.

Every species gets a stable look derived from its id, so all 43 monsters
are visually unique instead of one color-swapped blob. Body shape comes
from the primary type (beast blob, moth, fish, wyrm, bird, cub); details
(ears/horns/crest, pattern, tail, eyes, accents) vary per species id.
"""
import zlib

import pygame

SIZE = 32
OUTLINE = (28, 24, 40)

_TYPE_COLORS = {
    "leaf": (90, 185, 90),
    "water": (85, 135, 235),
    "storm": (245, 222, 110),
    "frost": (175, 225, 245),
    "stone": (155, 145, 125),
    "ember": (245, 120, 60),
}
_ACCENTS = {
    "leaf": (60, 140, 60),
    "water": (40, 80, 190),
    "storm": (200, 170, 40),
    "frost": (120, 180, 215),
    "stone": (105, 95, 80),
    "ember": (200, 70, 30),
}
_PATTERNS = ("stripes", "spots", "belly", "none")
_EARS = ("round", "pointy", "horns", "crest", "none")
_EYES = ("round", "fierce", "wide", "sleepy")
_TAILS = ("thin", "fluff", "fin", "none")


def _species_seed(species_id):
    return zlib.crc32(species_id.encode("utf-8"))


def _pick(seed, options, salt=0):
    return options[(seed >> (salt * 3)) % len(options)]


def _shades(base):
    light = tuple(min(255, c + 50) for c in base)
    dark = tuple(max(0, c - 60) for c in base)
    return light, dark


def _body_shape(species_id, types):
    """Silhouette archetype from primary type; seed nudges rare variants."""
    primary = types[0]
    shape_by_type = {
        "leaf": "blob",
        "water": "fish",
        "storm": "moth",
        "frost": "cub",
        "stone": "wyrm",
        "ember": "beast",
    }
    shape = shape_by_type.get(primary, "blob")
    seed = _species_seed(species_id)
    if "legendary" in species_id:
        return "wyrm"
    if shape == "blob" and _pick(seed, (0, 1), 2):
        return "beast"
    return shape


def _draw_body(sprite, shape, base, light, dark):
    """One distinct silhouette per archetype, all around 22-26px tall."""
    if shape == "blob":
        pygame.draw.ellipse(sprite, OUTLINE, (-1, 8, 34, 24))
        pygame.draw.ellipse(sprite, base, (0, 9, 32, 22))
        pygame.draw.ellipse(sprite, light, (3, 9, 26, 12))
    elif shape == "beast":
        pygame.draw.ellipse(sprite, OUTLINE, (2, 8, 28, 22))
        pygame.draw.ellipse(sprite, base, (3, 9, 26, 20))
        pygame.draw.ellipse(sprite, light, (5, 9, 22, 10))
        pygame.draw.polygon(sprite, base, [(1, 18), (4, 18), (2, 24)])
    elif shape == "moth":
        pygame.draw.ellipse(sprite, OUTLINE, (4, 10, 24, 18))
        pygame.draw.ellipse(sprite, base, (5, 11, 22, 16))
        pygame.draw.ellipse(sprite, light, (7, 11, 18, 8))
        for wy in (9, 26):
            pygame.draw.ellipse(sprite, OUTLINE, (0, wy, 12, 9))
            pygame.draw.ellipse(sprite, base, (1, wy + 1, 10, 7))
            pygame.draw.ellipse(sprite, OUTLINE, (20, wy, 12, 9))
            pygame.draw.ellipse(sprite, base, (21, wy + 1, 10, 7))
    elif shape == "fish":
        pygame.draw.ellipse(sprite, OUTLINE, (2, 8, 26, 18))
        pygame.draw.ellipse(sprite, base, (3, 9, 24, 16))
        pygame.draw.ellipse(sprite, light, (5, 9, 20, 8))
        pygame.draw.polygon(sprite, OUTLINE, [(24, 8), (31, 12), (31, 22), (24, 25)])
        pygame.draw.polygon(sprite, base, [(25, 10), (30, 13), (30, 21), (25, 23)])
    elif shape == "wyrm":
        pygame.draw.ellipse(sprite, OUTLINE, (0, 6, 30, 16))
        pygame.draw.ellipse(sprite, base, (1, 7, 28, 14))
        pygame.draw.ellipse(sprite, light, (3, 7, 24, 7))
        pygame.draw.polygon(sprite, OUTLINE, [(6, 20), (24, 20), (20, 27), (10, 27)])
        pygame.draw.polygon(sprite, dark, [(8, 20), (22, 20), (19, 25), (11, 25)])
    else:  # cub
        pygame.draw.ellipse(sprite, OUTLINE, (-1, 6, 34, 24))
        pygame.draw.ellipse(sprite, base, (0, 7, 32, 22))
        pygame.draw.ellipse(sprite, light, (3, 7, 26, 12))


def _draw_pattern(sprite, pattern, shape, dark, light):
    if pattern == "stripes":
        for x in (10, 15, 20):
            pygame.draw.line(sprite, dark, (x, 13), (x, 25), 2)
    elif pattern == "spots":
        for x, y in ((9, 18), (15, 22), (21, 16)):
            pygame.draw.circle(sprite, dark, (x, y), 2)
    elif pattern == "belly":
        pygame.draw.ellipse(sprite, dark, (9, 17, 14, 10))
        pygame.draw.ellipse(sprite, light, (10, 18, 12, 8))


def _draw_ears(sprite, style, base, dark):
    if style == "round":
        for ex in (8, 24):
            pygame.draw.circle(sprite, OUTLINE, (ex, 9), 4)
            pygame.draw.circle(sprite, base, (ex, 9), 3)
    elif style == "pointy":
        pygame.draw.polygon(sprite, OUTLINE, [(7, 6), (10, 12), (4, 11)])
        pygame.draw.polygon(sprite, base, [(8, 7), (9, 11), (6, 10)])
        pygame.draw.polygon(sprite, OUTLINE, [(25, 6), (28, 11), (22, 12)])
        pygame.draw.polygon(sprite, base, [(24, 7), (26, 10), (23, 11)])
    elif style == "horns":
        pygame.draw.polygon(sprite, OUTLINE, [(8, 4), (10, 9), (6, 9)])
        pygame.draw.polygon(sprite, (240, 230, 200), [(8, 5), (9, 8), (7, 8)])
        pygame.draw.polygon(sprite, OUTLINE, [(24, 4), (26, 9), (22, 9)])
        pygame.draw.polygon(sprite, (240, 230, 200), [(24, 5), (25, 8), (23, 8)])
    elif style == "crest":
        pygame.draw.polygon(sprite, OUTLINE, [(16, 2), (18, 8), (14, 8)])
        pygame.draw.polygon(sprite, dark, [(16, 3), (17, 7), (15, 7)])
        pygame.draw.polygon(sprite, OUTLINE, [(10, 4), (12, 9), (8, 9)])
        pygame.draw.polygon(sprite, dark, [(10, 5), (11, 8), (9, 8)])
        pygame.draw.polygon(sprite, OUTLINE, [(22, 4), (24, 9), (20, 9)])
        pygame.draw.polygon(sprite, dark, [(22, 5), (23, 8), (21, 8)])


def _draw_eyes(sprite, style, eye_y):
    white = (255, 255, 255)
    pupil = (20, 20, 30)
    if style == "round":
        for ex in (12, 20):
            pygame.draw.circle(sprite, white, (ex, eye_y), 3)
            pygame.draw.circle(sprite, pupil, (ex, eye_y + 1), 2)
    elif style == "fierce":
        for ex, tilt in ((11, 1), (21, -1)):
            pygame.draw.polygon(
                sprite, white,
                [(ex - 3, eye_y + tilt), (ex + 3, eye_y - tilt), (ex + 3, eye_y + 2 + tilt)],
            )
            pygame.draw.circle(sprite, pupil, (ex + 1, eye_y + 1), 2)
    elif style == "wide":
        for ex in (11, 21):
            pygame.draw.circle(sprite, white, (ex, eye_y), 4)
            pygame.draw.circle(sprite, pupil, (ex, eye_y + 1), 2)
            sprite.set_at((ex, eye_y - 2), white)
    else:  # sleepy
        for ex in (12, 20):
            pygame.draw.line(sprite, pupil, (ex - 2, eye_y + 1), (ex + 2, eye_y + 1), 2)
            pygame.draw.circle(sprite, white, (ex, eye_y), 1)


def _draw_tail(sprite, style, base, dark):
    if style == "thin":
        pygame.draw.lines(sprite, base, False, [(28, 22), (31, 19), (30, 15)], 2)
    elif style == "fluff":
        pygame.draw.ellipse(sprite, OUTLINE, (24, 18, 8, 8))
        pygame.draw.ellipse(sprite, dark, (25, 19, 6, 6))
    elif style == "fin":
        pygame.draw.polygon(sprite, OUTLINE, [(26, 14), (31, 9), (31, 19)])
        pygame.draw.polygon(sprite, base, [(27, 14), (30, 11), (30, 17)])


def _draw_feet(sprite, dark):
    for fx in (5, 21):
        pygame.draw.rect(sprite, OUTLINE, (fx, 27, 6, 3))
        pygame.draw.rect(sprite, dark, (fx + 1, 28, 4, 2))


def build_monster_sprite(species_id, types):
    """Return a 32x32 unique sprite for a species (cached per species id)."""
    cache = getattr(build_monster_sprite, "_cache", None)
    if cache is None:
        cache = build_monster_sprite._cache = {}
    if species_id in cache:
        return cache[species_id]

    seed = _species_seed(species_id)
    base = _TYPE_COLORS.get(types[0], (200, 200, 200))
    accent = _ACCENTS.get(types[-1], base)
    light, dark = _shades(base)
    shape = _body_shape(species_id, types)
    pattern = _pick(seed, _PATTERNS, 1)
    ears = _pick(seed, _EARS, 3)
    eyes = _pick(seed, _EYES, 4)
    tail = _pick(seed, _TAILS, 5)

    sprite = pygame.Surface((SIZE, SIZE), pygame.SRCALPHA)
    _draw_body(sprite, shape, base, light, dark)
    if shape == "moth":
        eye_y = 15
        pygame.draw.line(sprite, accent, (10, 13), (22, 13), 1)
    else:
        eye_y = {"blob": 14, "beast": 13, "fish": 14, "wyrm": 11, "cub": 13}[shape]
    _draw_pattern(sprite, pattern, shape, dark, light)
    _draw_ears(sprite, ears, base, dark)
    _draw_eyes(sprite, eyes, eye_y)
    if shape not in ("fish",):
        _draw_tail(sprite, tail, base, dark)
    if shape in ("blob", "beast", "cub"):
        _draw_feet(sprite, dark)
    # little fangs for fierce charm
    pygame.draw.polygon(sprite, (255, 255, 255), [(14, eye_y + 4), (15, eye_y + 7), (16, eye_y + 4)])
    pygame.draw.polygon(sprite, (255, 255, 255), [(17, eye_y + 4), (18, eye_y + 7), (19, eye_y + 4)])

    cache[species_id] = sprite
    return sprite
