from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"

# StatsBomb pitch (120 x 80)
PITCH_LENGTH = 120.0
PITCH_WIDTH = 80.0

# Grid for zone assignment
GRID_COLS = 12
GRID_ROWS = 8

# Progressive action threshold (meters toward opponent goal)
PROGRESSIVE_DISTANCE_M = 10.0

# Default open-data target (PL 2023/24 not in open data; Bundesliga is latest full league)
DEFAULT_COMPETITION = "1. Bundesliga"
DEFAULT_SEASON = "2023/2024"

# SKM v1 combination weights
SKM_W_D = 0.3
SKM_W_C = 0.3
SKM_W_R = 0.3

# Component clip ranges
D_CLIP = (0.5, 3.0)
C_CLIP = (0.5, 2.0)
R_CLIP = (0.8, 1.5)

# VAEP training
VAEP_NR_ACTIONS = 10
VAEP_NB_PREV_ACTIONS = 3
VAEP_N_ESTIMATORS = 80
VAEP_MAX_DEPTH = 3

# Role clustering
ROLE_N_CLUSTERS = 7

# Output paths
EVENTS_PARQUET = DATA_PROCESSED / "events.parquet"
ACTIONS_SCORED_PARQUET = DATA_PROCESSED / "actions_scored.parquet"
PLAYER_LEADERBOARD_PARQUET = DATA_PROCESSED / "player_leaderboard.parquet"
