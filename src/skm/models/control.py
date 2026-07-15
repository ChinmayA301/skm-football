"""skm_control: structural value layer (Phase 5b).

The roadmap describes skm_control as "defensive VAEP + progressive/pressure/
zone boost". Defensive VAEP already flows through ΔP (delta_p = vaep_value =
offensive_value + defensive_value), so re-adding it here would double count.
skm_control is therefore the *structural boost only*:

- successful progressive pass/carry/cross (≥ PROGRESSIVE_DISTANCE_M toward
  the opponent goal)
- successful on-ball action under pressure (press resistance)
- successful defensive action in the own defensive third

Each bonus is expressed in units of the sample's median positive ΔP, so the
layer self-calibrates to the VAEP scale instead of using magic constants.
Multipliers live in config (CONTROL_*_MULT).
"""

from __future__ import annotations

import logging
from typing import Dict, Optional

import numpy as np
import pandas as pd

from skm.config import (
    CONTROL_PRESS_MULT,
    CONTROL_PROG_MULT,
    CONTROL_ZONE_MULT,
    PITCH_LENGTH,
    PROGRESSIVE_DISTANCE_M,
)
from skm.models.moments import infer_home_teams

logger = logging.getLogger(__name__)

PROGRESS_TYPES = {"pass", "dribble", "cross"}
PRESSURE_TYPES = {"pass", "cross", "dribble", "take_on", "shot"}
DEFENSIVE_TYPES = {
    "tackle",
    "interception",
    "clearance",
    "keeper_save",
    "keeper_claim",
    "keeper_punch",
    "keeper_pick_up",
}

OWN_THIRD_M = PITCH_LENGTH / 3.0


def compute_skm_control(
    actions: pd.DataFrame,
    home_teams: Optional[Dict[int, int]] = None,
) -> pd.DataFrame:
    """
    Return a frame aligned to `actions` with:

    - is_progressive: successful pass/carry/cross moving ≥10m toward goal
    - skm_control: sum of structural bonuses (progressive, press resistance,
      own-third defensive success), in median-positive-ΔP units
    """
    import socceraction.spadl as spadl

    if home_teams is None:
        home_teams = infer_home_teams(actions)

    named = spadl.add_names(actions)
    success = named["result_name"] == "success"

    # Bonus unit: median positive ΔP on this sample
    pos = named["delta_p"].dropna()
    pos = pos[pos > 0]
    unit = float(pos.median()) if len(pos) else 1e-3
    logger.info("skm_control bonus unit (median positive ΔP): %.5f", unit)

    # Attack direction: home attacks +x, away attacks -x (SPADL convention)
    is_home = named["game_id"].astype(int).map(home_teams) == named["team_id"].astype(int)
    sign = np.where(is_home, 1.0, -1.0)
    forward = sign * (named["end_x"] - named["start_x"]).fillna(0)

    is_progressive = (
        named["type_name"].isin(PROGRESS_TYPES)
        & success
        & (forward >= PROGRESSIVE_DISTANCE_M)
    )

    under_pressure = named.get("under_pressure")
    if under_pressure is None:
        under_pressure = pd.Series(False, index=named.index)
    press_resist = (
        named["type_name"].isin(PRESSURE_TYPES)
        & success
        & under_pressure.fillna(False).astype(bool)
    )

    # Own defensive third: home defends x < 40, away defends x > 80
    own_third = np.where(
        is_home,
        named["start_x"] < OWN_THIRD_M,
        named["start_x"] > PITCH_LENGTH - OWN_THIRD_M,
    )
    zone_defense = named["type_name"].isin(DEFENSIVE_TYPES) & success & own_third

    control = unit * (
        CONTROL_PROG_MULT * is_progressive.astype(float)
        + CONTROL_PRESS_MULT * press_resist.astype(float)
        + CONTROL_ZONE_MULT * zone_defense.astype(float)
    )

    return pd.DataFrame(
        {"is_progressive": is_progressive.to_numpy(), "skm_control": control.to_numpy()},
        index=actions.index,
    )
