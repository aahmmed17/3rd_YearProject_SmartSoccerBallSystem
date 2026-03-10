# ============================================================
#  visualiser.py — two windows + arc speedometer
# ============================================================
#
#  Window 1 — Tracking:
#    Left  : 2D position plot, trail, velocity arrow, kick flash
#    Right : Arc/dial speedometer (m/s + km/h)
#
#  Window 2 — Sensor Data:
#    Top left  : Raw acceleration (ax, ay, az)
#    Top right : UWB ranges (r1, r2, r3)
#    Bottom    : Speed over time (full width)
#    Footer    : Stats bar + kick counter
# ============================================================

import math
from collections import deque

import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets, QtGui

from config import (
    A1, A2, A3,
    FIELD_WIDTH, FIELD_HEIGHT, FIELD_ORIGIN,
    TRAIL_LENGTH, BUFFER_LEN, UPDATE_MS,
    ACCEL_Y_RANGE, SPEED_Y_MAX, RANGE_Y_MAX,
    KICK_FLASH_MS, KICK_THRESHOLD
)


# ============================================================
#  Speedometer widget
# ============================================================

class Speedometer(QtWidgets.QWidget):
    MAX_SPEED_MS = 12.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self.speed_ms = 0.0
        self.setMinimumSize(280, 280)
        self.setStyleSheet("background-color: #1a1a2e;")

    def set_speed(self, speed_ms):
        self.speed_ms = max(0.0, speed_ms)
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        w, h  = self.width(), self.height()
        cx    = w // 2
        cy    = int(h * 0.52)
        radius = int(min(w, h) * 0.38)

        arc_rect = QtCore.QRectF(cx-radius, cy-radius, radius*2, radius*2)

        # Grey background arc
        pen = QtGui.QPen(QtGui.QColor(60, 60, 80), 14)
        pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawArc(arc_rect, 225*16, -270*16)

        # Coloured speed arc
        fraction = min(self.speed_ms / self.MAX_SPEED_MS, 1.0)
        if fraction < 0.5:
            r, g = int(255 * fraction * 2), 220
        else:
            r, g = 220, int(220 * (1 - (fraction - 0.5) * 2))
        pen2 = QtGui.QPen(QtGui.QColor(r, g, 40), 14)
        pen2.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
        painter.setPen(pen2)
        painter.drawArc(arc_rect, 225*16, int(-270 * fraction * 16))

        # Tick marks + labels
        for i in range(13):
            frac      = i / 12
            angle_rad = math.radians(225 - frac * 270)
            is_major  = (i % 3 == 0)
            inner_r   = radius - (18 if is_major else 10)

            x1 = cx + inner_r       * math.cos(angle_rad)
            y1 = cy - inner_r       * math.sin(angle_rad)
            x2 = cx + (radius - 2)  * math.cos(angle_rad)
            y2 = cy - (radius - 2)  * math.sin(angle_rad)

            painter.setPen(QtGui.QPen(QtGui.QColor(200, 200, 200), 2 if is_major else 1))
            painter.drawLine(QtCore.QPointF(x1, y1), QtCore.QPointF(x2, y2))

            if is_major:
                label_r = radius - 32
                lx = cx + label_r * math.cos(angle_rad)
                ly = cy - label_r * math.sin(angle_rad)
                painter.setFont(QtGui.QFont("Arial", 8))
                painter.setPen(QtGui.QPen(QtGui.QColor(180, 180, 180)))
                painter.drawText(
                    QtCore.QRectF(lx-14, ly-8, 28, 16),
                    QtCore.Qt.AlignmentFlag.AlignCenter,
                    str(round(frac * self.MAX_SPEED_MS))
                )

        # Needle
        needle_rad = math.radians(225 - fraction * 270)
        nx = cx + (radius - 22) * math.cos(needle_rad)
        ny = cy - (radius - 22) * math.sin(needle_rad)
        painter.setPen(QtGui.QPen(QtGui.QColor(255, 80, 80), 3,
                                   QtCore.Qt.PenStyle.SolidLine,
                                   QtCore.Qt.PenCapStyle.RoundCap))
        painter.drawLine(QtCore.QPointF(cx, cy), QtCore.QPointF(nx, ny))

        # Hub
        painter.setBrush(QtGui.QBrush(QtGui.QColor(255, 80, 80)))
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.drawEllipse(QtCore.QPointF(cx, cy), 7, 7)

        # m/s value
        painter.setFont(QtGui.QFont("Arial", 22, QtGui.QFont.Weight.Bold))
        painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255)))
        painter.drawText(
            QtCore.QRectF(cx-70, cy + radius*0.18, 140, 40),
            QtCore.Qt.AlignmentFlag.AlignCenter,
            f"{self.speed_ms:.2f}"
        )
        painter.setFont(QtGui.QFont("Arial", 10))
        painter.setPen(QtGui.QPen(QtGui.QColor(160, 160, 160)))
        painter.drawText(
            QtCore.QRectF(cx-40, cy + radius*0.18 + 36, 80, 20),
            QtCore.Qt.AlignmentFlag.AlignCenter, "m/s"
        )

        # km/h value
        painter.setFont(QtGui.QFont("Arial", 14, QtGui.QFont.Weight.Bold))
        painter.setPen(QtGui.QPen(QtGui.QColor(100, 200, 255)))
        painter.drawText(
            QtCore.QRectF(cx-60, cy + radius*0.18 + 60, 120, 30),
            QtCore.Qt.AlignmentFlag.AlignCenter,
            f"{self.speed_ms * 3.6:.1f} km/h"
        )

        painter.end()


