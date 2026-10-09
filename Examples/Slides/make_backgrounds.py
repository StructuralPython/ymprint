"""
Generates the vector PDF slide backgrounds used by slides.yml (1920 x 1080 pt, 16:9).

    uv run python make_backgrounds.py

Writes four single-page PDFs into backgrounds/:

    hero.pdf      title slide: synthwave sun over a perspective grid
    section.pdf   section dividers: wireframe millennium globe
    content.pdf   content slides: light "paper" with a dot grid and HUD trim
    closing.pdf   closing slide: centred sun and grid

Everything is drawn with ReportLab, the same library YMPrint renders with, using the
fonts bundled with YMPrint.
"""
import math
import pathlib
import random

from reportlab.lib.colors import HexColor, Color
from reportlab.pdfgen.canvas import Canvas

from ymprint.config.font_registry import register_fonts

W, H = 1920, 1080
OUT = pathlib.Path(__file__).parent / "backgrounds"

# Palette: the year 2000, as remembered by the year 2026
NIGHT = HexColor("#05061a")
INDIGO = HexColor("#160a40")
VIOLET = HexColor("#3a0f6e")
DUSK = HexColor("#6b1478")
CYAN = HexColor("#22e4ff")
MAGENTA = HexColor("#ff2bd6")
ORANGE = HexColor("#ff8a3d")
GOLD = HexColor("#ffe156")
PAPER = HexColor("#f7f6fc")
INK = HexColor("#1b1446")
DOT = HexColor("#d6d2ee")
RAINBOW = [CYAN, HexColor("#7b5cff"), MAGENTA, ORANGE]

MONO = "DejaVuSansMono"
MONO_BOLD = "DejaVuSansMono-Bold"
SANS_BOLD = "Montserrat-Bold"


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------

def gradient_rect(c, x, y, w, h, colors, vertical=True, positions=None):
    """Fills a rectangle with a linear gradient (bottom→top when vertical)."""
    c.saveState()
    p = c.beginPath()
    p.rect(x, y, w, h)
    c.clipPath(p, stroke=0, fill=0)
    if vertical:
        c.linearGradient(x, y, x, y + h, colors, positions, extend=False)
    else:
        c.linearGradient(x, y, x + w, y, colors, positions, extend=False)
    c.restoreState()


def stars(c, seed, n, y_min, y_max=H, x_min=0, x_max=W):
    rnd = random.Random(seed)
    c.saveState()
    for _ in range(n):
        x, y = rnd.uniform(x_min, x_max), rnd.uniform(y_min, y_max)
        r = rnd.choice([0.8, 1.0, 1.2, 1.6, 2.2])
        c.setFillColor(rnd.choice([HexColor("#ffffff"), CYAN, HexColor("#ffd6f5")]))
        c.setFillAlpha(rnd.uniform(0.25, 0.9))
        c.circle(x, y, r, stroke=0, fill=1)
        if r > 2:  # a few twinkles
            c.setStrokeColor(HexColor("#ffffff"))
            c.setStrokeAlpha(0.35)
            c.setLineWidth(0.6)
            c.line(x - 7, y, x + 7, y)
            c.line(x, y - 7, x, y + 7)
    c.restoreState()


def glow_line(c, x0, y0, x1, y1, color, width=2, layers=6):
    """A line with a soft neon halo built from wide, faint strokes."""
    c.saveState()
    c.setStrokeColor(color)
    c.setLineCap(1)
    for i in range(layers, 0, -1):
        c.setStrokeAlpha(0.05)
        c.setLineWidth(width + i * 5)
        c.line(x0, y0, x1, y1)
    c.setStrokeAlpha(1)
    c.setLineWidth(width)
    c.line(x0, y0, x1, y1)
    c.restoreState()


def halo(c, cx, cy, r, color, rings=14, spread=2.2, alpha=0.035):
    c.saveState()
    c.setFillColor(color)
    c.setFillAlpha(alpha)
    for i in range(rings):
        c.circle(cx, cy, r * (1 + (spread - 1) * (i + 1) / rings), stroke=0, fill=1)
    c.restoreState()


