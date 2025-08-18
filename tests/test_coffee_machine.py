import unittest
from unittest.mock import patch, AsyncMock
from datetime import datetime
from a53.coffee_machine import CoffeeMachine
from tests.fake_bleak_client import FakeBleakClient
from a53.parsers.constants import UUID_TIMER_STATE


class TestCoffeeMachine(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        # Patch BleakClient to return our FakeBleakClient instance
        self.patcher = patch("a53.coffee_machine.BleakClient", new_callable=AsyncMock)
        self.MockBleakClient = self.patcher.start()

        self.fake_bleak_client = FakeBleakClient("test_address")
        self.MockBleakClient.return_value = self.fake_bleak_client

        self.machine = CoffeeMachine(address="test_address")
        # Ensure the machine's client is our fake client
        self.machine._client = self.fake_bleak_client
        # Connect the machine for tests that require it
        await self.machine.connect()

    async def asyncTearDown(self):
        self.patcher.stop()

    async def test_connect_and_disconnect(self):
        # The machine is already connected in asyncSetUp, so we disconnect first
        await self.machine.disconnect()
        self.assertFalse(self.fake_bleak_client.is_connected)
        await self.machine.connect()
        self.assertTrue(self.fake_bleak_client.is_connected)

    async def test_get_brew_boiler_temp(self):
        self.fake_bleak_client.set_brew_boiler_temp(90.0)
        data = await self.machine.get_brew_boiler_temp()
        self.assertEqual(data["name"], "Brew")
        self.assertEqual(data["temp"], 90.0)

    async def test_get_steam_boiler_temp(self):
        self.fake_bleak_client.set_steam_boiler_temp(130.0)
        data = await self.machine.get_steam_boiler_temp()
        self.assertEqual(data["name"], "Steam")
        self.assertEqual(data["temp"], 130.0)

    async def test_enable_disable_schedule(self):
        # Enable schedule
        await self.machine.enable_schedule(True)
        # Access the boolean value from the tuple returned by get_parsed_characteristic_value
        timer_state = self.fake_bleak_client.get_parsed_characteristic_value(
            UUID_TIMER_STATE
        )
        self.assertTrue(timer_state[0][1])  # Check if the schedule is enabled

        # Disable schedule
        await self.machine.enable_schedule(False)
        # Access the boolean value from the tuple returned by get_parsed_characteristic_value
        timer_state = self.fake_bleak_client.get_parsed_characteristic_value(
            UUID_TIMER_STATE
        )
        self.assertFalse(timer_state[0][1])  # Check if the schedule is enabled

    async def test_get_timer_state(self):
        # Test when timer is enabled
        self.fake_bleak_client.set_schedule_status(True)
        state = await self.machine.get_timer_state()
        self.assertTrue(state)

        # Test when timer is disabled
        self.fake_bleak_client.set_schedule_status(False)
        state = await self.machine.get_timer_state()
        self.assertFalse(state)

    async def test_get_and_set_schedule(self):
        schedule = {"Monday": [{"start": "06:00", "end": "09:00", "boiler_on": True}]}

        # Set schedule
        await self.machine.set_schedule(schedule)

        # Get schedule
        decoded_schedule = await self.machine.get_schedule()
        self.assertEqual(decoded_schedule, schedule)

    async def test_get_and_set_current_time(self):
        now = datetime.now().replace(
            microsecond=0
        )  # Remove microseconds for exact comparison

        # Set current time
        await self.machine.set_current_time(now)

        # Get current time
        decoded_time = await self.machine.get_current_time()
        self.assertEqual(decoded_time, now)

    @patch("a53.coffee_machine.asyncio.sleep", return_value=None)
    async def test_power_on_and_off(self, mock_sleep):
        # Mock the necessary methods
        self.machine._backup_schedule = unittest.mock.MagicMock()

        # Test power on
        await self.machine.power_on()

        # Test power off
        await self.machine.power_off()
