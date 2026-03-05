# ============================================================
#  position_filter.py  —  EMA smoothing on UWB position
# ============================================================

import time
from config import ALPHA_POS


class PositionFilter:
    """
    Simple EMA filter on UWB trilaterated position.
    Also back-computes velocity from position change over time.
    No IMU involvement — clean and stable.
    """

    def __init__(self):
        self.x  = None;  self.y  = None
        self.vx = 0.0;   self.vy = 0.0
        self.last_time = None

    def update(self, uwb_x, uwb_y):
        now = time.time()

        if self.x is None:
            self.x = uwb_x
            self.y = uwb_y
            self.last_time = now
            return self.x, self.y, self.vx, self.vy

        dt = now - self.last_time
        self.last_time = now

        if dt <= 0 or dt > 0.5:
            dt = 0.05

        prev_x, prev_y = self.x, self.y

        # EMA correction
        self.x = ALPHA_POS * uwb_x + (1 - ALPHA_POS) * self.x
        self.y = ALPHA_POS * uwb_y + (1 - ALPHA_POS) * self.y

        # Velocity from position change
        self.vx = (self.x - prev_x) / dt
        self.vy = (self.y - prev_y) / dt

        return self.x, self.y, self.vx, self.vy

    def reset(self):
        self.x  = None;  self.y  = None
        self.vx = 0.0;   self.vy = 0.0
        self.last_time = None
