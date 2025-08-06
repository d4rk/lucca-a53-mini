import asyncio
from bleak import BleakClient
from bt.ble_worker import BLEWorker
from bt.ble_utils import discover_s1_devices
from parsers.characteristic_parsers import get_parser
from datetime import datetime, timedelta

class CoffeeMachine:
    """
    A high-level API for controlling the coffee machine via Bluetooth LE.
    """

    # Define characteristic UUIDs as class constants for clarity and easy access
    UUID_TIMER_STATE = "acab0002-67f5-479e-8711-b3b99198ce6c" # Timer State / Machine Power
    UUID_SCHEDULE = "acab0003-67f5-479e-8711-b3b99198ce6c"
    UUID_CURRENT_TIME = "acab0005-67f5-479e-8711-b3b99198ce6c"
    UUID_LAST_SYNC_TIME = "acab0004-67f5-479e-8711-b3b99198ce6c"
    UUID_BREW_BOILER = "acab0002-77f5-479e-8711-b3b99198ce6c"
    UUID_STEAM_BOILER = "acab0003-77f5-479e-8711-b3b99198ce6c"

    POWER_ON = True
    POWER_OFF = False

    def __init__(self, address: str, logging_enabled: bool = True):
        """
        Initializes the CoffeeMachine with the BLE device address.

        Args:
            address: The BLE address of the coffee machine.
            logging_enabled: Whether to enable logging. Defaults to True.
        """
        self._address = address
        self._ble_worker = BLEWorker()
        self._is_connected = False
        self.logging_enabled = logging_enabled

    async def connect(self):
        """
        Establishes a connection to the coffee machine.
        """
        if not self._is_connected:
            self._ble_worker.start()
            # Send a connect command to the worker and wait for confirmation
            connect_result_queue = self._ble_worker.connect_device(self._address)
            result = await asyncio.to_thread(connect_result_queue.get) # Blocking call in async context
            if result.get("success"):
                self._is_connected = True
                self._log(f"Connected to {self._address}.")
            else:
                self._log(f"Failed to connect: {result.get('error', 'Unknown error')}")
                self._ble_worker.stop() # Stop worker if connection fails
                raise ConnectionError(f"Failed to connect to {self._address}: {result.get('error', 'Unknown error')}")

    async def disconnect(self):
        """
        Closes the connection to the coffee machine.
        """
        if self._is_connected:
            disconnect_result_queue = self._ble_worker.disconnect_device()
            await asyncio.to_thread(disconnect_result_queue.get) # Wait for disconnect confirmation
            self._ble_worker.stop()
            self._is_connected = False
            self._log(f"Disconnected from {self._address}.")

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

        self._log(f"Fetching {name} boiler data...")
        result_queue = self._ble_worker.read_characteristic(uuid)
        raw_data = await asyncio.to_thread(result_queue.get)

        if isinstance(raw_data, dict) and "error" in raw_data:
            raise Exception(f"Error fetching {name} boiler data: {raw_data['error']}")

        parser = get_parser(uuid)
        if parser:
            parsed_data = parser.parse_value(raw_data)
            if parsed_data and len(parsed_data) >= 2:
                state_str = parsed_data[0][1]
                temp_str = parsed_data[1][1]
                return {
                    "state": state_str,
                    "temp": temp_str
                }
        return {"state": "Unknown", "temp": "Unknown"}

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
        self._log(f"Setting timer state to {'Enabled' if enabled else 'Disabled'} (writing {value.hex()} to {self.UUID_TIMER_STATE})...")
        write_result_queue = self._ble_worker.write_characteristic(self.UUID_TIMER_STATE, value)
        result = await asyncio.to_thread(write_result_queue.get)
        if not result.get("success"):
            raise Exception(f"Failed to set timer state: {result.get('error', 'Unknown error')}")
        self._log("Timer state command sent.")

    async def get_schedule(self) -> dict:
        """
        Retrieves the current weekly schedule from the machine.

        Returns:
            A dictionary representing the weekly schedule.
        """
        if not self._is_connected:
            raise ConnectionError("Not connected to the coffee machine.")

        self._log("Fetching schedule...")
        result_queue = self._ble_worker.read_characteristic(self.UUID_SCHEDULE)
        raw_schedule_data = await asyncio.to_thread(result_queue.get)

        if isinstance(raw_schedule_data, dict) and "error" in raw_schedule_data:
            raise Exception(f"Error fetching schedule: {raw_schedule_data['error']}")

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

        self._log(f"Setting schedule (writing {encoded_schedule.hex()} to {self.UUID_SCHEDULE})...")
        write_result_queue = self._ble_worker.write_characteristic(self.UUID_SCHEDULE, encoded_schedule)
        result = await asyncio.to_thread(write_result_queue.get)
        if not result.get("success"):
            raise Exception(f"Failed to set schedule: {result.get('error', 'Unknown error')}")
        self._log("Schedule command sent.")

    async def get_current_time(self) -> datetime:
        """
        Retrieves the current time from the machine.

        Returns:
            A datetime object representing the current time.
        """
        if not self._is_connected:
            raise ConnectionError("Not connected to the coffee machine.")

        self._log("Fetching current time...")
        result_queue = self._ble_worker.read_characteristic(self.UUID_CURRENT_TIME)
        raw_time_data = await asyncio.to_thread(result_queue.get)

        if isinstance(raw_time_data, dict) and "error" in raw_time_data:
            raise Exception(f"Error fetching current time: {raw_time_data['error']}")

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
        self._log("Powering on the machine...")
        await self._set_power_state(self.POWER_ON)
        self._log("Machine powered on successfully.")

    async def power_off(self):
        """
        Powers off the machine by setting a specific schedule and manipulating time.
        """
        self._log("Powering off the machine...")
        await self._set_power_state(self.POWER_OFF)
        self._log("Machine powered off successfully.")

    async def _set_power_state(self, power_state: bool):
        """
        Sets the power state of the machine by setting a specific schedule and manipulating time.
        """
        if not self._is_connected:
            raise ConnectionError("Not connected to the coffee machine.")

        # Read the current schedule and save a copy of it to schedule.bak
        self._log("Reading current schedule...")
        original_schedule = await self.get_schedule()
        self._backup_schedule(original_schedule)
        await self.enable_schedule(True)

        # Setting the schedule to: Monday: Slot 1: 9AM - 10AM, Boiler ON
        self._log("Setting new schedule...")
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
        self._log("New schedule set.")

        # Setting the time to the specified time.
        if power_state == self.POWER_ON:
            time = datetime(2024, 1, 1, 9, 5, 0)
            self._log(f"Setting machine time to Monday 9:01AM (within temp schedule).")
        else:
            time = datetime(2024, 1, 1, 10, 5, 0)
            self._log(f"Setting machine time to Monday 10:01AM (outside temp schedule).")

        last_sync_time = time - timedelta(minutes=1)
        await self.set_last_sync_time(last_sync_time)
        await self.set_current_time(time)
        self._log("Machine time set.")

        await asyncio.sleep(1)  # Wait for the machine to process the change
        # Disabling the timer state to prevent auto-scheduling.
        await self.enable_schedule(False)
        await asyncio.sleep(1)  # Wait for the machine to process the change

        # Setting the time back to the current local time.
        self._log("Setting machine time back to current local time...")
        current_local_time = datetime.now()
        last_sync_time = current_local_time - timedelta(minutes=1)
        await self.set_last_sync_time(current_local_time)
        await self.set_current_time(current_local_time)
        self._log("Machine time set back to current local time.")

        # Restore the original schedule
        self._log("Restoring original schedule...")
        await self.set_schedule(original_schedule)
        self._log("Original schedule restored.")

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

        self._log(f"Setting {description} to {dt.strftime('%Y-%m-%d %H:%M:%S')} (writing {value.hex()} to {uuid})...")
        write_result_queue = self._ble_worker.write_characteristic(uuid, value)
        result = await asyncio.to_thread(write_result_queue.get)
        if not result.get("success"):
            raise Exception(f"Failed to set {description}: {result.get('error', 'Unknown error')}")
        self._log(f"{description.capitalize()} command sent.")

    def _log(self, message: str):
        """
        Prints a message if logging is enabled.
        """
        if self.logging_enabled:
            print(message)

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
            self._log(f"Original schedule saved to {backup_filename}")
        except Exception as e:
            self._log(f"Warning: Could not save original schedule: {e}")

    @staticmethod
    async def discover():
        """
        Discovers available S1 coffee machines.

        Returns:
            A list of discovered S1 devices.
        """
        return await discover_s1_devices()
