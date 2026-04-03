# ============================================================
#  simulate.py  —  3D fake data for testing without hardware
# ============================================================

import math
import random
from position_filter import PositionFilter
from kick_detector import KickDetector
from visualiser import Visualiser
from trilaterate import trilaterate
import config

t = 0.0

# Orbit centre based on actual anchor positions
cx = (config.A1[0] + config.A2[0] + config.A3[0] + config.A4[0]) / 4
cy = (config.A1[1] + config.A2[1] + config.A3[1] + config.A4[1]) / 4


def fake_ranges_3d(x, y, z, noise=0.02):
    anchors = [config.A1, config.A2, config.A3, config.A4]
    ranges  = []
    for a in anchors:
        d = math.sqrt((x-a[0])**2 + (y-a[1])**2 + (z-a[2])**2)
        ranges.append(d + random.gauss(0, noise))
    return tuple(ranges)


class SimApp:
    def __init__(self):
        self.pos_filter = PositionFilter()
        self.kick_det   = KickDetector()
        self.vis        = Visualiser(on_update=self.process)

    def process(self):
        global t
        t += 0.05

        # Ball orbits the centre of the anchor layout
        x_raw = cx + 1.5 * math.cos(t * 0.5)
        y_raw = cy + 1.5 * math.sin(t * 0.5)
        z_raw = max(0.0, 0.4 * abs(math.sin(t * 1.5)))

        r1, r2, r3, r4 = fake_ranges_3d(x_raw, y_raw, z_raw)

        ax = random.gauss(0, 0.5)
        ay = random.gauss(0, 0.5)
        az = 9.81 + random.gauss(0, 0.3)
        # Simulate spin — faster when moving
        speed = math.sqrt((x_raw-config.A1[0])**2 + (y_raw-config.A1[1])**2)
        gx = random.gauss(0, 1.0) * speed
        gy = random.gauss(0, 1.0) * speed
        gz = random.gauss(0, 2.0) * speed
        kick = random.random() < 0.005

        pos = trilaterate(config.A1, config.A2, config.A3, config.A4,
                          r1, r2, r3, r4)
        if pos is None:
            print("[SIM] trilaterate returned None — check anchor coords in config.py")
            return None

        uwb_x, uwb_y, uwb_z = pos
        x, y, z, vx, vy, vz = self.pos_filter.update(uwb_x, uwb_y, uwb_z)

        if kick:
            self.kick_det.kick_count += 1

        return (x, y, z, vx, vy, vz,
                ax, ay, az,
                gx, gy, gz,
                r1, r2, r3, r4,
                kick, self.kick_det.kick_count)

    def run(self):
        self.vis.run()


if __name__ == "__main__":
    SimApp().run()