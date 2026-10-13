#!/usr/bin/env python3
"""Generate the static profile SVGs into assets/.  Run: python3 scripts/build.py

GitHub renders these through <img>: no JS, no hover, no external fonts or images.
Everything moves with CSS keyframes / SMIL only.
"""
import math
import random
from html import escape
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "assets"

BG = "#060608"
INK = "#0C0C10"
GOLD = "#E8C766"
GOLD_HI = "#FFF1C1"
GOLD_LO = "#9A7428"
CYAN = "#3DF5FF"
TITLE = "#F2D27A"  # solid: WebKit renders gradient fills on textLength-stretched text jagged
MONO = "'SF Mono','JetBrains Mono',Menlo,Consolas,'Liberation Mono','DejaVu Sans Mono'"
CJK = "'PingFang SC','Hiragino Sans GB','Microsoft YaHei','Noto Sans CJK SC','Source Han Sans SC',sans-serif"
FONT = f"{MONO},{CJK}"

rnd = random.Random(9)


def tw(s, size):
    """Estimated advance width: monospace Latin 0.6em, CJK 1em."""
    return sum(1.0 if ord(ch) >= 0x2E80 else 0.6 for ch in s) * size


def text(x, y, s, size, fill, *, anchor="start", weight=400, fit=False, extra="", ls=None):
    """<text>; fit=True pins the width with textLength so layout survives any fallback font."""
    attrs = f'x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" text-anchor="{anchor}"'
    if weight != 400:
        attrs += f' font-weight="{weight}"'
    if fit:
        attrs += f' textLength="{tw(s, size) if ls is None else ls:.1f}" lengthAdjust="spacingAndGlyphs"'
    return f"<text {attrs} {extra}>{escape(s)}</text>"


def svg(w, h, body, style, defs=""):
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
        f'font-family="{FONT}">\n'
        f"<style>{style}</style>\n"
        f'<defs>{COMMON_DEFS}{defs}'
        f'<clipPath id="frame"><rect width="{w}" height="{h}" rx="18"/></clipPath></defs>\n'
        f'<g clip-path="url(#frame)">\n<rect width="{w}" height="{h}" fill="{BG}"/>\n{body}\n</g>\n'
        f'<rect x=".5" y=".5" width="{w - 1}" height="{h - 1}" rx="18" fill="none" stroke="{GOLD}" stroke-opacity=".18"/>\n'
        "</svg>\n"
    )


COMMON_DEFS = f"""
<linearGradient id="gold" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="{GOLD_HI}"/><stop offset=".45" stop-color="{GOLD}"/>
  <stop offset=".75" stop-color="#C79A3A"/><stop offset="1" stop-color="{GOLD_LO}"/>
</linearGradient>
<linearGradient id="goldH" x1="0" y1="0" x2="1" y2="0">
  <stop offset="0" stop-color="{GOLD_LO}"/><stop offset=".5" stop-color="{GOLD_HI}"/><stop offset="1" stop-color="{GOLD_LO}"/>
</linearGradient>
<pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse">
  <rect width="4" height="1" fill="#fff" fill-opacity=".035"/>
</pattern>
<filter id="glow" x="-20%" y="-50%" width="140%" height="200%"><feGaussianBlur stdDeviation="9"/></filter>
<filter id="soft" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="3"/></filter>
"""

SCAN_CSS = """
@keyframes sweep{from{transform:translateY(-160px)}to{transform:translateY(var(--h))}}
.sweep{animation:sweep 7s linear infinite}
@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}
.blink{animation:blink 1.1s steps(1) infinite}
@keyframes pulse{0%,100%{opacity:.35}50%{opacity:1}}
"""


def overlay(w, h):
    """Scanlines + slow light sweep, laid over every panel."""
    return (
        f'<rect width="{w}" height="{h}" fill="url(#scan)"/>'
        f'<rect class="sweep" style="--h:{h}px" width="{w}" height="160" fill="url(#sweepG)"/>'
    )


SWEEP_DEF = """<linearGradient id="sweepG" x1="0" y1="0" x2="0" y2="1">
<stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#FFE9A8" stop-opacity=".05"/>
<stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>"""


def corners(x, y, w, h, n=26, inset=0, op=".7"):
    x0, y0, x1, y1 = x + inset, y + inset, x + w - inset, y + h - inset
    d = (f"M{x0},{y0 + n}V{y0}H{x0 + n} M{x1 - n},{y0}H{x1}V{y0 + n} "
         f"M{x1},{y1 - n}V{y1}H{x1 - n} M{x0 + n},{y1}H{x0}V{y1 - n}")
    return f'<path d="{d}" fill="none" stroke="{GOLD}" stroke-opacity="{op}" stroke-width="1.5"/>'


