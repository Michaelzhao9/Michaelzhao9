#!/usr/bin/env python3
"""Render the telemetry panel (dashboard.svg) from the GitHub REST API.

    PROFILE_PAT=<token> python3 scripts/stats.py out/dashboard.svg

Needs a token that can read the owner's private repos (classic PAT with `repo`).
Commits are counted per repo, so they show up whatever email they were authored with.
Without PROFILE_PAT it exits 0 and leaves the existing file alone, so the
public-only GITHUB_TOKEN never overwrites richer numbers with smaller ones.
Only aggregate numbers are rendered; no private repo name ever appears.
"""
import json
import math
import os
import sys
import time
import urllib.request
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build import (BG, CYAN, GOLD, GOLD_HI, TITLE, INK, SCAN_CSS, SWEEP_DEF, corners, overlay,  # noqa: E402
                   section_label, svg, text, tw)

LOGIN = os.environ.get("PROFILE_LOGIN", "Michaelzhao9")
# Repos that are mostly third-party code; they would skew the language mix.
SKIP = {"over56"}
# Markup, not programming languages (docs, prototypes, exported pages).
HIDE_LANGS = {"HTML", "CSS"}


def api(path, token):
    """GET a REST endpoint. GitHub answers 202 while it computes repo stats, so retry."""
    for _ in range(8):
        req = urllib.request.Request(f"https://api.github.com{path}", headers={
            "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "User-Agent": LOGIN})
        with urllib.request.urlopen(req, timeout=30) as r:
            if r.status != 202:
                return json.load(r)
        time.sleep(4)
    return None


def fetch(token):
    repos = [r for r in api("/user/repos?affiliation=owner&per_page=100", token)
             if not r["fork"] and r["name"] not in SKIP]
    langs, daily = {}, {}
    for r in repos:
        full = r["full_name"]
        # each repo counts once: bundled build output (tens of MB of JS) must not drown real code
        lb = {k: v for k, v in (api(f"/repos/{full}/languages", token) or {}).items() if k not in HIDE_LANGS}
        for k, v in lb.items():
            langs[k] = langs.get(k, 0) + v / sum(lb.values())
        for w in api(f"/repos/{full}/stats/commit_activity", token) or []:
            start = date.fromtimestamp(w["week"])
            for i, n in enumerate(w["days"]):
                d = start + timedelta(days=i)
                daily[d] = daily.get(d, 0) + n
    return {"repos": len(repos), "langs": langs, "daily": daily}


def summarize(raw, today):
    daily = raw["daily"]
    first = today - timedelta(days=363)
    days = [(first + timedelta(days=i)) for i in range(364)]
    weeks = [sum(daily.get(d, 0) for d in days[i:i + 7]) for i in range(0, 364, 7)]
    # streak: consecutive active days ending today (or yesterday, if today is still empty)
    day = today if daily.get(today) else today - timedelta(days=1)
    streak = 0
    while daily.get(day):
        streak += 1
        day -= timedelta(days=1)
    langs = raw["langs"]
    total = sum(langs.values()) or 1
    top = sorted(langs.items(), key=lambda kv: -kv[1])[:5]
    rest = total - sum(v for _, v in top)
    shares = [(k, v / total) for k, v in top] + ([("Other", rest / total)] if rest > 0 else [])
    return {
        "commits": sum(weeks),
        "active": sum(1 for d in days if daily.get(d)),
        "repos": raw["repos"],
        "streak": streak,
        "best_week": max(weeks),
        "weeks": weeks,
        "langs": shares,
    }


def selftest():
    t = date(2026, 10, 13)
    raw = {"repos": 2, "langs": {"Swift": 3, "Rust": 1},
           "daily": {t: 2, t - timedelta(days=1): 1, t - timedelta(days=3): 5, t - timedelta(days=400): 9}}
    s = summarize(raw, t)
    assert s["streak"] == 2 and s["commits"] == 8 and s["active"] == 3, s
    assert summarize({**raw, "daily": {t - timedelta(days=1): 1}}, t)["streak"] == 1
    assert s["langs"] == [("Swift", .75), ("Rust", .25)]
    print("selftest ok")


RAMP = [GOLD_HI, GOLD, "#C79A3A", "#9A7428", "#6B5020", "#3A3428"]


def render(s, stamp):
    W, H = 1200, 430
    style = SCAN_CSS + """
@keyframes up{from{transform:scaleY(0)}to{transform:scaleY(1)}}
.bar{transform-box:fill-box;transform-origin:50% 100%;animation:up .9s cubic-bezier(.2,.8,.2,1) both}
@keyframes rise{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:translateY(0)}}
.kpi{animation:rise .8s cubic-bezier(.2,.8,.2,1) both}
@keyframes arc{from{stroke-dashoffset:var(--l)}to{stroke-dashoffset:0}}
.arc{animation:arc 1.4s cubic-bezier(.6,0,.2,1) both}
@keyframes scanx{from{transform:translateX(0)}to{transform:translateX(392px)}}
.scanx{animation:scanx 4s linear infinite}
"""
    defs = SWEEP_DEF + f"""<linearGradient id="barG" x1="0" y1="0" x2="0" y2="1">
<stop offset="0" stop-color="{GOLD_HI}"/><stop offset="1" stop-color="{GOLD}" stop-opacity=".25"/></linearGradient>
<linearGradient id="scanG" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{CYAN}" stop-opacity="0"/>
<stop offset="1" stop-color="{CYAN}" stop-opacity=".35"/></linearGradient>"""
    body = [section_label(36, 46, "03", "TELEMETRY", "数据面板", W - 72)]

    # KPI tiles
    kpis = [("COMMITS", f"{s['commits']:,}", "PAST 52 WEEKS"),
            ("ACTIVE DAYS", f"{s['active']}", "PAST 52 WEEKS"),
            ("REPOSITORIES", f"{s['repos']}", "OWNED · PUB+PRIV"),
            ("STREAK", f"{s['streak']}", "DAYS · CURRENT")]
    for i, (label, val, sub) in enumerate(kpis):
        x, y = 36 + (i % 2) * 204, 76 + (i // 2) * 160
        body.append(f'<g class="kpi" style="animation-delay:{.1 + i * .12:.2f}s">'
                    f'<rect x="{x}" y="{y}" width="192" height="148" rx="10" fill="{INK}" stroke="{GOLD}" stroke-opacity=".22"/>'
                    + corners(x + 8, y + 8, 176, 132, n=10, op=".5")
                    + text(x + 22, y + 38, label, 11, GOLD, extra='opacity=".6" letter-spacing="2"')
                    + text(x + 22, y + 96, val, 44, TITLE, weight=700, fit=True, ls=len(val) * .62 * 44)
                    + text(x + 22, y + 124, sub, 10, "#7A7A7A", extra='letter-spacing="2"')
                    + "</g>")

    # weekly activity
    ax, ay, aw, ah = 464, 76, 420, 308
    body.append(f'<rect x="{ax}" y="{ay}" width="{aw}" height="{ah}" rx="10" fill="{INK}" stroke="{GOLD}" stroke-opacity=".22"/>')
    body.append(text(ax + 22, ay + 34, "52-WEEK ACTIVITY", 11, GOLD, extra='opacity=".6" letter-spacing="2"'))
    body.append(text(ax + aw - 22, ay + 34, f"PEAK {s['best_week']}/WK", 11, CYAN, anchor="end",
                     extra='opacity=".75" letter-spacing="2"'))
    weeks = s["weeks"] or [0]
    peak = max(weeks) or 1
    gx, gy, gw, gh = ax + 14, ay + 60, aw - 28, ah - 96
    for k in range(5):
        y = gy + gh * k / 4
        body.append(f'<line x1="{gx}" y1="{y:.1f}" x2="{gx + gw}" y2="{y:.1f}" stroke="{GOLD}" stroke-opacity=".08"/>')
    bw = gw / len(weeks)
    for k, v in enumerate(weeks):
        h = max(2, gh * math.sqrt(v / peak))  # sqrt: quiet weeks stay visible next to crunch weeks
        body.append(f'<rect class="bar" x="{gx + k * bw + 1:.1f}" y="{gy + gh - h:.1f}" width="{bw - 2:.1f}" height="{h:.1f}" '
                    f'fill="url(#barG)" style="animation-delay:{.3 + k * .018:.3f}s"/>')
    body.append(f'<line x1="{gx}" y1="{gy + gh}" x2="{gx + gw}" y2="{gy + gh}" stroke="{GOLD}" stroke-opacity=".5"/>')
    body.append(f'<rect class="scanx" x="{gx - 40}" y="{gy}" width="40" height="{gh}" fill="url(#scanG)"/>')
    body.append(text(gx, gy + gh + 22, "52W AGO", 10, "#6A6A6A", extra='letter-spacing="2"'))
    body.append(text(gx + gw, gy + gh + 22, "NOW", 10, "#6A6A6A", anchor="end", extra='letter-spacing="2"'))

    # language ring
    lx, ly, lw = 908, 76, 256
    body.append(f'<rect x="{lx}" y="{ly}" width="{lw}" height="{ah}" rx="10" fill="{INK}" stroke="{GOLD}" stroke-opacity=".22"/>')
    body.append(text(lx + 22, ly + 34, "LANGUAGES", 11, GOLD, extra='opacity=".6" letter-spacing="2"'))
    cx, cy, r = lx + 74, ly + 128, 46
    circ = 2 * math.pi * r
    acc = 0.0
    body.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#1C1C20" stroke-width="14"/>')
    for k, (name, share) in enumerate(s["langs"]):
        seg = max(share * circ - 2, .5)
        body.append(f'<circle class="arc" cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{RAMP[k]}" stroke-width="14" '
                    f'stroke-dasharray="{seg:.2f} {circ:.2f}" transform="rotate({-90 + acc * 360:.2f} {cx} {cy})" '
                    f'style="--l:{seg:.2f};animation-delay:{.4 + k * .15:.2f}s"/>')
        acc += share
    top = s["langs"][0] if s["langs"] else ("—", 0)
    body.append(text(cx, cy + 6, f"{top[1] * 100:.0f}%", 18, GOLD_HI, anchor="middle", weight=700))
    for k, (name, share) in enumerate(s["langs"]):
        y = ly + 206 + k * 16 if k < 3 else ly + 206 + (k - 3) * 16
        x = lx + 22 if k < 3 else lx + 136
        body.append(f'<rect x="{x}" y="{y - 8}" width="8" height="8" fill="{RAMP[k]}"/>')
        body.append(text(x + 14, y, name[:11], 11, "#B9B9B9"))
        body.append(text(x + 106, y, f"{share * 100:.0f}%", 11, GOLD, anchor="end"))
    body.append(text(lx + 150, ly + 112, "PRIMARY", 10, "#6A6A6A", extra='letter-spacing="2"'))
    body.append(text(lx + 150, ly + 132, top[0][:10], 15, GOLD_HI, weight=700))
    body.append(text(lx + 150, ly + 150, "BY PROJECT", 10, "#6A6A6A", extra='letter-spacing="1"'))

    body.append(text(W - 36, H - 16, f"SYNCED {stamp} UTC · AUTO-UPDATED DAILY", 10, GOLD, anchor="end",
                     extra='opacity=".35" letter-spacing="2"'))
    body.append(overlay(W, H))
    return svg(W, H, "\n".join(body), style, defs)


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "dashboard.svg")
    token = os.environ.get("PROFILE_PAT")
    if sys.argv[1:] == ["--selftest"]:
        selftest()
        sys.exit(0)
    if not token:
        print("PROFILE_PAT not set; keeping existing dashboard.svg")
        sys.exit(0)
    s = summarize(fetch(token), date.today())
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(s, date.today().isoformat()), encoding="utf-8")
    print("wrote", out, {k: v for k, v in s.items() if k != "weeks"})
