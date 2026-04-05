# ============================================================
#  config.py  —  3D tracking with 4 anchors
# ============================================================

# ---------------- SERIAL ----------------
PORT = "COM10"
BAUD = 115200

# ---------------- ANCHOR POSITIONS (x, y, z) in meters ------------
#
#  Top-down layout example:
#
#   A2(0, 2.4, 0)  -------- A4(2.4, 2.4, 2.0)  
#        |                        |
#        |                        |
#   A1(0, 0,   0)  -------- A3(2.4, 0,  2.0)   
#
A1 = (0.0,  0.0,  1.35)   
A2 = (4.5,  0.0,  0.1)   
A3 = (4.5, 3,  1.35)   
A4 = (0.0, 3,  0.1)   

# ---------------- RANGE INDEX MAPPING ----------------
# Maps anchor slot 0-3 from the ESP32 CSV to A1-A4 above.
# If position looks wrong, swap these around.
IDX_ANCHOR_1 = 0
IDX_ANCHOR_2 = 1
IDX_ANCHOR_3 = 2
IDX_ANCHOR_4 = 3

# ---------------- POSITION SMOOTHING ----------------
ALPHA_POS = 0.2   # lower = smoother, higher = more responsive

# ---------------- KICK DETECTION ----------------
KICK_THRESHOLD  = 20.0 #Acceleration threshold for kick
KICK_COOLDOWN_S = 1.0  #Seconds before another kick can be detected
KICK_FLASH_MS   = 500  #Duration for kick flash

# ---------------- VISUALISER ----------------
TRAIL_LENGTH  = 30
BUFFER_LEN    = 200
UPDATE_MS     = 20
SPEED_Y_MAX   = 12
ACCEL_Y_RANGE = 30
RANGE_Y_MAX   = 15.0
HEIGHT_Y_MAX  = 5.0   # max height shown on Z plot
