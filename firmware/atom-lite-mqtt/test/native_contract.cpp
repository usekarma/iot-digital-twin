#include "button.hpp"
#include "status_led.hpp"
#include <cassert>

int main() {
  using namespace atom_proof;
  StatusLed led;
  assert(led.rgb().red == 0 && led.rgb().green == 0 && led.rgb().blue == 0);
  led.puback(true); assert(led.state() == LedState::failed);  // Idle cannot turn green.
  led.connecting(); assert(led.rgb().blue == 24 && led.rgb().green == 0);
  led.puback(true); assert(led.state() == LedState::failed);  // CONNECT success is not PUBACK.
  led.connecting(); led.publishing();
  assert(led.rgb().red == 24 && led.rgb().green == 24 && led.rgb().blue == 0);
  led.puback(false); assert(led.rgb().red == 24 && led.rgb().green == 0);
  led.puback(true); assert(led.state() == LedState::failed);  // Failure cannot turn green.
  led.connecting(); led.publishing(); led.puback(true);
  assert(led.rgb().green == 24 && led.rgb().red == 0 && led.rgb().blue == 0);
  led.connecting(); assert(led.state() == LedState::connecting);  // New press clears green.
  led.failure(); assert(led.state() == LedState::failed);
  led.idle(); assert(led.state() == LedState::idle);
  // Both normal terminal reasons clear prior green; failures retain red.
  for (unsigned normal_reason = 0; normal_reason < 2; ++normal_reason) {
    led.connecting(); led.publishing(); led.puback(true);
    assert(led.state() == LedState::acknowledged);
    led.end_session(false);
    assert(led.state() == LedState::idle);
    assert(led.rgb().red == 0 && led.rgb().green == 0 && led.rgb().blue == 0);
  }
  led.connecting(); led.publishing(); led.end_session(true);
  assert(led.state() == LedState::failed);
  assert(led.rgb().red == 24 && led.rgb().green == 0 && led.rgb().blue == 0);
  // No event before arm; held-at-arm button requires stable release first.
  ButtonSession button;
  assert(button.sample(true, 100) == 0);
  assert(button.arm(100)); assert(!button.arm(101));
  assert(button.sample(true, 200) == 0);
  assert(button.sample(false, 210) == 0);
  assert(button.sample(false, 260) == 0);
  assert(button.sample(true, 270) == 0);
  assert(button.sample(false, 290) == 0);  // bounce must restart debounce
  assert(button.sample(true, 300) == 0);
  assert(button.sample(true, 349) == 0);
  assert(button.sample(true, 350) == 1);
  assert(button.sample(true, 900) == 0);  // hold does not repeat
  button.reset_edge(1000);
  assert(button.sample(false, 1001) == 0);
  assert(button.sample(false, 1051) == 0);
  assert(button.sample(true, 1060) == 0);
  assert(button.sample(true, 1110) == 2);
  button.reset_edge(1200);
  assert(button.sample(false, 1201) == 0);
  assert(button.sample(false, 1251) == 0);
  assert(button.sample(true, 1260) == 0);
  assert(button.sample(true, 1310) == 3);
  assert(!button.active()); assert(button.sample(false, 1500) == 0);
  assert(!button.arm(2000));
  ButtonSession expiry;
  assert(expiry.arm(0xfffffff0));
  assert(!expiry.expired(uint32_t(0xfffffff0u + 119999u)));
  assert(expiry.expired(uint32_t(0xfffffff0u + 120000u)));
  assert(expiry.sample(true, uint32_t(0xfffffff0u + 120000u)) == 0);
  const std::string session(32, 'b');
  assert(!valid_session(std::string(32, '0')));
  assert(!valid_session("bad"));
  assert(button_payload(session, 0).empty());
  assert(button_packet(session, 4).empty());
  const auto one = button_payload(session, 1);
  assert(one.find("\"sequence\":1") != std::string::npos);
  assert(one.find(session + "-1") != std::string::npos);
  assert(one != button_payload(session, 2));
  assert(one != button_payload(std::string(32, 'c'), 1));
  const auto event_packet = button_packet(session, 1);
  assert(event_packet[0] == 0x32);  // QoS1, no DUP or RETAIN
  assert(event_packet[1] & 0x80);  // multibyte remaining length
  assert(std::string(event_packet.end() - one.size(), event_packet.end()) == one);
  const std::string nonce(32, 'a');
  assert(valid_nonce(nonce));
  assert(!valid_nonce(std::string(31, 'a')));
  assert(!valid_nonce(std::string(32, 'A')));
  assert(!valid_nonce(std::string(32, '\"')));
  assert(valid_endpoint("example-ats.iot.us-east-1.amazonaws.com"));
  assert(!valid_endpoint("example-ats.iot.us-west-2.amazonaws.com"));
  assert(!valid_endpoint("example.iot.us-east-1.amazonaws.com"));
  assert(!valid_endpoint("https://example-ats.iot.us-east-1.amazonaws.com"));
  assert(!valid_endpoint("example-ats.iot.us-east-1.amazonaws.com.evil"));
  const Bytes expected{0x10, 0x19, 0, 4, 'M', 'Q', 'T', 'T', 4, 2, 0, 30, 0, 13,
                       'a','t','o','m','-','l','i','t','e','-','0','0','1'};
  assert(connect_packet() == expected);
  const auto pub = publish_packet(nonce);
  assert(pub[0] == 0x32);
  assert(pub[1] == 124);
  assert(pub[2] == 0 && pub[3] == 27);
  assert(std::string(pub.begin() + 4, pub.begin() + 31) == topic);
  assert(pub[31] == 0 && pub[32] == 1);
  assert(std::string(pub.begin() + 33, pub.end()) == payload(nonce));
  const auto larger = packet(0x32, Bytes(128));
  assert(larger[1] == 128 && larger[2] == 1);
  assert(connack({0x20,2,0,0}));
  assert(!connack({0x20,2,1,0}));
  assert(!connack({0x20,2,0,5}));
  assert(puback({0x40,2,0,1}));
  assert(!puback({0x40,2,0,2}));
  assert(!puback({0x40,3,0,1}));
  OneShot gate;
  assert(gate.arm()); assert(!gate.arm());
  assert(publish_packet("bad").empty());
  assert(packet(0x32, Bytes(2049)).empty());
}
