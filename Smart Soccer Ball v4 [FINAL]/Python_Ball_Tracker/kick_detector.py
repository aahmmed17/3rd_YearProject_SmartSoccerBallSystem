# ============================================================
#  kick_detector.py
# ============================================================

import math
import time
from config import KICK_THRESHOLD, KICK_COOLDOWN_S


class KickDetector:
    def __init__(self):
        self.kick_count  = 0
        self.last_kick_t = 0.0

    def update(self, ax, ay, az):
        magnitude = math.sqrt(ax**2 + ay**2 + az**2)
        now = time.time()

        if magnitude > KICK_THRESHOLD and now - self.last_kick_t > KICK_COOLDOWN_S:
            self.kick_count += 1
            self.last_kick_t = now
            return True

        return False

    def reset(self):
        self.kick_count  = 0
        self.last_kick_t = 0.0
