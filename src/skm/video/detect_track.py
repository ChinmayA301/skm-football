"""Player + ball detection and tracking on a user-owned clip.

Thin wrapper around ultralytics YOLO with its built-in ByteTrack tracker.
Heavy dependencies (torch) are behind the optional `[video]` extra:

    pip install -e ".[video]"

COCO classes used: 0 = person, 32 = sports ball. The foot point
(bottom-center of the bounding box) is what gets projected to pitch
coordinates — a standing player's feet are on the ground plane; heads are
not. Mean shirt color (upper half of the box) feeds team clustering.

No footage ships with this repo and none is fetched.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

PERSON_CLS = 0
BALL_CLS = 32
DEFAULT_MODEL = "yolov8n.pt"


def _require_ultralytics():
    try:
        from ultralytics import YOLO

        return YOLO
    except ImportError as exc:
        raise ImportError(
            "The CV pilot needs ultralytics (YOLO + ByteTrack). Install the "
            "optional extra:  pip install -e '.[video]'"
        ) from exc


def _video_fps(clip_path: str | Path, default: float = 25.0) -> float:
    """Read the source fps from the container; t_video depends on it."""
    try:
        import cv2

        cap = cv2.VideoCapture(str(clip_path))
        fps = cap.get(cv2.CAP_PROP_FPS)
        cap.release()
        if fps and fps > 0:
            return float(fps)
    except Exception:  # pragma: no cover - cv2 ships with ultralytics
        pass
    logger.warning("Could not read fps; assuming %.1f", default)
    return default


def _shirt_color(img: np.ndarray, xyxy: np.ndarray) -> tuple:
    """Mean BGR→RGB of the upper half of the bounding box (the shirt)."""
    x1, y1, x2, y2 = (int(v) for v in xyxy)
    y_mid = y1 + max(1, (y2 - y1) // 2)
    crop = img[max(0, y1) : y_mid, max(0, x1) : x2]
    if crop.size == 0:
        return (128.0, 128.0, 128.0)
    b, g, r = crop.reshape(-1, 3).mean(axis=0)
    return (float(r), float(g), float(b))


def run_tracker(
    clip_path: str | Path,
    model_name: str = DEFAULT_MODEL,
    stride: int = 2,
    max_frames: Optional[int] = None,
    conf: float = 0.3,
) -> pd.DataFrame:
    """
    Track persons + ball through a clip. Returns pixel-space detections:

        frame, t_video, track_id, cls, px, py, conf, r, g, b

    px/py is the foot point (bottom-center). The ball has no track
    identity requirement (track_id may be -1 when the tracker drops it).
    `stride` skips frames for speed (t_video stays true to the source fps).
    """
    YOLO = _require_ultralytics()
    model = YOLO(model_name)

    fps = _video_fps(clip_path)
    rows = []
    frame_idx = -stride  # first streamed result is source frame 0
    results = model.track(
        source=str(clip_path),
        stream=True,
        persist=True,
        classes=[PERSON_CLS, BALL_CLS],
        conf=conf,
        verbose=False,
        vid_stride=stride,
    )
    for res in results:
        frame_idx += stride
        if max_frames is not None and frame_idx >= max_frames:
            break
        if res.boxes is None or len(res.boxes) == 0:
            continue
        boxes = res.boxes
        ids = boxes.id.cpu().numpy() if boxes.id is not None else np.full(len(boxes), -1)
        for xyxy, cls_id, tid, c in zip(
            boxes.xyxy.cpu().numpy(),
            boxes.cls.cpu().numpy(),
            ids,
            boxes.conf.cpu().numpy(),
        ):
            r, g, b = _shirt_color(res.orig_img, xyxy)
            rows.append(
                {
                    "frame": frame_idx,
                    "t_video": frame_idx / fps,
                    "track_id": int(tid),
                    "cls": "person" if int(cls_id) == PERSON_CLS else "ball",
                    "px": float((xyxy[0] + xyxy[2]) / 2),  # bottom-center =
                    "py": float(xyxy[3]),  # feet on the ground plane
                    "conf": float(c),
                    "r": r,
                    "g": g,
                    "b": b,
                }
            )

    df = pd.DataFrame(rows)
    logger.info(
        "Tracked %s detections over %s frames (%s persons, %s ball)",
        len(df),
        df["frame"].nunique() if len(df) else 0,
        (df["cls"] == "person").sum() if len(df) else 0,
        (df["cls"] == "ball").sum() if len(df) else 0,
    )
    return df
