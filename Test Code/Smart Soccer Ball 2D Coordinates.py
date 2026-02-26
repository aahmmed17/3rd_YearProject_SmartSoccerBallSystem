import serial
import time
import math

# ---------------- SERIAL CONFIG ----------------
PORT = "COM10"          # 🔴 CHANGE THIS
BAUD = 115200
# ------------------------------------------------

# ---------------- ANCHOR COORDINATES (meters) ----------------
# PHYSICAL anchor positions
A1 = (0.0, 0.0)   # Anchor 1
A2 = (3.6,0.0 )   # Anchor 2
A3 = (0.0, 2.2)   # Anchor 3
# -------------------------------------------------------------

# ---------------- RANGE INDEX MAPPING ----------------
# Verified experimentally
IDX_ANCHOR_1 = 2  # ranges[0] → Physical Anchor 1
IDX_ANCHOR_2 = 0   # ranges[2] → Physical Anchor 2
IDX_ANCHOR_3 = 1   # ranges[1] → Physical Anchor 3
# -----------------------------------------------------

def trilaterate(p1, p2, p3, r1, r2, r3):
    """
    2D trilateration via linearized circle equations
    """
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


def main():
    ser = serial.Serial(PORT, BAUD, timeout=1)
    time.sleep(2)
    print("Serial connected")

    while True:
        try:
            line = ser.readline().decode().strip()
            if not line:
                continue

            parts = line.split(",")
            if len(parts) != 3:
                continue

            # raw ranges from ESP32
            ranges = [float(p) for p in parts]

            # map to physical anchors
            r1 = ranges[IDX_ANCHOR_1]
            r2 = ranges[IDX_ANCHOR_2]
            r3 = ranges[IDX_ANCHOR_3]

            pos = trilaterate(A1, A2, A3, r1, r2, r3)
            if pos is None:
                continue

            x, y = pos

            print(
                f"x = {x:.3f} m , y = {y:.3f} m | "
                f"r1={r1:.2f}, r2={r2:.2f}, r3={r3:.2f}"
            )

        except ValueError:
            continue
        except KeyboardInterrupt:
            print("\nStopped by user")
            break

    ser.close()


if __name__ == "__main__":
    main()