def section_label(x, y, num, en, zh, w):
    return (
        f'<rect x="{x}" y="{y - 11}" width="6" height="14" fill="{GOLD}"/>'
        + text(x + 16, y, f"// {num}", 13, GOLD, extra='opacity=".55" letter-spacing="2"')
        + text(x + 80, y, en, 15, GOLD, weight=700, fit=True)
        + text(x + 92 + tw(en, 15), y, zh, 14, "#8A8A8A")
        + f'<line x1="{x + 108 + tw(en, 15) + tw(zh, 14)}" y1="{y - 5}" x2="{x + w}" y2="{y - 5}" '
          f'stroke="{GOLD}" stroke-opacity=".22"/>'
        + f'<rect x="{x + w - 40}" y="{y - 7}" width="40" height="3" fill="{GOLD}" opacity=".6"/>'
    )


# --------------------------------------------------------------------- hero

# Custom angular display face on a 6x10 grid. Each glyph: list of (points, closed).
C_ = 1.7
GLYPHS = {
    "M": [([(0, 10), (0, 0), (3, 6), (6, 0), (6, 10)], False)],
    "I": [([(1, 0), (5, 0)], False), ([(3, 0), (3, 10)], False), ([(1, 10), (5, 10)], False)],
    "C": [([(6, 0), (C_, 0), (0, C_), (0, 10 - C_), (C_, 10), (6, 10)], False)],
    "H": [([(0, 0), (0, 10)], False), ([(6, 0), (6, 10)], False), ([(0, 5), (6, 5)], False)],
    "A": [([(0, 10), (0, 2.2), (2.2, 0), (3.8, 0), (6, 2.2), (6, 10)], False), ([(0, 6), (6, 6)], False)],
    "E": [([(6, 0), (0, 0), (0, 10), (6, 10)], False), ([(0, 5), (4.4, 5)], False)],
    "L": [([(0, 0), (0, 10), (6, 10)], False)],
    "Z": [([(0, 0), (6, 0), (0, 10), (6, 10)], False)],
    "O": [([(C_, 0), (6 - C_, 0), (6, C_), (6, 10 - C_), (6 - C_, 10), (C_, 10), (0, 10 - C_), (0, C_)], True)],
    "9": [([(6, 5.4), (C_, 5.4), (0, 5.4 - C_), (0, C_), (C_, 0), (6 - C_, 0), (6, C_), (6, 10 - C_),
            (6 - C_, 10), (0, 10)], False)],
}


def word_paths(word, x0, y0, s, adv=8.6):
    paths = []
    for i, ch in enumerate(word):
        ox = x0 + i * adv * s
        for pts, closed in GLYPHS[ch]:
            d = "M" + " L".join(f"{ox + px * s:.1f},{y0 + py * s:.1f}" for px, py in pts)
            paths.append((i, d + ("Z" if closed else "")))
    return paths


