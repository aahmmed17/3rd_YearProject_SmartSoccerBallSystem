# ============================================================
#  visualiser_3d.py  —  3D OpenGL tracking window
# ============================================================
#
#  Shows:
#    - Ball trail (coloured line)
#    - Ball sphere
#    - Spinning cube indicating ball spin rate
#    - Anchor positions (labelled cubes)
#    - Anchor bounding cuboid (wireframe)
#    - Velocity arrow
#    - Kick flash (red ring)
#    - Ground plane grid
# ============================================================

import math
import numpy as np
from collections import deque

import pyqtgraph as pg
import pyqtgraph.opengl as gl
from pyqtgraph.Qt import QtCore, QtGui, QtWidgets

from config import (
    A1, A2, A3, A4,
    TRAIL_LENGTH, KICK_FLASH_MS, UPDATE_MS
)


class Visualiser3D:
    def __init__(self, widget=None):
        if widget is not None:
            self.win = widget
            self._owns_window = False
        else:
            self.win = gl.GLViewWidget()
            self.win.setWindowTitle("Ball Tracker — 3D View")
            self.win.resize(900, 700)
            self.win.setCameraPosition(distance=10, elevation=25, azimuth=45)
            self.win.setBackgroundColor("#d3f7b6")
            self.win.show()
            self._owns_window = True

        self._build_ground_grid()
        self._build_anchor_cuboid()
        self._build_anchors()
        self._build_trail()
        self._build_ball()
        self._build_spin_cube()
        self._build_velocity_arrow()
        self._build_kick_flash()

        self.flash_timer  = 0
        self._spin_angle  = 0.0
        self._ball_pos    = np.array([0.0, 0.0, 0.0])

    # --------------------------------------------------------
    #  Ground grid
    # --------------------------------------------------------

    def _build_ground_grid(self):
        anchors = [A1, A2, A3, A4]
        xs = [a[0] for a in anchors]
        ys = [a[1] for a in anchors]
        cx = (max(xs) + min(xs)) / 2
        cy = (max(ys) + min(ys)) / 2
        span = max(max(xs)-min(xs), max(ys)-min(ys)) + 3.0

        grid = gl.GLGridItem()
        grid.setSize(span, span)
        grid.setSpacing(1, 1)
        grid.translate(cx, cy, 0)
        grid.setColor((60, 60, 100, 120))
        self.win.addItem(grid)

    # --------------------------------------------------------
    #  Anchor bounding cuboid
    # --------------------------------------------------------

    def _build_anchor_cuboid(self):
        """
        Draw a wireframe box whose corners are at the XY extents
        of the anchors, with Z going from 0 (floor) to max anchor height.
        """
        anchors = [A1, A2, A3, A4]
        xs = [a[0] for a in anchors]
        ys = [a[1] for a in anchors]
        zs = [a[2] for a in anchors]

        x0, x1 = min(xs), max(xs)
        y0, y1 = min(ys), max(ys)
        z0, z1 = 0.0, max(zs)          # floor to highest anchor

        # 8 corners of the box
        corners = np.array([
            [x0, y0, z0], [x1, y0, z0],
            [x1, y1, z0], [x0, y1, z0],
            [x0, y0, z1], [x1, y0, z1],
            [x1, y1, z1], [x0, y1, z1],
        ], dtype=float)

        # 12 edges as pairs of corner indices
        edges = [
            (0,1),(1,2),(2,3),(3,0),   # bottom face
            (4,5),(5,6),(6,7),(7,4),   # top face
            (0,4),(1,5),(2,6),(3,7),   # verticals
        ]

        for a, b in edges:
            line = gl.GLLinePlotItem(
                pos=np.array([corners[a], corners[b]]),
                color=(0.0, 0.0, 0.0, 1),
                width=1,
                antialias=True
            )
            self.win.addItem(line)

    # --------------------------------------------------------
    #  Anchors
    # --------------------------------------------------------

    def _build_anchors(self):
        anchors = [A1, A2, A3, A4]
        colours = [
            (255,  80,  80, 255),
            (255,  80,  80, 255),
            (255,  80,  80, 255),
            (255,  80,  80, 255),
        ]
        for i, (anchor, col) in enumerate(zip(anchors, colours)):
            x, y, z = anchor

            cube = gl.GLBoxItem(size=QtGui.QVector3D(0.15, 0.15, 0.15))
            cube.setColor(col)
            cube.translate(x - 0.075, y - 0.075, z - 0.075)
            self.win.addItem(cube)

            line_pts = np.array([[x, y, 0], [x, y, z]], dtype=float)
            line = gl.GLLinePlotItem(
                pos=line_pts,
                color=(1.0, 1.0, 1.0, 0.25),
                width=1,
                antialias=True
            )
            self.win.addItem(line)

            try:
                label = gl.GLTextItem(
                    pos=np.array([x, y, z + 0.2]),
                    text=f"A{i+1}",
                    color=QtGui.QColor(*col)
                )
                self.win.addItem(label)
            except AttributeError:
                pass

    # --------------------------------------------------------
    #  Trail
    # --------------------------------------------------------

    def _build_trail(self):
        self.trail_x = deque(maxlen=TRAIL_LENGTH)
        self.trail_y = deque(maxlen=TRAIL_LENGTH)
        self.trail_z = deque(maxlen=TRAIL_LENGTH)

        self.trail_item = gl.GLLinePlotItem(
            pos=np.zeros((2, 3)),
            width=3,
            antialias=True,
            mode='line_strip'
        )
        self.win.addItem(self.trail_item)

    def _trail_colour_array(self, n):
        colours = np.zeros((n, 4), dtype=float)
        for i in range(n):
            alpha = i / max(n - 1, 1)
            colours[i] = [1.0, 0.85, 0.0, alpha * 0.9]
        return colours

    # --------------------------------------------------------
    #  Ball sphere
    # --------------------------------------------------------

    def _build_ball(self):
        sphere = gl.MeshData.sphere(rows=12, cols=12, radius=0.12)
        self.ball_mesh = gl.GLMeshItem(
            meshdata=sphere,
            smooth=True,
            color=(0.2, 255, 255, 0),
            shader='shaded',
            glOptions='opaque'
        )
        self.win.addItem(self.ball_mesh)

    # --------------------------------------------------------
    #  Spin cube — small transparent wireframe that rotates
    #  at a rate proportional to gyro magnitude
    # --------------------------------------------------------

    def _build_spin_cube(self):
        self.spin_cube = gl.GLBoxItem(
            size=QtGui.QVector3D(0.22, 0.22, 0.22)
        )
        self.spin_cube.setColor((0.9, 0.4, 1.0, 0.35))
        self.win.addItem(self.spin_cube)
        self._spin_angle = 0.0

    # --------------------------------------------------------
    #  Velocity arrow
    # --------------------------------------------------------

    def _build_velocity_arrow(self):
        self.arrow_item = gl.GLLinePlotItem(
            pos=np.zeros((2, 3)),
            color=(0.0, 1.0, 0.4, 1.0),
            width=4,
            antialias=True
        )
        self.win.addItem(self.arrow_item)
        self.arrow_item.setVisible(False)

    # --------------------------------------------------------
    #  Kick flash ring
    # --------------------------------------------------------

    def _build_kick_flash(self):
        n = 32
        theta = np.linspace(0, 2 * math.pi, n)
        ring = np.zeros((n, 3))
        ring[:, 0] = 0.4 * np.cos(theta)
        ring[:, 1] = 0.4 * np.sin(theta)

        self.kick_ring = gl.GLLinePlotItem(
            pos=ring,
            color=(1.0, 0.2, 0.2, 1.0),
            width=3,
            antialias=True,
            mode='line_strip'
        )
        self.win.addItem(self.kick_ring)
        self.kick_ring.setVisible(False)
        self._kick_pos = np.array([0.0, 0.0, 0.0])

    # --------------------------------------------------------
    #  Update
    # --------------------------------------------------------

    def update(self, x, y, z, vx, vy, vz, kick, kick_count, spin=0.0):
        bz = max(0.0, z)
        speed = math.sqrt(vx**2 + vy**2 + vz**2)

        # ---- Trail ----
        self.trail_x.append(x)
        self.trail_y.append(y)
        self.trail_z.append(bz)
        n = len(self.trail_x)
        if n >= 2:
            pts = np.column_stack([
                list(self.trail_x),
                list(self.trail_y),
                list(self.trail_z)
            ])
            self.trail_item.setData(pos=pts, color=self._trail_colour_array(n))

        # ---- Ball + spin cube — move to ball position ----
        dx = x  - self._ball_pos[0]
        dy = y  - self._ball_pos[1]
        dz = bz - self._ball_pos[2]
        self.ball_mesh.translate(dx, dy, dz)

        # Spin cube: reset transform, move to ball, apply rotation
        self.spin_cube.resetTransform()
        # Rotate around Z axis at spin rate — angle accumulates each tick
        self._spin_angle += spin * (UPDATE_MS / 1000.0) * (180.0 / math.pi)
        self._spin_angle %= 360.0
        self.spin_cube.rotate(self._spin_angle, 0, 0, 1)
        self.spin_cube.translate(x - 0.11, y - 0.11, bz - 0.11)

        self._ball_pos = np.array([x, y, bz])

        # ---- Velocity arrow ----
        if speed > 0.1:
            scale = min(speed * 0.3, 1.5)
            end = np.array([x + vx/speed*scale,
                            y + vy/speed*scale,
                            bz + vz/speed*scale])
            self.arrow_item.setData(pos=np.array([[x, y, bz], end]))
            self.arrow_item.setVisible(True)
        else:
            self.arrow_item.setVisible(False)

        # ---- Kick flash ----
        if kick:
            self._kick_pos = np.array([x, y, bz])
            self.flash_timer = KICK_FLASH_MS

        if self.flash_timer > 0:
            self.flash_timer -= UPDATE_MS
            theta = np.linspace(0, 2 * math.pi, 32)
            ring = np.zeros((32, 3))
            ring[:, 0] = self._kick_pos[0] + 0.4 * np.cos(theta)
            ring[:, 1] = self._kick_pos[1] + 0.4 * np.sin(theta)
            ring[:, 2] = self._kick_pos[2]
            self.kick_ring.setData(pos=ring)
            self.kick_ring.setVisible(True)
            if self.flash_timer <= 0:
                self.kick_ring.setVisible(False)