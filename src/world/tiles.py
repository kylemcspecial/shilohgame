"""Tile definitions and SNES-style procedural tile rendering."""
import pygame

from ..engine.constants import TILE_SIZE
from ..world.gfx import PALETTES, dither, bevel, TILE

# Tile behavior flags
SOLID = "solid"
TALL_GRASS = "tall_grass"
DOOR = "door"
WARP = "warp"


class Tileset:
    """Renders tiles procedurally with palette shading; caches per char."""

    def __init__(self):
        self._cache = {}

    def render(self, tile_char):
        if tile_char not in self._cache:
            self._cache[tile_char] = _build_tile(tile_char)
        return self._cache[tile_char]


def _build_tile(tile_char):
    surface = pygame.Surface((TILE_SIZE, TILE_SIZE))
    painter = _PAINTERS.get(tile_char, _paint_grass)
    painter(surface)
    return surface


def _paint_grass(surface):
    g = PALETTES["grass"]
    surface.fill(g["mid"])
    dither(surface, (0, 0, TILE, TILE), g["light"], g["mid"])
    # sparse tufts
    for x, y in ((3, 5), (11, 3), (7, 11), (13, 9)):
        pygame.draw.line(surface, g["dark"], (x, y + 2), (x, y), 1)
        pygame.draw.line(surface, g["hi"], (x + 1, y + 2), (x + 1, y + 1), 1)


def _paint_tallgrass(surface):
    g = PALETTES["tallgrass"]
    surface.fill(g["mid"])
    dither(surface, (0, 0, TILE, TILE), g["dark"], g["mid"], parity=1)
    # dense blades with motion flicks
    for x in range(1, TILE - 1, 2):
        top = 2 if x % 4 else 5
        pygame.draw.line(surface, g["light"], (x, 15), (x, top))
        pygame.draw.line(surface, g["hi"], (x + 1, 15), (x + 1, top + 2))
        pygame.draw.line(surface, g["dark"], (x - 1, 15), (x - 1, top + 3))
    pygame.draw.line(surface, g["dark"], (0, 15), (15, 15), 1)


def _paint_tree(surface):
    t = PALETTES["tree"]
    g = PALETTES["grass"]
    surface.fill(g["mid"])
    dither(surface, (0, 0, TILE, TILE), g["light"], g["mid"])
    # trunk
    pygame.draw.rect(surface, t["trunk_mid"], (7, 10, 3, 6))
    pygame.draw.line(surface, t["trunk_light"], (8, 11), (8, 15))
    pygame.draw.line(surface, t["trunk_dark"], (9, 11), (9, 15))
    # canopy: layered blobs, light top-left
    pygame.draw.circle(surface, t["canopy_mid"], (8, 7), 6)
    pygame.draw.circle(surface, t["canopy_light"], (6, 5), 4)
    pygame.draw.circle(surface, t["canopy_mid"], (11, 8), 4)
    pygame.draw.circle(surface, t["canopy_dark"], (10, 10), 3)
    pygame.draw.line(surface, t["canopy_light"], (4, 3), (7, 2), 1)
    # ground shadow
    pygame.draw.line(surface, g["dark"], (4, 15), (12, 15), 1)


def _paint_road(surface):
    r = PALETTES["road"]
    surface.fill(r["mid"])
    dither(surface, (0, 0, TILE, TILE), r["light"], r["mid"])
    # worn edges
    pygame.draw.line(surface, r["dark"], (0, 0), (0, 15), 1)
    pygame.draw.line(surface, r["dark"], (15, 0), (15, 15), 1)
    # pebbles
    for x, y in ((4, 4), (10, 7), (6, 12), (12, 2)):
        pygame.draw.circle(surface, r["stone"], (x, y), 1)
        pygame.draw.circle(surface, r["dark"], (x + 1, y + 1), 1)


def _paint_house(surface):
    h = PALETTES["house"]
    g = PALETTES["grass"]
    surface.fill(g["mid"])
    dither(surface, (0, 0, TILE, TILE), g["light"], g["mid"])
    # walls with bevel
    pygame.draw.rect(surface, h["wall_mid"], (0, 4, TILE, 12))
    bevel(surface, (0, 4, TILE, 12), h["wall_light"], h["wall_dark"])
    # roofline
    pygame.draw.rect(surface, h["roof_mid"], (0, 0, TILE, 5))
    pygame.draw.line(surface, h["roof_light"], (0, 0), (14, 0), 1)
    pygame.draw.line(surface, h["roof_dark"], (0, 4), (15, 4), 2)
    # plank texture
    for y in (7, 11, 15):
        pygame.draw.line(surface, h["wall_dark"], (0, y), (15, y), 1)


