#pragma once
#include <array>
#include <cstdint>
#include <string>
#include <vector>

namespace atom_proof {
constexpr const char* client_id = "atom-lite-001";
constexpr const char* topic = "devices/atom-lite-001/probe";
using Bytes = std::vector<uint8_t>;

inline bool valid_nonce(const std::string& value) {
  if (value.size() != 32) return false;
  for (char c : value) if (!((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f'))) return false;
  return true;
}

inline bool valid_endpoint(const std::string& value) {
  const std::string suffix = ".iot.us-east-1.amazonaws.com";
  if (value.size() <= suffix.size() || value.size() > 128 ||
      value.compare(value.size() - suffix.size(), suffix.size(), suffix) != 0) return false;
  const std::string prefix = value.substr(0, value.size() - suffix.size());
  if (prefix.size() <= 4 || prefix.compare(prefix.size() - 4, 4, "-ats") != 0) return false;
  for (char c : prefix) if (!((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9') || c == '-')) return false;
  return prefix.front() != '-';
}

inline void append_string(Bytes& out, const std::string& value) {
  if (value.size() > 1024) return;
  out.push_back(static_cast<uint8_t>(value.size() >> 8));
  out.push_back(static_cast<uint8_t>(value.size()));
  out.insert(out.end(), value.begin(), value.end());
}

inline Bytes packet(uint8_t header, const Bytes& body) {
  if (body.size() > 2048) return {};
  Bytes out{header};
  size_t remaining = body.size();
  do {
    uint8_t digit = remaining % 128;
    remaining /= 128;
    if (remaining) digit |= 128;
    out.push_back(digit);
  } while (remaining);
  out.insert(out.end(), body.begin(), body.end());
  return out;
}

inline Bytes connect_packet() {
  Bytes body{0, 4, 'M', 'Q', 'T', 'T', 4, 2, 0, 30};
  append_string(body, client_id);
  return packet(0x10, body);
}

inline std::string payload(const std::string& nonce) {
  if (!valid_nonce(nonce)) return {};
  return std::string("{\"device_id\":\"atom-lite-001\",\"probe\":\"mqtt-proof\",\"nonce\":\"") + nonce + "\"}";
}

inline Bytes publish_packet(const std::string& nonce) {
  if (!valid_nonce(nonce)) return {};
  Bytes body;
  append_string(body, topic);
  body.insert(body.end(), {0, 1});
  const auto data = payload(nonce);
  body.insert(body.end(), data.begin(), data.end());
  return packet(0x32, body);  // QoS 1, no RETAIN, no DUP.
}

inline bool connack(const std::array<uint8_t, 4>& value) { return value == std::array<uint8_t, 4>{0x20, 2, 0, 0}; }
inline bool puback(const std::array<uint8_t, 4>& value) { return value == std::array<uint8_t, 4>{0x40, 2, 0, 1}; }

class OneShot {
 public:
  bool arm() { if (consumed_) return false; consumed_ = true; return true; }
 private:
  bool consumed_ = false;
};
}  // namespace atom_proof
