#pragma once
#include <cstdint>

namespace atom_proof {
struct Rgb { uint8_t red, green, blue; };
enum class LedState { idle, connecting, publishing, acknowledged, failed };
class StatusLed {
 public:
  void idle() { state_ = LedState::idle; }
  void connecting() { state_ = LedState::connecting; }
  void publishing() {
    state_ = state_ == LedState::connecting ? LedState::publishing : LedState::failed;
  }
  // Caller must supply the outcome of exact packet-ID PUBACK validation.
  void puback(bool valid) {
    state_ = valid && state_ == LedState::publishing ? LedState::acknowledged : LedState::failed;
  }
  void failure() { state_ = LedState::failed; }
  LedState state() const { return state_; }
  Rgb rgb() const {
    switch (state_) {
      case LedState::connecting: return {0, 0, 24};
      case LedState::publishing: return {24, 24, 0};
      case LedState::acknowledged: return {0, 24, 0};
      case LedState::failed: return {24, 0, 0};
      default: return {0, 0, 0};
    }
  }
 private:
  LedState state_ = LedState::idle;
};
}  // namespace atom_proof
