"""Tile definitions and simple programmatic tile rendering."""
import pygame

from ..engine.constants import TILE_SIZE

# Tile behavior flags
SOLID = "solid"
TALL_GRASS = "tall_grass"
DOOR = "door"
WARP = "warp"

_TileDef = tuple  # (name, solid, tall_grass, warp_target_or_None)


class Tileset:
    """Renders tiles as simple colored squares with small pixel details."""

    def __init__(self):
        self._cache = {}

    def render(self, tile_char):
        if tile_char in self._cache:
            return self._cache[tile_char]

        surface = pygame.Surface((TILE_SIZE, TILE_SIZE))
        base = _BASE_COLORS.get(tile_char, (60, 120, 60))
        surface.fill(base)
        _add_detail(surface, tile_char)
        self._cache[tile_char] = surface
        return surface


_BASE_COLORS = {
    "T": (34, 80, 34),
    ".": (72, 128, 72),
    "G": (60, 150, 60),
    "P": (72, 128, 72),
    "R": (168, 140, 96),
    "#": (200, 120, 80),
    "H": (220, 190, 120),
    "S": (180, 160, 200),
    "D": (120, 80, 50),
}


def _add_detail(surface, tile_char):
    if tile_char == "T":
        pygame.draw.rect(surface, (20, 50, 20), (0, 0, 16, 6))
        pygame.draw.rect(surface, (12, 36, 12), (4, 6, 8, 8))
    elif tile_char == "G":
        for x in (2, 8, 12):
            pygame.draw.line(surface, (40, 110, 40), (x, 4), (x, 13))
            pygame.draw.line(surface, (40, 110, 40), (x, 4), (x - 2, 9))
            pygame.draw.line(surface, (40, 110, 40), (x, 4), (x + 2, 9))
    elif tile_char == "#":
        pygame.draw.rect(surface, (140, 60, 50), (0, 2, 16, 8))
        pygame.draw.rect(surface, (90, 50, 40), (0, 10, 16, 6))
    elif tile_char == "H":
        pygame.draw.rect(surface, (240, 90, 90), (0, 2, 16, 7))
        pygame.draw.rect(surface, (150, 110, 70), (0, 9, 16, 7))
        pygame.draw.rect(surface, (255, 240, 200), (6, 11, 4, 5))
    elif tile_char == "S":
        pygame.draw.rect(surface, (150, 120, 190), (0, 2, 16, 7))
        pygame.draw.rect(surface, (110, 90, 140), (0, 9, 16, 7))
        pygame.draw.rect(surface, (240, 230, 255), (6, 11, 4, 5))
    elif tile_char == "D":
        pygame.draw.rect(surface, (90, 55, 30), (0, 0, 16, 16))
        pygame.draw.rect(surface, (160, 110, 60), (2, 2, 12, 14))
    elif tile_char == "R":
        for x in range(0, 16, 4):
            pygame.draw.circle(surface, (150, 125, 84), (x, 8), 1)


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
        return self.tile_at(tx, ty) in ("T", "#", "H", "S")

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
