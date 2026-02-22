import unittest
from datetime import datetime
from a53.parsers.characteristic_parsers import (
    DateTimeParser,
    TimerStateParser,
    ScheduleParser,
    BoilerParser,
    get_parser,
)
from a53.parsers.constants import (
    UUID_CURRENT_TIME,
    UUID_TIMER_STATE,
    UUID_SCHEDULE,
    UUID_BREW_BOILER,
)


class TestCharacteristicParsers(unittest.TestCase):
    def test_datetime_parser(self):
        parser = DateTimeParser("Test Time")
        now = datetime.now()
        encoded = parser.encode_value(now)
        self.assertEqual(len(encoded), 7)
        decoded = parser.parse_value(encoded)
        self.assertEqual(decoded[0][1], now.strftime("%Y-%m-%d %H:%M:%S"))

    def test_timer_state_parser(self):
        parser = TimerStateParser()
        encoded = parser.encode_value(True)
        self.assertEqual(encoded, bytearray([0x01]))
        decoded = parser.parse_value(encoded)
        self.assertEqual(decoded[0][1], True)

        encoded = parser.encode_value(False)
        self.assertEqual(encoded, bytearray([0x00]))
        decoded = parser.parse_value(encoded)
        self.assertEqual(decoded[0][1], False)

    def test_schedule_parser(self):
        parser = ScheduleParser()
        schedule = {"Monday": [{"start": "06:00", "end": "09:00", "boiler_on": True}]}
        encoded = parser.encode_value(schedule)
        self.assertEqual(len(encoded), 84)
        decoded = parser.parse_value(encoded)
        self.assertEqual(decoded["Monday"][0]["start"], "06:00")

    def test_boiler_parser(self):
        parser = BoilerParser("Brew")
        # Simulate raw data for brew boiler
        # 90 degrees C = 900 = 0x0384. Little-endian: 84 03. Status 1.
        raw_data = bytearray([0x84, 0x03, 0x01, 0x00])
        decoded = parser.parse_value(raw_data)
        self.assertIn(("Brew Boiler Temp", 90.0), decoded)
        self.assertIn(("Brew Boiler Status", 1), decoded)

        # Test negative temperature
        # -1.0 degrees C = -10. -10 in 16-bit 2's complement is 0xFFF6.
        # Little-endian: F6 FF. Status 0.
        raw_data_neg = bytearray([0xF6, 0xFF, 0x00, 0x00])
        decoded_neg = parser.parse_value(raw_data_neg)
        self.assertIn(("Brew Boiler Temp", -1.0), decoded_neg)
        self.assertIn(("Brew Boiler Status", 0), decoded_neg)

    def test_get_parser(self):
        self.assertIsInstance(get_parser(UUID_CURRENT_TIME), DateTimeParser)
        self.assertIsInstance(get_parser(UUID_TIMER_STATE), TimerStateParser)
        self.assertIsInstance(get_parser(UUID_SCHEDULE), ScheduleParser)
        self.assertIsInstance(get_parser(UUID_BREW_BOILER), BoilerParser)


if __name__ == "__main__":
    unittest.main()
