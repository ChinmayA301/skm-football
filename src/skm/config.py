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

# Adjusted SKM weighting layer (v1.5) — modest, disclosed priors
POSITION_W_CLIP = (0.9, 1.25)
ROLE_W_CLIP = (0.85, 1.2)
GAME_STATE_W_CLIP = (0.6, 1.4)
GAME_STATE_W_GARBAGE = 0.7  # |score_diff| >= 3
GAME_STATE_W_LATE_CLOSE = 1.3  # minute >= 85 and |score_diff| <= 1
SEQUENCE_SHOT_BOOST = 1.15  # non-shot actions in a chain ending in a shot
SEQUENCE_CHAIN_GAP_S = 15.0
SEQUENCE_MIN_CHAIN_LEN = 3

# Moment segmentation (Phase 5)
MOMENT_GAP_S = 20.0  # time gap that ends a moment
MOMENT_MAX_ACTIONS = 25  # length cap per moment
TRANSITION_PROGRESS_M = 25.0  # net forward progress to call a regain a transition
TRANSITION_WINDOW_ACTIONS = 4  # actions inspected for transition progress

# skm_control + moment credits (Phase 5b)
# Bonus unit = median positive delta_p on the sample (self-calibrating);
# multipliers below scale that unit.
CONTROL_PROG_MULT = 1.0  # successful progressive pass/carry/cross
CONTROL_PRESS_MULT = 0.5  # successful on-ball action under pressure
CONTROL_ZONE_MULT = 0.5  # successful defensive action in own third
MOMENT_CREDIT_ALPHA = 0.7  # own-action value share vs moment-shared value

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
MOMENTS_PARQUET = DATA_PROCESSED / "moments.parquet"
MOMENT_PLAYERS_PARQUET = DATA_PROCESSED / "moment_players.parquet"
PLAYER_CREDITS_PARQUET = DATA_PROCESSED / "player_credits.parquet"
PLAYER_SKM_V2_PARQUET = DATA_PROCESSED / "player_skm_v2.parquet"
