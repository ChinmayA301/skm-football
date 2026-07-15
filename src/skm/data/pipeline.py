"""Build cleaned event parquet from StatsBomb open data."""

import argparse
from typing import List, Optional
import logging
import sys
from pathlib import Path

import pandas as pd
from tqdm import tqdm

from skm.config import DATA_PROCESSED, DATA_RAW, DEFAULT_COMPETITION, DEFAULT_SEASON
from skm.data.download import (
    enrich_matches,
    fetch_events_for_match,
    fetch_matches,
    resolve_competition_season,
)
from skm.data.features import add_derived_features, flatten_events, select_output_columns

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


def build_events_dataframe(
    competition: str = DEFAULT_COMPETITION,
    season: str = DEFAULT_SEASON,
    max_matches: Optional[int] = None,
    cache: bool = True,
) -> pd.DataFrame:
    competition_id, season_id, comp_row = resolve_competition_season(competition, season)
    logger.info(
        "Resolved %s %s → competition_id=%s season_id=%s",
        competition,
        season,
        competition_id,
        season_id,
    )

    matches = fetch_matches(competition_id, season_id)
    matches = enrich_matches(matches, competition, season)

    if max_matches is not None:
        matches = matches.head(max_matches)

    frames: List[pd.DataFrame] = []
    cache_dir = DATA_RAW if cache else None

    for _, match_row in tqdm(
        matches.iterrows(),
        total=len(matches),
        desc="Matches",
        unit="match",
    ):
        match_id = int(match_row["match_id"])
        try:
            raw_events = fetch_events_for_match(match_id, cache_dir=cache_dir)
            flat = flatten_events(raw_events, match_row)
            enriched = add_derived_features(flat)
            frames.append(select_output_columns(enriched))
        except Exception as exc:
            logger.warning("Skipping match %s: %s", match_id, exc)

    if not frames:
        raise RuntimeError("No events loaded — check competition/season or network.")

    return pd.concat(frames, ignore_index=True)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Build SKM events parquet from StatsBomb open data")
    parser.add_argument("--competition", default=DEFAULT_COMPETITION)
    parser.add_argument("--season", default=DEFAULT_SEASON)
    parser.add_argument(
        "--competitions",
        default=None,
        help='Multiple competitions as "Name:Season,Name:Season" (overrides --competition/--season)',
    )
    parser.add_argument("--output", type=str, default=str(DATA_PROCESSED / "events.parquet"))
    parser.add_argument("--max-matches", type=int, default=None, help="Limit matches (for testing)")
    parser.add_argument("--no-cache", action="store_true", help="Skip raw JSON cache")
    args = parser.parse_args(argv)

    if args.competitions:
        pairs = [tuple(p.split(":", 1)) for p in args.competitions.split(",") if ":" in p]
        df = pd.concat(
            [
                build_events_dataframe(
                    competition=comp,
                    season=season,
                    max_matches=args.max_matches,
                    cache=not args.no_cache,
                )
                for comp, season in pairs
            ],
            ignore_index=True,
        )
    else:
        df = build_events_dataframe(
            competition=args.competition,
            season=args.season,
            max_matches=args.max_matches,
            cache=not args.no_cache,
        )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, index=False)

    logger.info(
        "Wrote %s rows, %s matches, %s players → %s",
        len(df),
        df["match_id"].nunique(),
        df["player_id"].nunique(),
        output_path,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
