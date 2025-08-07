import unittest
from a53.parsers.schedule_coder import ScheduleCoder


class TestScheduleCoder(unittest.TestCase):
    def test_encode_decode_schedule(self):
        schedule = {
            "Monday": [
                {"start": "06:00", "end": "09:00", "boiler_on": True},
                {"start": "17:00", "end": "22:00", "boiler_on": False},
            ],
            "Friday": [{"start": "12:00", "end": "13:00", "boiler_on": True}],
        }

        encoded = ScheduleCoder.encode_schedule(schedule)
        self.assertEqual(len(encoded), 84)

        decoded = ScheduleCoder.decode_schedule(encoded)

        self.assertEqual(decoded["Monday"][0]["start"], "06:00")
        self.assertEqual(decoded["Monday"][0]["end"], "09:00")
        self.assertTrue(decoded["Monday"][0]["boiler_on"])

        self.assertEqual(decoded["Monday"][1]["start"], "17:00")
        self.assertEqual(decoded["Monday"][1]["end"], "22:00")
        self.assertFalse(decoded["Monday"][1]["boiler_on"])

        self.assertEqual(decoded["Friday"][0]["start"], "12:00")
        self.assertEqual(decoded["Friday"][0]["end"], "13:00")
        self.assertTrue(decoded["Friday"][0]["boiler_on"])

    def test_empty_schedule(self):
        schedule = {}
        encoded = ScheduleCoder.encode_schedule(schedule)
        self.assertEqual(len(encoded), 84)
        self.assertTrue(all(b == 0 for b in encoded))

        decoded = ScheduleCoder.decode_schedule(encoded)
        self.assertEqual(decoded, {})


if __name__ == "__main__":
    unittest.main()