import collections
import enum
import time
from statistics import mean, stdev, linear_regression
from a53.common.logging import get_logger

L = get_logger(__name__)


class PowerState(enum.Enum):
    """Enum representing the power state of the boiler."""

    ON = "on"
    OFF = "off"
    WARMING_UP = "warming_up"
    UNKNOWN = "unknown"


class PowerStateEstimator:
    """Estimates the power state of a boiler based on temperature changes."""

    def __init__(self, target_temp=95.0, window_size=5):
        """Initializes the estimator.
        Args:
            target_temp (float, optional): The target temperature for ON state. Defaults to 95.0.
            window_size (int, optional): The number of recent temperature readings to consider. Defaults to 5.
        """
        self._temperatures = collections.deque(maxlen=window_size)
        self._timestamps = collections.deque(maxlen=window_size)
        self._slope = 0
        self._stddev = 0
        self._power_state = PowerState.UNKNOWN
        self._last_change_timestamp = time.time()
        self._target_temp = target_temp

    @property
    def is_on(self) -> bool:
        """Returns True if the boiler is considered ON or WARMING_UP."""
        return self._power_state in (PowerState.ON, PowerState.WARMING_UP)

    @property
    def power_state(self) -> PowerState:
        """Returns the current power state."""
        return self._power_state

    def set_power_state(self, state: PowerState, timestamp=None):
        """Manually sets the power state and updates the last change timestamp.
        Args:
            state (PowerState): The new power state.
            timestamp (int, optional): The timestamp in milliseconds. If None, uses system time.
        """
        if state != self._power_state:
            L.info(f"Power state changed from {self._power_state} to {state}")
            self._power_state = state
            self._last_change_timestamp = (
                time.time() if timestamp is None else timestamp
            )

    def temperature_updated(self, temperature, current_time_ms=None):
        """Updates the estimator with a new temperature reading.
        Args:
            temperature (float): The new temperature reading.
            current_time_ms (int, optional): The current time in milliseconds. If None, uses system time.
        """
        if current_time_ms is None:
            current_time = time.time()
        else:
            current_time = current_time_ms / 1000.0  # Convert to seconds
        self._temperatures.append(temperature)
        self._timestamps.append(current_time)
        self._recalculate_power_state()

    def _recalculate_power_state(self):
        """Recalculates the power state based on recent temperature readings."""
        temperature = self._temperatures[-1]
        current_time = self._timestamps[-1]
        if len(self._temperatures) < 4:
            L.debug(f"State: {self._power_state}, Temp: {temperature}")
            self.set_power_state(PowerState.UNKNOWN)
            return

        # Determine power state based on temperature trends
        slope, _ = linear_regression(list(self._timestamps), list(self._temperatures))
        stddev = stdev(self._temperatures)
        mean_temp = mean(self._temperatures)
        if mean_temp >= self._target_temp - 5 or temperature >= self._target_temp:
            # If close to or above target temp, consider it ON
            self.set_power_state(PowerState.ON, current_time)
        elif slope > 0.05 and stddev > 0.5:
            # Rapidly increasing temperature indicates WARMING_UP
            self.set_power_state(PowerState.WARMING_UP, current_time)
        elif slope < -0.01 and mean_temp < self._target_temp - 5:
            # Decreasing temperature indicates OFF
            self.set_power_state(PowerState.OFF, current_time)
        L.debug(
            f"State: {self._power_state}, Temp: {temperature}, Slope: {slope:.4f}, Stddev: {stddev:.4f}, Mean: {mean_temp:.2f}"
        )
