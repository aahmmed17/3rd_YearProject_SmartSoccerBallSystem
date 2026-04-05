# ============================================================
#  main.py  —  3D tracking with 4 anchors
# ============================================================

import sys
import time
import serial
import math

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

    def _parse_serial(self):
        """
        Read one CSV line from serial.
        Expected format (10 values):
          r1,r2,r3,r4,ax,ay,az,gx,gy,gz
        Returns (r1,r2,r3,r4,ax,ay,az,gx,gy,gz) or None.
        """
        if not self.ser.in_waiting:
            return None

        line = self.ser.readline().decode('utf-8', errors='ignore').strip()
        if not line:
            return None

        parts = line.split(",")
        if len(parts) != 10:
            return None

        values = [float(p) for p in parts]

        r1 = values[config.IDX_ANCHOR_1]
        r2 = values[config.IDX_ANCHOR_2]
        r3 = values[config.IDX_ANCHOR_3]
        r4 = values[config.IDX_ANCHOR_4]
        ax, ay, az = values[4], values[5], values[6]
        gx, gy, gz = values[7], values[8], values[9]

        return r1, r2, r3, r4, ax, ay, az, gx, gy, gz

    def process(self):
        try:
            parsed = self._parse_serial()
            if parsed is None:
                return None

            r1, r2, r3, r4, ax, ay, az, gx, gy, gz = parsed

            # 1. Calculate raw position via trilateration
            pos = trilaterate(config.A1, config.A2, config.A3, config.A4,
                              r1, r2, r3, r4)
            if pos is None:
                return None

            uwb_x, uwb_y, uwb_z = pos

            # ---- 2. OUT OF BOUNDS CHECK----
            # Define limit (e.g. 10.0 meters from the center)
            MAX_DISTANCE = 7.0 
            
            # Calculate distance from origin (0,0,0)
            distance = math.sqrt(uwb_x**2 + uwb_y**2 + uwb_z**2)
            
            # If the calculated point is too far away, ignore this frame
            if distance > MAX_DISTANCE:
                # Optional: print(f"Outlier ignored: {distance:.2f}m")
                return None
            # ---------------------------------------

            # 3. If sane, pass to filters
            x, y, z, vx, vy, vz = self.pos_filter.update(uwb_x, uwb_y, uwb_z)
            kick = self.kick_det.update(ax, ay, az)

            return (x, y, z, vx, vy, vz,
                    ax, ay, az,
                    gx, gy, gz,
                    r1, r2, r3, r4,
                    kick, self.kick_det.kick_count)

        except (ValueError, UnicodeDecodeError):
            return None
        except Exception as e:
            print(f"Error: {e}")
            return None

    def run(self):
        self.vis.run()


if __name__ == "__main__":
    App().run()
