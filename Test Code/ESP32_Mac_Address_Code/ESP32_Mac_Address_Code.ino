#include <WiFi.h>

void setup(){
  delay(1000);
  Serial.begin(115200);
  delay(1000);
  // WiFi.macAddress() returns the MAC address in the form of a 6-byte array
  Serial.print("ESP32 Board MAC Address:  ");
  Serial.println(WiFi.macAddress());
}

void loop(){}

