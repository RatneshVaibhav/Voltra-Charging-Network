"""Draw the README's headline chart from a published run (no plotting library needed).

    python scripts/make_readme_charts.py                      # reads run_date=2025-02-01
    python scripts/make_readme_charts.py --run-date 2025-02-01

Writes docs/img/reliability_gap_light.svg and docs/img/reliability_gap_dark.svg — the same four measures of the same
fleet, with the drivers' measure (the KPI) emphasised and the other three as grey context. Every number is read from
the run's metrics.json, so the chart can never drift from the pipeline.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "img"

# ink, grid and marks per GitHub theme (accent + de-emphasis grey validated for both surfaces)
THEMES = {
    "light": {"surface": "#fcfcfb", "ink": "#0b0b0b", "ink2": "#52514e", "grid": "#e1e0d9", "axis": "#c3c2b7",
              "accent": "#2a78d6", "context": "#898781"},
    "dark": {"surface": "#1a1a19", "ink": "#ffffff", "ink2": "#c3c2b7", "grid": "#2c2c2a", "axis": "#383835",
             "accent": "#3987e5", "context": "#898781"},
}
W, LEFT, RIGHT, TOP, ROW, BAR, PAD = 760, 266, 70, 80, 46, 20, 16


def _bar(x0: float, x1: float, y: float, h: float, r: float = 4) -> str:
    """Bar anchored square at the baseline with a 4px rounded data end."""
    return (f"M{x0:.1f},{y:.1f} H{x1 - r:.1f} Q{x1:.1f},{y:.1f} {x1:.1f},{y + r:.1f} V{y + h - r:.1f} "
            f"Q{x1:.1f},{y + h:.1f} {x1 - r:.1f},{y + h:.1f} H{x0:.1f} Z")


def svg(rows: list[tuple[str, str, float, bool]], theme: dict) -> str:
    plot_w = W - LEFT - RIGHT
    height = TOP + ROW * len(rows) + 40
    x = lambda v: LEFT + plot_w * v / 100                                     # noqa: E731 — axis starts at zero
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{height}" viewBox="0 0 {W} {height}" '
           f'font-family="system-ui, -apple-system, Segoe UI, sans-serif" role="img" '
           f'aria-label="Same fleet, four ways of measuring reliability">',
           # own background card: stays readable if the viewer's page theme and the chosen image disagree
           f'<rect width="{W}" height="{height}" rx="8" fill="{theme["surface"]}"/>',
           f'<text x="{PAD}" y="{PAD + 22}" font-size="17" font-weight="600" fill="{theme["ink"]}">'
           f'Same fleet, four ways of measuring reliability</text>',
           f'<text x="{PAD}" y="{PAD + 44}" font-size="13" fill="{theme["ink2"]}">The dashboard\'s view is '
           f'near-perfect; the drivers\' view is not. Percent, axis from 0.</text>']
    bottom = TOP + ROW * len(rows)
    for tick in (0, 25, 50, 75, 100):
        colour = theme["axis"] if tick == 0 else theme["grid"]
        out.append(f'<line x1="{x(tick):.1f}" y1="{TOP - 8}" x2="{x(tick):.1f}" y2="{bottom}" stroke="{colour}" '
                   f'stroke-width="1"/>')
        out.append(f'<text x="{x(tick):.1f}" y="{bottom + 18}" font-size="12" fill="{theme["ink2"]}" '
                   f'text-anchor="middle">{tick}</text>')
    for i, (label, basis, value, emphasis) in enumerate(rows):
        y = TOP + i * ROW + (ROW - BAR) / 2 - 4
        weight = "600" if emphasis else "400"
        out.append(f'<text x="{LEFT - 12}" y="{y + 9}" font-size="13" font-weight="{weight}" fill="{theme["ink"]}" '
                   f'text-anchor="end">{label}</text>')
        out.append(f'<text x="{LEFT - 12}" y="{y + 25}" font-size="11.5" fill="{theme["ink2"]}" '
                   f'text-anchor="end">{basis}</text>')
        fill = theme["accent"] if emphasis else theme["context"]
        out.append(f'<path d="{_bar(x(0), x(value), y, BAR)}" fill="{fill}"/>')
        out.append(f'<text x="{x(value) + 8:.1f}" y="{y + 15}" font-size="13" font-weight="{weight}" '
                   f'fill="{theme["ink"]}">{value:.2f}%</text>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--run-date", default="2025-02-01")
    run = ROOT / "data" / "processed" / f"run_date={p.parse_args().run_date}" / "metrics.json"
    m = json.loads(run.read_text())
    rel = m["illustrative_simulated_input"]["reliability_definitions"]
    rows = [
        ("Operator uptime", "simulated status feed", rel["operator_noc_uptime_pct"], False),
        ("Federal-style uptime", "simulated status feed", rel["federal_style_uptime_pct"], False),
        ("Charger availability", "inferred from real sessions", rel["inferred_availability_real_pct"], False),
        ("Drivers' first-try success", "the KPI · real sessions", m["kpi"]["baseline_ftcs_pct"], True),
    ]
    OUT.mkdir(parents=True, exist_ok=True)
    for name, theme in THEMES.items():
        (OUT / f"reliability_gap_{name}.svg").write_text(svg(rows, theme))
    print("wrote", ", ".join(f"docs/img/reliability_gap_{n}.svg" for n in THEMES), "from", run.relative_to(ROOT))


if __name__ == "__main__":
    main()