# ============================================================
#  Visualiser — two windows
# ============================================================

class Visualiser:
    def __init__(self, on_update):
        self.on_update   = on_update
        self.flash_timer = 0

        self.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

        self._build_tracking_window()
        self._build_data_window()

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self._tick)
        self.timer.start(UPDATE_MS)

    # ---- Window 1 ----

    def _build_tracking_window(self):
        self.tracking_win = QtWidgets.QWidget()
        self.tracking_win.setWindowTitle("Ball Tracker — Position")
        self.tracking_win.resize(920, 520)
        self.tracking_win.setStyleSheet("background-color: #1a1a2e;")

        layout = QtWidgets.QHBoxLayout()
        self.tracking_win.setLayout(layout)

        # Position plot
        pos_widget = pg.GraphicsLayoutWidget()
        pos_widget.setBackground('#1a1a2e')
        layout.addWidget(pos_widget, stretch=3)

        self.pos_plot = pos_widget.addPlot(title="Ball Position")
        self.pos_plot.setAspectLocked(True)
        self.pos_plot.showGrid(x=True, y=True, alpha=0.3)
        self.pos_plot.setLabel('left', 'Y (m)')
        self.pos_plot.setLabel('bottom', 'X (m)')

        ox, oy = FIELD_ORIGIN
        margin = 0.5
        self.pos_plot.setXRange(ox - margin, ox + FIELD_WIDTH  + margin)
        self.pos_plot.setYRange(oy - margin, oy + FIELD_HEIGHT + margin)

        field = pg.RectROI((ox, oy), (FIELD_WIDTH, FIELD_HEIGHT),
                            pen=pg.mkPen('w', width=2))
        field.setAcceptedMouseButtons(QtCore.Qt.MouseButton.NoButton)
        self.pos_plot.addItem(field)

        for i, anchor in enumerate([A1, A2, A3]):
            self.pos_plot.plot([anchor[0]], [anchor[1]],
                               pen=None, symbol='s', symbolSize=12, symbolBrush='r')
            lbl = pg.TextItem(text=f"A{i+1}", color='w', anchor=(0.5, 1.5))
            lbl.setPos(anchor[0], anchor[1])
            self.pos_plot.addItem(lbl)

        self.x_trail = deque(maxlen=TRAIL_LENGTH)
        self.y_trail = deque(maxlen=TRAIL_LENGTH)
        self.trail_curve = self.pos_plot.plot(pen=pg.mkPen('y', width=2))
        self.tag_dot     = self.pos_plot.plot(pen=None, symbol='o',
                                               symbolSize=20, symbolBrush='b')

        self.vel_arrow = pg.ArrowItem(angle=0, tipAngle=30, headLen=20, tailLen=20,
                                       pen=pg.mkPen('g', width=2), brush='g')
        self.pos_plot.addItem(self.vel_arrow)

        self.kick_flash = self.pos_plot.plot(pen=None, symbol='o', symbolSize=44,
                                              symbolBrush=None,
                                              symbolPen=pg.mkPen('r', width=3))
        self.kick_flash.setVisible(False)

        # Right side — speedometer on top, stats panel below
        right_widget = QtWidgets.QWidget()
        right_widget.setStyleSheet("background-color: #1a1a2e;")
        right_layout = QtWidgets.QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)
        right_widget.setLayout(right_layout)

        # Speedometer
        self.speedo = Speedometer()
        right_layout.addWidget(self.speedo, stretch=3)

        # Stats panel
        self.stats_panel = QtWidgets.QFrame()
        self.stats_panel.setStyleSheet("""
            QFrame {
                background-color: #0d0d1f;
                border: 2px solid #4a90d9;
                border-radius: 10px;
            }
        """)
        stats_layout = QtWidgets.QVBoxLayout()
        stats_layout.setContentsMargins(16, 12, 16, 12)
        stats_layout.setSpacing(8)
        self.stats_panel.setLayout(stats_layout)

        # Panel title
        title_lbl = QtWidgets.QLabel("LIVE STATS")
        title_lbl.setStyleSheet(
            "color: #4a90d9; font-size: 11px; font-weight: bold; "
            "letter-spacing: 2px; border: none;"
        )
        title_lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        stats_layout.addWidget(title_lbl)

        # Divider
        divider = QtWidgets.QFrame()
        divider.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        divider.setStyleSheet("background-color: #4a90d9; border: none; max-height: 1px;")
        stats_layout.addWidget(divider)

        def make_stat_row(title, value_color="#ffffff"):
            row = QtWidgets.QHBoxLayout()
            title_lbl = QtWidgets.QLabel(title)
            title_lbl.setStyleSheet(
                "color: #8888bb; font-size: 11px; border: none;"
            )
            value_lbl = QtWidgets.QLabel("—")
            value_lbl.setStyleSheet(
                f"color: {value_color}; font-size: 15px; "
                f"font-weight: bold; border: none;"
            )
            value_lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
            row.addWidget(title_lbl)
            row.addWidget(value_lbl)
            stats_layout.addLayout(row)
            return value_lbl

        self.stat_pos   = make_stat_row("Position",  "#00e5ff")
        self.stat_speed = make_stat_row("Speed m/s", "#ffffff")
        self.stat_kmh   = make_stat_row("Speed km/h","#64b5f6")
        self.stat_r1    = make_stat_row("Range r1",  "#ef5350")
        self.stat_r2    = make_stat_row("Range r2",  "#66bb6a")
        self.stat_r3    = make_stat_row("Range r3",  "#26c6da")
        self.stat_kicks = make_stat_row("Kicks",     "#ff7043")

        right_layout.addWidget(self.stats_panel, stretch=2)
        layout.addWidget(right_widget, stretch=2)

        self.tracking_win.show()

    # ---- Window 2 ----

    def _build_data_window(self):
        self.data_win = pg.GraphicsLayoutWidget(show=True,
                                                 title="Ball Tracker — Sensor Data")
        self.data_win.resize(1100, 580)
        self.data_win.setBackground('#1a1a2e')

        # Row 1
        self.accel_plot = self.data_win.addPlot(title="Raw Acceleration (m/s²)")
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
        self.accel_plot.addItem(pg.InfiniteLine(
            pos=KICK_THRESHOLD, angle=0,
            pen=pg.mkPen('r', width=1, style=QtCore.Qt.PenStyle.DashLine)
        ))

        self.range_plot = self.data_win.addPlot(title="UWB Ranges (m)")
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

        # Row 2
        self.data_win.nextRow()
        self.speed_plot = self.data_win.addPlot(title="Speed over Time (m/s)",
                                                 colspan=2)
        self.speed_plot.showGrid(x=True, y=True, alpha=0.3)
        self.speed_plot.setYRange(0, SPEED_Y_MAX)
        self.speed_plot.setLabel('left', 'm/s')
        self.speed_buf = deque(maxlen=BUFFER_LEN)
        self.speed_curve = self.speed_plot.plot(pen=pg.mkPen('y', width=1))

        # Row 3 — removed (stats now live in tracking window)

    # ---- Tick ----

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

        # Tracking window
        self.x_trail.append(x)
        self.y_trail.append(y)
        self.trail_curve.setData(list(self.x_trail), list(self.y_trail))
        self.tag_dot.setData([x], [y])

        self.vel_arrow.setPos(x, y)
        if speed > 0.05:
            angle = math.degrees(math.atan2(vy, vx))
            self.vel_arrow.setStyle(angle=180 - angle)

        if kick:
            self.kick_flash.setData([x], [y])
            self.kick_flash.setVisible(True)
            self.flash_timer = KICK_FLASH_MS

        self.speedo.set_speed(speed)

        # Stats panel
        self.stat_pos.setText(f"x={x:.2f} m,  y={y:.2f} m")
        self.stat_speed.setText(f"{speed:.2f} m/s")
        self.stat_kmh.setText(f"{speed*3.6:.1f} km/h")
        self.stat_r1.setText(f"{r1:.2f} m")
        self.stat_r2.setText(f"{r2:.2f} m")
        self.stat_r3.setText(f"{r3:.2f} m")
        self.stat_kicks.setText(str(kick_count))
        self.ax_buf.append(ax);  self.ay_buf.append(ay);  self.az_buf.append(az)
        self.ax_curve.setData(list(self.ax_buf))
        self.ay_curve.setData(list(self.ay_buf))
        self.az_curve.setData(list(self.az_buf))

        self.r1_buf.append(r1);  self.r2_buf.append(r2);  self.r3_buf.append(r3)
        self.r1_curve.setData(list(self.r1_buf))
        self.r2_curve.setData(list(self.r2_buf))
        self.r3_curve.setData(list(self.r3_buf))

        self.speed_buf.append(speed)
        self.speed_curve.setData(list(self.speed_buf))

    def run(self):
        import sys
        sys.exit(self.app.exec())