def hero():
    W, H = 1200, 520
    HZ = 352  # horizon
    name = "MICHAELZHAO9"
    s = 8.2
    nw = (len(name) - 1) * 8.6 * s + 6 * s
    nx, ny = (W - nw) / 2, 150
    cy = ny + 5 * s
    paths = word_paths(name, nx, ny, s)
    sw = 1.25 * s

    def strokes(stroke, width, cls=True, extra=""):
        out = []
        for i, d in paths:
            c = f' class="draw" style="animation-delay:{.25 + i * .07:.2f}s"' if cls else ""
            out.append(f'<path d="{d}" pathLength="1"{c}/>')
        return (f'<g fill="none" stroke="{stroke}" stroke-width="{width:.1f}" stroke-linecap="square" '
                f'stroke-linejoin="miter" {extra}>' + "".join(out) + "</g>")

    style = SCAN_CSS + f"""
.draw{{stroke-dasharray:1 1;stroke-dashoffset:1;animation:draw 1.3s cubic-bezier(.7,0,.2,1) forwards}}
@keyframes draw{{to{{stroke-dashoffset:0}}}}
.late{{opacity:0;animation:fadein 1s 1.6s forwards}}
@keyframes fadein{{to{{opacity:1}}}}
@keyframes breathe{{0%,100%{{opacity:.45}}50%{{opacity:.8}}}}
.halo{{opacity:0;animation:fadein 1s 1.6s forwards,breathe 4s 2.6s ease-in-out infinite}}
@keyframes shine{{0%,55%{{transform:translateX(-500px)}}85%,100%{{transform:translateX({W + 300}px)}}}}
.shine{{animation:shine 6s 2s cubic-bezier(.5,0,.3,1) infinite;transform:translateX(-500px)}}
@keyframes g1{{0%,88%,100%{{opacity:0;transform:translate(0,0)}}89%{{opacity:.9;transform:translate(-16px,0)}}
  91%{{opacity:.9;transform:translate(10px,0)}}93%{{opacity:.7;transform:translate(-5px,0)}}94%{{opacity:0}}}}
@keyframes g2{{0%,89%,100%{{opacity:0;transform:translate(0,0)}}90%{{opacity:.85;transform:translate(14px,0)}}
  92%{{opacity:.85;transform:translate(-8px,0)}}94%{{opacity:0}}}}
.g1{{animation:g1 5s 3s infinite;opacity:0}} .g2{{animation:g2 5s 3s infinite;opacity:0}}
@keyframes jolt{{0%,88.5%,94.5%,100%{{transform:translate(0,0)}}89.5%{{transform:translate(3px,0)}}
  91.5%{{transform:translate(-2px,0)}}}}
.jolt{{animation:jolt 5s 3s infinite}}
@keyframes spin{{to{{transform:rotate(360deg)}}}}
@keyframes rspin{{to{{transform:rotate(-360deg)}}}}
.r1,.r2,.r3{{transform-origin:600px {cy}px}}
.r1{{animation:spin 60s linear infinite}} .r2{{animation:rspin 34s linear infinite}} .r3{{animation:spin 90s linear infinite}}
@keyframes floor{{from{{transform:translateY(0)}}to{{transform:translateY({H - HZ}px)}}}}
.fl{{animation:floor 5s cubic-bezier(.75,0,.95,.6) infinite}}
@keyframes tw{{0%,100%{{opacity:.1}}50%{{opacity:.9}}}}
.st{{animation:tw 3s ease-in-out infinite}}
@keyframes hz{{0%,100%{{opacity:.7}}50%{{opacity:1}}}}
"""

    # --- backdrop
    defs = SWEEP_DEF + f"""
<radialGradient id="sun" cx="600" cy="{HZ}" r="520" gradientUnits="userSpaceOnUse">
  <stop offset="0" stop-color="{GOLD}" stop-opacity=".28"/><stop offset=".35" stop-color="#8A6418" stop-opacity=".1"/>
  <stop offset="1" stop-color="{GOLD}" stop-opacity="0"/></radialGradient>
<radialGradient id="vig" cx=".5" cy=".45" r=".75"><stop offset=".55" stop-color="#000" stop-opacity="0"/>
  <stop offset="1" stop-color="#000" stop-opacity=".85"/></radialGradient>
<linearGradient id="floorFade" x1="0" y1="{HZ}" x2="0" y2="{H}" gradientUnits="userSpaceOnUse">
  <stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".15" stop-color="#fff" stop-opacity=".35"/>
  <stop offset="1" stop-color="#fff" stop-opacity="1"/></linearGradient>
<mask id="floorM"><rect y="{HZ}" width="{W}" height="{H - HZ}" fill="url(#floorFade)"/></mask>
<linearGradient id="shineG" x1="0" y1="0" x2="1" y2="0">
  <stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".95"/>
  <stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
<mask id="nameM">{strokes("#fff", sw, cls=False)}</mask>
<clipPath id="band1"><rect x="0" y="{ny + 12}" width="{W}" height="18"/><rect x="0" y="{ny + 58}" width="{W}" height="9"/></clipPath>
<clipPath id="band2"><rect x="0" y="{ny + 34}" width="{W}" height="14"/><rect x="0" y="{ny + 72}" width="{W}" height="7"/></clipPath>
"""
    body = [f'<rect width="{W}" height="{H}" fill="url(#sun)"/>']

    # stars
    for _ in range(70):
        x, y = rnd.uniform(20, W - 20), rnd.uniform(20, HZ - 20)
        r = rnd.choice([.6, .8, 1, 1.3, 1.7])
        body.append(f'<circle class="st" cx="{x:.0f}" cy="{y:.0f}" r="{r}" fill="{GOLD_HI}" '
                    f'style="animation-delay:-{rnd.uniform(0, 3):.2f}s;animation-duration:{rnd.uniform(2, 5):.1f}s"/>')

    # reticle behind the name
    R = [(118, ""), (150, ""), (186, "")]
    ticks = "".join(
        f'<line x1="600" y1="{cy - 186}" x2="600" y2="{cy - 186 + (12 if k % 6 == 0 else 5)}" '
        f'transform="rotate({k * 5} 600 {cy})"/>' for k in range(72))
    arcs = []
    for a0 in (10, 100, 190, 280):
        a1 = a0 + 62
        p = lambda a: (600 + 150 * math.cos(math.radians(a)), cy + 150 * math.sin(math.radians(a)))
        (x0, y0), (x1, y1) = p(a0), p(a1)
        arcs.append(f'<path d="M{x0:.1f},{y0:.1f} A150,150 0 0 1 {x1:.1f},{y1:.1f}"/>')
    body.append(
        f'<g fill="none" stroke="{GOLD}" class="late">'
        f'<g class="r1" stroke-opacity=".28">{ticks}</g>'
        f'<g class="r2" stroke-opacity=".55" stroke-width="2">{"".join(arcs)}</g>'
        f'<circle class="r3" cx="600" cy="{cy}" r="{R[0][0]}" stroke-opacity=".22" stroke-dasharray="2 7"/>'
        f'<circle cx="600" cy="{cy}" r="230" stroke-opacity=".07"/>'
        f'<line x1="330" y1="{cy}" x2="420" y2="{cy}" stroke-opacity=".3"/>'
        f'<line x1="780" y1="{cy}" x2="870" y2="{cy}" stroke-opacity=".3"/>'
        "</g>")

    # floor grid
    fl = [f'<g mask="url(#floorM)" stroke="{GOLD}" fill="none">']
    for k in range(-22, 23):
        fl.append(f'<line x1="600" y1="{HZ}" x2="{600 + k * 110}" y2="{H}" stroke-opacity=".5"/>')
    n = 14
    for k in range(n):
        fl.append(f'<line class="fl" x1="0" y1="{HZ}" x2="{W}" y2="{HZ}" stroke-opacity=".75" '
                  f'style="animation-delay:-{k * 5 / n:.2f}s"/>')
    fl.append("</g>")
    body += fl
    body.append(f'<rect x="0" y="{HZ}" width="{W}" height="{H - HZ}" fill="url(#sun)" opacity=".5"/>')
    body.append(f'<line x1="0" y1="{HZ}" x2="{W}" y2="{HZ}" stroke="url(#goldH)" stroke-width="1.5" '
                f'style="animation:hz 3s ease-in-out infinite"/>')
    body.append(f'<line x1="200" y1="{HZ}" x2="{W - 200}" y2="{HZ}" stroke="{GOLD}" stroke-width="6" '
                f'filter="url(#glow)" opacity=".7"/>')

    # name
    body.append(f'<g class="jolt">')
    body.append(f'<g class="halo" filter="url(#glow)">{strokes(GOLD, sw * 1.3, cls=False)}</g>')
    body.append(strokes("url(#gold)", sw))
    body.append(f'<g class="late">{strokes(BG, sw * .26, cls=False)}</g>')
    body.append(f'<g mask="url(#nameM)"><rect class="shine" x="0" y="{ny - 20}" width="260" height="{10 * s + 40}" '
                f'fill="url(#shineG)" transform="skewX(-20)"/></g>')
    body.append(f'<g clip-path="url(#band1)"><g class="g1">{strokes(CYAN, sw, cls=False)}</g></g>')
    body.append(f'<g clip-path="url(#band2)"><g class="g2">{strokes(GOLD_HI, sw, cls=False)}</g></g>')
    body.append("</g>")

    # rotating tagline with typewriter
    phrases = [
        "INDIE DEVELOPER  ·  独立开发者",
        "AI TOOLS  ·  APPLE PLATFORMS  ·  GAMES",
        "SWIFT · RUST · TYPESCRIPT · PYTHON · C#",
        "THINK SLOW, SHIP FAST.  想得慢，做得快",
    ]
    ty, fs = 292, 17
    cyc = 16
    slot = 100 / len(phrases)
    css = []
    tag = []
    for i, ph in enumerate(phrases):
        w = tw(ph, fs)
        x0 = 600 - w / 2
        a, b = i * slot, (i + 1) * slot
        typed = a + slot * .42
        steps = len(ph)
        css.append(
            f"@keyframes ph{i}{{0%,{max(a - .01, 0):.2f}%{{opacity:0}}{a:.2f}%,{b - 1.5:.2f}%{{opacity:1}}"
            f"{b - .5:.2f}%,100%{{opacity:0}}}}"
            f"@keyframes rv{i}{{0%,{a:.2f}%{{transform:translateX({-w - 2:.1f}px);animation-timing-function:steps({steps},end)}}"
            f"{typed:.2f}%,100%{{transform:translateX(0)}}}}"
            f"@keyframes cu{i}{{0%,{a:.2f}%{{transform:translateX(0);animation-timing-function:steps({steps},end)}}"
            f"{typed:.2f}%,100%{{transform:translateX({w + 4:.1f}px)}}}}"
        )
        defs += (f'<clipPath id="tc{i}"><rect x="{x0 - 2:.1f}" y="{ty - 22}" width="{w + 4:.1f}" height="32" '
                 f'style="animation:rv{i} {cyc}s 1.8s infinite;transform:translateX({-w - 2:.1f}px)"/></clipPath>')
        tag.append(
            f'<g style="animation:ph{i} {cyc}s 1.8s infinite;opacity:0">'
            f'<g clip-path="url(#tc{i})">{text(x0, ty, ph, fs, GOLD_HI, fit=True, extra="letter-spacing=\'1\'")}</g>'
            f'<g style="animation:cu{i} {cyc}s 1.8s infinite"><rect class="blink" x="{x0:.1f}" y="{ty - 15}" '
            f'width="9" height="19" fill="{GOLD}"/></g></g>')
    style += "".join(css)
    body.append(f'<g>{"".join(tag)}</g>')
    body.append(f'<g stroke="{GOLD}" stroke-opacity=".5" class="late">'
                f'<line x1="240" y1="{ty - 6}" x2="330" y2="{ty - 6}"/><line x1="870" y1="{ty - 6}" x2="960" y2="{ty - 6}"/>'
                f'<rect x="333" y="{ty - 9}" width="6" height="6" fill="{GOLD}" transform="rotate(45 336 {ty - 6})"/>'
                f'<rect x="861" y="{ty - 9}" width="6" height="6" fill="{GOLD}" transform="rotate(45 864 {ty - 6})"/></g>')

    # HUD chrome
    hud = 'opacity=".6" letter-spacing="2"'
    body.append(corners(0, 0, W, H, n=30, inset=22))
    body.append(text(48, 52, "MZ9 // PROFILE.SYS", 11, GOLD, extra=hud))
    body.append(text(48, 70, "BUILD 2026.10 · REV 9", 11, GOLD, extra='opacity=".35" letter-spacing="2"'))
    body.append(f'<circle cx="{W - 140}" cy="48" r="4" fill="{CYAN}" style="animation:pulse 1.6s ease-in-out infinite"/>')
    body.append(text(W - 128, 52, "ONLINE", 11, CYAN, extra='letter-spacing="2" opacity=".85"'))
    sig = "".join(f'<rect x="{W - 140 + k * 8}" y="{70 - 3 - k * 2}" width="5" height="{4 + k * 2}" fill="{GOLD}" '
                  f'opacity="{.8 if k < 4 else .25}"/>' for k in range(5))
    body.append(sig + text(W - 92, 70, "SIG", 11, GOLD, extra='opacity=".35" letter-spacing="2"'))
    hexes = ["0x7F3A·C91E", "0x1B0D·44AF", "0xE2C8·9D07", "0x5A61·F0B3"]
    hx = []
    for k, hv in enumerate(hexes):
        a, b = k * 25, (k + 1) * 25
        style += f"@keyframes hx{k}{{0%,{a}%{{opacity:0}}{a + .01}%,{b}%{{opacity:.45}}{b + .01}%,100%{{opacity:0}}}}"
        hx.append(text(48, H - 44, hv, 11, GOLD, extra=f'letter-spacing="2" style="animation:hx{k} 2.4s steps(1) infinite;opacity:0"'))
    body.append("".join(hx))
    body.append(text(48, H - 62, "SEC.CHANNEL", 11, GOLD, extra='opacity=".3" letter-spacing="2"'))
    body.append(text(W - 48, H - 44, "SCROLL ▼", 11, GOLD, anchor="end",
                     extra='letter-spacing="3" style="animation:pulse 2s ease-in-out infinite"'))

    body.append(f'<rect width="{W}" height="{H}" fill="url(#vig)"/>')
    body.append(overlay(W, H))
    return svg(W, H, "\n".join(body), style, defs)


