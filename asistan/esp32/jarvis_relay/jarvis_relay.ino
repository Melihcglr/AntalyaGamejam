/*
 * Jarvis ESP32 röle (Arduino)
 * HTTP :8788 — /health /relay/on|off|toggle|status
 * AUTH_TOKEN doluysa Bearer / X-Jarvis-Token gerekir (/health hariç).
 * mDNS: jarvis-relay.local
 */

#include <WiFi.h>
#include <WebServer.h>
#include <ESPmDNS.h>

const char* WIFI_SSID = "WIFI_ADI";
const char* WIFI_PASS = "WIFI_SIFRE";
const char* AUTH_TOKEN = "";
const char* MDNS_NAME = "jarvis-relay";

const int RELAY_PIN = 5;
const bool RELAY_ACTIVE_LOW = true;

WebServer server(8788);
bool relayOn = false;

void applyRelay(bool on) {
  relayOn = on;
  digitalWrite(RELAY_PIN, RELAY_ACTIVE_LOW ? (on ? LOW : HIGH) : (on ? HIGH : LOW));
}

void sendJson(int code, const String& body) {
  server.send(code, "application/json", body);
}

bool authOk() {
  if (AUTH_TOKEN == nullptr || strlen(AUTH_TOKEN) == 0) return true;
  if (server.hasHeader("X-Jarvis-Token") && server.header("X-Jarvis-Token") == String(AUTH_TOKEN)) {
    return true;
  }
  if (server.hasHeader("Authorization")) {
    String a = server.header("Authorization");
    if (a.startsWith("Bearer ") && a.substring(7) == String(AUTH_TOKEN)) return true;
  }
  if (server.hasArg("token") && server.arg("token") == String(AUTH_TOKEN)) return true;
  return false;
}

bool requireAuth() {
  if (authOk()) return true;
  sendJson(401, "{\"ok\":false,\"error\":\"unauthorized\"}");
  return false;
}

void handleHealth() {
  sendJson(200, String("{\"ok\":true,\"device\":\"jarvis-relay\",\"mdns\":\"") + MDNS_NAME +
                    ".local\",\"state\":\"" + (relayOn ? "on" : "off") + "\"}");
}

void handleOn() {
  if (!requireAuth()) return;
  applyRelay(true);
  sendJson(200, "{\"ok\":true,\"state\":\"on\"}");
}
void handleOff() {
  if (!requireAuth()) return;
  applyRelay(false);
  sendJson(200, "{\"ok\":true,\"state\":\"off\"}");
}
void handleToggle() {
  if (!requireAuth()) return;
  applyRelay(!relayOn);
  sendJson(200, String("{\"ok\":true,\"state\":\"") + (relayOn ? "on" : "off") + "\"}");
}
void handleStatus() {
  if (!requireAuth()) return;
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

  if (MDNS.begin(MDNS_NAME)) {
    MDNS.addService("http", "tcp", 8788);
  }

  server.on("/", handleHealth);
  server.on("/health", handleHealth);
  server.on("/relay/on", handleOn);
  server.on("/relay/off", handleOff);
  server.on("/relay/toggle", handleToggle);
  server.on("/relay/status", handleStatus);
  server.begin();
}

void loop() {
  server.handleClient();
}
