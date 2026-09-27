"""Small local Pygame adapter for the authoritative HSR host.

The adapter owns timing, input, and drawing only. Rules, RNG, persistence, and
public-state projection remain in HSRHost/RunService.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    try:
        import pygame
    except ImportError as exc:
        raise SystemExit(
            "Pygame is optional. Install it with: "
            "python -m pip install -r requirements-local.txt"
        ) from exc

    from hollowstar.host import HSRHost

    pygame.init()
    screen = pygame.display.set_mode((960, 540), pygame.RESIZABLE)
    pygame.display.set_caption("Hollow Star Reliquary - Local Client")
    font = pygame.font.Font(None, 28)
    clock = pygame.time.Clock()
    host = HSRHost.from_options(data_root=ROOT / ".local")
    host.handle({"id": "pygame-boot", "command": "boot", "mode": "SANDBOX"})
    running = True
    message = "Local engine ready. Press Enter to create a run; Escape to quit."

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_RETURN:
                    result = host.handle({
                        "id": "pygame-create",
                        "command": "create_run",
                        "party": ["Doran", "Wren"],
                        "opposition": ["Townsperson"],
                        "seed": "pygame-local",
                        "scenario": "reliquary",
                    })
                    message = "Run created locally." if result.get("ok") else str(result)

        screen.fill((18, 23, 38))
        title = font.render("Hollow Star Reliquary", True, (230, 235, 255))
        body = font.render(message[:110], True, (190, 205, 225))
        screen.blit(title, (32, 32))
        screen.blit(body, (32, 84))
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
