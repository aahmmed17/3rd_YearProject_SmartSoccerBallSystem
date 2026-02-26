import sys
import serial
import time
from collections import deque

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets

# ---------------- SERIAL CONFIG ----------------
PORT = "COM10"
BAUD = 115200
# ------------------------------------------------

# ---------------- ANCHOR POSITIONS (meters) ----------------
Anch1_x, Anch1_y = 0.0, 0.0
Anch2_x, Anch2_y = -3.6,  0.0
Anch3_x, Anch3_y = 0.0, -2.2

A1 = (Anch1_x, Anch1_y)
A2 = (Anch2_x, Anch2_y)
A3 = (Anch3_x, Anch3_y)

# Mapped based on tested logic:
IDX_ANCHOR_1 = 2
IDX_ANCHOR_2 = 0
IDX_ANCHOR_3 = 1
# ----------------------------------------------------

# ---------------- EMA FILTER SETTINGS ----------------
ALPHA = 0.15   # 0.1 = heavy smoothing, 0.5 = light smoothing
# -----------------------------------------------------

def trilaterate(p1, p2, p3, r1, r2, r3):
    x1, y1 = p1
    x2, y2 = p2
    x3, y3 = p3

    A = 2 * (x2 - x1)
    B = 2 * (y2 - y1)
    C = r1**2 - r2**2 - x1**2 + x2**2 - y1**2 + y2**2

    D = 2 * (x3 - x1)
    E = 2 * (y3 - y1)
    F = r1**2 - r3**2 - x1**2 + x3**2 - y1**2 + y3**2

    denom = A * E - B * D
    if abs(denom) < 1e-6:
        return None

    x = (C * E - B * F) / denom
    y = (A * F - C * D) / denom
    return x, y

class EMAFilter:
    def __init__(self, alpha):
        self.alpha = alpha
        self.x = None
        self.y = None

    def update(self, new_x, new_y):
        if self.x is None:
            self.x = new_x
            self.y = new_y
        else:
            self.x = self.alpha * new_x + (1 - self.alpha) * self.x
            self.y = self.alpha * new_y + (1 - self.alpha) * self.y
        return self.x, self.y

class UWBTracker:
    def __init__(self):
        # Open serial connection
        try:
            self.ser = serial.Serial(PORT, BAUD, timeout=0.1)
            time.sleep(2)
        except Exception as e:
            print(f"Error opening serial port {PORT}: {e}")
            sys.exit(1)

        self.filter = EMAFilter(ALPHA)

        self.app = QtWidgets.QApplication(sys.argv)
        self.win = pg.GraphicsLayoutWidget(show=True, title="UWB Live Ball Tracker")
        self.win.resize(900, 700)

        self.plot = self.win.addPlot()
        self.plot.setAspectLocked(True)
        self.plot.showGrid(x=True, y=True, alpha=0.3)

        # -------- Dynamic Map Sizing --------
        anchors = [A1, A2, A3]
        xs = [a[0] for a in anchors]
        ys = [a[1] for a in anchors]

        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)

        margin = 1.0
        self.plot.setXRange(min_x - margin, max_x + margin)
        self.plot.setYRange(min_y - margin, max_y + margin)

        width = max_x - min_x
        height = max_y - min_y

        # FIXED: RectROI handling for newer pyqtgraph versions
        self.room = pg.RectROI((min_x, min_y), (width, height), pen=pg.mkPen('w', width=2))
        # Disable interaction (moving/scaling)
        self.room.setAcceptedMouseButtons(QtCore.Qt.MouseButton.NoButton)
        self.plot.addItem(self.room)

        # -------- Anchors Visualization --------
        for i, anchor in enumerate(anchors):
            self.plot.plot([anchor[0]], [anchor[1]],
                          pen=None, symbol='s', symbolSize=12, symbolBrush='r')
            label = pg.TextItem(text=f"A{i+1}", color='w', anchor=(0.5, 1.5))
            label.setPos(anchor[0], anchor[1])
            self.plot.addItem(label)

        # -------- Trail & Ball --------
        self.trail_length = 60
        self.x_trail = deque(maxlen=self.trail_length)
        self.y_trail = deque(maxlen=self.trail_length)

        self.trail_curve = self.plot.plot(pen=pg.mkPen(color='y', width=2))
        self.tag_dot = self.plot.plot(pen=None, symbol='o', symbolSize=20, symbolBrush='b')

        # -------- Timer --------
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_data)
        self.timer.start(20)

        print("Tracker running...")
        sys.exit(self.app.exec())

    def update_data(self):
        try:
            if self.ser.in_waiting:
                line = self.ser.readline().decode().strip()
                if not line:
                    return

                parts = line.split(",")
                if len(parts) != 3:
                    return

                ranges = [float(p) for p in parts]

                r1 = ranges[IDX_ANCHOR_1]
                r2 = ranges[IDX_ANCHOR_2]
                r3 = ranges[IDX_ANCHOR_3]

                pos = trilaterate(A1, A2, A3, r1, r2, r3)
                if pos is None:
                    return

                x_raw, y_raw = pos

                # -------- Apply EMA Filter --------
                x, y = self.filter.update(x_raw, y_raw)

                self.x_trail.append(x)
                self.y_trail.append(y)

                self.trail_curve.setData(list(self.x_trail), list(self.y_trail))
                self.tag_dot.setData([x], [y])

        except Exception as e:
            # Silent fail for minor parsing errors
            pass

if __name__ == "__main__":
    UWBTracker()