# --------------------------------------------------------------------- about: terminal + stack orbit

def about():
    W, H = 1200, 500
    style = SCAN_CSS
    defs = SWEEP_DEF
    body = [section_label(36, 46, "01", "ABOUT", "关于我", W - 72)]

    # terminal window
    tx, ty, tw_, th = 36, 76, 680, 392
    body.append(f'<rect x="{tx}" y="{ty}" width="{tw_}" height="{th}" rx="12" fill="{INK}" stroke="{GOLD}" stroke-opacity=".25"/>')
    body.append(f'<path d="M{tx},{ty + 36}H{tx + tw_}" stroke="{GOLD}" stroke-opacity=".18"/>')
    for k, c in enumerate([GOLD, "#8A6A2A", "#3A3426"]):
        body.append(f'<circle cx="{tx + 22 + k * 20}" cy="{ty + 18}" r="6" fill="{c}"/>')
    body.append(text(tx + tw_ / 2, ty + 23, "michaelzhao9@hq: ~ — zsh", 12, "#7A7A7A", anchor="middle"))

    lines = [
        ("cmd", "whoami"),
        ("out", "michaelzhao9 — indie developer / 独立开发者"),
        ("cmd", "cat focus.txt"),
        ("out", "AI tools · Apple platforms · Game dev · Screeps AI"),
        ("cmd", "ls ~/stack"),
        ("out", "swift  rust  typescript  python  c#  unity  react"),
        ("cmd", "echo $MOTTO"),
        ("out", "想得慢，做得快。Think slow, ship fast."),
    ]
    cyc = 18.0
    t = 0.6
    fs = 15
    lx, ly = tx + 26, ty + 76
    end = 88
    for i, (kind, s) in enumerate(lines):
        y = ly + i * 37
        prefix = "❯ " if kind == "cmd" else "  "
        x0 = lx + (tw(prefix, fs))
        w = tw(s, fs)
        dur = .045 * len(s) if kind == "cmd" else .25
        a, b = t / cyc * 100, (t + dur) / cyc * 100
        t += dur + (.35 if kind == "cmd" else .55)
        steps = len(s) if kind == "cmd" else 1
        style += (f"@keyframes l{i}{{0%,{a:.2f}%{{transform:translateX({-w - 4:.1f}px);"
                  f"animation-timing-function:steps({steps},end)}}{b:.2f}%,100%{{transform:translateX(0)}}}}")
        defs += (f'<clipPath id="lc{i}"><rect x="{x0 - 2:.1f}" y="{y - 18}" width="{w + 4:.1f}" height="26" '
                 f'style="animation:l{i} {cyc}s infinite;transform:translateX({-w - 4:.1f}px)"/></clipPath>')
        style += (f"@keyframes p{i}{{0%,{a:.2f}%{{opacity:0}}{a + .01:.2f}%,{end}%{{opacity:1}}{end + 4}%,100%{{opacity:0}}}}")
        fill = "#EDEDED" if kind == "cmd" else ("#D9B65C" if i == len(lines) - 1 else "#9A9A9A")
        row = ""
        if kind == "cmd":
            row += text(lx, y, "❯", fs, GOLD, weight=700)
        row += f'<g clip-path="url(#lc{i})">{text(x0, y, s, fs, fill, fit=True)}</g>'
        body.append(f'<g style="animation:p{i} {cyc}s infinite;opacity:0">{row}</g>')
    a = t / cyc * 100
    y = ly + len(lines) * 37
    style += f"@keyframes pz{{0%,{a:.2f}%{{opacity:0}}{a + .01:.2f}%,{end}%{{opacity:1}}{end + 4}%,100%{{opacity:0}}}}"
    body.append(f'<g style="animation:pz {cyc}s infinite;opacity:0">{text(lx, y, "❯", fs, GOLD, weight=700)}'
                f'<rect class="blink" x="{lx + tw("❯ ", fs):.1f}" y="{y - 14}" width="9" height="18" fill="{GOLD}"/></g>')

    # orbit
    ox, oy = 958, 282
    body.append(corners(740, 76, 424, 392, n=18, op=".45"))
    body.append(text(760, 104, "STACK.ORBIT", 11, GOLD, extra='opacity=".5" letter-spacing="3"'))
    body.append(text(1144, 104, "7 MODULES", 11, GOLD, anchor="end", extra='opacity=".35" letter-spacing="2"'))
    defs += f"""<radialGradient id="core" cx="{ox}" cy="{oy}" r="110" gradientUnits="userSpaceOnUse">
<stop offset="0" stop-color="{GOLD}" stop-opacity=".35"/><stop offset="1" stop-color="{GOLD}" stop-opacity="0"/></radialGradient>"""
    body.append(f'<circle cx="{ox}" cy="{oy}" r="110" fill="url(#core)"/>')

    def ell(rx, ry, rot):
        pts = []
        for k in range(97):
            a = 2 * math.pi * k / 96
            x, y = rx * math.cos(a), ry * math.sin(a)
            c, s_ = math.cos(math.radians(rot)), math.sin(math.radians(rot))
            pts.append((ox + x * c - y * s_, oy + x * s_ + y * c))
        return "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + "Z"

    orbits = [
        (ell(182, 62, -16), 26, ["Swift", "Rust", "TypeScript", "Python"]),
        (ell(128, 128 * .78, 24), 19, ["Unity", "React", "C#"]),
    ]
    for oi, (d, dur, chips) in enumerate(orbits):
        body.append(f'<path id="orb{oi}" d="{d}" fill="none" stroke="{GOLD}" stroke-opacity=".22" stroke-dasharray="3 5"/>')
        body.append(f'<path d="{d}" fill="none" stroke="{GOLD_HI}" stroke-width="2" pathLength="100" '
                    f'stroke-dasharray="8 92" stroke-linecap="round" opacity=".8">'
                    f'<animate attributeName="stroke-dashoffset" from="100" to="0" dur="{dur * .6:.1f}s" repeatCount="indefinite"/></path>')
    # core hexagon
    hexp = " ".join(f"{ox + 36 * math.cos(math.radians(60 * k + 30)):.1f},{oy + 36 * math.sin(math.radians(60 * k + 30)):.1f}" for k in range(6))
    hexi = " ".join(f"{ox + 24 * math.cos(math.radians(60 * k + 30)):.1f},{oy + 24 * math.sin(math.radians(60 * k + 30)):.1f}" for k in range(6))
    style += f".hx{{transform-origin:{ox}px {oy}px;animation:spin 14s linear infinite}}@keyframes spin{{to{{transform:rotate(360deg)}}}}"
    body.append(f'<polygon points="{hexp}" fill="{INK}" stroke="url(#gold)" stroke-width="2"/>')
    body.append(f'<polygon class="hx" points="{hexi}" fill="none" stroke="{GOLD}" stroke-opacity=".6" stroke-dasharray="4 4"/>')
    body.append(f'<circle cx="{ox}" cy="{oy}" r="6" fill="{GOLD_HI}" style="animation:pulse 2s ease-in-out infinite"/>')
    body.append(f'<circle cx="{ox}" cy="{oy}" r="10" fill="{GOLD}" filter="url(#soft)" style="animation:pulse 2s ease-in-out infinite"/>')
    body.append(text(ox, oy + 60, "MZ9.CORE", 10, GOLD, anchor="middle", extra='opacity=".55" letter-spacing="3"'))
    for oi, (d, dur, chips) in enumerate(orbits):
        for k, name in enumerate(chips):
            cw = tw(name, 12) + 22
            begin = -dur * k / len(chips)
            body.append(
                f'<g><animateMotion dur="{dur}s" begin="{begin:.2f}s" repeatCount="indefinite"><mpath href="#orb{oi}"/></animateMotion>'
                f'<rect x="{-cw / 2:.1f}" y="-13" width="{cw:.1f}" height="26" rx="4" fill="{BG}" stroke="{GOLD}" stroke-opacity=".75"/>'
                f'<rect x="{-cw / 2:.1f}" y="-13" width="3" height="26" fill="{GOLD}"/>'
                + text(2, 4.5, name, 12, GOLD_HI, anchor="middle", fit=True) + "</g>")
    body.append(text(760, 448, "SPEED ×1.00", 10, GOLD, extra='opacity=".3" letter-spacing="2"'))
    body.append(text(1144, 448, "ORBIT STABLE", 10, CYAN, anchor="end", extra='opacity=".6" letter-spacing="2"'))
    body.append(overlay(W, H))
    return svg(W, H, "\n".join(body), style, defs)


