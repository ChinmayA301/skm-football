"""SKM v5 layers on the v4 competence base: context-weighted decisive
actions + a pressure / press-breaking component.

The founding thesis is role competence over attacking intent (delivered by
`skm.models.competence`). But genuinely *decisive* actions — goals, assists,
saves, line-breaking passes, chance creation, tackles — still matter more
than routine ones and must be rewarded heavily. The point is to reward them
**within context**, not by outcome alone:

- A goal from very low xG (a hard finish) scores more than one from very
  high xG (a tap-in). Difficulty, not just the goal.
- A pass from deep that launches a counter can rival a high-xG goal.
- A goal/action in a comeback, in the final minutes, that swings the result
  is weighted up over the same action at 4-0 in the 20th.
- The same context logic applies to every decisive action type.

What event data supports well (built here): difficulty via xG, game-state
via running score + minute + final result, press-resistance via the
under_pressure flag and 360 defender distance.

What it only approximates (and is deferred to the future live-video "moment
frame" pipeline, see docs/ROADMAP.md): true causal "this action led to the
win", off-ball chance creation, continuous pressure geometry. Those are
scoped as the productionised organic-ingestion version, not faked here.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from skm.config import (
    ACTIONS_SCORED_PARQUET,
    DATA_PROCESSED,
    EVENTS_PARQUET,
    GAMES_PARQUET,
    PROGRESSIVE_DISTANCE_M,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PLAYER_V5_PARQUET = DATA_PROCESSED / "player_skm_v5.parquet"

# Base importance of decisive action types (relative, on the same scale).
DECISIVE_BASE = {
    "goal": 1.00,
    "assist": 0.60,
    "key_pass": 0.35,
    "line_break": 0.30,
    "shot": 0.12,
    "keeper_save": 0.45,
    "tackle": 0.22,
    "interception": 0.22,
    "clearance": 0.08,
}
SHOT_TYPES = {"shot", "shot_penalty", "shot_freekick"}
DEFENSIVE_TYPES = {"tackle", "interception", "clearance"}


def _difficulty_mult(kind: str, xg: float) -> float:
    """Harder = more credit. Goals: inverse-xG (low-xG finish worth ~2x a
    tap-in). Saves: proportional to shot xG faced. Others: neutral 1.0."""
    if kind == "goal":
        xg = 0.05 if np.isnan(xg) else float(np.clip(xg, 0.02, 0.98))
        return float(np.clip(0.5 + (1.0 - xg), 0.6, 1.5))
    if kind == "keeper_save":
        xg = 0.1 if np.isnan(xg) else float(np.clip(xg, 0.02, 0.98))
        return float(np.clip(0.6 + xg, 0.6, 1.5))
    return 1.0


def _game_state_mult(minute: float, score_diff_before: int, team_won: bool) -> float:
    """Leverage: late + tight + result-swinging actions weighted up; garbage
    time down. score_diff_before is the actor team's lead before the action."""
    m = 1.0
    # trailing or level = higher stakes; big lead = lower
    if score_diff_before <= -1:
        m *= 1.25
    elif score_diff_before == 0:
        m *= 1.10
    elif score_diff_before >= 3:
        m *= 0.7
    # late minutes amplify tight-game actions
    if minute >= 80 and score_diff_before <= 1:
        m *= 1.25
    # comeback that ends in a win (approx: acted while not ahead, team won)
    if score_diff_before <= 0 and team_won and minute >= 70:
        m *= 1.20
    return float(np.clip(m, 0.6, 2.2))


