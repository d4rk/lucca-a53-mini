import asyncio
from bleak import BleakClient
from ble_worker import BLEWorker
from characteristic_parsers import get_parser

class CoffeeMachineAPI:
    """
    A high-level API for controlling the coffee machine via Bluetooth LE.
    """

    # Define characteristic UUIDs as class constants for clarity and easy access
    UUID_MACHINE_POWER = "acab0002-67f5-479e-8711-b3b99198ce6c" # Timer State / Machine Power
    UUID_SCHEDULE = "acab0003-67f5-479e-8711-b3b99198ce6c"
    UUID_CURRENT_TIME = "acab0005-67f5-479e-8711-b3b99198ce6c"
    UUID_TIMER_TIME = "acab0004-67f5-479e-8711-b3b99198ce6c"
    UUID_BREW_BOILER = "acab0002-77f5-479e-8711-b3b99198ce6c"
    UUID_STEAM_BOILER = "acab0003-77f5-479e-8711-b3b99198ce6c"

    def __init__(self, address: str):
        """
        Initializes the CoffeeMachineAPI with the BLE device address.

        Args:
            address: The BLE address of the coffee machine.
        """
        self._address = address
        self._ble_worker = BLEWorker()
        self._is_connected = False
        self._polling_result_queue = None

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
                print(f"Connected to {self._address}.")
            else:
                print(f"Failed to connect: {result.get('error', 'Unknown error')}")
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
            print(f"Disconnected from {self._address}.")

    async def get_status(self) -> list:
        """
        Reads and returns the current status of all relevant characteristics.

        Returns:
            A list of service dictionaries, each containing characteristic data.
        """
        if not self._is_connected:
            raise ConnectionError("Not connected to the coffee machine.")

        # Request all characteristics from the worker
        result_queue = self._ble_worker.list_characteristics(self._address, poll_interval=0)
        raw_characteristics_data = await asyncio.to_thread(result_queue.get) # Blocking call in async context

        if isinstance(raw_characteristics_data, dict) and "error" in raw_characteristics_data:
            raise Exception(f"Error fetching characteristics: {raw_characteristics_data['error']}")
        
        return raw_characteristics_data

    async def set_machine_power(self, on: bool):
        """
        Turns the coffee machine power on or off.

        Args:
            on: True to turn on, False to turn off.
        """
        if not self._is_connected:
            raise ConnectionError("Not connected to the coffee machine.")

        value = bytearray([0x01 if on else 0x00])
        print(f"Setting machine power to {'On' if on else 'Off'} (writing {value.hex()} to {self.UUID_MACHINE_POWER})...")
        write_result_queue = self._ble_worker.write_characteristic(self.UUID_MACHINE_POWER, value)
        result = await asyncio.to_thread(write_result_queue.get)
        if not result.get("success"):
            raise Exception(f"Failed to set machine power: {result.get('error', 'Unknown error')}")
        print("Machine power command sent.")

    async def set_timer_state(self, enabled: bool):
        """
        Enables or disables the schedule timer.

        Args:
            enabled: True to enable, False to disable.
        """
        if not self._is_connected:
            raise ConnectionError("Not connected to the coffee machine.")

        value = bytearray([0x01 if enabled else 0x00])
        print(f"Setting timer state to {'Enabled' if enabled else 'Disabled'} (writing {value.hex()} to {self.UUID_MACHINE_POWER})...")
        write_result_queue = self._ble_worker.write_characteristic(self.UUID_MACHINE_POWER, value)
        result = await asyncio.to_thread(write_result_queue.get)
        if not result.get("success"):
            raise Exception(f"Failed to set timer state: {result.get('error', 'Unknown error')}")
        print("Timer state command sent.")

    async def get_schedule(self) -> dict:
        """
        Retrieves the current weekly schedule from the machine.

        Returns:
            A dictionary representing the weekly schedule.
        """
        if not self._is_connected:
            raise ConnectionError("Not connected to the coffee machine.")

        print("Fetching schedule...")
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

        # This is where you'd convert the high-level schedule_data dict
        # into the 84-byte bytearray format required by the UUID_SCHEDULE characteristic.
        # This encoding logic is complex and needs to be implemented.
        encoded_schedule = self._encode_schedule(schedule_data)
        
        print(f"Setting schedule (writing {encoded_schedule.hex()} to {self.UUID_SCHEDULE})...")
        write_result_queue = self._ble_worker.write_characteristic(self.UUID_SCHEDULE, encoded_schedule)
        result = await asyncio.to_thread(write_result_queue.get)
        if not result.get("success"):
            raise Exception(f"Failed to set schedule: {result.get('error', 'Unknown error')}")
        print("Schedule command sent.")

    def _encode_schedule(self, schedule_data: dict) -> bytearray:
        """
        Encodes the high-level schedule dictionary into the 84-byte bytearray format.
        """
        # Initialize an empty 84-byte bytearray (7 days * 3 slots * 4 bytes/slot)
        encoded_bytes = bytearray(84)
        
        DAYS_OF_WEEK_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        for day_index, day_name in enumerate(DAYS_OF_WEEK_ORDER):
            slots = schedule_data.get(day_name, [])
            for slot_index in range(3): # Max 3 slots per day
                offset = (day_index * 3 + slot_index) * 4
                
                if slot_index < len(slots):
                    slot = slots[slot_index]
                    start_time_str = slot.get("start", "00:00")
                    end_time_str = slot.get("end", "00:00")
                    boiler_on = slot.get("boiler_on", False)

                    start_hour, start_minute = map(int, start_time_str.split(':'))
                    end_hour, end_minute = map(int, end_time_str.split(':'))

                    # Reconstruct the 4-byte slot data based on our understanding
                    # Byte 0: End Minute
                    # Byte 1: End Hour
                    # Byte 2: Start Minute
                    # Byte 3: Start Hour (lower 7 bits) + Boiler On (MSB)

                    encoded_bytes[offset] = end_minute
                    encoded_bytes[offset + 1] = end_hour
                    encoded_bytes[offset + 2] = start_minute
                    
                    start_hour_byte = start_hour & 0x7F # Mask out MSB
                    if boiler_on:
                        start_hour_byte |= 0x80 # Set MSB for boiler on
                    encoded_bytes[offset + 3] = start_hour_byte
                else:
                    # If slot is not provided, ensure it's all zeros (disabled)
                    encoded_bytes[offset:offset+4] = bytearray([0x00, 0x00, 0x00, 0x00])
        
        return encoded_bytes

    async def start_polling(self, poll_interval: float):
        """
        Starts polling all characteristics and returns a queue for results.
        """
        if not self._is_connected:
            raise ConnectionError("Not connected to the coffee machine.")
        self._polling_result_queue = self._ble_worker.list_characteristics(self._address, poll_interval)
        return self._polling_result_queue

    async def stop_polling(self):
        """
        Stops any active polling.
        """
        if self._polling_result_queue:
            # There's no explicit stop polling command in ble_worker, 
            # but stopping the worker will stop polling.
            # For now, we'll just clear the reference.
            self._polling_result_queue = None