# --------------------------------------------------------------------- projects

PROJECTS = [
    ("NOTER", "实时笔记", "macOS · iPadOS · iOS", False,
     ["住在 Mac 菜单栏的实时笔记：本机 Qwen3-ASR 转写，", "大模型边听边整理。录音永远不离开你的设备。"],
     ["Swift", "SwiftUI", "On-device ASR", "LLM"]),
    ("YUEPU", "乐谱", "iPadOS · iOS · macOS", False,
     ["给职业演奏者的乐谱阅读与记谱工具。翻页 < 16ms，", "标注永不丢失，断网也能撑完一整场音乐会。"],
     ["Swift", "Apple Pencil", "CloudKit", "PDF"]),
    ("PEILIAN", "音陪", "iPadOS · Web · 小程序", False,
     ["按「同时听到几个音」逐级递进的视唱练耳。", "一套课程三端实现：iPad 原生、网页、微信小程序。"],
     ["SwiftUI", "SwiftData", "React", "CloudBase"]),
    ("SEIZE THE EDGE", "夺锋", "Unity · Action Roguelite", False,
     ["2D 横版动作肉鸽。平 A、暴击、振刀三者相克，", "六关十八区，十项肉鸽技能自由装配 Q / E / R。"],
     ["Unity", "C#", "Roguelite", "Game Design"]),
    ("SALVAGE", "这堆归我了", "Unity 6 · First-person", False,
     ["第一人称垃圾回收游戏。扮演土豆工人搬空垃圾山，", "赚钱买工具，一步步改变搬运的方式。"],
     ["Unity 6", "C#", "Physics", "Sandbox"]),
    ("MODER", "游戏修改器", "macOS · Windows", False,
     ["面向单机游戏的 AI 修改器。", "Rust 打造，原生支持 macOS 与 Windows。"],
     ["Rust", "AI", "Cross-platform"]),
    ("LAWYER", "法律助手", "Web · AI Agent", False,
     ["面向个人咨询、企业法务和律师的 AI 法律助手。", "DeepSeek + PostgreSQL 法律库 + 联网 MCP。"],
     ["Python", "React", "PostgreSQL", "MCP"]),
    ("ULTIMATE-BOT", "Screeps AI", "Screeps · Autonomous", False,
     ["全自动 Screeps 机器人。「想」与「做」分离，", "模块之间只传数据——想得慢，做得快。"],
     ["TypeScript", "Screeps", "Architecture"]),
]


