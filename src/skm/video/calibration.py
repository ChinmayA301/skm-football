"""Pixel → pitch homography from manual point correspondences.

Automatic pitch-line calibration is a research problem (SoccerNet-Calibration
exists because of it). The honest pilot approach is manual: the user marks
4+ known pitch landmarks in a representative frame (penalty spots, corner
arcs, center circle, box corners) and records pixel ↔ pitch pairs in a JSON
file. Broadcast cameras pan and zoom, so a calibration is only valid for
one camera shot; the pilot targets single-camera tactical clips first.

Pitch coordinates follow SPADL: x ∈ [0, 120], y ∈ [0, 80], attacking
direction handled downstream.

Calibration JSON schema:
    {"points": [{"px": 640, "py": 360, "x": 60.0, "y": 40.0}, ...]}

The homography is estimated with the normalized Direct Linear Transform
(Hartley normalization + SVD) in pure numpy — no OpenCV dependency.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Tuple

import numpy as np


def _normalize(pts: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Hartley normalization: translate to centroid, scale to mean dist √2."""
    centroid = pts.mean(axis=0)
    dists = np.sqrt(((pts - centroid) ** 2).sum(axis=1))
    scale = np.sqrt(2) / max(dists.mean(), 1e-12)
    T = np.array(
        [
            [scale, 0, -scale * centroid[0]],
            [0, scale, -scale * centroid[1]],
            [0, 0, 1],
        ]
    )
    homog = np.column_stack([pts, np.ones(len(pts))])
    return (T @ homog.T).T[:, :2], T


def fit_homography(pixel_pts: np.ndarray, pitch_pts: np.ndarray) -> np.ndarray:
    """DLT estimate of H such that pitch ≈ H · pixel. Needs ≥4 points."""
    pixel_pts = np.asarray(pixel_pts, dtype=float)
    pitch_pts = np.asarray(pitch_pts, dtype=float)
    if len(pixel_pts) < 4 or len(pixel_pts) != len(pitch_pts):
        raise ValueError("Need at least 4 pixel↔pitch correspondences")

    src, T_src = _normalize(pixel_pts)
    dst, T_dst = _normalize(pitch_pts)

    rows = []
    for (u, v), (x, y) in zip(src, dst):
        rows.append([-u, -v, -1, 0, 0, 0, u * x, v * x, x])
        rows.append([0, 0, 0, -u, -v, -1, u * y, v * y, y])
    A = np.array(rows)
    _, _, Vt = np.linalg.svd(A)
    Hn = Vt[-1].reshape(3, 3)

    H = np.linalg.inv(T_dst) @ Hn @ T_src
    return H / H[2, 2]


def apply_homography(H: np.ndarray, pixel_pts: np.ndarray) -> np.ndarray:
    """Map (N, 2) pixel points to pitch coordinates."""
    pts = np.asarray(pixel_pts, dtype=float)
    homog = np.column_stack([pts, np.ones(len(pts))])
    mapped = (H @ homog.T).T
    return mapped[:, :2] / mapped[:, 2:3]


def reprojection_error(H: np.ndarray, pixel_pts, pitch_pts) -> float:
    """Mean distance (pitch meters) between mapped and true pitch points."""
    mapped = apply_homography(H, pixel_pts)
    return float(np.sqrt(((mapped - np.asarray(pitch_pts, float)) ** 2).sum(axis=1)).mean())


def load_calibration(path: str | Path) -> np.ndarray:
    """Load correspondences JSON and return the fitted homography."""
    data = json.loads(Path(path).read_text())
    pts = data["points"]
    pixel = np.array([[p["px"], p["py"]] for p in pts], dtype=float)
    pitch = np.array([[p["x"], p["y"]] for p in pts], dtype=float)
    H = fit_homography(pixel, pitch)
    err = reprojection_error(H, pixel, pitch)
    if err > 2.0:
        raise ValueError(
            f"Calibration reprojection error {err:.1f} m > 2.0 m — "
            "re-mark the landmarks (are they from the same camera shot?)"
        )
    return H
