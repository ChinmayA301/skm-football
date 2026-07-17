# CV video pilot (experimental)

Runs player + ball tracking on a **video clip you own**, projects
detections to pitch coordinates, computes the same pressure geometry SKM's
difficulty model uses — and then validates itself against StatsBomb 360
freeze-frame ground truth before any number is trusted.

```
clip you own → YOLO + ByteTrack → homography → pitch tracks
             → nearest-defender geometry → agreement gate vs StatsBomb 360
```

**Status: experimental.** No footage ships with this repo and none is
fetched — broadcast video is copyrighted. Until the agreement gate passes
on your clip, every CV-derived number is a capability demo, not a
measurement.

## Install

```bash
pip install -e ".[video]"   # adds ultralytics (YOLO + ByteTrack; pulls torch)
```

## Choosing a clip (this matters more than anything else)

| Requirement | Why |
|---|---|
| A match from the repo's scored sample (WC 2022, Euro 2024, Bundesliga 23/24, Ligue 1 22/23, La Liga 20/21) | The gate needs StatsBomb 360 ground truth for the same events |
| **Single camera shot, no cuts** — tactical/wide angle if available | The homography is only valid for one camera pose; broadcast cuts break it |
| 10–60 seconds of open play | Long enough to pair ≥10 events, short enough to calibrate once |
| You know the match clock at the first frame | The `--offset` joins video time to event time |

A panning main broadcast camera degrades accuracy; a fixed tactical camera
is the intended input. Keep the clip local — don't commit or redistribute it.

## Run

```bash
# 1. Write the calibration template
skm-video-pilot --init-calibration calib.json

# 2. Open one frame of your clip in any image viewer and record pixel
#    positions of 4+ known pitch landmarks (penalty spots, box corners,
#    center spot). Fill them into calib.json. 6+ points beat 4.

# 3. Make sure 360 features are built (skm-build-360), then:
skm-video-pilot --clip clip.mp4 --calibration calib.json \
    --game-id 3857273 --period 1 --offset 1830
```

`--offset` = the period's match clock, in seconds, at the clip's first
frame (e.g. a clip starting at 30:30 of the first half → `--offset 1830`).

## What you get

- `data/processed/cv_tracks.parquet` — every detection in pitch coordinates
  with track identity and team assignment (2-means on shirt color)
- `data/processed/cv_pressure.parquet` — per-frame ball-carrier pressure:
  nearest defender distance, defenders within 5 m / 10 m
- **The gate verdict** — CV nearest-defender distances paired with
  StatsBomb 360 values at event times: Spearman ρ ≥ 0.5 and MAE ≤ 3 m
  over ≥10 paired events (provisional thresholds, stated up front)

## Known limits

- **Team assignment** is 2-means on shirt color: referees and goalkeepers
  can land in either cluster. Inspect `cv_tracks.parquet` before trusting it.
- **One calibration per camera shot.** Any cut, pan, or zoom needs a new
  calibration; the pilot doesn't detect shot changes.
- **Ball detection is the weak link** — small, fast, motion-blurred.
  Frames without a confident ball detection produce no pressure row
  (reported as coverage, never interpolated).
- **Occlusion**: players hidden behind others are simply missing; the 360
  comparison has the same visible-area caveat on its side.
- The foot point (bottom-center of the box) approximates ground position;
  airborne players and keepers diving violate it.

## First real-clip run (WC 2022 final, honest result)

Run on a locally-owned broadcast clip of Argentina–France (game 3869685,
second half, 68:53–70:28 — a 95 s window with 33 StatsBomb 360-covered
events). This is the documented reality, negative parts included.

**What ran successfully on real footage:**

| Step | Result |
|---|---|
| Detection + tracking (yolov8n, stride 3) | 5,841 detections over 948 frames in 100 s |
| Players | 5,814 person detections tracked |
| Homography projection (center-circle calibration, 0.36 m reprojection) | 98% of detections land on the pitch |
| Team assignment (2-means on shirt color) | ran |

**What failed, and why it's the right outcome:**

- **Ball detection: 24 of 948 frames.** The generic COCO "sports ball"
  class barely catches a fast, small, motion-blurred football. With so few
  ball frames — and the broadcast camera panning away from the midfield
  calibration — no frame had a ball *and* a player within the 3 m carrier
  threshold. Pressure frames: **0**.
- **Gate verdict: 0 pairs, not evaluable.** The gate correctly *refused to
  emit a ρ/MAE number* rather than fabricate agreement from nothing. A
  no-number result is the honest one here.

**Diagnosis — what a passing run actually needs:**

1. **A football-specific detector.** Ball detection is the bottleneck; a
   model trained on football (ball + players) rather than generic COCO is
   the single biggest lever.
2. **Calibration that tracks camera motion.** A single homography is valid
   for one camera pose; broadcast footage pans continuously. Either a
   near-static tactical/wide camera, or per-frame homography from automated
   pitch-line detection.
3. **Optionally, anchor the carrier on the StatsBomb ball location** at
   event times instead of CV ball detection — this tests player
   detection/projection independently of the flaky ball detector (a weaker
   but more robust gate variant; future work).

The takeaway: the pipeline is real and runs on real footage, the gate works
as a guard, and broadcast main-camera footage with a generic detector is
**not** sufficient for a trustworthy CV pressure measurement — exactly what
this staged, gated design is meant to surface before any number is trusted.

## Environment note (numpy / opencv)

Installing `[video]` pulls `opencv-python`/`ultralytics`, whose recent
builds prefer `numpy>=2`, while `socceraction` requires `numpy<2`. Pin
numpy back after installing the extra:

```bash
pip install -e ".[video]"
pip install "numpy>=1.26,<2.0"   # ultralytics + opencv run fine on 1.26 at runtime
```

## Why the gate exists

The rest of SKM's difficulty pipeline runs on measured StatsBomb 360
geometry with a validated accuracy gain (held-out AUC 0.690 → 0.829 — see
[RESULTS.md](RESULTS.md)). Camera-derived geometry only earns its way into
that pipeline by agreeing with the measured data where both exist. Until
then it's a demo.
