#include <WiFi.h>
#include <esp_now.h>

void onDataRecv(const uint8_t *mac, const uint8_t *incomingData, int len) {
  char buffer[100];
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

  if (esp_now_init() != ESP_OK) {
    return;
  }

  esp_now_register_recv_cb(onDataRecv);
}

void loop() {}


