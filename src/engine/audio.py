"""Audio: generated chiptune-style SFX and music, fully optional.

Produces square-wave beeps via pygame.sndarray with numpy when available;
falls back to silent no-op sounds so the game stays fully playable with
audio off or on systems without a mixer (spec 2.4).
"""
import math
import os

import pygame

try:
    import numpy as _np
except ImportError:
    _np = None

_DEFAULT_SAMPLE_RATE = 22050


def _mixer_rate():
    init = pygame.mixer.get_init()
    if init:
        return init[0]
    return _DEFAULT_SAMPLE_RATE


def _tone_samples(freq, duration, volume, wave="square"):
    rate = _mixer_rate()
    n = int(rate * duration)
    if _np is None or n <= 0:
        return None
    t = _np.arange(n) / rate
    if wave == "square":
        samples = _np.sign(_np.sin(2 * math.pi * freq * t))
    else:
        samples = _np.sin(2 * math.pi * freq * t)
    fade = _np.linspace(1.0, 0.0, n)
    samples = (samples * fade * volume * 0.5 * 32767).astype(_np.int16)
    stereo = _np.column_stack((samples, samples))
    return stereo


class Audio:
    """SFX cache with music/SFX volume; degrades to silence if audio is off."""

    def __init__(self, sfx_volume=0.7, music_volume=0.5):
        self.sfx_volume = sfx_volume
        self.music_volume = music_volume
        self._cache = {}
        self._music_channel = None
        self.available = bool(
            pygame.mixer.get_init() or self._try_init_mixer()
        )

    @staticmethod
    def _try_init_mixer():
        if pygame.mixer.get_init():
            return True
        try:
            pygame.mixer.init(frequency=_DEFAULT_SAMPLE_RATE, size=-16, channels=2, buffer=512)
            return True
        except pygame.error:
            return False

    def _build(self, key, freq, duration, wave="square"):
        if key in self._cache:
            return self._cache[key]
        snd = _make_sound(freq, duration, wave)
        self._cache[key] = snd
        return snd

    def play(self, key, freq=440, duration=0.08, wave="square"):
        if not self.available or self.sfx_volume <= 0:
            return
        snd = self._build(key, freq, duration, wave)
        if snd is not None:
            snd.set_volume(self.sfx_volume)
            snd.play()

    # Named cues
    def confirm(self):
        self.play("confirm", 660, 0.06)

    def hit(self):
        self.play("hit", 220, 0.09, wave="sawtooth" if _np else "square")

    def faint(self):
        self.play("faint", 160, 0.25)

    def catch_success(self):
        self.play("catch", 880, 0.15)
        self.play("catch2", 1320, 0.12)

    def catch_fail(self):
        self.play("fail", 200, 0.15)

    def level_up(self):
        self.play("lvl", 523, 0.08)
        self.play("lvl2", 784, 0.1)

    def heal(self):
        self.play("heal", 700, 0.12, wave="sine" if _np else "square")


def _make_sound(freq, duration, wave):
    if _np is None:
        return None
    try:
        stereo = _tone_samples(freq, duration, 1.0, wave)
        if stereo is None:
            return None
        return pygame.sndarray.make_sound(stereo)
    except (pygame.error, ValueError):
        return None


class SilentSound:
    """No-op stand-in when no audio device exists."""

    def play(self):
        pass

    def set_volume(self, v):
        pass
