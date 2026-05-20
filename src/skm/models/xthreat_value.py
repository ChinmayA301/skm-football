"""Expected Threat (xT) baseline value V for comparison."""

from __future__ import annotations

import pandas as pd


def fit_and_rate_xt(actions: pd.DataFrame, games: pd.DataFrame) -> pd.Series:
    """Fit xT on all actions and return xT_value per action (index-aligned)."""
    import socceraction.spadl as spadl
    import socceraction.xthreat as xthreat

    ltr_by_game = {}
    for game_id, game_actions in actions.groupby("game_id"):
        home_id = int(games.loc[game_id, "home_team_id"])
        ltr_by_game[game_id] = spadl.play_left_to_right(game_actions, home_id)

    all_ltr = pd.concat(ltr_by_game.values(), ignore_index=True)
    model = xthreat.ExpectedThreat(l=12, w=8)
    model.fit(all_ltr)

    parts = []
    for game_id, game_actions in actions.groupby("game_id"):
        vals = model.rate(ltr_by_game[game_id])
        parts.append(pd.Series(vals, index=game_actions.index))
    return pd.concat(parts)