def synth_sun(c, cx, cy, r, horizon):
    """A striped gradient sun, clipped to the sky above 'horizon'."""
    halo(c, cx, cy, r, MAGENTA)
    c.saveState()
    clip = c.beginPath()
    clip.circle(cx, cy, r)
    c.clipPath(clip, stroke=0, fill=0)
    # Horizontal bands that get thinner towards the top of the sun
    bands = c.beginPath()
    bands.rect(cx - r, max(cy, horizon), 2 * r, r + 20)
    y, gap, band = cy, 14, 34
    while y > max(cy - r, horizon):
        top = y
        bottom = max(y - band, horizon)
        bands.rect(cx - r, bottom, 2 * r, top - bottom)
        y = bottom - gap
        gap += 4
        band = max(band - 4, 10)
    c.clipPath(bands, stroke=0, fill=0)
    c.linearGradient(cx, cy - r, cx, cy + r, [MAGENTA, ORANGE, GOLD], [0, 0.45, 1], extend=False)
    c.restoreState()


def perspective_grid(c, vx, horizon, color, bottom=0, rows=16, cols=34, alpha=0.9):
    """A neon floor receding to the vanishing point (vx, horizon)."""
    c.saveState()
    clip = c.beginPath()
    clip.rect(0, bottom, W, horizon - bottom)
    c.clipPath(clip, stroke=0, fill=0)
    gradient_rect(c, 0, bottom, W, horizon - bottom, [NIGHT, INDIGO, VIOLET], positions=[0, 0.7, 1])
    c.setStrokeColor(color)
    c.setLineWidth(1.6)
    depth = horizon - bottom
    # Rows: spacing grows geometrically away from the horizon
    for i in range(1, rows + 1):
        t = (i / rows) ** 2.2
        y = horizon - depth * t
        c.setStrokeAlpha(alpha * min(1, 0.15 + t * 1.3))
        c.line(0, y, W, y)
    # Columns: rays from the vanishing point, faded in segments near the horizon
    spread = W * 2.6
    for j in range(cols + 1):
        x_bottom = vx - spread / 2 + spread * j / cols
        segments = 10
        for s in range(segments):
            t0, t1 = s / segments, (s + 1) / segments
            xa = vx + (x_bottom - vx) * t0
            xb = vx + (x_bottom - vx) * t1
            ya = horizon - depth * t0
            yb = horizon - depth * t1
            c.setStrokeAlpha(alpha * (0.1 + 0.9 * t1))
            c.line(xa, ya, xb, yb)
    c.restoreState()
    glow_line(c, 0, horizon, W, horizon, MAGENTA, width=2.5, layers=8)


