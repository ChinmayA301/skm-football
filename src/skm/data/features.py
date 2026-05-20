"""Derived features for SKM event rows."""

from __future__ import annotations

import numpy as np
import pandas as pd

from skm.config import GRID_COLS, GRID_ROWS, PITCH_LENGTH, PITCH_WIDTH, PROGRESSIVE_DISTANCE_M

MINUTE_BUCKETS = [
    (0, 15, "0-15"),
    (15, 30, "15-30"),
    (30, 45, "30-45"),
    (45, 60, "45-60"),
    (60, 75, "60-75"),
    (75, 90, "75-90"),
    (90, 999, "90+"),
]


def assign_zone(x: float | None, y: float | None) -> str | None:
    if x is None or y is None or (isinstance(x, float) and np.isnan(x)):
        return None
    col = min(int(x / PITCH_LENGTH * GRID_COLS), GRID_COLS - 1)
    row = min(int(y / PITCH_WIDTH * GRID_ROWS), GRID_ROWS - 1)
    return f"{col}_{row}"


def distance_toward_goal(
    start_x: float,
    start_y: float,
    end_x: float,
    end_y: float,
    attacking_right: bool,
) -> float:
    if attacking_right:
        return end_x - start_x
    return start_x - end_x


def is_progressive(
    start_x: float | None,
    start_y: float | None,
    end_x: float | None,
    end_y: float | None,
    attacking_right: bool,
) -> bool:
    if any(v is None or (isinstance(v, float) and np.isnan(v)) for v in (start_x, start_y, end_x, end_y)):
        return False
    delta = distance_toward_goal(start_x, start_y, end_x, end_y, attacking_right)
    in_final_third_start = (start_x >= 80) if attacking_right else (start_x <= 40)
    in_final_third_end = (end_x >= 80) if attacking_right else (end_x <= 40)
    return delta >= PROGRESSIVE_DISTANCE_M or (not in_final_third_start and in_final_third_end)


def minute_bucket(minute: int | float | None) -> str | None:
    if minute is None or (isinstance(minute, float) and np.isnan(minute)):
        return None
    m = int(minute)
    for lo, hi, label in MINUTE_BUCKETS:
        if lo <= m < hi:
            return label
    return "90+"


def scoreline_state(home_score: int, away_score: int, team_is_home: bool) -> str:
    team_score = home_score if team_is_home else away_score
    opp_score = away_score if team_is_home else home_score
    if team_score > opp_score:
        return "leading"
    if team_score < opp_score:
        return "trailing"
    return "drawing"


def _nested_name(obj) -> str | None:
    if isinstance(obj, dict):
        return obj.get("name")
    if isinstance(obj, str):
        return obj
    return None


def _nested_id(obj):
    if isinstance(obj, dict):
        return obj.get("id")
    return obj


def _parse_location(loc) -> tuple[float | None, float | None]:
    if isinstance(loc, (list, tuple)) and len(loc) >= 2:
        return float(loc[0]), float(loc[1])
    return None, None


def _is_present(val) -> bool:
    if val is None:
        return False
    try:
        if isinstance(val, float) and np.isnan(val):
            return False
    except TypeError:
        pass
    return True


def _first_end_location(row: pd.Series) -> tuple[float | None, float | None]:
    for col in ("pass_end_location", "carry_end_location", "shot_end_location", "goalkeeper_end_location"):
        if col in row.index:
            val = row[col]
            if _is_present(val):
                return _parse_location(val)
    return None, None


def _is_flat_statsbombpy(events: pd.DataFrame) -> bool:
    if events.empty:
        return "pass_end_location" in events.columns
    return "pass_end_location" in events.columns


def flatten_events(events: pd.DataFrame, match_row: pd.Series) -> pd.DataFrame:
    """Normalize StatsBomb events (statsbombpy flat or nested JSON) into flat columns."""
    if _is_flat_statsbombpy(events):
        return _flatten_flat_events(events, match_row)
    return _flatten_nested_events(events, match_row)


