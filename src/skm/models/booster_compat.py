"""Stub broken xgboost/lightgbm so socceraction.vaep can import without libomp."""

from __future__ import annotations

import sys
import types


def stub_broken_boosters() -> None:
    for name in ("lightgbm", "xgboost"):
        try:
            __import__(name)
        except OSError:
            sys.modules[name] = types.ModuleType(name)
        except ImportError:
            pass