def projects():
    W = 1200
    cw, ch, gap, top, side = 552, 212, 24, 80, 36
    rows = math.ceil(len(PROJECTS) / 2)
    H = top + rows * ch + (rows - 1) * gap + 36
    style = SCAN_CSS + "@keyframes flow{from{stroke-dashoffset:1000}to{stroke-dashoffset:0}}"
    defs = SWEEP_DEF
    body = [section_label(side, 46, "02", "PROJECTS", "项目舱", W - 2 * side)]
    for i, (en, zh, plat, public, desc, tags) in enumerate(PROJECTS):
        x = side + (i % 2) * (cw + gap)
        y = top + (i // 2) * (ch + gap)
        k = 18
        poly = f"{x + k},{y} {x + cw},{y} {x + cw},{y + ch - k} {x + cw - k},{y + ch} {x},{y + ch} {x},{y + k}"
        g = [f'<polygon points="{poly}" fill="{INK}" stroke="{GOLD}" stroke-opacity=".22"/>',
             f'<polygon points="{poly}" fill="none" stroke="{GOLD_HI}" stroke-width="1.6" pathLength="1000" '
             f'stroke-dasharray="70 930" style="animation:flow 7s linear infinite;animation-delay:-{i * .9:.1f}s"/>',
             f'<path d="M{x},{y + k}L{x + k},{y}" stroke="{GOLD}" stroke-width="3"/>',
             f'<path d="M{x + cw - k},{y + ch}L{x + cw},{y + ch - k}" stroke="{GOLD}" stroke-width="3"/>',
             text(x + cw - 20, y + ch - 14, f"{i + 1:02d}", 110, GOLD, anchor="end", weight=700,
                  extra='opacity=".045"')]
        dot = CYAN if public else GOLD
        g.append(f'<circle cx="{x + 30}" cy="{y + 30}" r="3.5" fill="{dot}" '
                 f'style="animation:pulse 2s ease-in-out infinite;animation-delay:-{i * .3:.1f}s"/>')
        g.append(text(x + 42, y + 34, f"PRJ-{i + 1:02d} · {'PUBLIC' if public else 'PRIVATE'}", 11, dot,
                      extra='opacity=".75" letter-spacing="2"'))
        g.append(text(x + cw - 24, y + 34, plat, 11, "#8C8C8C", anchor="end", extra='letter-spacing="1"'))
        ts = 26
        tl = len(en) * .62 * ts
        g.append(text(x + 28, y + 78, en, ts, TITLE, weight=700, fit=True, ls=tl))
        g.append(text(x + 28 + tl + 14, y + 77, zh, 17, "#8C8C8C"))
        for j, ln in enumerate(desc):
            g.append(text(x + 28, y + 112 + j * 24, ln, 14.5, "#B9B9B9"))
        cx_ = x + 28
        for t_ in tags:
            w = tw(t_, 11) + 18
            g.append(f'<rect x="{cx_:.1f}" y="{y + ch - 46}" width="{w:.1f}" height="22" rx="3" fill="{GOLD}" '
                     f'fill-opacity=".07" stroke="{GOLD}" stroke-opacity=".35"/>')
            g.append(text(cx_ + w / 2, y + ch - 31, t_, 11, GOLD, anchor="middle", fit=True))
            cx_ += w + 8
        body.append("<g>" + "".join(g) + "</g>")
    body.append(overlay(W, H))
    return svg(W, H, "\n".join(body), style, defs)


# --------------------------------------------------------------------- footer

def footer():
    W, H = 1200, 240
    style = SCAN_CSS + """
@keyframes rise{0%{transform:translateY(0);opacity:0}15%{opacity:.9}100%{transform:translateY(-170px);opacity:0}}
.pt{animation:rise 6s linear infinite}
@keyframes wipe{from{stroke-dashoffset:1}to{stroke-dashoffset:0}}
"""
    defs = SWEEP_DEF + f"""<radialGradient id="fsun" cx="600" cy="240" r="420" gradientUnits="userSpaceOnUse">
<stop offset="0" stop-color="{GOLD}" stop-opacity=".25"/><stop offset="1" stop-color="{GOLD}" stop-opacity="0"/></radialGradient>"""
    body = [f'<rect width="{W}" height="{H}" fill="url(#fsun)"/>']
    for _ in range(60):
        x = rnd.gauss(600, 260)
        body.append(f'<circle class="pt" cx="{x:.0f}" cy="{rnd.uniform(200, 250):.0f}" r="{rnd.choice([.7, 1, 1.4, 1.8])}" '
                    f'fill="{GOLD_HI}" style="animation-delay:-{rnd.uniform(0, 6):.2f}s;animation-duration:{rnd.uniform(4, 8):.1f}s"/>')
    body.append(f'<line x1="120" y1="58" x2="1080" y2="58" stroke="url(#goldH)" stroke-opacity=".6"/>')
    body.append(f'<rect x="596" y="54" width="8" height="8" fill="{GOLD}" transform="rotate(45 600 58)"/>')
    body.append(text(600, 118, "THINK SLOW · SHIP FAST", 30, TITLE, anchor="middle", weight=700, fit=True,
                     ls=22 * 30 * .62))
    body.append(text(600, 152, "想 得 慢 ，做 得 快", 15, "#9A9A9A", anchor="middle", extra='letter-spacing="4"'))
    body.append(text(600, 206, "MICHAELZHAO9  ·  2026  ·  END OF TRANSMISSION", 11, GOLD, anchor="middle",
                     extra='opacity=".45" letter-spacing="3"'))
    body.append(f'<rect class="blink" x="{600 + tw("MICHAELZHAO9  ·  2026  ·  END OF TRANSMISSION", 11) / 2 + 22:.0f}" y="197" '
                f'width="7" height="12" fill="{GOLD}" opacity=".6"/>')
    body.append(corners(0, 0, W, H, n=22, inset=20, op=".4"))
    body.append(overlay(W, H))
    return svg(W, H, "\n".join(body), style, defs)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    for name, fn in [("hero", hero), ("about", about), ("projects", projects), ("footer", footer)]:
        (OUT / f"{name}.svg").write_text(fn(), encoding="utf-8")
        print("wrote", name)
