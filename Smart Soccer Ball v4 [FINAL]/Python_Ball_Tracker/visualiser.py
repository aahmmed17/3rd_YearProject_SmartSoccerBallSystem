# ============================================================
#  visualiser.py  —  3D tracking, 4 anchors
# ============================================================
#
#  Window 1 — Tracking:
#    Left        : 2D top-down position plot (X/Y)
#    Centre-top  : Ball height over time (Z)
#    Right       : Arc speedometer + LIVE STATS panel
#
#  Window 2 — Sensor Data:
#    Top left    : Raw acceleration (ax, ay, az)
#    Top right   : UWB ranges (r1, r2, r3, r4)
#    Bottom      : Speed over time
# ============================================================

import math
import numpy as np
from collections import deque

import pyqtgraph as pg
import pyqtgraph.opengl as gl
from pyqtgraph.Qt import QtCore, QtWidgets, QtGui

from config import (
    A1, A2, A3, A4,
    TRAIL_LENGTH, BUFFER_LEN, UPDATE_MS,
    ACCEL_Y_RANGE, SPEED_Y_MAX, RANGE_Y_MAX,
    KICK_FLASH_MS, KICK_THRESHOLD
)
from visualiser_3d import Visualiser3D


# ============================================================
#  Speedometer widget
# ============================================================

class Speedometer(QtWidgets.QWidget):
    MAX_SPEED_MS = 12.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self.speed_ms = 0.0
        self.setMinimumSize(240, 240)
        self.setStyleSheet("background-color: #1a1a2e;")

    def set_speed(self, speed_ms):
        self.speed_ms = max(0.0, speed_ms)
        self.update()

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        w, h   = self.width(), self.height()
        cx     = w // 2
        cy     = int(h * 0.52)
        radius = int(min(w, h) * 0.38)

        arc_rect = QtCore.QRectF(cx-radius, cy-radius, radius*2, radius*2)

        pen = QtGui.QPen(QtGui.QColor(60, 60, 80), 14)
        pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawArc(arc_rect, 225*16, -270*16)

        fraction = min(self.speed_ms / self.MAX_SPEED_MS, 1.0)
        if fraction < 0.5:
            r, g = int(255 * fraction * 2), 220
        else:
            r, g = 220, int(220 * (1 - (fraction - 0.5) * 2))
        pen2 = QtGui.QPen(QtGui.QColor(r, g, 40), 14)
        pen2.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
        painter.setPen(pen2)
        painter.drawArc(arc_rect, 225*16, int(-270 * fraction * 16))

        for i in range(13):
            frac      = i / 12
            angle_rad = math.radians(225 - frac * 270)
            is_major  = (i % 3 == 0)
            inner_r   = radius - (18 if is_major else 10)

            x1 = cx + inner_r      * math.cos(angle_rad)
            y1 = cy - inner_r      * math.sin(angle_rad)
            x2 = cx + (radius - 2) * math.cos(angle_rad)
            y2 = cy - (radius - 2) * math.sin(angle_rad)

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

        needle_rad = math.radians(225 - fraction * 270)
        nx = cx + (radius - 22) * math.cos(needle_rad)
        ny = cy - (radius - 22) * math.sin(needle_rad)
        painter.setPen(QtGui.QPen(QtGui.QColor(255, 80, 80), 3,
                                   QtCore.Qt.PenStyle.SolidLine,
                                   QtCore.Qt.PenCapStyle.RoundCap))
        painter.drawLine(QtCore.QPointF(cx, cy), QtCore.QPointF(nx, ny))

        painter.setBrush(QtGui.QBrush(QtGui.QColor(255, 80, 80)))
        painter.setPen(QtCore.Qt.PenStyle.NoPen)
        painter.drawEllipse(QtCore.QPointF(cx, cy), 7, 7)

        painter.setFont(QtGui.QFont("Arial", 20, QtGui.QFont.Weight.Bold))
        painter.setPen(QtGui.QPen(QtGui.QColor(255, 255, 255)))
        painter.drawText(
            QtCore.QRectF(cx-60, cy + radius*0.18, 120, 36),
            QtCore.Qt.AlignmentFlag.AlignCenter,
            f"{self.speed_ms:.2f}"
        )
        painter.setFont(QtGui.QFont("Arial", 9))
        painter.setPen(QtGui.QPen(QtGui.QColor(160, 160, 160)))
        painter.drawText(
            QtCore.QRectF(cx-40, cy + radius*0.18 + 32, 80, 18),
            QtCore.Qt.AlignmentFlag.AlignCenter, "m/s"
        )
        painter.setFont(QtGui.QFont("Arial", 13, QtGui.QFont.Weight.Bold))
        painter.setPen(QtGui.QPen(QtGui.QColor(100, 200, 255)))
        painter.drawText(
            QtCore.QRectF(cx-60, cy + radius*0.18 + 52, 120, 26),
            QtCore.Qt.AlignmentFlag.AlignCenter,
            f"{self.speed_ms * 3.6:.1f} km/h"
        )
        painter.end()


