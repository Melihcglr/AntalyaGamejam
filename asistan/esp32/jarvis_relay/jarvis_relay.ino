/*
 * Jarvis ESP32 röle örneği (Arduino framework)
 * - WiFi Access Point veya STA
 * - HTTP: /relay/on /relay/off /relay/toggle /relay/status /
 *
 * Bağlantı: röle IN → GPIO 5 (RELAY_PIN), VCC/GND röleye göre.
 * Jarvis config: devices.isik.base_url = http://<ESP32-IP>
 */

#include <WiFi.h>
#include <WebServer.h>

const char* WIFI_SSID = "WIFI_ADI";
const char* WIFI_PASS = "WIFI_SIFRE";

const int RELAY_PIN = 5;
// Bazı röle kartları LOW ile açılır:
const bool RELAY_ACTIVE_LOW = true;

WebServer server(80);
bool relayOn = false;

void applyRelay(bool on) {
  relayOn = on;
  digitalWrite(RELAY_PIN, RELAY_ACTIVE_LOW ? (on ? LOW : HIGH) : (on ? HIGH : LOW));
}

void sendJson(int code, const String& body) {
  server.send(code, "application/json", body);
}

void handleRoot() {
  sendJson(200, "{\"ok\":true,\"device\":\"jarvis-relay\",\"state\":\"" + String(relayOn ? "on" : "off") + "\"}");
}

void handleOn() {
  applyRelay(true);
  sendJson(200, "{\"ok\":true,\"state\":\"on\"}");
}

void handleOff() {
  applyRelay(false);
  sendJson(200, "{\"ok\":true,\"state\":\"off\"}");
}

void handleToggle() {
  applyRelay(!relayOn);
  sendJson(200, String("{\"ok\":true,\"state\":\"") + (relayOn ? "on" : "off") + "\"}");
}

void handleStatus() {
  sendJson(200, String("{\"ok\":true,\"state\":\"") + (relayOn ? "on" : "off") + "\"}");
}

void setup() {
  pinMode(RELAY_PIN, OUTPUT);
  applyRelay(false);

  Serial.begin(115200);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("WiFi baglaniyor");
  while (WiFi.status() != WL_CONNECTED) {
    delay(400);
    Serial.print(".");
  }
  Serial.println();
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());

  server.on("/", handleRoot);
  server.on("/relay/on", handleOn);
  server.on("/relay/off", handleOff);
  server.on("/relay/toggle", handleToggle);
  server.on("/relay/status", handleStatus);
  server.begin();
}

void loop() {
  server.handleClient();
}
