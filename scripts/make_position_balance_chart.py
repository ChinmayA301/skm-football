"""Render the position-balance chart: who does each metric's top 40 reward?

This is the headline visual — it is the clearest statement of what competence
does that output metrics do not. Regenerate it after any pipeline rebuild:

    python scripts/make_position_balance_chart.py

Writes docs/assets/metric_position_balance.png.

Note on goals+assists: raw G+A totals cannot rank this sample. Only 30 of the
233 qualified players have more than 2 G+A, and 24 are tied at exactly 2 — so a
"top 40 by G+A" admits 10 of those 24 arbitrarily, and the position mix you get
depends on the tie-break rather than on the data. We therefore rank G+A **per
90**, which is continuous and ties-free, and is also the like-for-like
comparison against VAEP per 90.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skm.config import PROJECT_ROOT  # noqa: E402

APP_DATA = PROJECT_ROOT / "data" / "app"
OUT = PROJECT_ROOT / "docs" / "assets" / "metric_position_balance.png"

# Back-to-front pitch order
POSITIONS = ["GK", "CB", "FB", "DM", "CM", "AM", "W", "ST"]
TOP_N = 40

# dataviz reference palette, categorical slots 1-3 (validated all-pairs, light).
# Contrast of the aqua slot is under 3:1, so every bar carries a direct label.
SERIES = [
    ("ga_per90", "Goals+assists per 90  (traditional output)", "#2a78d6"),
    ("delta_p_per90", "VAEP ΔP per 90  (possession value)", "#eb6834"),
    ("competence", "SKM competence v4  (role-relative)", "#1baf7a"),
]

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"


def load() -> pd.DataFrame:
    comp = pd.read_parquet(APP_DATA / "player_competence.parquet")
    lb = pd.read_parquet(APP_DATA / "player_leaderboard.parquet")
    ev = pd.read_parquet(APP_DATA / "events.parquet")

    goals = ev[(ev.event_type == "Shot") & (ev.outcome == "Goal")].groupby("player_id").size()
    assists = ev[ev.pass_goal_assist.fillna(False).astype(bool)].groupby("player_id").size()
    ga = goals.add(assists, fill_value=0)

    df = comp[["player_id", "pos", "player", "competence"]].merge(
        lb[["player_id", "delta_p_per90", "minutes_est"]], on="player_id", how="left"
    )
    df["ga_per90"] = df.player_id.map(ga).fillna(0) / df.minutes_est * 90
    return df


def position_mix(df: pd.DataFrame, col: str) -> dict[str, int]:
    counts = df.nlargest(TOP_N, col).pos.value_counts()
    return {p: int(counts.get(p, 0)) for p in POSITIONS}


def main() -> int:
    df = load()
    mixes = [(label, color, position_mix(df, col)) for col, label, color in SERIES]

    fig, ax = plt.subplots(figsize=(11, 6.4), dpi=200)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)

    n = len(SERIES)
    height = 0.26
    y = range(len(POSITIONS))

    for i, (label, color, mix) in enumerate(mixes):
        offset = (i - (n - 1) / 2) * height
        ys = [p + offset for p in y]
        vals = [mix[p] for p in POSITIONS]
        ax.barh(ys, vals, height=height * 0.92, color=color, label=label, zorder=3)
        for yy, v in zip(ys, vals):
            ax.text(v + 0.18, yy, str(v), va="center", ha="left",
                    fontsize=9, color=INK_2, zorder=4)

    ax.set_yticks(list(y))
    ax.set_yticklabels(POSITIONS, fontsize=11, color=INK)
    ax.invert_yaxis()  # GK at top: reads back-to-front down the pitch
    ax.set_xlabel(f"players in the metric's top {TOP_N}", fontsize=10, color=INK_2)
    ax.set_xlim(0, max(max(m.values()) for _, _, m in mixes) + 1.6)
    ax.tick_params(axis="x", colors=MUTED, labelsize=9)
    ax.tick_params(axis="y", length=0)

    ax.xaxis.grid(True, color=GRID, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right", "bottom"):
        ax.spines[side].set_visible(False)
    ax.spines["left"].set_color("#c3c2b7")

    ax.set_title(
        "Who does each metric reward? Position mix of each metric's top 40",
        fontsize=14, color=INK, loc="left", pad=58, fontweight="bold",
    )
    ga_cb = mixes[0][2]["CB"]
    comp_cb = mixes[2][2]["CB"]
    ax.text(
        0, 1.105,
        f"Competence puts {comp_cb} centre-backs in the top 40. "
        f"Goals+assists puts {ga_cb}.",
        transform=ax.transAxes, fontsize=11, color=INK_2, ha="left",
    )

    # Legend above the plot: inside the axes it collides with the long W bars.
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.005, 1, 0.06), mode="expand",
              ncol=3, frameon=False, fontsize=9, handlelength=1.1,
              handletextpad=0.6, columnspacing=1.4, borderaxespad=0)

    fig.text(
        0.008, 0.012,
        "StatsBomb open data · 216 matches, 5 competitions · 233 players with "
        "≥400 actions · G+A ranked per 90 (raw totals tie 24 players at the "
        "top-40 cutoff)",
        fontsize=7.5, color=MUTED,
    )

    fig.tight_layout(rect=(0, 0.03, 1, 1))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, facecolor=SURFACE, bbox_inches="tight")
    print(f"wrote {OUT}")

    for label, _, mix in mixes:
        flat = " ".join(f"{p}{mix[p]:>3}" for p in POSITIONS)
        print(f"  {label.splitlines()[0]:28s} {flat}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
