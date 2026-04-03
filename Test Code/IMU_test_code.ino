#include <Wire.h>
#include <Adafruit_ICM20649.h>
#include <Adafruit_Sensor.h>

Adafruit_ICM20649 icm;

#define NEW_SDA 16
#define NEW_SCL 17

void setup() {
  Serial.begin(115200);
  while (!Serial) delay(10); 

  Serial.println("--- HUZZAH32: IMU Remap Test (Swapped) ---");
  Serial.println("Checking Pins: SDA=17, SCL=16");

  
  Wire.begin(NEW_SDA, NEW_SCL);
  Wire.setClock(400000); // Standard fast mode

  if (!icm.begin_I2C()) {
    Serial.println("FAILED: ICM-20649 not found.");
    while (1) delay(10);
  }

  Serial.println("SUCCESS: IMU detected on pins 17/16!");
}

void loop() {
  sensors_event_t accel, gyro, temp;
  icm.getEvent(&accel, &gyro, &temp);

  Serial.print("Accel X: "); Serial.print(accel.acceleration.x);
  Serial.print(" | Y: "); Serial.print(accel.acceleration.y);
  Serial.print(" | Z: "); Serial.println(accel.acceleration.z);

  delay(100);
}
