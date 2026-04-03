# ============================================================
#  position_filter.py  —  EMA smoothing on 3D UWB position
# ============================================================

import time
from config import ALPHA_POS


class PositionFilter:
    """
    EMA filter on trilaterated 3D position.
    Velocity back-computed from position change over dt.
    """

    def __init__(self):
        self.x  = None
        self.y  = None
        self.z  = None
        self.vx = 0.0
        self.vy = 0.0
        self.vz = 0.0
        self.last_time = None

    def update(self, uwb_x, uwb_y, uwb_z):
        now = time.time()

        if self.x is None:
            self.x = uwb_x
            self.y = uwb_y
            self.z = uwb_z
            self.last_time = now
            return self.x, self.y, self.z, self.vx, self.vy, self.vz

        dt = now - self.last_time
        self.last_time = now

        if dt <= 0 or dt > 0.5:
            dt = 0.05

        prev_x, prev_y, prev_z = self.x, self.y, self.z

        self.x = ALPHA_POS * uwb_x + (1 - ALPHA_POS) * self.x
        self.y = ALPHA_POS * uwb_y + (1 - ALPHA_POS) * self.y
        self.z = ALPHA_POS * uwb_z + (1 - ALPHA_POS) * self.z

        self.vx = (self.x - prev_x) / dt
        self.vy = (self.y - prev_y) / dt
        self.vz = (self.z - prev_z) / dt

        return self.x, self.y, self.z, self.vx, self.vy, self.vz

    def reset(self):
        self.x  = None
        self.y  = None
        self.z  = None
        self.vx = 0.0
        self.vy = 0.0
        self.vz = 0.0
        self.last_time = None
