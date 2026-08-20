"""Match-importance context for SKM v5: opponent strength + competition stage.

Two feasible upgrades to "how much did the setting raise the stakes of this
action", beyond in-match scoreline/minute:

1. **Opponent strength.** `opponent_quality` in the event feed is a stub
   (constant 1.0). Here it is derived *from the data*: each team's rating is
   its mean goal difference per match **within its own competition** (teams
   from different competitions never meet, so cross-competition ratings are
   not comparable). An action against a strong opponent is weighted up.

2. **Competition stage.** Tournament knockout rounds and finals carry more
   weight than group games (Group → R16 → QF → SF → Final). League matches
   are a single "Regular Season" stage, so this mostly affects the World Cup
   and Euro slices — stated honestly, not applied where it doesn't exist.

Not auto-modelled here (the open feed can't derive them cleanly) but wired as
an optional **human-set / human-reviewed input** — the honest home for these
in the end-goal pipeline, exactly like the expert moment-preference labels:
- player-vs-player matchup quality (e.g. beating a specific elite fullback) —
  360 frames have no player identities, only positions;
- real-world stakes (title / qualification / relegation impact) — needs
  standings and competition structure.

`load_human_context()` reads a reviewer-filled CSV of per-game multipliers for
these; absent or unfilled → neutral 1.0 (never fabricated). This lets a human
supply what automation can't, without the metric inventing it.
"""

from __future__ import annotations

import logging
from typing import Dict, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Knockout stages weighted above group/regular-season play.
STAGE_WEIGHT = {
    "Regular Season": 1.0,
    "Group Stage": 1.0,
    "Round of 16": 1.10,
    "Quarter-finals": 1.20,
    "Semi-finals": 1.30,
    "3rd Place Final": 1.20,
    "Final": 1.40,
}


def team_strength(games: pd.DataFrame) -> pd.DataFrame:
    """Per-(competition, team) strength = z-scored mean goal difference within
    the competition. Returns columns: competition, team_id, strength."""
    g = games.reset_index() if games.index.name == "game_id" else games.copy()
    rows = []
    for _, r in g.iterrows():
        comp = r.get("competition", "?")
        hs, as_ = int(r.get("home_score", 0)), int(r.get("away_score", 0))
        rows.append((comp, int(r["home_team_id"]), hs - as_))
        rows.append((comp, int(r["away_team_id"]), as_ - hs))
    gd = pd.DataFrame(rows, columns=["competition", "team_id", "gd"])
    agg = gd.groupby(["competition", "team_id"])["gd"].mean().reset_index(name="mean_gd")
    # z-score within competition
    agg["strength"] = agg.groupby("competition")["mean_gd"].transform(
        lambda s: (s - s.mean()) / (s.std(ddof=0) or 1.0)
    )
    return agg[["competition", "team_id", "strength"]]


def fetch_stage_map(game_ids, comp_season_pairs) -> Dict[int, str]:
    """game_id → competition_stage from StatsBomb match metadata."""
    from skm.data.download import resolve_competition_season
    from statsbombpy import sb

    stage: Dict[int, str] = {}
    for comp, season in comp_season_pairs:
        try:
            cid, sid, _ = resolve_competition_season(comp, season)
            m = sb.matches(competition_id=cid, season_id=sid)
            if "competition_stage" in m.columns:
                for _, r in m.iterrows():
                    stage[int(r["match_id"])] = str(r["competition_stage"])
        except Exception as exc:
            logger.warning("stage fetch failed for %s %s: %s", comp, season, exc)
    return {gid: stage.get(int(gid), "Regular Season") for gid in game_ids}


def load_human_context(path) -> Dict[int, float]:
    """Optional reviewer-set per-game stakes/matchup multiplier.

    CSV schema: game_id, importance_mult, note. Missing file or rows → {} so
    the caller defaults to neutral 1.0. This is the human-in-the-loop slot for
    signals automation can't derive (real-world stakes, matchup quality) — the
    end-goal pipeline's human-reviewed input, never fabricated.
    """
    from pathlib import Path

    p = Path(path)
    if not p.exists() or p.stat().st_size == 0:
        return {}
    df = pd.read_csv(p)
    if "game_id" not in df.columns or "importance_mult" not in df.columns:
        return {}
    return {
        int(r["game_id"]): float(r["importance_mult"])
        for _, r in df.dropna(subset=["game_id", "importance_mult"]).iterrows()
    }


def match_importance(
    actions: pd.DataFrame,
    games: pd.DataFrame,
    stage_map: Optional[Dict[int, str]] = None,
    opp_scale: float = 0.15,
    human_context: Optional[Dict[int, float]] = None,
) -> pd.Series:
    """Per-action match-importance multiplier = opponent-strength × stage ×
    optional human-reviewed per-game multiplier.

    opponent strength: the acting team's OPPONENT rating in that game; facing
    a stronger side multiplies up (1 + opp_scale·strength), clipped. stage:
    STAGE_WEIGHT lookup (1.0 when unknown / league). human_context: reviewer
    override (stakes/matchup), defaulting to 1.0 — never fabricated.
    """
    human_context = human_context or {}
    g = games.reset_index() if games.index.name == "game_id" else games.copy()
    opp = {}  # game_id -> {team_id: opponent_strength}
    strength = team_strength(g)
    skey = {(row.competition, int(row.team_id)): row.strength for row in strength.itertuples()}
    for _, r in g.iterrows():
        comp = r.get("competition", "?")
        h, a = int(r["home_team_id"]), int(r["away_team_id"])
        sh, sa = skey.get((comp, h), 0.0), skey.get((comp, a), 0.0)
        opp[int(r["game_id"])] = {h: sa, a: sh}  # each team's OPPONENT strength

    stage_map = stage_map or {}
    gid = actions["game_id"].astype(int).to_numpy()
    tid = actions["team_id"].astype(int).to_numpy()
    mult = np.ones(len(actions))
    for i in range(len(actions)):
        opp_s = opp.get(gid[i], {}).get(tid[i], 0.0)
        stage_w = STAGE_WEIGHT.get(stage_map.get(gid[i], "Regular Season"), 1.0)
        human_w = human_context.get(int(gid[i]), 1.0)
        mult[i] = np.clip(1.0 + opp_scale * opp_s, 0.8, 1.3) * stage_w * human_w
    return pd.Series(mult, index=actions.index)
