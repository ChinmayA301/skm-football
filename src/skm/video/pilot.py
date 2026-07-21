"""CV pilot CLI: user-owned clip → pitch tracks → pressure → agreement gate.

    # 1. Write a calibration template, then fill in 4+ landmarks
    skm-video-pilot --init-calibration calib.json

    # 2. Run the pilot against a clip from a 360-covered match
    skm-video-pilot --clip clip.mp4 --calibration calib.json \
        --game-id 3857273 --period 1 --offset 1830

`--offset` is the match clock (period `time_seconds`) at the clip's first
frame. The gate verdict compares CV-derived nearest-defender distances at
event times with StatsBomb 360 freeze-frame ground truth; until it passes,
CV numbers are a capability demo, not a measurement.

Full runbook (clip spec, calibration walkthrough): docs/CV_PILOT.md.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Optional

import pandas as pd

from skm.config import ACTIONS_360_PARQUET, ACTIONS_SCORED_PARQUET, DATA_PROCESSED
from skm.video.calibration import apply_homography, load_calibration
from skm.video.geometry import agreement_report, assign_teams, pressure_timeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PITCH_MARGIN_M = 3.0  # detections mapped outside the pitch (+margin) are dropped

CALIB_TEMPLATE = {
    "_instructions": (
        "Mark 4+ pitch landmarks visible in ONE representative frame of the "
        "clip (same camera shot). px/py = pixel position in the frame; "
        "x/y = pitch position in meters, SPADL frame (x 0-120 left goal to "
        "right goal, y 0-80 top to bottom). Good landmarks: penalty spots "
        "(12, 40) / (108, 40), box corners (18, 18)/(18, 62)/(102, 18)/(102, 62), "
        "center spot (60, 40), corner flags (0, 0)/(120, 0)/(0, 80)/(120, 80). "
        "Spread points across the visible area; 6+ points beat 4."
    ),
    "points": [
        {"px": 0, "py": 0, "x": 0.0, "y": 0.0},
        {"px": 0, "py": 0, "x": 0.0, "y": 0.0},
        {"px": 0, "py": 0, "x": 0.0, "y": 0.0},
        {"px": 0, "py": 0, "x": 0.0, "y": 0.0},
    ],
}


def _load_360_actions() -> Optional[pd.DataFrame]:
    for path in (ACTIONS_SCORED_PARQUET, ACTIONS_360_PARQUET):
        if path.exists():
            df = pd.read_parquet(path)
            if "nearest_def_m" in df.columns:
                return df
    return None


def run_pilot(
    clip: str,
    calibration: str,
    game_id: Optional[int] = None,
    period: int = 1,
    offset: float = 0.0,
    stride: int = 2,
    max_frames: Optional[int] = None,
    output_dir: Optional[Path] = None,
) -> dict:
    from skm.video.detect_track import run_tracker

    H = load_calibration(calibration)
    tracks = run_tracker(clip, stride=stride, max_frames=max_frames)
    if tracks.empty:
        raise RuntimeError("No detections — check the clip path and content.")

    pitch = apply_homography(H, tracks[["px", "py"]].to_numpy())
    tracks["x"], tracks["y"] = pitch[:, 0], pitch[:, 1]
    inside = tracks["x"].between(-PITCH_MARGIN_M, 120 + PITCH_MARGIN_M) & tracks["y"].between(
        -PITCH_MARGIN_M, 80 + PITCH_MARGIN_M
    )
    dropped = int((~inside).sum())
    tracks = tracks[inside].reset_index(drop=True)
    logger.info("Projected to pitch; dropped %s off-pitch detections", dropped)

    teams = assign_teams(tracks)
    pressure = pressure_timeline(tracks, teams)
    coverage = pressure["frame"].nunique() / max(tracks["frame"].nunique(), 1)
    logger.info(
        "Pressure computed on %s frames (%.0f%% of tracked frames have ball + carrier)",
        len(pressure),
        coverage * 100,
    )

    out_dir = output_dir or DATA_PROCESSED
    out_dir.mkdir(parents=True, exist_ok=True)
    tracks.to_parquet(out_dir / "cv_tracks.parquet", index=False)
    pressure.to_parquet(out_dir / "cv_pressure.parquet", index=False)

    result = {"n_detections": len(tracks), "n_pressure_frames": len(pressure)}
    if game_id is not None:
        actions = _load_360_actions()
        if actions is None:
            result["gate"] = {"passed": False, "reason": "no 360 features found — run skm-build-360 first"}
        else:
            result["gate"] = agreement_report(pressure, actions, game_id, period, offset)
    return result


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description="CV video pilot (Stage 2)")
    parser.add_argument("--init-calibration", metavar="PATH", help="Write a calibration template and exit")
    parser.add_argument("--clip", help="Path to a locally owned video clip")
    parser.add_argument("--calibration", help="Calibration JSON (see --init-calibration)")
    parser.add_argument("--game-id", type=int, default=None, help="Match id for the 360 agreement gate")
    parser.add_argument("--period", type=int, default=1)
    parser.add_argument("--offset", type=float, default=0.0, help="Match clock (s) at the clip's first frame")
    parser.add_argument("--stride", type=int, default=2, help="Process every Nth frame")
    parser.add_argument("--max-frames", type=int, default=None)
    args = parser.parse_args(argv)

    if args.init_calibration:
        Path(args.init_calibration).write_text(json.dumps(CALIB_TEMPLATE, indent=2))
        print(f"Template written to {args.init_calibration} — fill in the landmarks, then rerun.")
        return 0

    if not args.clip or not args.calibration:
        parser.error("--clip and --calibration are required (or use --init-calibration)")

    result = run_pilot(
        clip=args.clip,
        calibration=args.calibration,
        game_id=args.game_id,
        period=args.period,
        offset=args.offset,
        stride=args.stride,
        max_frames=args.max_frames,
    )

    print(f"\nDetections: {result['n_detections']:,} · pressure frames: {result['n_pressure_frames']:,}")
    gate = result.get("gate")
    if gate:
        print("\n=== 360 agreement gate ===")
        for k in ("n_pairs", "rho", "mae_m", "reason"):
            if k in gate:
                print(f"{k}: {gate[k]}")
        print("PASSED ✅" if gate.get("passed") else "NOT PASSED — CV numbers stay demo-only")
    else:
        print("No --game-id given: skipped the agreement gate (demo mode).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
