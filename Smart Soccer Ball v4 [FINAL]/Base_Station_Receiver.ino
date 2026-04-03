#include <WiFi.h>
#include <esp_now.h>
#include <esp_wifi.h>    // needed for esp_wifi_set_channel, tx power, data rate

void onDataRecv(const uint8_t *mac, const uint8_t *incomingData, int len) {
  char buffer[150];
  memcpy(buffer, incomingData, len);
  buffer[len] = '\0';

  // Print ONLY the CSV
  Serial.println(buffer);
}

void setup() {
  Serial.begin(115200);
  delay(2000);

  WiFi.mode(WIFI_STA);
  WiFi.disconnect();

  // Lock to channel 1 — must match tag and anchors
  esp_wifi_set_channel(1, WIFI_SECOND_CHAN_NONE);

  // Maximum TX power
  esp_wifi_set_max_tx_power(84);

  if (esp_now_init() != ESP_OK) {
    Serial.println("ESP-NOW init failed");
    return;
  }

  // 2 Mbps PHY rate — must match the tag
  esp_wifi_config_espnow_rate(WIFI_IF_STA, WIFI_PHY_RATE_9M);

  esp_now_register_recv_cb(onDataRecv);

  Serial.println("Receiver ready");
}

void loop() {}