def _paint_lodge(surface):
    h = PALETTES["house"]
    g = PALETTES["grass"]
    surface.fill(g["mid"])
    dither(surface, (0, 0, TILE, TILE), g["light"], g["mid"])
    # red cross emblem building
    pygame.draw.rect(surface, h["wall_light"], (0, 4, TILE, 12))
    bevel(surface, (0, 4, TILE, 12), (255, 240, 220), h["wall_dark"])
    pygame.draw.rect(surface, h["roof_dark"], (0, 0, TILE, 5))
    pygame.draw.rect(surface, (200, 70, 60), (0, 1, TILE, 3))
    pygame.draw.line(surface, (150, 50, 44), (0, 4), (15, 4), 1)
    # cross
    pygame.draw.rect(surface, (230, 240, 240), (7, 6, 2, 6))
    pygame.draw.rect(surface, (230, 240, 240), (5, 8, 6, 2))
    # door
    pygame.draw.rect(surface, h["door"], (6, 12, 4, 4))
    pygame.draw.line(surface, (60, 40, 24), (8, 12), (8, 15), 1)


def _paint_shop(surface):
    h = PALETTES["house"]
    g = PALETTES["grass"]
    surface.fill(g["mid"])
    dither(surface, (0, 0, TILE, TILE), g["light"], g["mid"])
    # purple-roofed shop with awning
    pygame.draw.rect(surface, h["wall_mid"], (0, 4, TILE, 12))
    bevel(surface, (0, 4, TILE, 12), h["wall_light"], h["wall_dark"])
    pygame.draw.rect(surface, (110, 88, 150), (0, 0, TILE, 5))
    pygame.draw.line(surface, (150, 128, 190), (0, 0), (14, 0), 1)
    # awning stripes
    for x in range(0, TILE, 4):
        pygame.draw.rect(surface, (170, 140, 210), (x, 4, 2, 3))
    # window with glow
    pygame.draw.rect(surface, (90, 70, 120), (4, 8, 8, 5))
    pygame.draw.rect(surface, (240, 230, 255), (5, 9, 6, 3))
    # counter
    pygame.draw.rect(surface, h["door"], (1, 13, 14, 3))
    bevel(surface, (1, 13, 14, 3), h["wall_light"], (60, 40, 24))


def _paint_door(surface):
    h = PALETTES["house"]
    pygame.draw.rect(surface, h["door"], (0, 0, TILE, TILE))
    # planks + frame + glowing gap at the bottom (it's an exit)
    for x in range(2, TILE, 4):
        pygame.draw.line(surface, (70, 46, 28), (x, 0), (x, 15))
    bevel(surface, (0, 0, TILE, TILE), (130, 92, 56), (48, 32, 20))
    pygame.draw.rect(surface, (255, 240, 180), (2, 13, 12, 2))
    pygame.draw.rect(surface, (255, 220, 120), (4, 14, 8, 1))


def _paint_shrine(surface):
    """Legendary shrine: carved stone dais with a glowing sigil."""
    g = PALETTES["grass"]
    surface.fill(g["mid"])
    dither(surface, (0, 0, TILE, TILE), g["light"], g["mid"])
    pygame.draw.rect(surface, (30, 28, 40), (2, 6, 12, 8))
    pygame.draw.rect(surface, (140, 130, 150), (3, 7, 10, 6))
    pygame.draw.circle(surface, (90, 220, 140), (8, 9), 2)
    pygame.draw.circle(surface, (200, 255, 220), (8, 8), 1)
    for px in (5, 11):
        pygame.draw.line(surface, (110, 100, 120), (px, 6), (px, 13), 1)


def _paint_berry_plant(surface):
    """Berry plant: bush with red berries (picked state drawn in scene)."""
    g = PALETTES["tallgrass"]
    surface.fill(PALETTES["grass"]["mid"])
    dither(surface, (0, 0, TILE, TILE), PALETTES["grass"]["light"], PALETTES["grass"]["mid"])
    pygame.draw.circle(surface, (24, 64, 32), (8, 9), 6)
    pygame.draw.circle(surface, (48, 112, 48), (8, 8), 6)
    for bx, by in ((5, 7), (9, 6), (7, 10), (10, 9)):
        pygame.draw.circle(surface, (200, 50, 60), (bx, by), 1)
        surface.set_at((bx, by - 1), (255, 120, 120))


def _paint_boulder(surface):
    """Pushable boulder: round rock with shading, sits on grass."""
    g = PALETTES["grass"]
    surface.fill(g["mid"])
    dither(surface, (0, 0, TILE, TILE), g["light"], g["mid"])
    pygame.draw.circle(surface, (30, 28, 40), (8, 9), 6)
    pygame.draw.circle(surface, (150, 145, 130), (8, 8), 6)
    pygame.draw.circle(surface, (195, 190, 175), (6, 6), 2)
    pygame.draw.line(surface, (110, 105, 95), (5, 10), (10, 11), 1)


