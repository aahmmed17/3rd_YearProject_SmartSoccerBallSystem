# ============================================================
#  trilaterate.py  —  3D trilateration with 4 anchors
# ============================================================
#
#  With 4 anchors in 3D we have an over-determined system
#  (4 equations, 3 unknowns). We use least-squares via
#  numpy to get the best-fit solution rather than picking
#  3 anchors and discarding the 4th.
#
#  Each sphere equation:
#    (x-xi)^2 + (y-yi)^2 + (z-zi)^2 = ri^2
#
#  Subtracting anchor 1's equation from anchors 2, 3, 4
#  linearises the system into Ax = b form.
# ============================================================

import numpy as np

def trilaterate(p1, p2, p3, p4, r1, r2, r3, r4):
    """
    Solve 3D position from 4 anchor positions and ranges.

    Args:
        p1..p4 : (x, y, z) tuples for each anchor
        r1..r4 : measured ranges to each anchor (metres)

    Returns:
        (x, y, z) or None if system is degenerate
    """
    anchors = [p1, p2, p3, p4]
    ranges  = [r1, r2, r3, r4]

    x1, y1, z1 = p1

    # Build linearised system by subtracting anchor 1's equation
    # from each of the remaining anchors
    A_rows = []
    b_rows = []

    for i in range(1, 4):
        xi, yi, zi = anchors[i]
        ri = ranges[i]

        A_rows.append([
            2 * (xi - x1),
            2 * (yi - y1),
            2 * (zi - z1)
        ])
        b_rows.append(
            r1**2 - ri**2
            - x1**2 + xi**2
            - y1**2 + yi**2
            - z1**2 + zi**2
        )

    A = np.array(A_rows, dtype=float)
    b = np.array(b_rows, dtype=float)

    # Check for degenerate geometry (anchors coplanar/colinear)
    if abs(np.linalg.det(A)) < 1e-6:
        return None

    try:
        pos, _, _, _ = np.linalg.lstsq(A, b, rcond=None)
        return float(pos[0]), float(pos[1]), float(pos[2])
    except np.linalg.LinAlgError:
        return None
