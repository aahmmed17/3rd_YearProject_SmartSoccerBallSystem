# ============================================================
#  config.py
# ============================================================

# ---------------- SERIAL ----------------
PORT = "COM10"
BAUD = 115200

# ---------------- ANCHOR POSITIONS (meters) ----------------
A1 = (0.0, 0.0)
A2 = (0.0, 2.4)
A3 = (2.4, 2.4)

# ---------------- RANGE INDEX MAPPING ----------------
# If position looks wrong swap these around
IDX_ANCHOR_1 = 0
IDX_ANCHOR_2 = 1
IDX_ANCHOR_3 = 2

# ---------------- FIELD BOUNDS (meters) ----------------
FIELD_WIDTH  = 2.4
FIELD_HEIGHT = 2.4
FIELD_ORIGIN = (0.0, 0.0)

# ---------------- POSITION SMOOTHING ----------------
ALPHA_POS = 0.35   # lower = smoother, higher = more responsive

# ---------------- KICK DETECTION ----------------
KICK_THRESHOLD  = 20.0  # m/s^2 — raise if false positives, lower if kicks missed
KICK_COOLDOWN_S = 1.0   # minimum seconds between kicks
KICK_FLASH_MS   = 500   # ms the flash stays on screen

# ---------------- VISUALISER ----------------
TRAIL_LENGTH  = 80
BUFFER_LEN    = 200
UPDATE_MS     = 20
SPEED_Y_MAX   = 12
ACCEL_Y_RANGE = 30
RANGE_Y_MAX   = 15.0
