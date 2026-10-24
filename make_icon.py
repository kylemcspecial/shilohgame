"""Generate the game icon (icon.png) and window sprite assets.

Runs on any machine with pygame-ce installed; no asset files are checked in.
Output: assets/icon.png (64x64).
"""
import os

import pygame

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")


def build_icon(path=None):
    pygame.init()
    size = 64
    icon = pygame.Surface((size, size), pygame.SRCALPHA)

    # dark forest-green rounded background
    pygame.draw.rect(icon, (24, 44, 28), (2, 2, 60, 60), border_radius=12)
    pygame.draw.rect(icon, (70, 140, 80), (2, 2, 60, 60), width=2, border_radius=12)

    # monster silhouette (ember type)
    body = (234, 120, 60)
    dark = (150, 60, 30)
    pygame.draw.ellipse(icon, body, (14, 22, 36, 28))
    pygame.draw.circle(icon, body, (32, 20), 13)
    # ears
    pygame.draw.polygon(icon, body, [(21, 12), (25, 20), (17, 20)])
    pygame.draw.polygon(icon, body, [(43, 12), (47, 20), (39, 20)])
    # eyes
    pygame.draw.circle(icon, (255, 255, 255), (26, 19), 4)
    pygame.draw.circle(icon, (255, 255, 255), (38, 19), 4)
    pygame.draw.circle(icon, (20, 20, 20), (27, 20), 2)
    pygame.draw.circle(icon, (20, 20, 20), (39, 20), 2)
    # fierce grin
    pygame.draw.arc(icon, dark, (24, 24, 16, 10), 3.3, 6.1, 2)
    # teeth
    pygame.draw.polygon(icon, (255, 255, 255), [(27, 31), (29, 35), (31, 31)])
    pygame.draw.polygon(icon, (255, 255, 255), [(33, 31), (35, 35), (37, 31)])
    # claw slashes
    pygame.draw.line(icon, (240, 220, 120), (10, 48), (20, 42), 2)
    pygame.draw.line(icon, (240, 220, 120), (54, 48), (44, 42), 2)

    os.makedirs(OUT_DIR, exist_ok=True)
    out = path or os.path.join(OUT_DIR, "icon.png")
    pygame.image.save(icon, out)
    pygame.quit()
    return out


if __name__ == "__main__":
    print("wrote", build_icon())
