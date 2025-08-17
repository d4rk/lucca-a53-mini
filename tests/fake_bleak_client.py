import asyncio
from datetime import datetime
from typing import Dict, Optional, Callable, Any
from a53.parsers.constants import (
    UUID_TIMER_STATE,
    UUID_SCHEDULE,
    UUID_CURRENT_TIME,
    UUID_LAST_SYNC_TIME,
    UUID_BREW_BOILER,
    UUID_STEAM_BOILER,
)
from a53.parsers.characteristic_parsers import get_parser


class FakeBleakClient:
    """
    A fake BleakClient for testing purposes.
    It simulates BLE characteristic read/write operations and connection status.
    """

    def __init__(
        self,
        address: str = "AA:BB:CC:DD:EE:FF",
        disconnected_callback: Optional[Callable[[Any], None]] = None,
    ):
        self.address = address
        self._is_connected = False
        self._disconnected_callback = disconnected_callback
        self._characteristics: Dict[str, bytearray] = {}
        self._initialize_characteristics()
        self._notifications: Dict[str, Callable[[bytearray], None]] = {}

    def _initialize_characteristics(self) -> None:
        """
        Initializes characteristics with default or reasonable test values.
        """
        # Using current date for time characteristics
        now = datetime.now()
        self.set_current_time(
            now.year, now.month, now.day, now.hour, now.minute, now.second
        )
        self.set_last_synced_time(
            now.year, now.month, now.day, now.hour, now.minute, now.second
        )

        # Set Boiler temperatures to some default values
        self.set_brew_boiler_temp(90.0)
        self.set_steam_boiler_temp(120.0)

        self.set_schedule_status(True)  # Enabled by default
        self.set_schedule({})  # Empty schedule by default

    def set_schedule_status(self, enabled: bool):
        parser = get_parser(UUID_TIMER_STATE)
        self._characteristics[UUID_TIMER_STATE] = parser.encode_value(enabled)

    def set_schedule(self, schedule_data: Dict):
        parser = get_parser(UUID_SCHEDULE)
        self._characteristics[UUID_SCHEDULE] = parser.encode_value(schedule_data)

    def set_brew_boiler_temp(self, temp: float):
        parser = get_parser(UUID_BREW_BOILER)
        # BoilerParser.encode_value expects a tuple (temp, status_code_byte)
        # Assuming status_code_byte is always 0x01 for simplicity in fake client
        self._characteristics[UUID_BREW_BOILER] = parser.encode_value((temp, 0x01))

    def set_steam_boiler_temp(self, temp: float):
        parser = get_parser(UUID_STEAM_BOILER)
        self._characteristics[UUID_STEAM_BOILER] = parser.encode_value((temp, 0x01))

    def set_current_time(
        self, year: int, month: int, day: int, hour: int, minute: int, second: int
    ):
        dt_obj = datetime(year, month, day, hour, minute, second)
        parser = get_parser(UUID_CURRENT_TIME)
        self._characteristics[UUID_CURRENT_TIME] = parser.encode_value(dt_obj)

    def set_last_synced_time(
        self, year: int, month: int, day: int, hour: int, minute: int, second: int
    ):
        dt_obj = datetime(year, month, day, hour, minute, second)
        parser = get_parser(UUID_LAST_SYNC_TIME)
        self._characteristics[UUID_LAST_SYNC_TIME] = parser.encode_value(dt_obj)

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    async def connect(self):
        """Simulates connecting to the device."""
        await asyncio.sleep(0.01)  # Simulate async operation
        self._is_connected = True
        print(f"FakeBleakClient: Connected to {self.address}")

    async def disconnect(self):
        """Simulates disconnecting from the device."""
        await asyncio.sleep(0.01)  # Simulate async operation
        self._is_connected = False
        print(f"FakeBleakClient: Disconnected from {self.address}")
        if self._disconnected_callback:
            self._disconnected_callback(self)

    async def read_gatt_char(self, uuid: str) -> bytearray:
        """Simulates reading a GATT characteristic."""
        if not self._is_connected:
            raise ConnectionError("Not connected to fake device.")
        await asyncio.sleep(0.01)  # Simulate async operation
        uuid_lower = uuid.lower()
        if uuid_lower in self._characteristics:
            print(
                f"FakeBleakClient: Reading {uuid_lower} -> {self._characteristics[uuid_lower].hex()}"
            )
            return self._characteristics[uuid_lower]
        else:
            raise ValueError(f"Characteristic {uuid} not found in fake client.")

    async def write_gatt_char(self, uuid: str, data: bytearray, response: bool = False):
        """Simulates writing a GATT characteristic."""
        if not self._is_connected:
            raise ConnectionError("Not connected to fake device.")
        await asyncio.sleep(0.01)  # Simulate async operation
        uuid_lower = uuid.lower()
        if uuid_lower in self._characteristics:
            # For read-only characteristics, raise an error
            if uuid_lower in [UUID_BREW_BOILER, UUID_STEAM_BOILER]:
                raise PermissionError(f"Characteristic {uuid} is read-only.")
            self._characteristics[uuid_lower] = bytearray(data)  # Store a copy
            print(f"FakeBleakClient: Writing {data.hex()} to {uuid_lower}")
            # Simulate notification if there's a callback registered
            if uuid_lower in self._notifications:
                # This is a simplified notification. In a real scenario,
                # the notification would be triggered by a change in the characteristic
                # on the "device" side, not directly by a write.
                # For testing, we can trigger it immediately.
                self._notifications[uuid_lower](self._characteristics[uuid_lower])
        else:
            raise ValueError(f"Characteristic {uuid} not found in fake client.")

    async def start_notify(self, uuid: str, callback: Callable[[bytearray], None]):
        """Simulates starting notifications for a characteristic."""
        if not self._is_connected:
            raise ConnectionError("Not connected to fake device.")
        await asyncio.sleep(0.01)
        uuid_lower = uuid.lower()
        self._notifications[uuid_lower] = callback
        print(f"FakeBleakClient: Started notifications for {uuid_lower}")

    async def stop_notify(self, uuid: str):
        """Simulates stopping notifications for a characteristic."""
        if not self._is_connected:
            raise ConnectionError("Not connected to fake device.")
        await asyncio.sleep(0.01)
        uuid_lower = uuid.lower()
        if uuid_lower in self._notifications:
            del self._notifications[uuid_lower]
            print(f"FakeBleakClient: Stopped notifications for {uuid_lower}")

    def set_characteristic_value(self, uuid: str, value: bytearray):
        """
        Allows tests to set the raw byte value of a characteristic.
        """
        uuid_lower = uuid.lower()
        if uuid_lower in self._characteristics:
            self._characteristics[uuid_lower] = bytearray(value)
            print(f"FakeBleakClient: Test value for {uuid_lower} set to {value.hex()}")
        else:
            raise ValueError(f"Characteristic {uuid} not found in fake client.")

    def get_characteristic_value(self, uuid: str) -> bytearray:
        """
        Allows tests to get the raw byte value of a characteristic.
        """
        uuid_lower = uuid.lower()
        if uuid_lower in self._characteristics:
            return self._characteristics[uuid_lower]
        else:
            raise ValueError(f"Characteristic {uuid} not found in fake client.")

    def get_parsed_characteristic_value(self, uuid: str) -> Any:
        """
        Allows tests to get the parsed value of a characteristic using the actual parsers.
        """
        uuid_lower = uuid.lower()
        raw_value = self.get_characteristic_value(uuid_lower)
        parser = get_parser(uuid_lower)
        if parser:
            return parser.parse_value(raw_value)
        else:
            raise ValueError(f"No parser found for characteristic {uuid}.")
