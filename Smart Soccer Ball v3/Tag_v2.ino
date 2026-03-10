#include <SPI.h>
#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>          // needed for esp_wifi_set_channel, tx power, data rate
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
float    ranges[MAX_ANCHORS]      = {0};

// CHANGE 1: Replace bool updated[] with timestamps so stale anchors
//           don't block transmission
unsigned long lastUpdate[MAX_ANCHORS] = {0};

// How long before an anchor reading is considered stale (ms)
// At ~25Hz we expect a fresh reading every 40ms — 80ms gives 2 missed rounds
const unsigned long STALE_MS = 80;

// Minimum send interval — caps output at ~25Hz (40ms per packet)
const unsigned long SEND_INTERVAL_MS = 40;
unsigned long lastSend = 0;
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
void tryTransmit();

void onSent(const wifi_tx_info_t *tx_info, esp_now_send_status_t status) {
  // Silent
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  // -------- ESP-NOW --------
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();

  // CHANGE 2: Lock WiFi channel to 1 on all devices so ESP-NOW
  //           packets are never silently dropped due to channel mismatch
  esp_wifi_set_channel(1, WIFI_SECOND_CHAN_NONE);

  // CHANGE 3: Maximum TX power reduces MAC-layer retransmits
  //           which were adding invisible latency
  esp_wifi_set_max_tx_power(84);  // 84 = 21 dBm

  if (esp_now_init() != ESP_OK) {
    Serial.println("ESP-NOW init failed");
    return;
  }

  // CHANGE 4: 2 Mbps PHY rate halves air-time per packet,
  //           shrinking the collision window with DW1000 SPI
  esp_wifi_config_espnow_rate(WIFI_IF_STA, WIFI_PHY_RATE_9M);

  esp_now_register_send_cb(onSent);

  esp_now_peer_info_t peer = {};
  memcpy(peer.peer_addr, baseStationMAC, 6);
  peer.channel = 1;   // match the channel set above
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
  // Poll IMU at 100Hz
  if (millis() - lastIMU >= 10) {
    sensors_event_t accel_evt, gyro_evt, temp_evt;
    icm.getEvent(&accel_evt, &gyro_evt, &temp_evt);

    ax = accel_evt.acceleration.x;
    ay = accel_evt.acceleration.y;
    az = accel_evt.acceleration.z;

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

  float    dist = dev->getRange();
  uint16_t addr = dev->getShortAddress();

  if (dist <= 0.0 || dist > 30.0) return;

  // Resolve anchor index, registering new anchors as they appear
  int index = -1;
  for (int i = 0; i < MAX_ANCHORS; i++) {
    if (seenAnchors[i] == addr) { index = i; break; }
  }
  if (index == -1) {
    for (int i = 0; i < MAX_ANCHORS; i++) {
      if (seenAnchors[i] == 0) { seenAnchors[i] = addr; index = i; break; }
    }
  }
  if (index == -1) return;

  ranges[index]     = dist;
  lastUpdate[index] = millis();

  tryTransmit();
}

void tryTransmit() {
  unsigned long now = millis();

  // CHANGE 1 (cont): All three anchors must have at least one reading
  //                  before we start transmitting
  bool allHaveData = lastUpdate[0] && lastUpdate[1] && lastUpdate[2];
  if (!allHaveData) return;

  // At least one anchor must have a fresh reading this cycle —
  // prevents sending a packet of entirely stale data
  bool anyFresh = ((now - lastUpdate[0]) < STALE_MS) ||
                  ((now - lastUpdate[1]) < STALE_MS) ||
                  ((now - lastUpdate[2]) < STALE_MS);
  if (!anyFresh) return;

  // Rate limit to ~25Hz
  if ((now - lastSend) < SEND_INTERVAL_MS) return;
  lastSend = now;

  char csv[128];
  snprintf(csv, sizeof(csv),
    "%.3f,%.3f,%.3f,%.4f,%.4f,%.4f,%.4f,%.4f,%.4f",
    ranges[0], ranges[1], ranges[2],
    ax, ay, az,
    gx, gy, gz
  );
  esp_now_send(baseStationMAC, (uint8_t*)csv, strlen(csv));
}

void newDevice(DW1000Device* dev)      { Serial.println("Anchor Found"); }
void inactiveDevice(DW1000Device* dev) { Serial.println("Anchor Lost"); }

