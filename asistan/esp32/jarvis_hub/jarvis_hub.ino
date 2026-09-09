/*
 * Jarvis ESP32 Hub
 * ----------------
 * Aynı WiFi'de PC (Jarvis) açıksa komutu PC'ye iletir.
 * PC kapalıysa yerelde işler: ışık rölesi + Wake-on-LAN (bilgisayar aç).
 *
 * Endpointler:
 *   GET  /health
 *   GET  /relay/on|off|toggle|status
 *   POST /api/command   JSON: {"text":"ışığı aç"}
 *   GET  /api/command?text=isigi+ac
 *
 * Kurulum: WIFI_*, PC_HOST, PC_PORT, PC_MAC doldur.
 */

#include <WiFi.h>
#include <WebServer.h>
#include <HTTPClient.h>
#include <WiFiUdp.h>

const char* WIFI_SSID = "WIFI_ADI";
const char* WIFI_PASS = "WIFI_SIFRE";

// Jarvis PC (Windows) — config.json host 0.0.0.0 olmalı
const char* PC_HOST = "192.168.1.20";
const uint16_t PC_PORT = 8787;
const uint16_t PC_HEALTH_TIMEOUT_MS = 800;

// Wake-on-LAN — PC Ethernet/WiFi MAC (AA:BB:CC:DD:EE:FF)
const char* PC_MAC = "AA:BB:CC:DD:EE:FF";

const int RELAY_PIN = 5;
const bool RELAY_ACTIVE_LOW = true;

// İsteğe bağlı: anakart power-SW rölesi (WOL yoksa)
const int PC_POWER_RELAY_PIN = -1;  // yoksa -1
const bool PC_POWER_ACTIVE_LOW = true;
const uint16_t PC_POWER_PULSE_MS = 400;

WebServer server(80);
WiFiUDP udp;
bool relayOn = false;

String jsonEscape(const String& s) {
  String o;
  for (size_t i = 0; i < s.length(); i++) {
    char c = s[i];
    if (c == '"' || c == '\\') o += '\\';
    o += c;
  }
  return o;
}

void applyRelay(bool on) {
  relayOn = on;
  digitalWrite(RELAY_PIN, RELAY_ACTIVE_LOW ? (on ? LOW : HIGH) : (on ? HIGH : LOW));
}

void pulsePcPower() {
  if (PC_POWER_RELAY_PIN < 0) return;
  digitalWrite(PC_POWER_RELAY_PIN, PC_POWER_ACTIVE_LOW ? LOW : HIGH);
  delay(PC_POWER_PULSE_MS);
  digitalWrite(PC_POWER_RELAY_PIN, PC_POWER_ACTIVE_LOW ? HIGH : LOW);
}

bool parseMac(const char* macStr, uint8_t out[6]) {
  unsigned int v[6];
  if (sscanf(macStr, "%x:%x:%x:%x:%x:%x", &v[0], &v[1], &v[2], &v[3], &v[4], &v[5]) != 6) {
    return false;
  }
  for (int i = 0; i < 6; i++) out[i] = (uint8_t)v[i];
  return true;
}

bool sendWol() {
  uint8_t mac[6];
  if (!parseMac(PC_MAC, mac)) return false;
  uint8_t packet[102];
  memset(packet, 0xFF, 6);
  for (int i = 0; i < 16; i++) memcpy(packet + 6 + i * 6, mac, 6);
  IPAddress bcast = WiFi.localIP();
  bcast[3] = 255;
  udp.beginPacket(bcast, 9);
  udp.write(packet, sizeof(packet));
  bool ok = udp.endPacket();
  // Bazı ağlarda 7 de kullanılır
  udp.beginPacket(bcast, 7);
  udp.write(packet, sizeof(packet));
  udp.endPacket();
  return ok;
}

bool pcOnline() {
  HTTPClient http;
  String url = String("http://") + PC_HOST + ":" + PC_PORT + "/api/health";
  http.setTimeout(PC_HEALTH_TIMEOUT_MS);
  if (!http.begin(url)) return false;
  int code = http.GET();
  String body = http.getString();
  http.end();
  // Yalnızca gerçek Jarvis health (200 + ok/role)
  if (code != 200) return false;
  body.toLowerCase();
  return body.indexOf("\"ok\":true") >= 0 || body.indexOf("pc-jarvis") >= 0;
}

String forwardToPc(const String& text) {
  HTTPClient http;
  String url = String("http://") + PC_HOST + ":" + PC_PORT + "/api/command";
  http.setTimeout(15000);
  if (!http.begin(url)) return "{\"ok\":false,\"error\":\"pc begin failed\"}";
  http.addHeader("Content-Type", "application/json");
  String body = String("{\"text\":\"") + jsonEscape(text) + "\"}";
  int code = http.POST(body);
  String resp = http.getString();
  http.end();
  if (code <= 0) return "{\"ok\":false,\"error\":\"pc unreachable\",\"via\":\"esp\"}";
  if (resp.length() == 0) {
    return String("{\"ok\":") + (code < 400 ? "true" : "false") + ",\"via\":\"pc\",\"http\":" + code + "}";
  }
  // PC yanıtına via ekle (basit)
  if (resp.endsWith("}")) {
    resp.remove(resp.length() - 1);
    resp += ",\"via\":\"pc\"}";
  }
  return resp;
}

