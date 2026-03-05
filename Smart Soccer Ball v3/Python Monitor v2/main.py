# ============================================================
#  main.py
# ============================================================

import sys
import time
import serial

import config
from trilaterate import trilaterate
from position_filter import PositionFilter
from kick_detector import KickDetector
from visualiser import Visualiser


class App:
    def __init__(self):
        try:
            self.ser = serial.Serial(config.PORT, config.BAUD, timeout=0.1)
            time.sleep(2)
            print(f"Connected to {config.PORT}")
        except Exception as e:
            print(f"Failed to open serial port {config.PORT}: {e}")
            sys.exit(1)

        self.pos_filter = PositionFilter()
        self.kick_det   = KickDetector()
        self.vis        = Visualiser(on_update=self.process)

    def process(self):
        try:
            if not self.ser.in_waiting:
                return None

            line = self.ser.readline().decode('utf-8', errors='ignore').strip()
            if not line:
                return None

            parts = line.split(",")
            if len(parts) != 9:
                return None

            values = [float(p) for p in parts]

            ranges             = values[0:3]
            ax, ay, az         = values[3], values[4], values[5]
            # gyro values[6:9] not used in this mode

            r1 = ranges[config.IDX_ANCHOR_1]
            r2 = ranges[config.IDX_ANCHOR_2]
            r3 = ranges[config.IDX_ANCHOR_3]

            pos = trilaterate(config.A1, config.A2, config.A3, r1, r2, r3)
            if pos is None:
                return None

            uwb_x, uwb_y = pos

            # Out-of-bounds filter
            ox, oy = config.FIELD_ORIGIN
            if not (ox - 1.0 <= uwb_x <= ox + config.FIELD_WIDTH  + 1.0 and
                    oy - 1.0 <= uwb_y <= oy + config.FIELD_HEIGHT + 1.0):
                return None

            x, y, vx, vy = self.pos_filter.update(uwb_x, uwb_y)

            kick = self.kick_det.update(ax, ay, az)

            return x, y, vx, vy, ax, ay, az, r1, r2, r3, kick, self.kick_det.kick_count

        except (ValueError, UnicodeDecodeError):
            return None
        except Exception as e:
            print(f"Error: {e}")
            return None

    def run(self):
        self.vis.run()


if __name__ == "__main__":
    App().run()