def _flatten_flat_events(events: pd.DataFrame, match_row: pd.Series) -> pd.DataFrame:
    df = events.copy()

    df["match_id"] = int(match_row["match_id"])
    df["competition"] = match_row.get("competition", "")
    df["season"] = match_row.get("season", "")
    df["match_date"] = match_row.get("match_date", "")
    df["home_team"] = match_row["home_team"]
    df["away_team"] = match_row["away_team"]
    df["home_score"] = int(match_row.get("home_score", 0) or 0)
    df["away_score"] = int(match_row.get("away_score", 0) or 0)

    df["event_type"] = df["type"]
    df["player"] = df.get("player")
    df["player_id"] = df.get("player_id")
    df["team"] = df.get("team")

    locs = df["location"].map(_parse_location)
    df["start_x"] = locs.map(lambda t: t[0])
    df["start_y"] = locs.map(lambda t: t[1])

    ends = df.apply(_first_end_location, axis=1)
    df["end_x"] = ends.map(lambda t: t[0])
    df["end_y"] = ends.map(lambda t: t[1])

    df["outcome"] = None
    if "pass_outcome" in df.columns:
        df.loc[df["event_type"] == "Pass", "outcome"] = df["pass_outcome"].fillna("Complete")
    if "dribble_outcome" in df.columns:
        mask = df["event_type"] == "Dribble"
        df.loc[mask, "outcome"] = df.loc[mask, "dribble_outcome"]

    df["under_pressure"] = df.get("under_pressure", False)
    df["under_pressure"] = df["under_pressure"].astype(object).where(df["under_pressure"].notna(), False).astype(bool)

    df["body_part"] = None
    if "pass_body_part" in df.columns:
        df.loc[df["event_type"] == "Pass", "body_part"] = df["pass_body_part"]
    if "shot_body_part" in df.columns:
        df.loc[df["event_type"] == "Shot", "body_part"] = df["shot_body_part"]

    df["pass_type"] = df.get("pass_type") if "pass_type" in df.columns else None

    if "shot_statsbomb_xg" in df.columns:
        df["shot_xg"] = pd.to_numeric(df["shot_statsbomb_xg"], errors="coerce")
    elif "shot_xg" not in df.columns:
        df["shot_xg"] = np.nan

    if "pass_goal_assist" in df.columns:
        df["pass_goal_assist"] = df["pass_goal_assist"].fillna(False).astype(bool)
    else:
        df["pass_goal_assist"] = False

    df["minute"] = df["minute"].astype(int)
    df["second"] = df.get("second", 0).fillna(0).astype(int)

    return df


def _flatten_nested_events(events: pd.DataFrame, match_row: pd.Series) -> pd.DataFrame:
    """Fallback for cached nested JSON from open-data API."""
    df = events.copy()

    df["match_id"] = int(match_row["match_id"])
    df["competition"] = match_row.get("competition", "")
    df["season"] = match_row.get("season", "")
    df["match_date"] = match_row.get("match_date", "")
    df["home_team"] = match_row["home_team"]
    df["away_team"] = match_row["away_team"]
    df["home_score"] = int(match_row.get("home_score", 0) or 0)
    df["away_score"] = int(match_row.get("away_score", 0) or 0)

    df["event_type"] = df["type"].map(_nested_name)
    df["player"] = df["player"].map(_nested_name)
    df["player_id"] = events["player"].map(_nested_id)
    df["team"] = df["team"].map(_nested_name)

    locs = df["location"].map(_parse_location)
    df["start_x"] = locs.map(lambda t: t[0])
    df["start_y"] = locs.map(lambda t: t[1])

    pass_end = df["pass"].apply(lambda p: p.get("end_location") if isinstance(p, dict) else None) if "pass" in df else None
    carry_end = df["carry"].apply(lambda c: c.get("end_location") if isinstance(c, dict) else None) if "carry" in df else None

    def pick_end(row):
        for val in (pass_end[row.name] if pass_end is not None else None, carry_end[row.name] if carry_end is not None else None):
            if val is not None:
                return _parse_location(val)
        return None, None

    ends = df.apply(pick_end, axis=1)
    df["end_x"] = ends.map(lambda t: t[0])
    df["end_y"] = ends.map(lambda t: t[1])

    df["under_pressure"] = df.get("under_pressure", False).fillna(False).astype(bool)
    df["minute"] = df["minute"].astype(int)
    df["second"] = df.get("second", 0).fillna(0).astype(int)
    df["outcome"] = None
    df["body_part"] = None
    df["pass_type"] = None

    return df


def add_derived_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["team_is_home"] = out["team"] == out["home_team"]
    out["attacking_right"] = out["team_is_home"]

    out["zone"] = [assign_zone(x, y) for x, y in zip(out["start_x"], out["start_y"])]

    out["progressive"] = [
        is_progressive(sx, sy, ex, ey, ar)
        for sx, sy, ex, ey, ar in zip(
            out["start_x"],
            out["start_y"],
            out["end_x"],
            out["end_y"],
            out["attacking_right"],
        )
    ]

    out["match_minute_bucket"] = out["minute"].map(minute_bucket)

    out["scoreline_state"] = [
        scoreline_state(h, a, th)
        for h, a, th in zip(out["home_score"], out["away_score"], out["team_is_home"])
    ]

    out["opponent_quality"] = 1.0

    return out


def select_output_columns(df: pd.DataFrame) -> pd.DataFrame:
    cols = [
        "match_id",
        "competition",
        "season",
        "match_date",
        "home_team",
        "away_team",
        "team",
        "player",
        "player_id",
        "minute",
        "second",
        "event_type",
        "start_x",
        "start_y",
        "end_x",
        "end_y",
        "outcome",
        "under_pressure",
        "body_part",
        "pass_type",
        "shot_xg",
        "pass_goal_assist",
        "zone",
        "progressive",
        "scoreline_state",
        "match_minute_bucket",
        "opponent_quality",
    ]
    existing = [c for c in cols if c in df.columns]
    return df[existing].copy()
