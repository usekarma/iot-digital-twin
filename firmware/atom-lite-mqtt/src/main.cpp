#include <Arduino.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <cJSON.h>
#include <esp_wifi.h>
#include <sys/time.h>
#include <esp32-hal-rgb-led.h>
#include "amazon_root_ca.h"
#include "button.hpp"
#include "status_led.hpp"

namespace {
String frame, ssid, password, endpoint, certificate, private_key, nonce;
int64_t epoch = 0;
bool configured = false, terminal = false, overflow = false;
atom_proof::ButtonSession button;
atom_proof::StatusLed status_led;
void show_led() {
  const auto rgb = status_led.rgb();
  neopixelWrite(27, rgb.red, rgb.green, rgb.blue);  // One GRB SK6812, dim channels.
}
void led_failure() { status_led.failure(); show_led(); }
const size_t max_frame = 8192;

void wipe(String& value) {
  for (size_t i = 0; i < value.length(); ++i) value.setCharAt(i, '\0');
  value = "";
}

void finish(const char* result) {
  const bool failed = strncmp(result, "ERROR_", 6) == 0 || strcmp(result, "PUBLICATION_UNKNOWN") == 0;
  status_led.end_session(failed);
  show_led();  // Both SESSION_EXPIRED and SESSION_COMPLETE clear the LED before terminal state.
  WiFi.disconnect(false, false);
  WiFi.mode(WIFI_OFF);
  wipe(password); wipe(private_key); wipe(certificate); wipe(frame);
  terminal = true;
  Serial.println(result);
}

bool configure(const String& input) {
  cJSON* root = cJSON_ParseWithOpts(input.c_str(), nullptr, true);
  if (!root) return false;
  const char* names[] = {"ssid", "wifi_password", "endpoint", "certificate_pem", "private_key_pem", "nonce", "epoch"};
  unsigned seen = 0;
  bool valid = cJSON_IsObject(root) && cJSON_GetArraySize(root) == 7;
  for (cJSON* item = root->child; item; item = item->next) {
    unsigned found = 0;
    for (unsigned i = 0; i < 7; ++i) if (item->string && strcmp(item->string, names[i]) == 0) found = 1u << i;
    if (!found || (seen & found)) valid = false;
    seen |= found;
  }
  valid = valid && seen == 127;
  for (unsigned i = 0; i < 6; ++i) valid = valid && cJSON_IsString(cJSON_GetObjectItemCaseSensitive(root, names[i]));
  cJSON* clock = cJSON_GetObjectItemCaseSensitive(root, "epoch");
  valid = valid && cJSON_IsNumber(clock);
  if (valid) {
    ssid = cJSON_GetObjectItemCaseSensitive(root, "ssid")->valuestring;
    password = cJSON_GetObjectItemCaseSensitive(root, "wifi_password")->valuestring;
    endpoint = cJSON_GetObjectItemCaseSensitive(root, "endpoint")->valuestring;
    certificate = cJSON_GetObjectItemCaseSensitive(root, "certificate_pem")->valuestring;
    private_key = cJSON_GetObjectItemCaseSensitive(root, "private_key_pem")->valuestring;
    nonce = cJSON_GetObjectItemCaseSensitive(root, "nonce")->valuestring;
    epoch = static_cast<int64_t>(clock->valuedouble);
    valid = ssid.length() >= 1 && ssid.length() <= 32 && password.length() >= 8 && password.length() <= 63 &&
      atom_proof::valid_endpoint(endpoint.c_str()) && atom_proof::valid_session(nonce.c_str()) &&
      certificate.length() <= 3072 && certificate.startsWith("-----BEGIN CERTIFICATE-----") &&
      private_key.length() <= 2048 && private_key.startsWith("-----BEGIN ") && private_key.indexOf("PRIVATE KEY") > 0 &&
      epoch >= 1767225600 && epoch < 2524608000 && clock->valuedouble == static_cast<double>(epoch);
  }
  // Do not leave parsed credential copies intact in freed JSON buffers.
  for (const char* name : {"wifi_password", "private_key_pem"}) {
    cJSON* item = cJSON_GetObjectItemCaseSensitive(root, name);
    if (cJSON_IsString(item)) memset(item->valuestring, 0, strlen(item->valuestring));
  }
  cJSON_Delete(root);
  if (!valid) { wipe(password); wipe(private_key); wipe(certificate); }
  return valid;
}

bool read_ack(WiFiClientSecure& client, std::array<uint8_t, 4>& ack) {
  const uint32_t start = millis();
  size_t count = 0;
  while (count < ack.size() && millis() - start < 5000) {
    if (client.available()) ack[count++] = static_cast<uint8_t>(client.read());
    else if (!client.connected()) break;
    else delay(5);
  }
  return count == ack.size();
}

void publish_button(uint32_t sequence) {
  status_led.connecting(); show_led();
  WiFi.persistent(false);
  WiFi.setAutoReconnect(false);
  if (!WiFi.mode(WIFI_STA) || esp_wifi_set_storage(WIFI_STORAGE_RAM) != ESP_OK) { finish("ERROR_WIFI_INIT"); return; }
  WiFi.begin(ssid.c_str(), password.c_str());
  const uint32_t started = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - started < 30000) delay(50);
  if (WiFi.status() != WL_CONNECTED) { finish("ERROR_WIFI"); return; }
  Serial.println("WIFI_READY");
  WiFiClientSecure client;
  client.setCACert(amazon_root_ca);
  client.setCertificate(certificate.c_str());
  client.setPrivateKey(private_key.c_str());
  client.setHandshakeTimeout(20);
  client.setTimeout(5000);
  if (!client.connect(endpoint.c_str(), 8883)) { client.stop(); finish("ERROR_TLS"); return; }
  Serial.println("TLS_READY");
  auto packet = atom_proof::connect_packet();
  std::array<uint8_t, 4> ack{};
  if (client.write(packet.data(), packet.size()) != packet.size() || !read_ack(client, ack) || !atom_proof::connack(ack)) {
    client.stop(); finish("ERROR_MQTT_CONNECT"); return;
  }
  Serial.println("MQTT_READY");
  packet = atom_proof::button_packet(nonce.c_str(), sequence);
  Serial.print("EVENT "); Serial.println(atom_proof::button_payload(nonce.c_str(), sequence).c_str());
  status_led.publishing(); show_led();
  if (client.write(packet.data(), packet.size()) != packet.size() || !read_ack(client, ack) || !atom_proof::puback(ack)) {
    client.stop(); finish("PUBLICATION_UNKNOWN"); return;
  }
  status_led.puback(true); show_led();  // Only after exact PUBACK validation above.
  const uint8_t disconnect[] = {0xe0, 0};
  client.write(disconnect, sizeof(disconnect));
  client.stop();
  WiFi.disconnect(false, false); WiFi.mode(WIFI_OFF);
  Serial.println("PUBACK_RECEIVED");
  if (sequence == 3) finish("SESSION_COMPLETE");
  else button.reset_edge(millis());
}
}  // namespace

