"""StatsBomb open-data download helpers."""

import json
from typing import Optional, Tuple
import logging
from pathlib import Path

import pandas as pd
from statsbombpy import sb

from skm.config import DATA_RAW, DEFAULT_COMPETITION, DEFAULT_SEASON

logger = logging.getLogger(__name__)


def list_competitions() -> pd.DataFrame:
    return sb.competitions()


def resolve_competition_season(
    competition_name: str = DEFAULT_COMPETITION,
    season_name: str = DEFAULT_SEASON,
) -> Tuple[int, int, pd.Series]:
    comps = list_competitions()
    mask = (comps["competition_name"] == competition_name) & (comps["season_name"] == season_name)
    hits = comps[mask]
    if hits.empty:
        available = comps[["competition_name", "season_name"]].drop_duplicates()
        raise ValueError(
            f"No competition '{competition_name}' season '{season_name}'. "
            f"Available:\n{available.to_string(index=False)}"
        )
    row = hits.iloc[0]
    return int(row["competition_id"]), int(row["season_id"]), row


def fetch_matches(competition_id: int, season_id: int) -> pd.DataFrame:
    matches = sb.matches(competition_id=competition_id, season_id=season_id)
    matches = matches.copy()
    matches["match_id"] = matches["match_id"].astype(int)
    return matches


def fetch_events_for_match(match_id: int, cache_dir: Optional[Path] = DATA_RAW) -> pd.DataFrame:
    if cache_dir is not None:
        cache_path = cache_dir / f"events_{match_id}.json"
        if cache_path.exists():
            with cache_path.open() as f:
                records = json.load(f)
            return pd.DataFrame(records)

    events = sb.events(match_id=match_id)
    if cache_dir is not None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = cache_dir / f"events_{match_id}.json"
        events.to_json(cache_path, orient="records", date_format="iso")
    return events


def _team_name(value, fallback_key: str) -> str:
    if isinstance(value, dict):
        return value.get(fallback_key) or value.get("name") or ""
    return str(value) if value is not None else ""


def enrich_matches(matches: pd.DataFrame, competition: str, season: str) -> pd.DataFrame:
    m = matches.copy()
    m["competition"] = competition
    m["season"] = season

    if "home_team_name" in m.columns:
        m["home_team"] = m["home_team_name"]
        m["away_team"] = m["away_team_name"]
    else:
        m["home_team"] = m["home_team"].map(lambda t: _team_name(t, "home_team_name"))
        m["away_team"] = m["away_team"].map(lambda t: _team_name(t, "away_team_name"))

    if "home_score" not in m.columns:
        m["home_score"] = 0
    if "away_score" not in m.columns:
        m["away_score"] = 0
    m["home_score"] = m["home_score"].fillna(0).astype(int)
    m["away_score"] = m["away_score"].fillna(0).astype(int)
    return m
