# ============================================================
#  visualiser.py
# ============================================================

import math
from collections import deque

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets

from config import (
    A1, A2, A3,
    FIELD_WIDTH, FIELD_HEIGHT, FIELD_ORIGIN,
    TRAIL_LENGTH, BUFFER_LEN, UPDATE_MS,
    ACCEL_Y_RANGE, SPEED_Y_MAX, RANGE_Y_MAX,
    KICK_FLASH_MS, KICK_THRESHOLD
)


class Visualiser:
    def __init__(self, on_update):
        self.on_update   = on_update
        self.flash_timer = 0

        self.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        self.win = pg.GraphicsLayoutWidget(show=True, title="UWB Ball Tracker")
        self.win.resize(1200, 850)

        self._build_position_plot()
        self._build_accel_plot()
        self.win.nextRow()
        self._build_speed_plot()
        self._build_range_plot()
        self.win.nextRow()
        self._build_stats_label()

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self._tick)
        self.timer.start(UPDATE_MS)

    def _build_position_plot(self):
        self.pos_plot = self.win.addPlot(title="Ball Position")
        self.pos_plot.setAspectLocked(True)
        self.pos_plot.showGrid(x=True, y=True, alpha=0.3)
        self.pos_plot.setLabel('left', 'Y (m)')
        self.pos_plot.setLabel('bottom', 'X (m)')

        ox, oy = FIELD_ORIGIN
        margin = 0.5
        self.pos_plot.setXRange(ox - margin, ox + FIELD_WIDTH  + margin)
        self.pos_plot.setYRange(oy - margin, oy + FIELD_HEIGHT + margin)

        field = pg.RectROI(
            (ox, oy), (FIELD_WIDTH, FIELD_HEIGHT),
            pen=pg.mkPen('w', width=2)
        )
        field.setAcceptedMouseButtons(QtCore.Qt.MouseButton.NoButton)
        self.pos_plot.addItem(field)

        for i, anchor in enumerate([A1, A2, A3]):
            self.pos_plot.plot(
                [anchor[0]], [anchor[1]],
                pen=None, symbol='s', symbolSize=12, symbolBrush='r'
            )
            lbl = pg.TextItem(text=f"A{i+1}", color='w', anchor=(0.5, 1.5))
            lbl.setPos(anchor[0], anchor[1])
            self.pos_plot.addItem(lbl)

        self.x_trail = deque(maxlen=TRAIL_LENGTH)
        self.y_trail = deque(maxlen=TRAIL_LENGTH)
        self.trail_curve = self.pos_plot.plot(pen=pg.mkPen('y', width=2))
        self.tag_dot     = self.pos_plot.plot(
            pen=None, symbol='o', symbolSize=20, symbolBrush='b'
        )

        self.vel_arrow = pg.ArrowItem(
            angle=0, tipAngle=30, headLen=20, tailLen=20,
            pen=pg.mkPen('g', width=2), brush='g'
        )
        self.pos_plot.addItem(self.vel_arrow)

        self.kick_flash = self.pos_plot.plot(
            pen=None, symbol='o', symbolSize=44, symbolBrush=None,
            symbolPen=pg.mkPen('r', width=3)
        )
        self.kick_flash.setVisible(False)

    def _build_accel_plot(self):
        self.accel_plot = self.win.addPlot(title="Raw Acceleration (m/s²)")
        self.accel_plot.addLegend()
        self.accel_plot.showGrid(x=True, y=True, alpha=0.3)
        self.accel_plot.setYRange(-ACCEL_Y_RANGE, ACCEL_Y_RANGE)
        self.accel_plot.setLabel('left', 'm/s²')

        self.ax_buf = deque(maxlen=BUFFER_LEN)
        self.ay_buf = deque(maxlen=BUFFER_LEN)
        self.az_buf = deque(maxlen=BUFFER_LEN)
        self.ax_curve = self.accel_plot.plot(pen=pg.mkPen('r', width=1), name='ax')
        self.ay_curve = self.accel_plot.plot(pen=pg.mkPen('c', width=1), name='ay')
        self.az_curve = self.accel_plot.plot(pen=pg.mkPen('y', width=1), name='az')

        thresh = pg.InfiniteLine(
            pos=KICK_THRESHOLD, angle=0,
            pen=pg.mkPen('r', width=1, style=QtCore.Qt.PenStyle.DashLine)
        )
        self.accel_plot.addItem(thresh)

    def _build_speed_plot(self):
        self.speed_plot = self.win.addPlot(title="Speed (m/s)")
        self.speed_plot.showGrid(x=True, y=True, alpha=0.3)
        self.speed_plot.setYRange(0, SPEED_Y_MAX)
        self.speed_plot.setLabel('left', 'm/s')
        self.speed_buf = deque(maxlen=BUFFER_LEN)
        self.speed_curve = self.speed_plot.plot(pen=pg.mkPen('y', width=1))

    def _build_range_plot(self):
        self.range_plot = self.win.addPlot(title="UWB Ranges (m)")
        self.range_plot.addLegend()
        self.range_plot.showGrid(x=True, y=True, alpha=0.3)
        self.range_plot.setYRange(0, RANGE_Y_MAX)
        self.range_plot.setLabel('left', 'metres')
        self.r1_buf = deque(maxlen=BUFFER_LEN)
        self.r2_buf = deque(maxlen=BUFFER_LEN)
        self.r3_buf = deque(maxlen=BUFFER_LEN)
        self.r1_curve = self.range_plot.plot(pen=pg.mkPen('r', width=1), name='r1')
        self.r2_curve = self.range_plot.plot(pen=pg.mkPen('g', width=1), name='r2')
        self.r3_curve = self.range_plot.plot(pen=pg.mkPen('c', width=1), name='r3')

    def _build_stats_label(self):
        self.stats_label = pg.LabelItem(justify='left')
        self.win.addItem(self.stats_label, colspan=2)

    def _tick(self):
        result = self.on_update()

        if self.flash_timer > 0:
            self.flash_timer -= UPDATE_MS
            if self.flash_timer <= 0:
                self.kick_flash.setVisible(False)

        if result is None:
            return

        x, y, vx, vy, ax, ay, az, r1, r2, r3, kick, kick_count = result
        speed = math.sqrt(vx**2 + vy**2)

        # Position
        self.x_trail.append(x)
        self.y_trail.append(y)
        self.trail_curve.setData(list(self.x_trail), list(self.y_trail))
        self.tag_dot.setData([x], [y])

        # Velocity arrow
        self.vel_arrow.setPos(x, y)
        if speed > 0.05:
            angle = math.degrees(math.atan2(vy, vx))
            self.vel_arrow.setStyle(angle=180 - angle)

        # Kick flash
        if kick:
            self.kick_flash.setData([x], [y])
            self.kick_flash.setVisible(True)
            self.flash_timer = KICK_FLASH_MS

        # Accel
        self.ax_buf.append(ax)
        self.ay_buf.append(ay)
        self.az_buf.append(az)
        self.ax_curve.setData(list(self.ax_buf))
        self.ay_curve.setData(list(self.ay_buf))
        self.az_curve.setData(list(self.az_buf))

        # Speed
        self.speed_buf.append(speed)
        self.speed_curve.setData(list(self.speed_buf))

        # Ranges
        self.r1_buf.append(r1)
        self.r2_buf.append(r2)
        self.r3_buf.append(r3)
        self.r1_curve.setData(list(self.r1_buf))
        self.r2_curve.setData(list(self.r2_buf))
        self.r3_curve.setData(list(self.r3_buf))

        # Stats
        self.stats_label.setText(
            f"  Position: x={x:.3f} m, y={y:.3f} m   |   "
            f"Speed: {speed:.2f} m/s   |   "
            f"Ranges: r1={r1:.2f}, r2={r2:.2f}, r3={r3:.2f} m   |   "
            f"Kicks: {kick_count}"
        )

    def run(self):
        import sys
        sys.exit(self.app.exec())
