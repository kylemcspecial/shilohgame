"""Crisp cached fonts: render vector text at high res, smooth-scale down.

pygame's default font is vector, so rendering at Nx and smooth-scaling gives
anti-aliased letterforms at small sizes — far easier to read than chunky
8px bitmap glyphs — while keeping the retro proportions.
"""
import pygame

_SCALE = 3
_cache = {}


class CrispFont:
    """Drop-in replacement for pygame.font.Font with legible output."""

    def __init__(self, size, scale=_SCALE):
        self._path = pygame.font.get_default_font()
        self._scale = scale
        self._size = size
        self._sizes = {}
        self._font = self._make_font()

    def _make_font(self):
        if not pygame.font.get_init():
            pygame.font.init()
        return pygame.font.Font(self._path, self._size * self._scale)

    def _live_font(self):
        """Fonts die if pygame.quit() runs; rebuild lazily when that happens."""
        try:
            self._font.size("")
        except pygame.error:
            self._font = self._make_font()
        return self._font

    def _render_uncached(self, text):
        big = self._live_font().render(text, True, (255, 255, 255))
        w = max(1, big.get_width() // self._scale)
        h = max(1, big.get_height() // self._scale)
        return pygame.transform.smoothscale(big, (w, h))

    def render(self, text, antialias=True, color=(255, 255, 255), background=None):
        big = self._live_font().render(str(text), True, color)
        w = max(1, big.get_width() // self._scale)
        h = max(1, big.get_height() // self._scale)
        small = pygame.transform.smoothscale(big, (w, h))
        if background is None:
            return small
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.fill(background)
        surf.blit(small, (0, 0))
        return surf

    def size(self, text):
        text = str(text)
        if text not in self._sizes:
            self._sizes[text] = self._render_uncached(text).get_size()
        return self._sizes[text]

    def get_height(self):
        return self._live_font().get_height() // self._scale


def get_font(size):
    """Cached CrispFont for a given point size."""
    if size not in _cache:
        _cache[size] = CrispFont(size)
    return _cache[size]
