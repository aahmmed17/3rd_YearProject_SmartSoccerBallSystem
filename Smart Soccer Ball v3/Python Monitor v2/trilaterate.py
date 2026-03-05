# ============================================================
#  trilaterate.py
# ============================================================

def trilaterate(p1, p2, p3, r1, r2, r3):
    x1, y1 = p1;  x2, y2 = p2;  x3, y3 = p3

    A = 2*(x2-x1);  B = 2*(y2-y1)
    C = r1**2 - r2**2 - x1**2 + x2**2 - y1**2 + y2**2

    D = 2*(x3-x1);  E = 2*(y3-y1)
    F = r1**2 - r3**2 - x1**2 + x3**2 - y1**2 + y3**2

    denom = A*E - B*D
    if abs(denom) < 1e-6:
        return None

    x = (C*E - B*F) / denom
    y = (A*F - C*D) / denom
    return x, y
