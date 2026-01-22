#include <Wire.h>

/* -------- ADXL375 I2C -------- */
#define ADXL375_ADDR   0x53   // 0x1D if SDO = 3.3V

#define POWER_CTL      0x2D
#define DATA_FORMAT    0x31
#define BW_RATE        0x2C
#define DATAX0         0x32

/* -------- Physical Constants -------- */
#define G_TO_MS2       9.80665
#define SENSITIVITY    0.049     // g/LSB (ADXL375)
#define BALL_MASS      0.43      // kg (size 5 soccer ball)

/* -------- Detection Parameters -------- */
#define IMPACT_G       15.0      // impact threshold (g)
#define WINDOW_MS      10        // integration window (ms)

/* -------- State Variables -------- */
bool impactDetected = false;

unsigned long impactTime = 0;
unsigned long lastTime = 0;

float velocity = 0.0;
float kickSpeed = 0.0;

float peakAccel = 0.0;
float peakForce = 0.0;

/* -------- I2C Helpers -------- */
void writeRegister(byte reg, byte value) {
  Wire.beginTransmission(ADXL375_ADDR);
  Wire.write(reg);
  Wire.write(value);
  Wire.endTransmission();
}

void readRegisters(byte reg, byte count, byte *dest) {
  Wire.beginTransmission(ADXL375_ADDR);
  Wire.write(reg);
  Wire.endTransmission(false);
  Wire.requestFrom(ADXL375_ADDR, count);

  for (byte i = 0; i < count; i++) {
    dest[i] = Wire.read();
  }
}

/* -------- Read Acceleration (g) -------- */
void readAccel(float &ax, float &ay, float &az) {
  byte buf[6];
  readRegisters(DATAX0, 6, buf);

  int16_t x = (int16_t)((buf[1] << 8) | buf[0]);
  int16_t y = (int16_t)((buf[3] << 8) | buf[2]);
  int16_t z = (int16_t)((buf[5] << 8) | buf[4]);

  ax = x * SENSITIVITY;
  ay = y * SENSITIVITY;
  az = z * SENSITIVITY;
}

/* -------- Setup -------- */
void setup() {
  Serial.begin(115200);
  Wire.begin();

  // Measurement mode
  writeRegister(POWER_CTL, 0x08);

  // Full resolution, ±200g
  writeRegister(DATA_FORMAT, 0x0B);

  // Output data rate: 3200 Hz (use 0x0E for 1600 Hz on Uno)
  writeRegister(BW_RATE, 0x0F);

  lastTime = micros();
}

/* -------- Main Loop -------- */
void loop() {
  unsigned long now = micros();
  float dt = (now - lastTime) / 1e6;
  lastTime = now;

  float ax, ay, az;
  readAccel(ax, ay, az);

  // Acceleration magnitude (g)
  float amag = sqrt(ax * ax + ay * ay + az * az);

  // Remove gravity approximately and convert to m/s²
  float accel_ms2 = (amag - 1.0) * G_TO_MS2;

  /* -------- Impact Detection -------- */
  if (!impactDetected && amag > IMPACT_G) {
    impactDetected = true;
    impactTime = now;

    velocity = 0.0;
    peakAccel = 0.0;
    peakForce = 0.0;
  }

  /* -------- Integration Window -------- */
  if (impactDetected) {

    if (accel_ms2 > 0) {
      velocity += accel_ms2 * dt;

      if (accel_ms2 > peakAccel) {
        peakAccel = accel_ms2;
        peakForce = BALL_MASS * peakAccel;
      }
    }

    // End of impact window
    if ((now - impactTime) > WINDOW_MS * 1000) {
      impactDetected = false;

      kickSpeed = velocity;
      float impulse = BALL_MASS * kickSpeed;

      Serial.println("----- Kick Detected -----");
      Serial.print("Kick speed: ");
      Serial.print(kickSpeed);
      Serial.println(" m/s");

      Serial.print("Peak accel: ");
      Serial.print(peakAccel / G_TO_MS2);
      Serial.println(" g");

      Serial.print("Peak force: ");
      Serial.print(peakForce);
      Serial.println(" N");

      Serial.print("Impulse: ");
      Serial.print(impulse);
      Serial.println(" N·s");

      Serial.println("-------------------------\n");
    }
  }
}