def build_decisive_actions(
    actions: pd.DataFrame,
    events: pd.DataFrame,
    games: pd.DataFrame,
    importance: Optional[pd.Series] = None,
) -> pd.DataFrame:
    """Return a per-action frame of decisive actions with context-weighted value.

    value = base[type] × difficulty(xg) × game_state(minute, score, result)
            × match_importance(opponent strength × competition stage)

    `importance` is an optional per-action multiplier aligned to `actions`
    (from `skm.models.match_context.match_importance`); defaults to 1.0.
    """
    import socceraction.spadl as spadl

    from skm.models.moments import infer_home_teams

    named = spadl.add_names(actions).copy()
    named["minute"] = (named["period_id"] - 1) * 45 + named["time_seconds"] / 60.0

    # xG + assist flag from events. The flattened events.parquet has no event
    # id, so join on (match, player, whole-minute) — approximate but adequate
    # for sparse shots/assists. (A future version keying on event id or the
    # organic pipeline removes the approximation.)
    ev = events.copy()
    ev["mm"] = ev["minute"].astype(int)
    shots_ev = ev[ev["event_type"] == "Shot"].dropna(subset=["player_id"])
    xg_key = (
        shots_ev.groupby(["match_id", "player_id", "mm"])["shot_xg"].max()
        if "shot_xg" in ev.columns
        else pd.Series(dtype=float)
    )
    assist_ev = ev[ev.get("pass_goal_assist", pd.Series(False, index=ev.index)).fillna(False).astype(bool)]
    assist_keys = set(zip(assist_ev["match_id"], assist_ev["player_id"], assist_ev["minute"].astype(int)))

    named["mm"] = named["minute"].astype(int)
    keys = list(zip(named["game_id"], named["player_id"], named["mm"]))
    named["xg"] = [xg_key.get(k, np.nan) for k in keys]
    named["is_assist"] = [k in assist_keys for k in keys]

    home = infer_home_teams(actions)
    sign = named.apply(lambda r: 1.0 if home.get(int(r["game_id"])) == int(r["team_id"]) else -1.0, axis=1)
    named["forward"] = sign * (named["end_x"] - named["start_x"]).fillna(0)

    # running score before each action (goal = successful shot)
    named["is_goal"] = named["type_name"].isin(SHOT_TYPES) & (named["result_name"] == "success")
    g = named.sort_values(["game_id", "period_id", "time_seconds"], kind="stable")
    team_goals = g.groupby(["game_id", "team_id"])["is_goal"].cumsum() - g["is_goal"].astype(int)
    tot_goals = g.groupby("game_id")["is_goal"].cumsum() - g["is_goal"].astype(int)
    named.loc[g.index, "score_diff_before"] = (team_goals - (tot_goals - team_goals)).astype(int)

    # match result per (game, team)
    winners = {}
    for gid, gm in games.reset_index().set_index("game_id").iterrows():
        hs, as_ = gm.get("home_score", 0), gm.get("away_score", 0)
        winners[int(gid)] = (int(gm.get("home_team_id", -1)) if hs > as_
                             else int(gm.get("away_team_id", -1)) if as_ > hs else None)
    named["team_won"] = named.apply(lambda r: winners.get(int(r["game_id"])) == int(r["team_id"]), axis=1)
    named["importance"] = 1.0 if importance is None else importance.reindex(named.index).fillna(1.0)

    rows = []
    for _, r in named.iterrows():
        t = r["type_name"]
        kind, base = None, 0.0
        if r["is_goal"]:
            kind, base = "goal", DECISIVE_BASE["goal"]
        elif r["is_assist"]:
            kind, base = "assist", DECISIVE_BASE["assist"]
        elif t in SHOT_TYPES:
            kind, base = "shot", DECISIVE_BASE["shot"]
        elif t == "keeper_save":
            kind, base = "keeper_save", DECISIVE_BASE["keeper_save"]
        elif t in DEFENSIVE_TYPES and r["result_name"] == "success":
            kind, base = t, DECISIVE_BASE[t]
        elif t in {"pass", "cross"} and r["result_name"] == "success" and r["forward"] >= PROGRESSIVE_DISTANCE_M:
            kind, base = "line_break", DECISIVE_BASE["line_break"]
        if kind is None:
            continue
        diff = _difficulty_mult(kind, r.get("xg", np.nan))
        gs = _game_state_mult(r["minute"], int(r.get("score_diff_before", 0) or 0), bool(r["team_won"]))
        imp = float(r.get("importance", 1.0))
        rows.append(
            {
                "player_id": r["player_id"],
                "game_id": int(r["game_id"]),
                "kind": kind,
                "xg": r.get("xg", np.nan),
                "minute": r["minute"],
                "score_diff_before": int(r.get("score_diff_before", 0) or 0),
                "difficulty_mult": diff,
                "game_state_mult": gs,
                "importance_mult": imp,
                "value": base * diff * gs * imp,
            }
        )
    return pd.DataFrame(rows)


def pressure_value(actions: pd.DataFrame) -> pd.Series:
    """Press-breaking value per action: successful on-ball retention/progression
    under pressure, scaled by pressure intensity (360 nearest defender when
    available, else the under_pressure flag)."""
    import socceraction.spadl as spadl

    named = spadl.add_names(actions)
    onball = named["type_name"].isin(["pass", "cross", "dribble", "take_on"])
    success = named["result_name"] == "success"
    up = named.get("under_pressure")
    up = up.fillna(False).astype(bool) if up is not None else pd.Series(False, index=named.index)

    near = named.get("nearest_def_m")
    if near is not None:
        # closer defender = more pressure; 1.0 at ~1m, ~0 by 8m
        intensity = np.clip((8.0 - near.fillna(8.0)) / 7.0, 0.0, 1.0)
    else:
        intensity = up.astype(float)
    val = np.where(onball & success & (up | (intensity > 0.4)), intensity, 0.0)
    return pd.Series(val, index=actions.index)