def wire_globe(c, cx, cy, r, color, alpha=0.8, width=1.4, tilt=0.32, meridians=12, parallels=7):
    """A tilted wireframe globe drawn from ellipses."""
    c.saveState()
    c.setStrokeColor(color)
    c.setLineWidth(width)
    c.setStrokeAlpha(alpha)
    c.circle(cx, cy, r, stroke=1, fill=0)
    # Parallels: ellipses squashed by the tilt
    for k in range(1, parallels + 1):
        lat = -math.pi / 2 + math.pi * k / (parallels + 1)
        ry = r * math.cos(lat)
        y = cy + r * math.sin(lat)
        c.ellipse(cx - ry, y - ry * tilt, cx + ry, y + ry * tilt, stroke=1, fill=0)
    # Meridians: ellipses of varying width
    for k in range(meridians // 2):
        rx = abs(r * math.cos(math.pi * k / meridians))
        c.ellipse(cx - rx, cy - r, cx + rx, cy + r, stroke=1, fill=0)
    c.restoreState()


def orbit(c, cx, cy, rx, ry, angle, color, alpha=0.9, width=2, dash=None):
    c.saveState()
    c.translate(cx, cy)
    c.rotate(angle)
    c.setStrokeColor(color)
    c.setStrokeAlpha(alpha)
    c.setLineWidth(width)
    if dash:
        c.setDash(dash)
    c.ellipse(-rx, -ry, rx, ry, stroke=1, fill=0)
    c.restoreState()


def hud_brackets(c, inset, size, color, alpha=0.9, width=3):
    c.saveState()
    c.setStrokeColor(color)
    c.setStrokeAlpha(alpha)
    c.setLineWidth(width)
    for x, sx in ((inset, 1), (W - inset, -1)):
        for y, sy in ((inset, 1), (H - inset, -1)):
            p = c.beginPath()
            p.moveTo(x + sx * size, y)
            p.lineTo(x, y)
            p.lineTo(x, y + sy * size)
            c.drawPath(p, stroke=1, fill=0)
    c.restoreState()


def crop_marks(c, inset, length, color, alpha=0.5):
    """Printer's registration marks: a wink at desktop publishing."""
    c.saveState()
    c.setStrokeColor(color)
    c.setStrokeAlpha(alpha)
    c.setLineWidth(1)
    for x in (inset, W - inset):
        for y in (inset, H - inset):
            c.line(x - length, y, x + length, y)
            c.line(x, y - length, x, y + length)
            c.circle(x, y, length * 0.45, stroke=1, fill=0)
    c.restoreState()


def scanlines(c, alpha=0.07, step=4):
    c.saveState()
    c.setStrokeColor(HexColor("#000000"))
    c.setStrokeAlpha(alpha)
    c.setLineWidth(1.4)
    for y in range(0, H, step):
        c.line(0, y, W, y)
    c.restoreState()


def label(c, x, y, text, color, size=17, font=MONO, alpha=0.85, anchor="left", tracking=2.5):
    c.saveState()
    c.setFillColor(color)
    c.setFillAlpha(alpha)
    t = c.beginText()
    t.setFont(font, size)
    t.setCharSpace(tracking)
    width = c.stringWidth(text, font, size) + tracking * (len(text) - 1)
    t.setTextOrigin(x - width if anchor == "right" else x, y)
    t.textOut(text)
    c.drawText(t)
    c.restoreState()


def chrome_pill(c, x, y, w, h, text, size=18):
    """A brushed-chrome lozenge with an engraved label."""
    c.saveState()
    p = c.beginPath()
    p.roundRect(x, y, w, h, h / 2)
    c.clipPath(p, stroke=0, fill=0)
    c.linearGradient(x, y, x, y + h,
                     [HexColor("#8c93b8"), HexColor("#f4f6ff"), HexColor("#b9bfdc"), HexColor("#ffffff")],
                     [0, 0.48, 0.52, 1], extend=False)
    c.restoreState()
    c.saveState()
    c.setStrokeColor(HexColor("#5a5f86"))
    c.setLineWidth(1.2)
    c.roundRect(x, y, w, h, h / 2, stroke=1, fill=0)
    c.restoreState()
    label(c, x + w / 2 + c.stringWidth(text, MONO_BOLD, size) / 2 + 1.5 * (len(text) - 1), y + h / 2 - size * 0.35,
          text, INK, size=size, font=MONO_BOLD, alpha=1, anchor="right", tracking=3)


def rainbow_bar(c, x, y, w, h):
    gradient_rect(c, x, y, w, h, RAINBOW, vertical=False)


def status_dots(c, x, y, colors, r=6, gap=22):
    c.saveState()
    for i, col in enumerate(colors):
        c.setFillColor(col)
        c.circle(x + i * gap, y, r, stroke=0, fill=1)
    c.restoreState()


def new_canvas(name):
    OUT.mkdir(exist_ok=True)
    c = Canvas(str(OUT / name), pagesize=(W, H))
    c.setTitle(f"YMPrint slide background: {name}")
    c.setAuthor("YMPrint")
    return c


# ---------------------------------------------------------------------------
# Backgrounds
# ---------------------------------------------------------------------------

def dark_frame(c, tagline):
    """Shared HUD trim for the dark slides."""
    scanlines(c)
    hud_brackets(c, 36, 54, CYAN, alpha=0.75, width=3)
    label(c, 120, H - 66, "YMPRINT", CYAN, size=19, font=MONO_BOLD, tracking=6)
    label(c, 258, H - 66, "// SLIDE ENGINE", HexColor("#ffffff"), size=19, alpha=0.55)
    label(c, W - 120, H - 66, tagline, HexColor("#ffffff"), size=17, alpha=0.55, anchor="right")
    status_dots(c, W - 166, 64, [CYAN, MAGENTA, GOLD], r=6)
    label(c, 120, 58, "YAML  ▸  PDF  ▸  1920×1080  ▸  100% VECTOR", HexColor("#ffffff"), size=16, alpha=0.5)


def make_hero():
    c = new_canvas("hero.pdf")
    horizon = 300
    gradient_rect(c, 0, horizon, W, H - horizon, [DUSK, VIOLET, INDIGO, NIGHT], positions=[0, 0.25, 0.6, 1])
    stars(c, seed=2000, n=170, y_min=horizon + 120)
    synth_sun(c, 1460, 540, 300, horizon)
    # Distant wireframe mountains on the horizon
    c.saveState()
    rnd = random.Random(7)
    for base_x, peaks, scale, color in ((40, 9, 120, CYAN), (980, 6, 80, MAGENTA)):
        p = c.beginPath()
        p.moveTo(base_x, horizon)
        x = base_x
        for _ in range(peaks):
            x += rnd.uniform(40, 90)
            p.lineTo(x, horizon + rnd.uniform(0.3, 1) * scale)
        p.lineTo(x + 60, horizon)
        c.setFillColor(NIGHT)
        c.setFillAlpha(0.85)
        c.setStrokeColor(color)
        c.setStrokeAlpha(0.7)
        c.setLineWidth(1.6)
        c.drawPath(p, stroke=1, fill=1)
    c.restoreState()
    perspective_grid(c, 1460, horizon, CYAN)
    rainbow_bar(c, 120, 458, 220, 6)
    dark_frame(c, "REV 2000.26  //  BUILD Y2K-OK")
    c.showPage()
    c.save()


def make_section():
    c = new_canvas("section.pdf")
    horizon = 230
    gradient_rect(c, 0, horizon, W, H - horizon, [VIOLET, INDIGO, NIGHT], positions=[0, 0.45, 1])
    stars(c, seed=1999, n=120, y_min=horizon + 60)
    cx, cy, r = 1450, 600, 290
    halo(c, cx, cy, r, CYAN, rings=12, spread=1.7, alpha=0.03)
    c.saveState()
    c.setFillColor(NIGHT)
    c.setFillAlpha(0.6)
    c.circle(cx, cy, r, stroke=0, fill=1)
    c.restoreState()
    wire_globe(c, cx, cy, r, CYAN, alpha=0.75)
    orbit(c, cx, cy, r * 1.45, r * 0.32, 18, MAGENTA, alpha=0.9, width=2.5)
    orbit(c, cx, cy, r * 1.3, r * 0.22, -24, GOLD, alpha=0.6, width=1.5, dash=[10, 8])
    # A satellite on the magenta orbit
    a = math.radians(200)
    sx, sy = r * 1.45 * math.cos(a), r * 0.32 * math.sin(a)
    rot = math.radians(18)
    px = cx + sx * math.cos(rot) - sy * math.sin(rot)
    py = cy + sx * math.sin(rot) + sy * math.cos(rot)
    halo(c, px, py, 9, MAGENTA, rings=6, spread=3, alpha=0.12)
    c.setFillColor(HexColor("#ffffff"))
    c.circle(px, py, 7, stroke=0, fill=1)
    perspective_grid(c, 1450, horizon, MAGENTA, rows=12, alpha=0.75)
    rainbow_bar(c, 120, 458, 160, 6)
    dark_frame(c, "SECTION  //  STAND BY")
    c.showPage()
    c.save()


def make_content():
    c = new_canvas("content.pdf")
    c.setFillColor(PAPER)
    c.rect(0, 0, W, H, stroke=0, fill=1)
    # Dot grid
    c.setFillColor(DOT)
    for x in range(40, W, 40):
        for y in range(40, H, 40):
            c.circle(x, y, 1.6, stroke=0, fill=1)
    # A huge, faint globe bleeding off the bottom-right corner
    wire_globe(c, W - 40, -60, 420, HexColor("#7b5cff"), alpha=0.12, width=2)
    orbit(c, W - 40, -60, 600, 150, 14, MAGENTA, alpha=0.12, width=2)
    # Header trim: rainbow edge and a hairline under the title zone
    rainbow_bar(c, 0, H - 10, W, 10)
    gradient_rect(c, 120, H - 252, W - 240, 3, RAINBOW, vertical=False)
    c.saveState()
    c.setFillColor(INK)
    for i, col in enumerate([CYAN, MAGENTA, ORANGE]):
        c.setFillColor(col)
        c.rect(W - 120 - 18 - i * 26, H - 252 - 7.5, 18, 18, stroke=0, fill=1)
    c.restoreState()
    crop_marks(c, 40, 14, INK, alpha=0.35)
    # Footer
    chrome_pill(c, 120, 38, 196, 40, "YMPRINT", size=17)
    label(c, 340, 50, "SLIDES  //  THE TECHNOLOGY OF THE YEAR 2000… TODAY", INK, size=16, alpha=0.6)
    label(c, W - 120, 50, "1920×1080  ·  VECTOR PDF", INK, size=16, alpha=0.6, anchor="right")
    c.showPage()
    c.save()


def make_closing():
    c = new_canvas("closing.pdf")
    horizon = 330
    gradient_rect(c, 0, horizon, W, H - horizon, [DUSK, VIOLET, INDIGO, NIGHT], positions=[0, 0.25, 0.6, 1])
    stars(c, seed=2026, n=190, y_min=horizon + 80)
    synth_sun(c, W / 2, 360, 180, horizon)
    perspective_grid(c, W / 2, horizon, CYAN, rows=14)
    dark_frame(c, "END OF TRANSMISSION")
    c.showPage()
    c.save()


if __name__ == "__main__":
    register_fonts()
    for make in (make_hero, make_section, make_content, make_closing):
        make()
    print(f"Backgrounds written to {OUT}")
