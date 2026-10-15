#pragma once
#include "protocol.hpp"

namespace atom_proof {
// GPIO polling: require a stable release after arm and after every attempt.
class ButtonSession {
 public:
  bool arm(uint32_t now) {
    if (ever_armed_) return false;
    ever_armed_ = active_ = true; started_ = now; reset_edge(now); return true;
  }
  void reset_edge(uint32_t now) { candidate_ = true; released_ = false; changed_ = now; }
  bool expired(uint32_t now) const { return active_ && uint32_t(now - started_) >= 120000; }
  bool active() const { return active_; }
  uint32_t sample(bool pressed, uint32_t now) {
    if (!active_ || expired(now)) return 0;
    if (pressed != candidate_) { candidate_ = pressed; changed_ = now; }
    if (uint32_t(now - changed_) < 50) return 0;
    if (!pressed) { released_ = true; return 0; }
    if (!released_) return 0;
    released_ = false;
    if (++sequence_ == 3) active_ = false;
    return sequence_;
  }
 private:
  bool ever_armed_ = false, active_ = false, candidate_ = true, released_ = false;
  uint32_t started_ = 0, changed_ = 0, sequence_ = 0;
};
inline bool valid_session(const std::string& session) {
  return valid_nonce(session) && session != std::string(32, '0');
}
inline std::string button_payload(const std::string& session, uint32_t sequence) {
  if (!valid_session(session) || sequence < 1 || sequence > 3) return {};
  return std::string("{\"device_id\":\"atom-lite-001\",\"event\":\"button_press\",\"session_id\":\"") + session +
    "\",\"event_id\":\"" + session + "-" + std::to_string(sequence) + "\",\"sequence\":" + std::to_string(sequence) + "}";
}
inline Bytes button_packet(const std::string& session, uint32_t sequence) {
  const auto data = button_payload(session, sequence);
  if (data.empty()) return {};
  Bytes body; append_string(body, topic); body.insert(body.end(), {0, 1});
  body.insert(body.end(), data.begin(), data.end()); return packet(0x32, body);
}
}  // namespace atom_proof
