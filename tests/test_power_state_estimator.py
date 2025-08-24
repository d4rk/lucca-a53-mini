import unittest
import os
from a53.common.power_state_estimator import PowerStateEstimator, PowerState


class TestPowerStateEstimator(unittest.TestCase):

    def test_power_state_off_to_warming_up_to_on(self):
        estimator = PowerStateEstimator(target_temp=95.0)
        expected_states = [
            (PowerState.UNKNOWN, 3),
            (PowerState.OFF, 3),
            (PowerState.WARMING_UP, 8),
            (PowerState.ON, 10),
        ]
        self._verify_readings(estimator, "warming_up1.txt", expected_states)

    def test_power_state_off1(self):
        estimator = PowerStateEstimator(target_temp=95.0)
        expected_states = [
            (PowerState.UNKNOWN, 3),
            (PowerState.OFF, 40),
        ]
        self._verify_readings(estimator, "cooling_down1.txt", expected_states)

    def test_power_state_off2(self):
        estimator = PowerStateEstimator(target_temp=95.0)
        expected_states = [
            (PowerState.UNKNOWN, 3),
            (PowerState.ON, 24),
            (PowerState.OFF, None),
        ]
        self._verify_readings(estimator, "cooling_down2.txt", expected_states)

    def test_power_state_on(self):
        estimator = PowerStateEstimator(target_temp=95.0)
        expected_states = [
            (PowerState.UNKNOWN, 3),
            (PowerState.ON, 40),
        ]
        self._verify_readings(estimator, "on1.txt", expected_states)

    def _get_readings_from_file(self, filename):
        current_dir = os.path.dirname(__file__)
        file_path = os.path.join(current_dir, "test_data", filename)
        with open(file_path, "r") as f:
            content = [line.split(",") for line in f.readlines()]
        return [(int(timestamp), float(temp)) for timestamp, temp in content]

    def _verify_readings(self, estimator, filename, expected_states):
        readings = self._get_readings_from_file(filename)
        for expected_state, count in expected_states:
            if count is None:
                count = len(readings)
            for _ in range(count):
                timestamp, temp = readings.pop(0)
                estimator.temperature_updated(temp, timestamp)
                self.assertEqual(estimator.power_state, expected_state)


if __name__ == "__main__":
    unittest.main()
