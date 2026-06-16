"""
throbber.py — Live-mode throbber with file-change explosions.

Usage:
    python throbber.py

Monitors demo_file.txt in the current working directory.
Edit that file and save to trigger a colour explosion on the throbber.
Press Ctrl+C to quit.
"""

import time
import math
import os
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

from rich.console import Console
from rich.live import Live
from rich.text import Text


# ── Configuration ────────────────────────────────────────────────────────────

WATCH_FILE = Path("demo_file.txt")
WIDTH = 80          # number of cells in the throbber bar
FPS = 30            # render rate
WAVE_SPEED = 0.015   # fraction of WIDTH advanced per frame

# How many frames the wave "glow" is wide (Gaussian sigma in cells)
WAVE_SIGMA = 4.0

# Explosion colours (bright, vivid)
EXPLOSION_COLOURS = [
    (255, 50,  50),   # red
    (255, 140,  0),   # orange
    (255, 230,  0),   # yellow
    (0,   220, 80),   # green
    (0,   180, 255),  # cyan
    (60,  60,  255),  # blue
    (180,  0,  255),  # violet
    (255,  0,  180),  # pink
]

# How many frames an explosion lasts (rise + hold + fade)
EXPLOSION_DURATION = int(FPS * 1.8)   # ~1.8 s
EXPLOSION_SIGMA_MAX = WIDTH / 2.8     # how wide the colour wave spreads at peak

# Trail / fade: cells visited recently stay bright longer (0–1 per frame)
TRAIL_DECAY = 0.88   # per-frame multiplier for trail brightness


# ── State ────────────────────────────────────────────────────────────────────

@dataclass
class Explosion:
    origin: float          # cell position where it started
    colour: tuple          # (r, g, b)
    frame: int = 0         # frames since birth
    duration: int = EXPLOSION_DURATION

    @property
    def progress(self) -> float:
        return self.frame / self.duration

    @property
    def alive(self) -> bool:
        return self.frame < self.duration

    def intensity(self) -> float:
        """0→1→0 bell curve over the lifetime."""
        p = self.progress
        # quick rise, slow fade
        if p < 0.15:
            return p / 0.15
        return 1.0 - ((p - 0.15) / 0.85) ** 0.6

    def sigma(self) -> float:
        """Wave spread (in cells) as function of time."""
        p = self.progress
        # spread grows then holds
        spread = min(p / 0.4, 1.0)
        return 1.0 + spread * EXPLOSION_SIGMA_MAX

    def colour_at(self, cell: int) -> Optional[tuple]:
        """Return an (r,g,b) tinted by distance and intensity, or None."""
        dist = abs(cell - self.origin)
        sigma = self.sigma()
        gauss = math.exp(-0.5 * (dist / sigma) ** 2)
        intensity = self.intensity() * gauss
        if intensity < 0.01:
            return None
        r, g, b = self.colour
        return (int(r * intensity), int(g * intensity), int(b * intensity))