# ============================================================
#  Visualiser
# ============================================================

class Visualiser:
    def __init__(self, on_update):
        self.on_update = on_update

        self.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

        self._build_tracking_window()
        self._build_data_window()
        self._build_2d_window()

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self._tick)
        self.timer.start(UPDATE_MS)

    # --------------------------------------------------------
    #  Window 1 — Tracking
    # --------------------------------------------------------

    def _build_tracking_window(self):

        def style_plot(plot, tick_size=12, title_size=13):
            for axis in ['left', 'bottom']:
                plot.getAxis(axis).setStyle(tickFont=QtGui.QFont('Arial', tick_size))
            plot.titleLabel.item.setFont(
                QtGui.QFont('Arial', title_size, QtGui.QFont.Weight.Bold))


        self.tracking_win = QtWidgets.QWidget()
        self.tracking_win.setWindowTitle("Ball Tracker — 3D Position")
        self.tracking_win.resize(1200, 620)
        self.tracking_win.setStyleSheet("background-color: #1a1a2e;")

        outer = QtWidgets.QHBoxLayout()
        outer.setContentsMargins(4, 4, 4, 4)
        outer.setSpacing(8)
        self.tracking_win.setLayout(outer)

        # ---- Left: 3D GL view embedded in window ----
        self.gl_widget = gl.GLViewWidget()
        self.gl_widget.setCameraPosition(distance=12, elevation=25, azimuth=45)
        self.gl_widget.setBackgroundColor("#cdcdf1")
        self.gl_widget.setMinimumSize(600, 500)
        outer.addWidget(self.gl_widget, stretch=4)

        # Build 3D scene inside the embedded widget
        self.view3d = Visualiser3D(widget=self.gl_widget)

        # ---- Centre: IMU orientation cube ----
        self.imu_gl = gl.GLViewWidget()
    
        self.imu_gl.setCameraPosition(distance=4, elevation=25, azimuth=45)
        self.imu_gl.setBackgroundColor("#2e2e42")
        self.imu_gl.setMinimumSize(200, 200)
        self.imu_gl.setMaximumWidth(240)
        outer.addWidget(self.imu_gl, stretch=1)

        # IMU cube axes for orientation reference
        self.imu_cube = gl.GLBoxItem(size=QtGui.QVector3D(1.0, 0.6, 0.4))
        # Use a bright, solid color to ensure it's not blending into the white background
        self.imu_cube.setColor((0.2, 0.5, 1.0, 1.0)) 
        
        # Add the item to the GL widget
        self.imu_gl.addItem(self.imu_cube)

        # Axis lines on IMU cube — X=red, Y=green, Z=blue
        for pts, col in [
            (np.array([[0,0,0],[0.8,0,0]]), (1,0,0,1)),
            (np.array([[0,0,0],[0,0.5,0]]), (0,1,0,1)),
            (np.array([[0,0,0],[0,0,0.4]]), (0.3,0.5,1,1)),
        ]:
            ax = gl.GLLinePlotItem(pos=pts, color=col, width=3, antialias=True)
            self.imu_gl.addItem(ax)

        self._imu_roll  = 0.0
        self._imu_pitch = 0.0
        self._imu_yaw   = 0.0

        # Kick flash placeholder (used by _tick for flash timer)
        self.flash_timer = 0

        # ---- Right: speedometer + stats ----
        right_widget = QtWidgets.QWidget()
        right_widget.setStyleSheet("background-color: #1a1a2e;")
        right_layout = QtWidgets.QVBoxLayout()
        right_layout.setContentsMargins(4, 4, 4, 4)
        right_layout.setSpacing(8)
        right_widget.setLayout(right_layout)
        outer.addWidget(right_widget, stretch=2)

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
        stats_layout.setContentsMargins(14, 10, 14, 10)
        stats_layout.setSpacing(6)
        self.stats_panel.setLayout(stats_layout)

        title_lbl = QtWidgets.QLabel("LIVE STATS")
        title_lbl.setStyleSheet(
            "color: #4a90d9; font-size: 12px; font-weight: bold; "
            "letter-spacing: 2px; border: none;")
        title_lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        stats_layout.addWidget(title_lbl)

        divider = QtWidgets.QFrame()
        divider.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        divider.setStyleSheet("background-color: #4a90d9; border: none; max-height: 1px;")
        stats_layout.addWidget(divider)

        def make_stat_row(title, value_color="#ffffff"):
            row = QtWidgets.QHBoxLayout()
            t = QtWidgets.QLabel(title)
            t.setStyleSheet("color: #8888bb; font-size: 11px; border: none;")
            v = QtWidgets.QLabel("—")
            v.setStyleSheet(
                f"color: {value_color}; font-size: 14px; font-weight: bold; border: none;")
            v.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight)
            row.addWidget(t)
            row.addWidget(v)
            stats_layout.addLayout(row)
            return v

        self.stat_pos    = make_stat_row("X / Y",     "#00e5ff")
        self.stat_height = make_stat_row("Height Z",  "#ff9800")
        self.stat_speed  = make_stat_row("Speed m/s", "#ffffff")
        self.stat_kmh    = make_stat_row("Speed km/h","#64b5f6")
        self.stat_vz     = make_stat_row("Vert. vel", "#ce93d8")
        self.stat_spin   = make_stat_row("Spin",      "#f48fb1")
        self.stat_r1     = make_stat_row("Range r1",  "#ef5350")
        self.stat_r2     = make_stat_row("Range r2",  "#66bb6a")
        self.stat_r3     = make_stat_row("Range r3",  "#26c6da")
        self.stat_r4     = make_stat_row("Range r4",  "#ffd54f")
        self.stat_kicks  = make_stat_row("Kicks",     "#ff7043")

        right_layout.addWidget(self.stats_panel, stretch=4)

        self.tracking_win.show()

    # --------------------------------------------------------
    #  Window 2 — Sensor Data
    # --------------------------------------------------------

    def _build_data_window(self):


        def style_plot(plot):
            font_tick  = QtGui.QFont('Arial', 14, QtGui.QFont.Weight.Bold)
            font_title = QtGui.QFont('Arial', 16)
            font_label = QtGui.QFont('Arial', 13)
            for axis in ['left', 'bottom']:
                plot.getAxis(axis).setStyle(tickFont=font_tick)
                plot.getAxis(axis).setTextPen(pg.mkPen('#1a1a2e'))
                plot.getAxis(axis).label.setFont(font_label)
                # Fix applied here:
                plot.getAxis(axis).label.setDefaultTextColor(QtGui.QColor('#1a1a2e'))
            plot.titleLabel.item.setFont(font_title)
            plot.titleLabel.item.setDefaultTextColor(QtGui.QColor('#1a1a2e'))

        self.data_win = pg.GraphicsLayoutWidget(show=True,
                                                 title="Ball Tracker — Sensor Data")
        self.data_win.resize(1200, 620)
        self.data_win.setBackground("#ffffff")

        # Row 1 — accel + gyro side by side
        self.accel_plot = self.data_win.addPlot(title="Acceleration (m/s²)")
        style_plot(self.accel_plot)

        self.accel_plot.addLegend()
        self.accel_plot.showGrid(x=True, y=True, alpha=0.3)
        self.accel_plot.setYRange(-ACCEL_Y_RANGE, ACCEL_Y_RANGE)
        self.accel_plot.setLabel('left', 'm/s²')
        self.ax_buf = deque(maxlen=BUFFER_LEN)
        self.ay_buf = deque(maxlen=BUFFER_LEN)
        self.az_buf = deque(maxlen=BUFFER_LEN)
        self.ax_curve = self.accel_plot.plot(pen=pg.mkPen('r', width=2), name='ax')
        self.ay_curve = self.accel_plot.plot(pen=pg.mkPen('c', width=2), name='ay')
        self.az_curve = self.accel_plot.plot(pen=pg.mkPen('y', width=2), name='az')
        self.accel_plot.addItem(pg.InfiniteLine(
            pos=KICK_THRESHOLD, angle=0,
            pen=pg.mkPen('r', width=1, style=QtCore.Qt.PenStyle.DashLine)
        ))

        self.gyro_plot = self.data_win.addPlot(title="Gyroscope (rad/s)")
        style_plot(self.gyro_plot)

        self.gyro_plot.addLegend()
        self.gyro_plot.showGrid(x=True, y=True, alpha=0.3)
        self.gyro_plot.setYRange(-20, 20)
        self.gyro_plot.setLabel('left', 'rad/s')
        self.gx_buf = deque(maxlen=BUFFER_LEN)
        self.gy_buf = deque(maxlen=BUFFER_LEN)
        self.gz_buf = deque(maxlen=BUFFER_LEN)
        self.gx_curve = self.gyro_plot.plot(pen=pg.mkPen("#fbff00", width=2), name='gx')
        self.gy_curve = self.gyro_plot.plot(pen=pg.mkPen("#00c0e2", width=2), name='gy')
        self.gz_curve = self.gyro_plot.plot(pen=pg.mkPen("#ff3300", width=2), name='gz')

        # Row 2 — ranges + speed side by side
        self.data_win.nextRow()
        self.range_plot = self.data_win.addPlot(title="UWB Ranges (m)")
        style_plot(self.range_plot)
        
        self.range_plot.addLegend()
        self.range_plot.showGrid(x=True, y=True, alpha=0.3)
        self.range_plot.setYRange(0, RANGE_Y_MAX)
        self.range_plot.setLabel('left', 'metres')
        self.r1_buf = deque(maxlen=BUFFER_LEN)
        self.r2_buf = deque(maxlen=BUFFER_LEN)
        self.r3_buf = deque(maxlen=BUFFER_LEN)
        self.r4_buf = deque(maxlen=BUFFER_LEN)
        self.r1_curve = self.range_plot.plot(pen=pg.mkPen('r',       width=2), name='r1')
        self.r2_curve = self.range_plot.plot(pen=pg.mkPen('g',       width=2), name='r2')
        self.r3_curve = self.range_plot.plot(pen=pg.mkPen('c',       width=2), name='r3')
        self.r4_curve = self.range_plot.plot(pen=pg.mkPen('#ffd54f', width=1), name='r4')

        self.speed_plot = self.data_win.addPlot(title="Speed over Time (m/s)")
        style_plot(self.speed_plot)

        self.speed_plot.showGrid(x=True, y=True, alpha=0.3)
        self.speed_plot.setYRange(0, SPEED_Y_MAX)
        self.speed_plot.setLabel('left', 'm/s')
        self.speed_buf = deque(maxlen=BUFFER_LEN)
        self.speed_curve = self.speed_plot.plot(pen=pg.mkPen('y', width=3))

    # --------------------------------------------------------
    #  Window 3 — 2D Top-Down
    # --------------------------------------------------------

    def _build_2d_window(self):
        def style_plot(plot, tick_size=12, title_size=13):
            for axis in ['left', 'bottom']:
                plot.getAxis(axis).setStyle(tickFont=QtGui.QFont('Arial', tick_size))
            plot.titleLabel.item.setFont(
                QtGui.QFont('Arial', title_size, QtGui.QFont.Weight.Bold))
            
        self.win_2d = pg.GraphicsLayoutWidget(show=True,
                                              title="Ball Tracker — Top-Down 2D")
        self.win_2d.resize(600, 600)
        self.win_2d.setBackground("#e1f1ca")

        self.pos_plot = self.win_2d.addPlot(title="Ball Position (Top-Down X/Y)")
        self.pos_plot.setAspectLocked(True)
        self.pos_plot.showGrid(x=True, y=True, alpha=0.3)
        self.pos_plot.setLabel('left',   'Y (m)')
        self.pos_plot.setLabel('bottom', 'X (m)')
        self.pos_plot.enableAutoRange()

        # Anchor markers
        anchor_colours = ['b', 'b', 'b', 'b']
        for i, (anchor, col) in enumerate(zip([A1, A2, A3, A4], anchor_colours)):
            self.pos_plot.plot([anchor[0]], [anchor[1]],
                               pen=None, symbol='s', symbolSize=12,
                               symbolBrush=col)
            lbl = pg.TextItem(
                text=f"A{i+1}\n({'gnd' if anchor[2] == 0 else f'z={anchor[2]}m'})",
                color='black', anchor=(0.5, 1.5)
            )
            lbl.setPos(anchor[0], anchor[1])
            self.pos_plot.addItem(lbl)

        # Trail + ball dot
        self.x_trail = deque(maxlen=TRAIL_LENGTH)
        self.y_trail = deque(maxlen=TRAIL_LENGTH)
        self.trail_curve = self.pos_plot.plot(pen=pg.mkPen('b', width=2))
        self.tag_dot     = self.pos_plot.plot(pen=None, symbol='o',
                                               symbolSize=18, symbolBrush='y')

        # Velocity arrow
        self.vel_arrow = pg.ArrowItem(angle=0, tipAngle=30, headLen=20, tailLen=20,
                                       pen=pg.mkPen('g', width=2), brush='g')
        self.pos_plot.addItem(self.vel_arrow)

        # Kick flash ring
        self.kick_flash = self.pos_plot.plot(pen=None, symbol='o', symbolSize=44,
                                              symbolBrush=None,
                                              symbolPen=pg.mkPen('r', width=3))
        self.kick_flash.setVisible(False)
        self.flash_timer_2d = 0

    # --------------------------------------------------------
    #  Tick
    # --------------------------------------------------------

    def _tick(self):
        result = self.on_update()

        if result is None:
            return

        # Unpack 3D result
        x, y, z, vx, vy, vz, ax, ay, az, gx, gy, gz, r1, r2, r3, r4, kick, kick_count = result

        speed_3d = math.sqrt(vx**2 + vy**2 + vz**2)
        speed_2d = math.sqrt(vx**2 + vy**2)
        spin     = math.sqrt(gx**2 + gy**2 + gz**2)  # rad/s

        # ---- 3D view ----
        self.view3d.update(x, y, z, vx, vy, vz, kick, kick_count, spin)

        # ---- 2D window ----
        self.x_trail.append(x)
        self.y_trail.append(y)
        self.trail_curve.setData(list(self.x_trail), list(self.y_trail))
        self.tag_dot.setData([x], [y])

        self.vel_arrow.setPos(x, y)
        if speed_2d > 0.05:
            angle = math.degrees(math.atan2(vy, vx))
            self.vel_arrow.setStyle(angle=180 - angle)

        if kick:
            self.kick_flash.setData([x], [y])
            self.kick_flash.setVisible(True)
            self.flash_timer_2d = KICK_FLASH_MS

        if self.flash_timer_2d > 0:
            self.flash_timer_2d -= UPDATE_MS
            if self.flash_timer_2d <= 0:
                self.kick_flash.setVisible(False)

        # ---- Speedometer ----
        self.speedo.set_speed(speed_3d)

        # ---- Stats panel ----
        self.stat_pos.setText(f"{x:.2f},  {y:.2f} m")
        self.stat_height.setText(f"{z:.2f} m")
        self.stat_speed.setText(f"{speed_3d:.2f} m/s")
        self.stat_kmh.setText(f"{speed_3d * 3.6:.1f} km/h")
        self.stat_vz.setText(f"{vz:+.2f} m/s")
        self.stat_spin.setText(f"{spin:.1f} rad/s")
        self.stat_r1.setText(f"{r1:.2f} m")
        self.stat_r2.setText(f"{r2:.2f} m")
        self.stat_r3.setText(f"{r3:.2f} m")
        self.stat_r4.setText(f"{r4:.2f} m")
        self.stat_kicks.setText(str(kick_count))

        # ---- Data window ----
        self.ax_buf.append(ax)
        self.ay_buf.append(ay)
        self.az_buf.append(az)
        self.ax_curve.setData(list(self.ax_buf))
        self.ay_curve.setData(list(self.ay_buf))
        self.az_curve.setData(list(self.az_buf))

        self.gx_buf.append(gx)
        self.gy_buf.append(gy)
        self.gz_buf.append(gz)
        self.gx_curve.setData(list(self.gx_buf))
        self.gy_curve.setData(list(self.gy_buf))
        self.gz_curve.setData(list(self.gz_buf))

        self.r1_buf.append(r1)
        self.r2_buf.append(r2)
        self.r3_buf.append(r3)
        self.r4_buf.append(r4)
        self.r1_curve.setData(list(self.r1_buf))
        self.r2_curve.setData(list(self.r2_buf))
        self.r3_curve.setData(list(self.r3_buf))
        self.r4_curve.setData(list(self.r4_buf))

        self.speed_buf.append(speed_3d)
        self.speed_curve.setData(list(self.speed_buf))

        # ---- IMU orientation cube ----
        # Integrate gyro to estimate orientation angles
        # 1. Update the accumulation variables
        dt = UPDATE_MS / 1000.0
        self._imu_roll  += gx * dt * (180.0 / math.pi)
        self._imu_pitch += gy * dt * (180.0 / math.pi)
        self._imu_yaw   += gz * dt * (180.0 / math.pi)

        # 2. CLEAR previous frame's transformations
        self.imu_cube.resetTransform()

        # 3. APPLY rotations in a stable order (Yaw -> Pitch -> Roll)
        self.imu_cube.rotate(self._imu_yaw,   0, 0, 1) # Rotate around Z
        self.imu_cube.rotate(self._imu_pitch, 0, 1, 0) # Rotate around Y
        self.imu_cube.rotate(self._imu_roll,  1, 0, 0) # Rotate around X

        # 4. CENTER the cube AFTER rotating it
        # This ensures it spins in place in the middle of the side panel
        self.imu_cube.translate(-0.5, -0.3, -0.2)

    def run(self):
        import sys
        sys.exit(self.app.exec())
