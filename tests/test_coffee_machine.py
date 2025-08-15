
import unittest
from unittest.mock import patch, AsyncMock
import asyncio
from datetime import datetime

from a53.coffee_machine import CoffeeMachine

class TestCoffeeMachine(unittest.TestCase):

    @patch('a53.coffee_machine.BleakClient')
    def setUp(self, MockBleakClient):
        self.mock_bleak_client = MockBleakClient.return_value
        self.mock_bleak_client.connect = AsyncMock()
        self.mock_bleak_client.disconnect = AsyncMock()
        self.mock_bleak_client.read_gatt_char = AsyncMock()
        self.mock_bleak_client.write_gatt_char = AsyncMock()
        self.machine = CoffeeMachine(address="test_address")
        self.machine._client = self.mock_bleak_client

    def test_connect_and_disconnect(self):
        async def run_test():
            # Test connect
            self.mock_bleak_client.is_connected = False
            await self.machine.connect()
            self.machine._client.connect.assert_called_once()
            self.machine._is_connected = True

            # Test disconnect
            await self.machine.disconnect()
            self.machine._client.disconnect.assert_called_once()

        asyncio.run(run_test())

    def test_get_brew_boiler_temp(self):
        async def run_test():
            self.machine._is_connected = True
            self.mock_bleak_client.read_gatt_char.return_value = bytearray([0x84, 0x03, 0x01, 0x00])  # 90 degrees, status 1

            data = await self.machine.get_brew_boiler_temp()
            self.assertEqual(data['name'], "Brew")
            self.assertEqual(data['state'], "3")
            self.assertEqual(data['temp'], "90.0")

        asyncio.run(run_test())

    def test_get_steam_boiler_temp(self):
        async def run_test():
            self.machine._is_connected = True
            self.mock_bleak_client.read_gatt_char.return_value = bytearray([0x14, 0x05, 0x01, 0x00])  # 130 degrees, status 1

            data = await self.machine.get_steam_boiler_temp()
            self.assertEqual(data['name'], "Steam")
            self.assertEqual(data['state'], "5")
            self.assertEqual(data['temp'], "130.0")

        asyncio.run(run_test())

    def test_enable_disable_schedule(self):
        async def run_test():
            self.machine._is_connected = True

            # Enable schedule
            await self.machine.enable_schedule(True)
            self.mock_bleak_client.write_gatt_char.assert_called_with(self.machine.UUID_TIMER_STATE, bytearray([0x01]))

            # Disable schedule
            await self.machine.enable_schedule(False)
            self.mock_bleak_client.write_gatt_char.assert_called_with(self.machine.UUID_TIMER_STATE, bytearray([0x00]))

        asyncio.run(run_test())

    def test_get_timer_state(self):
        async def run_test():
            self.machine._is_connected = True

            # Test when timer is enabled
            self.mock_bleak_client.read_gatt_char.return_value = bytearray([0x01])
            state = await self.machine.get_timer_state()
            self.assertTrue(state)

            # Test when timer is disabled
            self.mock_bleak_client.read_gatt_char.return_value = bytearray([0x00])
            state = await self.machine.get_timer_state()
            self.assertFalse(state)

        asyncio.run(run_test())

    def test_get_and_set_schedule(self):
        async def run_test():
            self.machine._is_connected = True
            schedule = {
                "Monday": [{
                    "start": "06:00",
                    "end": "09:00",
                    "boiler_on": True
                }]
            }

            # Set schedule
            await self.machine.set_schedule(schedule)
            # We don't assert the encoded value here as it's complex. We trust the parser tests.
            self.mock_bleak_client.write_gatt_char.assert_called_with(self.machine.UUID_SCHEDULE, unittest.mock.ANY)

            # Get schedule
            # Mock the read_gatt_char to return the encoded schedule
            from a53.parsers.schedule_coder import ScheduleCoder
            self.mock_bleak_client.read_gatt_char.return_value = ScheduleCoder.encode_schedule(schedule)
            decoded_schedule = await self.machine.get_schedule()
            self.assertEqual(decoded_schedule["Monday"][0]["start"], "06:00")

        asyncio.run(run_test())

    def test_get_and_set_current_time(self):
        async def run_test():
            self.machine._is_connected = True
            now = datetime.now()

            # Set current time
            await self.machine.set_current_time(now)
            self.mock_bleak_client.write_gatt_char.assert_called_with(self.machine.UUID_CURRENT_TIME, unittest.mock.ANY)

            # Get current time
            from a53.parsers.characteristic_parsers import DateTimeParser
            self.mock_bleak_client.read_gatt_char.return_value = DateTimeParser("Current Time").encode_value(now)
            decoded_time = await self.machine.get_current_time()
            self.assertEqual(decoded_time.strftime("%Y-%m-%d %H:%M:%S"), now.strftime("%Y-%m-%d %H:%M:%S"))

        asyncio.run(run_test())

    @patch('a53.coffee_machine.asyncio.sleep', return_value=None)
    def test_power_on_and_off(self, mock_sleep):
        async def run_test():
            self.machine._is_connected = True

            # Mock the necessary methods
            self.machine._get_schedule_unlocked = AsyncMock(return_value={})
            self.machine._set_schedule_unlocked = AsyncMock()
            self.machine._enable_schedule_unlocked = AsyncMock()
            self.machine._set_current_time_unlocked = AsyncMock()
            self.machine._set_last_sync_time_unlocked = AsyncMock()
            self.machine._backup_schedule = unittest.mock.MagicMock()

            # Test power on
            await self.machine.power_on()

            # Test power off
            await self.machine.power_off()

        asyncio.run(run_test())
