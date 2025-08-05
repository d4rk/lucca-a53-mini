import asyncio
from bleak import BleakClient
from bt.ble_worker import BLEWorker
from bt.ble_utils import discover_s1_devices
from parsers.characteristic_parsers import get_parser
from parsers.schedule_coder import ScheduleCoder
from datetime import datetime

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

    async def set_timer_state(self, enabled: bool):
        """
        Enables or disables the schedule timer.

        Args:
            enabled: True to enable, False to disable.
        """
        if not self._is_connected:
            raise ConnectionError("Not connected to the coffee machine.")

        value = bytearray([0x01 if enabled else 0x00])
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

        encoded_schedule = ScheduleCoder.encode_schedule(schedule_data)

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
        if not self._is_connected:
            raise ConnectionError("Not connected to the coffee machine.")

        self._log("Powering on the machine...")

        # 1. Read the current schedule and save a copy of it to schedule.bak
        self._log("Reading current schedule...")
        original_schedule = await self.get_schedule()
        try:
            import json
            with open("schedule.bak", "w") as f:
                json.dump(original_schedule, f)
            self._log("Original schedule saved to schedule.bak")
        except Exception as e:
            self._log(f"Warning: Could not save original schedule: {e}")

        # 2. Setting the schedule to: Monday: Slot 1: 9AM - 10AM, Boiler ON
        self._log("Setting new schedule...")
        new_schedule = {
            "Monday": [{
                "start": "09:00",
                "end": "21:00",
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

        # 3. Setting the time to a date that is a Monday at 9AM.
        self._log("Setting machine time to Monday 9AM...")
        from datetime import datetime
        current_local_time = datetime.now() # Save current local time
        # Use a fixed Monday date for consistency, e.g., Jan 1, 2024 was a Monday
        monday_901am = datetime(2024, 1, 1, 9, 1, 0)
        await self.set_last_sync_time(monday_901am)
        await self.set_current_time(monday_901am)
        self._log("Machine time set to Monday 9:01AM (within temp schedule).")

        # 4. Disabling the timer state to prevent auto-scheduling.
        await self.set_timer_state(False)

        # 5. Setting the time back to the current local time.
        self._log("Setting machine time back to current local time...")
        current_local_time = datetime.now() # Save current local time
        await self.set_last_sync_time(current_local_time)
        await self.set_current_time(current_local_time)
        self._log("Machine time set back to current local time.")

        # 6. Restore the original schedule
        self._log("Restoring original schedule...")
        await self.set_schedule(original_schedule)
        self._log("Original schedule restored.")

        self._log("Machine powered on successfully.")

    def _encode_time_value(self, dt: datetime) -> bytearray:
        """
        Encodes a datetime object into the 7-byte format required by the machine.
        Seconds are assumed to be 0.
        """
        encoded_year = dt.year - 2000
        return bytearray([encoded_year, dt.month, dt.day, 0x00, dt.hour, dt.minute, 0x00])

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

        value = self._encode_time_value(dt)

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

    @staticmethod
    async def discover():
        """
        Discovers available S1 coffee machines.

        Returns:
            A list of discovered S1 devices.
        """
        return await discover_s1_devices()