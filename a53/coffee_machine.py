import asyncio
from bleak import BleakClient
from a53.bt.ble_utils import discover_s1_devices
from a53.parsers.characteristic_parsers import get_parser
from datetime import datetime, timedelta
from a53.common.logging import get_logger

L = get_logger(__name__)

class CoffeeMachine:
    """
    A high-level API for controlling the coffee machine via Bluetooth LE.
    """

    from a53.parsers.constants import (
        UUID_TIMER_STATE,
        UUID_SCHEDULE,
        UUID_CURRENT_TIME,
        UUID_LAST_SYNC_TIME,
        UUID_BREW_BOILER,
        UUID_STEAM_BOILER,
    )

    POWER_ON = True
    POWER_OFF = False

    def __init__(self, address: str):
        """
        Initializes the CoffeeMachine with the BLE device address.

        Args:
            address: The BLE address of the coffee machine.
        """
        self._address = address
        self._client = BleakClient(address, disconnected_callback=self._on_disconnect)
        self._is_connected = False

    def _on_disconnect(self, client):
        self._is_connected = False
        L.warning(f"Disconnected from {client.address}. Will attempt to reconnect.")
        asyncio.create_task(self.connect())

    async def connect(self):
        """
        Establishes a connection to the coffee machine.
        """
        if self._is_connected:
            return

        L.info(f"Attempting to connect to {self._address}...")
        try:
            await self._client.connect()
            self._is_connected = self._client.is_connected
            if self._is_connected:
                L.info(f"Connected to {self._address}.")
            else:
                L.warning(f"Failed to connect to {self._address}.")
        except Exception as e:
            L.error(f"Failed to connect to {self._address}: {e}")
            self._is_connected = False

    async def disconnect(self):
        """
        Closes the connection to the coffee machine.
        """
        if self._is_connected:
            await self._client.disconnect()
            self._is_connected = False
            L.info(f"Disconnected from {self._address}.")

    async def get_brew_boiler_temp(self) -> dict:
        """
        Retrieves the brew boiler temperature and state.

        Returns:
            A dictionary with "temp" and "state".
        """
        return await self._get_boiler_data(self.UUID_BREW_BOILER, "Brew")

    async def get_steam_boiler_temp(self) -> dict:
        """
        Retrieves the steam boiler temperature and state.

        Returns:
            A dictionary with "temp" and "state".
        """
        return await self._get_boiler_data(self.UUID_STEAM_BOILER, "Steam")

    async def _get_boiler_data(self, uuid: str, name: str) -> dict:
        """
        Reads and parses boiler data from a given characteristic.
        """
        if not self._is_connected:
            raise ConnectionError("Not connected to the coffee machine.")

        L.info(f"Fetching {name} boiler data...")
        raw_data = await self._client.read_gatt_char(uuid)

        parser = get_parser(uuid)
        if parser:
            parsed_data = parser.parse_value(raw_data)
            if parsed_data and len(parsed_data) >= 2:
                state_str = parsed_data[0][1]
                temp_str = parsed_data[1][1]
                return {
                    "name": name,
                    "state": state_str,
                    "temp": temp_str
                }
        return {"name": name, "state": "Unknown", "temp": "Unknown"}

    async def enable_schedule(self, enabled: bool):
        """
        Enables or disables the schedule timer.

        Args:
            enabled: True to enable, False to disable.
        """
        if not self._is_connected:
            raise ConnectionError("Not connected to the coffee machine.")

        parser = get_parser(self.UUID_TIMER_STATE)
        if not parser:
            raise Exception(f"No parser found for UUID {self.UUID_TIMER_STATE}")

        value = parser.encode_value(enabled)
        L.info(f"Setting timer state to {'Enabled' if enabled else 'Disabled'} (writing {value.hex()} to {self.UUID_TIMER_STATE})...")
        await self._client.write_gatt_char(self.UUID_TIMER_STATE, value)
        L.info("Timer state command sent.")

    async def get_timer_state(self) -> bool:
        """
        Retrieves the current state of the schedule timer (enabled/disabled).

        Returns:
            True if enabled, False if disabled.
        """
        if not self._is_connected:
            raise ConnectionError("Not connected to the coffee machine.")

        L.info("Fetching timer state...")
        raw_data = await self._client.read_gatt_char(self.UUID_TIMER_STATE)

        parser = get_parser(self.UUID_TIMER_STATE)
        if parser:
            parsed_data = parser.parse_value(raw_data)
            # Assuming the parser for UUID_TIMER_STATE returns a boolean or a value that can be interpreted as boolean
            # The enable_schedule method encodes a boolean, so parsing should return a boolean or similar.
            if parsed_data and len(parsed_data) > 0:
                # The parser returns a list of (description, value) tuples. We need the value.
                return bool(parsed_data[0][1])
        raise Exception("Failed to parse timer state.")

    async def get_schedule(self) -> dict:
        """
        Retrieves the current weekly schedule from the machine.

        Returns:
            A dictionary representing the weekly schedule.
        """
        if not self._is_connected:
            raise ConnectionError("Not connected to the coffee machine.")

        L.info("Fetching schedule...")
        raw_schedule_data = await self._client.read_gatt_char(self.UUID_SCHEDULE)

        parser = get_parser(self.UUID_SCHEDULE)
        if parser:
            parsed_schedule = parser.parse_value(raw_schedule_data)
            return parsed_schedule
        return {}

    async def set_schedule(self, schedule_data: dict):
        """
        Sets the weekly schedule on the machine.

        Args:
            schedule_data: A dictionary representing the weekly schedule.
                           Example: { "Monday": [{"start": "06:00", "end": "09:00", "boiler_on": True}], ... }
        """
        if not self._is_connected:
            raise ConnectionError("Not connected to the coffee machine.")

        parser = get_parser(self.UUID_SCHEDULE)
        if not parser:
            raise Exception(f"No parser found for UUID {self.UUID_SCHEDULE}")

        encoded_schedule = parser.encode_value(schedule_data)

        L.info(f"Setting schedule (writing {encoded_schedule.hex()} to {self.UUID_SCHEDULE})...")
        await self._client.write_gatt_char(self.UUID_SCHEDULE, encoded_schedule)
        L.info("Schedule command sent.")

    async def get_current_time(self) -> datetime:
        """
        Retrieves the current time from the machine.

        Returns:
            A datetime object representing the current time.
        """
        if not self._is_connected:
            raise ConnectionError("Not connected to the coffee machine.")

        L.info("Fetching current time...")
        raw_time_data = await self._client.read_gatt_char(self.UUID_CURRENT_TIME)

        parser = get_parser(self.UUID_CURRENT_TIME)
        if parser:
            # The parser returns a list of (description, value) tuples. We need the value.
            parsed_values = parser.parse_value(raw_time_data)
            if parsed_values and len(parsed_values) > 0:
                # Assuming the DateTimeParser returns a string in "YYYY-MM-DD HH:MM:SS" format
                dt_str = parsed_values[0][1]
                return datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        raise Exception("Failed to parse current time.")

    async def set_current_time(self, dt: datetime):
        """
        Sets the current time on the machine.

        Args:
            dt: A datetime object representing the time to set.
        """
        await self._set_time_characteristic(dt, self.UUID_CURRENT_TIME, "current time")

    async def set_last_sync_time(self, dt: datetime):
        """
        Sets the last sync time on the machine.

        Args:
            dt: A datetime object representing the time to set.
        """
        await self._set_time_characteristic(dt, self.UUID_LAST_SYNC_TIME, "last sync time")

    async def power_on(self):
        """
        Powers on the machine by setting a specific schedule and manipulating time.
        """
        L.info("Powering on the machine...")
        await self._set_power_state(self.POWER_ON)
        L.info("Machine powered on successfully.")

    async def power_off(self):
        """
        Powers off the machine by setting a specific schedule and manipulating time.
        """
        L.info("Powering off the machine...")
        await self._set_power_state(self.POWER_OFF)
        L.info("Machine powered off successfully.")

    async def _set_power_state(self, power_state: bool):
        """
        Sets the power state of the machine by setting a specific schedule and manipulating time.
        """
        if not self._is_connected:
            raise ConnectionError("Not connected to the coffee machine.")

        L.info("Reading current schedule...")
        original_schedule = await self.get_schedule()
        self._backup_schedule(original_schedule)
        await self.enable_schedule(True)

        L.info("Setting new schedule...")
        new_schedule = {
            "Monday": [{
                "start": "09:00",
                "end": "10:00",
                "boiler_on": True
            }],
            "Tuesday": [],
            "Wednesday": [],
            "Thursday": [],
            "Friday": [],
            "Saturday": [],
            "Sunday": []
        }
        await self.set_schedule(new_schedule)
        L.info("New schedule set.")

        if power_state == self.POWER_ON:
            time = datetime(2024, 1, 1, 9, 5, 0)
            L.info(f"Setting machine time to Monday 9:05AM (within temp schedule).")
        else:
            time = datetime(2024, 1, 1, 10, 5, 0)
            L.info(f"Setting machine time to Monday 10:05AM (outside temp schedule).")

        last_sync_time = time - timedelta(minutes=1)
        await self.set_last_sync_time(last_sync_time)
        await self.set_current_time(time)
        L.info("Machine time set.")

        await asyncio.sleep(1)
        await self.enable_schedule(False)
        await asyncio.sleep(1)

        L.info("Setting machine time back to current local time...")
        current_local_time = datetime.now()
        last_sync_time = current_local_time - timedelta(minutes=1)
        await self.set_last_sync_time(current_local_time)
        await self.set_current_time(current_local_time)
        L.info("Machine time set back to current local time.")

        L.info("Restoring original schedule...")
        await self.set_schedule(original_schedule)
        L.info("Original schedule restored.")

    async def _set_time_characteristic(self, dt: datetime, uuid: str, description: str):
        """
        Sets a time-based characteristic on the machine.

        Args:
            dt: A datetime object representing the time to set.
            uuid: The UUID of the characteristic to write to.
            description: A human-readable description of the characteristic (e.g., "current time").
        """
        if not self._is_connected:
            raise ConnectionError("Not connected to the coffee machine.")

        parser = get_parser(uuid)
        if not parser:
            raise Exception(f"No parser found for UUID {uuid}")

        value = parser.encode_value(dt)

        L.info(f"Setting {description} to {dt.strftime('%Y-%m-%d %H:%M:%S')} (writing {value.hex()} to {uuid})...")
        await self._client.write_gatt_char(uuid, value)
        L.info(f"{description.capitalize()} command sent.")

    def _backup_schedule(self, schedule_data: dict):
        """
        Saves the current schedule to a backup file.
        """
        try:
            import json
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"schedule.{timestamp}.json"
            with open(backup_filename, "w") as f:
                json.dump(schedule_data, f)
            L.info(f"Original schedule saved to {backup_filename}")
        except Exception as e:
            L.warning(f"Warning: Could not save original schedule: {e}")

    @staticmethod
    async def discover():
        """
        Discovers available S1 coffee machines.

        Returns:
            A list of discovered S1 devices.
        """
        return await discover_s1_devices()
