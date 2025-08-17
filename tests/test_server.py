import unittest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from tests.fake_bleak_client import FakeBleakClient

# Import the server module directly
import server


class MockS1Device:
    def __init__(self, address, name="Mock S1 Device"):
        self.address = address
        self.name = name


class TestServer(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        # Patch dependencies
        self.mock_discover_patch = patch(
            "server.discover_s1_devices", new_callable=AsyncMock
        )
        self.mock_logger_patch = patch(
            "a53.common.logging.get_logger", return_value=MagicMock()
        )
        self.mock_bleak_client_patch = patch(
            "a53.coffee_machine.BleakClient", new_callable=MagicMock
        )

        self.mock_discover = self.mock_discover_patch.start()
        self.mock_logger = self.mock_logger_patch.start()
        self.mock_bleak_client_cls = self.mock_bleak_client_patch.start()

        # Configure mock_discover to return a list of MockS1Device
        self.mock_discover.return_value = [MockS1Device("AA:BB:CC:DD:EE:FF", "Mock S1")]

        # Configure FakeBleakClient to be returned by the patch
        self.fake_bleak_client = FakeBleakClient("AA:BB:CC:DD:EE:FF")
        self.mock_bleak_client_cls.return_value = self.fake_bleak_client

        # Default to schedule disabled
        self.fake_bleak_client.set_schedule_status(False)

        # Set up the Quart app client
        self.app = server.app
        self.app.testing = True
        self.app.dependency_overrides = {}
        self.app_client = self.app.test_client()

        # Reset global state in server.py for each test
        server.coffee_machine = None
        server.MACHINE_ADDRESS = None
        server.connection_lock = asyncio.Lock()

        # For most tests, we want the machine to be connected initially
        # We'll let server.py's connect_to_machine handle the connection
        # which will now use our patched BleakClient.
        await server.connect_to_machine()
        # After connect_to_machine, server.coffee_machine should be set
        self.coffee_machine_instance_in_server = server.coffee_machine
        # Ensure the internal client of this instance is our fake client
        self.coffee_machine_instance_in_server._client = self.fake_bleak_client
        self.coffee_machine_instance_in_server._is_connected = True

    async def asyncTearDown(self):
        self.mock_discover_patch.stop()
        self.mock_logger_patch.stop()
        self.mock_bleak_client_patch.stop()

        # Clean up global state in server.py to avoid interference between tests
        server.coffee_machine = None
        server.MACHINE_ADDRESS = None
        server.connection_lock = asyncio.Lock()

    async def test_get_temperatures_success(self):
        # # Set specific boiler temperatures for this test
        self.fake_bleak_client.set_brew_boiler_temp(92.0)
        self.fake_bleak_client.set_steam_boiler_temp(105.0)

        response = await self.app_client.get("/api/temperature")
        self.assertEqual(response.status_code, 200)
        data = await response.get_json()
        self.assertEqual(data["brew_boiler"]["temp"], "92.0")
        self.assertEqual(data["steam_boiler"]["temp"], "105.0")

    async def test_power_on_machine_success(self):
        response = await self.app_client.post("/api/power/on")
        self.assertEqual(response.status_code, 200)
        data = await response.get_json()
        self.assertEqual(data["status"], "success")

    async def test_power_off_machine_success(self):
        response = await self.app_client.post("/api/power/off")
        self.assertEqual(response.status_code, 200)
        data = await response.get_json()
        self.assertEqual(data["status"], "success")

    async def test_enable_schedule_success(self):
        response = await self.app_client.post("/api/schedule/enable")
        self.assertEqual(response.status_code, 200)
        data = await response.get_json()
        self.assertEqual(data["status"], "success")

    async def test_disable_schedule_success(self):
        response = await self.app_client.post("/api/schedule/disable")
        self.assertEqual(response.status_code, 200)
        data = await response.get_json()
        self.assertEqual(data["status"], "success")

    async def test_get_full_schedule_success(self):
        expected_schedule = {
            "Monday": [{"start": "08:00", "end": "09:00", "boiler_on": True}]
        }
        self.fake_bleak_client.set_schedule(expected_schedule)
        response = await self.app_client.get("/api/schedule")
        self.assertEqual(response.status_code, 200)
        data = await response.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["schedule"], expected_schedule)

    async def test_get_schedule_status_enabled(self):
        self.fake_bleak_client.set_schedule_status(True)
        response = await self.app_client.get("/api/schedule/status")
        self.assertEqual(response.status_code, 200)
        data = await response.get_json()
        self.assertEqual(data["status"], "success")
        self.assertTrue(data["enabled"])

    async def test_get_schedule_status_disabled(self):
        self.fake_bleak_client.set_schedule_status(False)
        response = await self.app_client.get("/api/schedule/status")
        self.assertEqual(response.status_code, 200)
        data = await response.get_json()
        self.assertEqual(data["status"], "success")
        self.assertFalse(data["enabled"])

    async def test_disconnect_machine_success(self):
        self.coffee_machine_instance_in_server.disconnect = AsyncMock()
        response = await self.app_client.post("/api/disconnect")
        self.assertEqual(response.status_code, 200)
        data = await response.get_json()
        self.assertEqual(data["status"], "success")
        self.coffee_machine_instance_in_server.disconnect.assert_called_once()

    async def test_ensure_connected_no_device_found(self):
        # Configure discover_s1_devices to return an empty list for this specific test
        self.mock_discover.return_value = []
        server.coffee_machine = None
        server.MACHINE_ADDRESS = None

        response = await self.app_client.get("/api/temperature")
        self.assertEqual(response.status_code, 503)
        data = await response.get_json()
        self.assertTrue("error" in data)

    async def test_api_error_handling(self):
        # Simulate an error during temperature fetching
        self.coffee_machine_instance_in_server.get_brew_boiler_temp = AsyncMock(
            side_effect=Exception("Test Error")
        )
        self.coffee_machine_instance_in_server.get_steam_boiler_temp = AsyncMock(
            side_effect=Exception("Test Error")
        )

        response = await self.app_client.get("/api/temperature")
        self.assertEqual(response.status_code, 500)
        data = await response.get_json()
        self.assertTrue("error" in data)


if __name__ == "__main__":
    unittest.main()
