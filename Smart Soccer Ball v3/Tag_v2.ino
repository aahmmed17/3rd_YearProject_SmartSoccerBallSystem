#include <SPI.h>
#include <WiFi.h>
#include <esp_now.h>
#include <Wire.h>
#include <Adafruit_ICM20649.h>
#include <Adafruit_Sensor.h>
#include <DW1000Ranging.h>

// -------- PIN CONFIG --------
#define PIN_RST 32
#define PIN_SS  15
#define PIN_IRQ 21
#define SDA_PIN 23
#define SCL_PIN 22
// ----------------------------

// -------- ESP-NOW --------
uint8_t baseStationMAC[] = {0xE4, 0xB0, 0x63, 0xAE, 0xED, 0x80};
// -------------------------

// -------- UWB --------
char tagAddress[] = "7D:00:22:EA:82:60:3B:9C";
const int MAX_ANCHORS = 3;
uint16_t seenAnchors[MAX_ANCHORS] = {0};
float ranges[MAX_ANCHORS] = {0};
bool updated[MAX_ANCHORS] = {false};
// ---------------------

// -------- IMU --------
Adafruit_ICM20649 icm;
float ax = 0, ay = 0, az = 0;
float gx = 0, gy = 0, gz = 0;
unsigned long lastIMU = 0;
// ---------------------

void newRange();
void newDevice(DW1000Device* d);
void inactiveDevice(DW1000Device* d);

void onSent(const wifi_tx_info_t *tx_info, esp_now_send_status_t status) {
  // Silent
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  // -------- ESP-NOW --------
  WiFi.mode(WIFI_STA);
  if (esp_now_init() != ESP_OK) {
    Serial.println("ESP-NOW init failed");
    return;
  }
  esp_now_register_send_cb(onSent);
  esp_now_peer_info_t peer = {};
  memcpy(peer.peer_addr, baseStationMAC, 6);
  peer.channel = 0;
  peer.encrypt = false;
  if (esp_now_add_peer(&peer) != ESP_OK) {
    Serial.println("Failed to add peer");
    return;
  }

  // -------- IMU --------
  Wire.begin(SDA_PIN, SCL_PIN);
  Wire.setClock(400000);
  if (!icm.begin_I2C()) {
    Serial.println("IMU init failed!");
  } else {
    Serial.println("IMU Ready");
  }

  // -------- UWB --------
  SPI.begin();
  DW1000Ranging.initCommunication(PIN_RST, PIN_SS, PIN_IRQ);
  DW1000Ranging.attachNewRange(newRange);
  DW1000Ranging.attachNewDevice(newDevice);
  DW1000Ranging.attachInactiveDevice(inactiveDevice);
  DW1000Ranging.startAsTag(tagAddress, DW1000.MODE_LONGDATA_RANGE_LOWPOWER);

  Serial.println("System Online");
}

void loop() {
  // Poll IMU at 100Hz using timer rather than dataReady()
  // to avoid interfering with DW1000 ranging loop
  if (millis() - lastIMU >= 10) {
    sensors_event_t accel_evt, gyro_evt, temp_evt;
    icm.getEvent(&accel_evt, &gyro_evt, &temp_evt);

    // Adafruit library returns m/s² directly — no conversion needed
    ax = accel_evt.acceleration.x;
    ay = accel_evt.acceleration.y;
    az = accel_evt.acceleration.z;

    // Gyro in rad/s
    gx = gyro_evt.gyro.x;
    gy = gyro_evt.gyro.y;
    gz = gyro_evt.gyro.z;

    lastIMU = millis();
  }

  DW1000Ranging.loop();
}

void newRange() {
  DW1000Device* dev = DW1000Ranging.getDistantDevice();
  if (!dev) return;

  float dist = dev->getRange();
  uint16_t addr = dev->getShortAddress();

  if (dist <= 0.0 || dist > 30.0) return;

  int index = -1;
  for (int i = 0; i < MAX_ANCHORS; i++) {
    if (seenAnchors[i] == addr) { index = i; break; }
  }
  if (index == -1) {
    for (int i = 0; i < MAX_ANCHORS; i++) {
      if (seenAnchors[i] == 0) { seenAnchors[i] = addr; index = i; break; }
    }
  }

  if (index != -1) {
    ranges[index] = dist;
    updated[index] = true;

    bool allUpdated = true;
    for (int i = 0; i < MAX_ANCHORS; i++) {
      if (!updated[i]) { allUpdated = false; break; }
    }

    if (allUpdated) {
      char csv[128];
      snprintf(csv, sizeof(csv),
        "%.3f,%.3f,%.3f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f",
        ranges[0], ranges[1], ranges[2],
        ax, ay, az,
        gx, gy, gz
      );
      esp_now_send(baseStationMAC, (uint8_t*)csv, strlen(csv));

      for (int i = 0; i < MAX_ANCHORS; i++) updated[i] = false;
    }
  }
}

void newDevice(DW1000Device* dev)      { Serial.println("Anchor Found"); }
void inactiveDevice(DW1000Device* dev) { Serial.println("Anchor Lost"); }