void setup() {
  Serial.setRxBufferSize(2048);
  Serial.begin(115200);
  status_led.idle(); show_led();
  pinMode(39, INPUT);  // ATOM Lite active-low button; external board pull-up.
  Serial.println("ATOM_BUTTON_V1 READY");
}
void loop() {
  static uint32_t banner = 0;
  if (!configured && !terminal && millis() - banner > 2000) { Serial.println("ATOM_BUTTON_V1 READY"); banner = millis(); }
  while (Serial.available()) {
    const char c = static_cast<char>(Serial.read());
    if (c == '\r') continue;
    if (c == '\n') {
      if (terminal) { wipe(frame); continue; }
      if (overflow) { wipe(frame); overflow = false; led_failure(); Serial.println("CONFIG_REJECTED"); continue; }
      if (!configured && frame.startsWith("CONFIG ")) {
        configured = configure(frame.substring(7));
        if (configured) { status_led.idle(); show_led(); }
        else led_failure();
        Serial.println(configured ? "CONFIG_READY" : "CONFIG_REJECTED");
      } else if (frame == "ARM_BUTTON" && configured && button.arm(millis())) {
        timeval clock{static_cast<time_t>(epoch), 0};
        if (settimeofday(&clock, nullptr) != 0) finish("ERROR_CLOCK");
        else Serial.println("BUTTON_ARMED");
      }
      else { led_failure(); Serial.println("COMMAND_REJECTED"); }
      wipe(frame);
    } else if (!overflow) {
      if (frame.length() >= max_frame) { wipe(frame); overflow = true; }
      else frame += c;
    }
  }
  if (!terminal && button.expired(millis())) finish("SESSION_EXPIRED");
  if (!terminal && configured) {
    const uint32_t sequence = button.sample(digitalRead(39) == LOW, millis());
    if (sequence) publish_button(sequence);
  }
  delay(5);
}