class ThrobberState:
    def __init__(self, width: int):
        self.width = width
        self.pos: float = 0.0        # 0.0 … 1.0 (fraction of width), ping-pong
        self.direction: int = 1      # +1 or -1
        self.trail: list[float] = [0.0] * width   # per-cell brightness 0–1
        self.explosions: list[Explosion] = []
        self._colour_cycle = 0

    def next_explosion_colour(self) -> tuple:
        c = EXPLOSION_COLOURS[self._colour_cycle % len(EXPLOSION_COLOURS)]
        self._colour_cycle += 1
        return c

    def trigger_explosion(self):
        origin_cell = self.pos * (self.width - 1)
        colour = self.next_explosion_colour()
        self.explosions.append(Explosion(origin=origin_cell, colour=colour))

    def advance(self):
        # Move the white wave head
        self.pos += self.direction * WAVE_SPEED
        if self.pos >= 1.0:
            self.pos = 1.0
            self.direction = -1
        elif self.pos <= 0.0:
            self.pos = 0.0
            self.direction = 1

        head_cell = self.pos * (self.width - 1)

        # Decay trail
        for i in range(self.width):
            self.trail[i] *= TRAIL_DECAY

        # White wave deposits brightness into trail
        for i in range(self.width):
            dist = abs(i - head_cell)
            gauss = math.exp(-0.5 * (dist / WAVE_SIGMA) ** 2)
            self.trail[i] = max(self.trail[i], gauss)

        # Age explosions
        for exp in self.explosions:
            exp.frame += 1
        self.explosions = [e for e in self.explosions if e.alive]

    def render(self) -> Text:
        line = Text()

        # Pre-compute per-cell explosion dominance (0 = full white, 1 = full colour).
        # We take the maximum colour intensity across all live explosions for each cell.
        cell_colour: list[Optional[tuple]] = [None] * self.width
        cell_dominance: list[float] = [0.0] * self.width

        for exp in self.explosions:
            for i in range(self.width):
                c = exp.colour_at(i)
                if c:
                    r, g, b = c
                    # Dominance = how strongly this cell is "owned" by the explosion.
                    # Use the peak channel so vivid colours dominate fully.
                    dominance = max(r, g, b) / 255.0
                    if dominance > cell_dominance[i]:
                        cell_dominance[i] = dominance
                        cell_colour[i] = (r, g, b)

        for i in range(self.width):
            dominance = cell_dominance[i]
            white_brightness = self.trail[i] * (1.0 - dominance)  # suppressed by explosion

            if dominance > 0.01 and cell_colour[i] is not None:
                er, eg, eb = cell_colour[i]
                # Colour channel at full explosion intensity; white fades in beneath as it dies
                r = min(255, er + int(80 * white_brightness))
                g = min(255, eg + int(80 * white_brightness))
                b = min(255, eb + int(80 * white_brightness))
            else:
                v = int(white_brightness * 80)
                r, g, b = v, v, v

            # Pick block character by local brightness
            total = (r + g + b) / 3
            if total > 200:
                ch = "█"
            elif total > 130:
                ch = "▓"
            elif total > 70:
                ch = "▒"
            elif total > 20:
                ch = "░"
            else:
                ch = " "

            line.append(ch, style=f"rgb({r},{g},{b})")

        return line


# ── File watcher ─────────────────────────────────────────────────────────────

class FileWatcher:
    def __init__(self, path: Path):
        self.path = path
        self._mtime: Optional[float] = self._read_mtime()

    def _read_mtime(self) -> Optional[float]:
        try:
            return self.path.stat().st_mtime
        except FileNotFoundError:
            return None

    def changed(self) -> bool:
        mtime = self._read_mtime()
        if mtime != self._mtime:
            self._mtime = mtime
            return True
        return False


# ── Main ─────────────────────────────────────────────────────────────────────

def ensure_demo_file():
    if not WATCH_FILE.exists():
        WATCH_FILE.write_text("Edit and save this file to trigger an explosion!\n")
        print(f"Created {WATCH_FILE}")


def build_display(state: ThrobberState, status: str) -> Text:
    bar = state.render()
    label = Text(f"\n {status}", style="dim white")
    bar.append_text(label)
    return bar


def main():
    ensure_demo_file()
    console = Console()
    state = ThrobberState(WIDTH)
    watcher = FileWatcher(WATCH_FILE)
    frame_time = 1.0 / FPS

    console.print(
        f"\n[bold cyan]Throbber live mode[/bold cyan]  "
        f"[dim]watching [white]{WATCH_FILE}[/white] — "
        f"Ctrl+C to quit[/dim]\n"
    )

    status = f"watching {WATCH_FILE} …"

    with Live(
        build_display(state, status),
        console=console,
        refresh_per_second=FPS,
        transient=False,
    ) as live:
        try:
            while True:
                t0 = time.monotonic()

                if watcher.changed():
                    state.trigger_explosion()
                    status = f"change detected in {WATCH_FILE}!"
                elif not state.explosions:
                    status = f"watching {WATCH_FILE} …"

                state.advance()
                live.update(build_display(state, status))

                elapsed = time.monotonic() - t0
                sleep = max(0.0, frame_time - elapsed)
                time.sleep(sleep)

        except KeyboardInterrupt:
            console.print("\n[dim]Live mode ended.[/dim]\n")


if __name__ == "__main__":
    main()