def build_v5(
    actions: pd.DataFrame,
    events: pd.DataFrame,
    games: pd.DataFrame,
    competence: pd.DataFrame,
    min_actions: int = 400,
    w_competence: float = 1.2,
    w_decisive: float = 1.0,
    w_pressure: float = 0.5,
    importance: Optional[pd.Series] = None,
) -> pd.DataFrame:
    """Blend v4 competence with per-90 decisive-action and pressure value into
    a standardized v5 rating. All three parts are z-standardized so the blend
    weights are interpretable and no single scale dominates.

    Default weights (1.2, 1.0, 0.5) were selected by grid search against the
    metric's own DESIGN criteria — decoupled from raw goals, position-balanced,
    decisive + competence both contributing — NOT fitted to ground-truth
    labels (none exist yet). The sensitivity analysis showed the conclusions
    (|ρ(v5, goals)| < 0.1, balanced positions) are robust across all reasonable
    weights; true fitting awaits expert/scout labels. Priors, disclosed."""
    # per-player n and rough minutes (action-count proxy, consistent with repo)
    counts = actions.groupby("player_id").size().rename("n_actions").reset_index()
    per_min = counts["n_actions"].sum() / max(len(actions) / 90.0, 1.0)
    counts["minutes_est"] = counts["n_actions"] / max(per_min / 90.0, 1e-6)

    dec = build_decisive_actions(actions, events, games, importance=importance)
    dec_tot = dec.groupby("player_id")["value"].sum().rename("decisive_total")

    press = actions.copy()
    press["press_val"] = pressure_value(actions).to_numpy()
    press_tot = press.groupby("player_id")["press_val"].sum().rename("pressure_total")

    board = counts.merge(dec_tot, on="player_id", how="left").merge(press_tot, on="player_id", how="left")
    board = board.merge(competence[["player_id", "competence", "pos"]], on="player_id", how="left")
    board = board[board["n_actions"] >= min_actions].copy()
    board["decisive_per90"] = board["decisive_total"].fillna(0) / board["minutes_est"] * 90
    board["pressure_per90"] = board["pressure_total"].fillna(0) / board["minutes_est"] * 90

    def _z(s):
        s = s.fillna(0.0)
        return (s - s.mean()) / (s.std(ddof=0) or 1.0)

    board["skm_v5"] = (
        w_competence * _z(board["competence"])
        + w_decisive * _z(board["decisive_per90"])
        + w_pressure * _z(board["pressure_per90"])
    ) / (w_competence + w_decisive + w_pressure)
    return board.sort_values("skm_v5", ascending=False)


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description="SKM v5 (competence + context decisive + pressure)")
    parser.add_argument("--competence-input", default=str(DATA_PROCESSED / "player_competence.parquet"))
    parser.add_argument("--output", default=str(PLAYER_V5_PARQUET))
    parser.add_argument("--match-context", action="store_true",
                        help="Fetch competition stage + compute opponent strength (network)")
    parser.add_argument("--human-context", default=None,
                        help="CSV of reviewer-set per-game importance multipliers")
    args = parser.parse_args(argv)

    actions = pd.read_parquet(ACTIONS_SCORED_PARQUET)
    events = pd.read_parquet(EVENTS_PARQUET)
    games = pd.read_parquet(GAMES_PARQUET).set_index("game_id")
    competence = pd.read_parquet(args.competence_input)

    importance = None
    if args.match_context or args.human_context:
        from skm.models.match_context import fetch_stage_map, load_human_context, match_importance

        g = games.reset_index()
        pairs = g[["competition", "season"]].drop_duplicates().apply(tuple, axis=1).tolist()
        stage_map = fetch_stage_map(g["game_id"].tolist(), pairs) if args.match_context else None
        human = load_human_context(args.human_context) if args.human_context else None
        importance = match_importance(actions, games, stage_map=stage_map, human_context=human)
        logger.info("Applied match-context importance (mean %.3f)", importance.mean())

    board = build_v5(actions, events, games, competence, importance=importance)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    board.to_parquet(args.output, index=False)
    logger.info("Wrote v5 for %s players → %s", len(board), args.output)
    print(board.head(15)[["player_id", "pos", "skm_v5", "competence", "decisive_per90", "pressure_per90"]].round(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