def _paint_switch(surface):
    """Switch plate: recessed square that lights up (state drawn in scene)."""
    g = PALETTES["grass"]
    surface.fill(g["mid"])
    dither(surface, (0, 0, TILE, TILE), g["light"], g["mid"])
    pygame.draw.rect(surface, (60, 56, 72), (3, 3, 10, 10))
    pygame.draw.rect(surface, (120, 116, 140), (4, 4, 8, 8))


def _paint_stone_path(surface):
    """Stepping stones across a stream: two round stones."""
    w = PALETTES.get("water") or {"mid": (50, 90, 170), "hi": (90, 140, 220)}
    surface.fill(w["mid"])
    pygame.draw.circle(surface, (140, 132, 120), (5, 11), 4)
    pygame.draw.circle(surface, (170, 162, 150), (5, 10), 3)
    pygame.draw.circle(surface, (140, 132, 120), (11, 5), 4)
    pygame.draw.circle(surface, (170, 162, 150), (11, 4), 3)


def _paint_lantern(surface):
    """Lantern post: lit/unlit state drawn as overlay in the scene."""
    g = PALETTES["grass"]
    surface.fill(g["mid"])
    dither(surface, (0, 0, TILE, TILE), g["light"], g["mid"])
    pygame.draw.line(surface, (60, 50, 40), (8, 15), (8, 6), 2)
    pygame.draw.rect(surface, (30, 28, 40), (4, 1, 8, 7))
    pygame.draw.rect(surface, (255, 220, 120), (5, 2, 6, 5))


def _paint_riddle(surface):
    """Riddle stone: carved monolith with a question glyph."""
    g = PALETTES["grass"]
    surface.fill(g["mid"])
    dither(surface, (0, 0, TILE, TILE), g["light"], g["mid"])
    pygame.draw.rect(surface, (30, 28, 40), (4, 1, 8, 14))
    pygame.draw.rect(surface, (150, 145, 130), (5, 2, 6, 12))
    pygame.draw.line(surface, (90, 86, 76), (6, 4), (10, 4), 1)
    pygame.draw.line(surface, (90, 86, 76), (8, 5), (8, 8), 1)
    pygame.draw.line(surface, (90, 86, 76), (6, 10), (10, 10), 1)


def _paint_npc_tile(surface):
    g = PALETTES["grass"]
    surface.fill(g["mid"])
    dither(surface, (0, 0, TILE, TILE), g["light"], g["mid"])
    # villager silhouette marker (distinct from trainers)
    pygame.draw.circle(surface, (240, 200, 150), (8, 5), 3)
    pygame.draw.rect(surface, (170, 120, 90), (5, 8, 6, 6))
    pygame.draw.line(surface, (120, 84, 60), (5, 14), (10, 14))


def _paint_player_start(surface):
    _paint_grass(surface)
    g = PALETTES["grass"]
    pygame.draw.circle(surface, g["hi"], (8, 8), 3, 1)


_PAINTERS = {
    "T": _paint_tree,
    ".": _paint_grass,
    "G": _paint_tallgrass,
    "P": _paint_player_start,
    "R": _paint_road,
    "#": _paint_house,
    "H": _paint_lodge,
    "S": _paint_shop,
    "D": _paint_door,
    "B": _paint_boulder,
    "b": _paint_berry_plant,
    "L": _paint_shrine,
    "o": _paint_switch,
    "~": _paint_stone_path,
    "Y": _paint_lantern,
    "?": _paint_riddle,
    "N": _paint_npc_tile,
}


class TileMap:
    """Static map loaded from JSON zone data."""

    def __init__(self, zone_data):
        self.name = zone_data["name"]
        self.legend = zone_data["legend"]
        rows = zone_data["tiles"]
        self.width = len(rows[0])
        self.height = len(rows)
        self.grid = [list(row) for row in rows]
        self.exits = zone_data.get("exits", {})
        self.warps = list(zone_data.get("warps", []))
        self.player_start = None
        for y, row in enumerate(self.grid):
            for x, char in enumerate(row):
                if char == "P":
                    self.player_start = (x, y)

    def tile_at(self, tx, ty):
        if 0 <= tx < self.width and 0 <= ty < self.height:
            return self.grid[ty][tx]
        return "T"

    def is_solid(self, tx, ty):
        return self.tile_at(tx, ty) in ("T", "#", "H", "S", "B")

    def is_tall_grass(self, tx, ty):
        return self.tile_at(tx, ty) == "G"

    def is_healing_lodge(self, tx, ty):
        return self.tile_at(tx, ty) == "H"

    def is_door(self, tx, ty):
        return self.tile_at(tx, ty) == "D"

    def warp_at(self, tx, ty):
        for warp in self.warps:
            if warp["x"] == tx and warp["y"] == ty:
                return warp
        return None