String turkishFold(String s) {
  s.toLowerCase();
  s.replace("ı", "i");
  s.replace("İ", "i");
  s.replace("ş", "s");
  s.replace("Ş", "s");
  s.replace("ğ", "g");
  s.replace("Ğ", "g");
  s.replace("ü", "u");
  s.replace("Ü", "u");
  s.replace("ö", "o");
  s.replace("Ö", "o");
  s.replace("ç", "c");
  s.replace("Ç", "c");
  return s;
}

String handleLocal(const String& textRaw) {
  String t = turkishFold(textRaw);

  bool wantPcOn =
      t.indexOf("bilgisayar ac") >= 0 || t.indexOf("pc ac") >= 0 ||
      t.indexOf("bilgisayari ac") >= 0 || t.indexOf("pc yi ac") >= 0 ||
      t.indexOf("wake") >= 0 || t.indexOf("uyandir") >= 0;

  bool lightOn = (t.indexOf("isik ac") >= 0 || t.indexOf("lambayi ac") >= 0 || t.indexOf("lamba ac") >= 0 ||
                  (t.indexOf("isik") >= 0 && t.indexOf("yak") >= 0));
  bool lightOff = (t.indexOf("isik kapat") >= 0 || t.indexOf("lambayi kapat") >= 0 ||
                   t.indexOf("lamba kapat") >= 0 || t.indexOf("isik sondur") >= 0);

  if (wantPcOn) {
    bool wol = sendWol();
    pulsePcPower();
    return String("{\"ok\":true,\"via\":\"esp\",\"action\":\"pc_wake\",\"wol\":") +
           (wol ? "true" : "false") + "}";
  }
  if (lightOn) {
    applyRelay(true);
    return "{\"ok\":true,\"via\":\"esp\",\"action\":\"light_on\",\"state\":\"on\"}";
  }
  if (lightOff) {
    applyRelay(false);
    return "{\"ok\":true,\"via\":\"esp\",\"action\":\"light_off\",\"state\":\"off\"}";
  }
  if (t.indexOf("isik") >= 0 && (t.indexOf("toggle") >= 0 || t.indexOf("degistir") >= 0)) {
    applyRelay(!relayOn);
    return String("{\"ok\":true,\"via\":\"esp\",\"action\":\"light_toggle\",\"state\":\"") +
           (relayOn ? "on" : "off") + "\"}";
  }

  return "{\"ok\":false,\"via\":\"esp\",\"error\":\"pc offline; sadece isik/pc ac destekleniyor\"}";
}

String routeCommand(const String& text) {
  if (text.length() == 0) return "{\"ok\":false,\"error\":\"empty\"}";
  if (pcOnline()) {
    return forwardToPc(text);
  }
  return handleLocal(text);
}

void sendJson(int code, const String& body) {
  server.send(code, "application/json", body);
}

void handleHealth() {
  bool pc = pcOnline();
  sendJson(200, String("{\"ok\":true,\"role\":\"esp-hub\",\"relay\":\"") + (relayOn ? "on" : "off") +
                    "\",\"pc_online\":" + (pc ? "true" : "false") + "}");
}

void handleCommandGet() {
  if (!server.hasArg("text")) {
    sendJson(400, "{\"ok\":false,\"error\":\"text required\"}");
    return;
  }
  sendJson(200, routeCommand(server.arg("text")));
}

void handleCommandPost() {
  String body = server.arg("plain");
  String text = "";
  int i = body.indexOf("\"text\"");
  if (i >= 0) {
    int c1 = body.indexOf('"', i + 6);
    int c2 = body.indexOf('"', c1 + 1);
    // find value after :
    int colon = body.indexOf(':', i);
    int q1 = body.indexOf('"', colon + 1);
    int q2 = body.indexOf('"', q1 + 1);
    if (q1 >= 0 && q2 > q1) text = body.substring(q1 + 1, q2);
  }
  if (text.length() == 0 && server.hasArg("text")) text = server.arg("text");
  sendJson(200, routeCommand(text));
}

void setup() {
  pinMode(RELAY_PIN, OUTPUT);
  applyRelay(false);
  if (PC_POWER_RELAY_PIN >= 0) {
    pinMode(PC_POWER_RELAY_PIN, OUTPUT);
    digitalWrite(PC_POWER_RELAY_PIN, PC_POWER_ACTIVE_LOW ? HIGH : LOW);
  }

  Serial.begin(115200);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(400);
    Serial.print(".");
  }
  Serial.println();
  Serial.print("ESP IP: ");
  Serial.println(WiFi.localIP());
  udp.begin(9);

  server.on("/", handleHealth);
  server.on("/health", handleHealth);
  server.on("/relay/on", []() { applyRelay(true); sendJson(200, "{\"ok\":true,\"state\":\"on\"}"); });
  server.on("/relay/off", []() { applyRelay(false); sendJson(200, "{\"ok\":true,\"state\":\"off\"}"); });
  server.on("/relay/toggle", []() {
    applyRelay(!relayOn);
    sendJson(200, String("{\"ok\":true,\"state\":\"") + (relayOn ? "on" : "off") + "\"}");
  });
  server.on("/relay/status", []() {
    sendJson(200, String("{\"ok\":true,\"state\":\"") + (relayOn ? "on" : "off") + "\"}");
  });
  server.on("/api/command", HTTP_GET, handleCommandGet);
  server.on("/api/command", HTTP_POST, handleCommandPost);
  server.begin();
}

void loop() {
  server.handleClient();
}
