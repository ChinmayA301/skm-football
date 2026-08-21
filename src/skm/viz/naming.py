"""SPADL action/result names without requiring socceraction at runtime.

The dashboard only needs `type_name` / `result_name` labels. Pulling those
from socceraction drags in the whole modelling stack (and its `numpy<2` pin,
which caps the deployable Python version). Instead the app bundle bakes the
columns in at build time (`scripts/make_app_bundle.py`), and this helper uses
them when present, falling back to socceraction for local/dev frames that
haven't been through the bundler.
"""

from __future__ import annotations

import pandas as pd

NAME_COLUMNS = ("type_name", "result_name")


def has_names(actions: pd.DataFrame) -> bool:
    return all(c in actions.columns for c in NAME_COLUMNS)


def add_action_names(actions: pd.DataFrame) -> pd.DataFrame:
    """Return `actions` with type_name/result_name columns.

    Uses pre-baked columns when available (no heavy import); otherwise defers
    to socceraction, which is only installed in the full modelling env.
    """
    if has_names(actions):
        return actions

    try:
        import socceraction.spadl as spadl  # local/dev path only
    except ImportError as exc:  # pragma: no cover - deploy misconfiguration
        raise RuntimeError(
            "Action frame has no type_name/result_name columns and socceraction "
            "is not installed. On a slim deployment these labels must be baked "
            "into the bundle — regenerate it with "
            "`python scripts/make_app_bundle.py`. For local model work install "
            "the full stack: `pip install -e '.[model]'`."
        ) from exc

    return spadl.add_names(actions)
