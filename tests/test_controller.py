import unittest
import json
import controller
from unittest.mock import AsyncMock, patch, MagicMock
from io import StringIO


class TestController(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        # Patch CoffeeMachine and _select_device_address
        self.patcher_coffee_machine = patch("controller.CoffeeMachine")
        self.mock_coffee_machine = self.patcher_coffee_machine.start()

        self.patcher_select_device_address = patch(
            "controller._select_device_address", new_callable=AsyncMock
        )
        self.mock_select_device_address = self.patcher_select_device_address.start()

        # Initialize common attributes of the mocked CoffeeMachine instance
        self.mock_machine_instance = self.mock_coffee_machine.return_value
        self.mock_machine_instance.connect = AsyncMock()
        self.mock_machine_instance.disconnect = AsyncMock()
        self.mock_machine_instance._is_connected = False  # Default state

        # Default return value for _select_device_address
        self.mock_select_device_address.return_value = "AA:BB:CC:DD:EE:FF"

    async def asyncTearDown(self):
        self.patcher_coffee_machine.stop()
        self.patcher_select_device_address.stop()

    async def test_async_main_power_on(self):
        self.mock_machine_instance.power_on = AsyncMock()

        args = MagicMock(
            set_schedule=False,
            print_schedule=False,
            power_on=True,
            power_off=False,
            enable_schedule=False,
            disable_schedule=False,
            brew_boiler_temp=False,
            steam_boiler_temp=False,
            address=None,
        )

        await controller.async_main(args)

        self.mock_select_device_address.assert_called_once_with(None)
        self.mock_coffee_machine.assert_called_once_with("AA:BB:CC:DD:EE:FF")
        self.mock_machine_instance.connect.assert_called_once()
        self.mock_machine_instance.power_on.assert_called_once()

    async def test_async_main_set_schedule(self):
        self.mock_machine_instance.set_schedule = AsyncMock()

        args = MagicMock(
            set_schedule=True,
            print_schedule=False,
            power_on=False,
            power_off=False,
            enable_schedule=False,
            disable_schedule=False,
            brew_boiler_temp=False,
            steam_boiler_temp=False,
            address=None,
        )

        # Mock sys.stdin for JSON input
        test_schedule = {"start": "08:00", "end": "17:00"}
        with patch("sys.stdin", StringIO(json.dumps(test_schedule))):
            await controller.async_main(args)

        self.mock_select_device_address.assert_called_once_with(None)
        self.mock_coffee_machine.assert_called_once_with("AA:BB:CC:DD:EE:FF")
        self.mock_machine_instance.connect.assert_called_once()
        self.mock_machine_instance.set_schedule.assert_called_once_with(test_schedule)

    async def test_async_main_print_schedule(self):
        self.mock_machine_instance.get_schedule = AsyncMock(
            return_value={"start": "09:00", "end": "18:00"}
        )

        args = MagicMock(
            set_schedule=False,
            print_schedule=True,
            power_on=False,
            power_off=False,
            enable_schedule=False,
            disable_schedule=False,
            brew_boiler_temp=False,
            steam_boiler_temp=False,
            address=None,
        )

        with patch("sys.stdout", new=StringIO()) as mock_stdout:
            await controller.async_main(args)
            output = mock_stdout.getvalue().strip()
            self.assertIn('"start": "09:00"', output)
            self.assertIn('"end": "18:00"', output)

        self.mock_select_device_address.assert_called_once_with(None)
        self.mock_coffee_machine.assert_called_once_with("AA:BB:CC:DD:EE:FF")
        self.mock_machine_instance.connect.assert_called_once()
        self.mock_machine_instance.get_schedule.assert_called_once()

    async def test_async_main_connection_error(self):
        self.mock_machine_instance.connect = AsyncMock(
            side_effect=ConnectionError("Test Connection Error")
        )
        self.mock_machine_instance._is_connected = (
            True  # Set this to True to ensure disconnect is called
        )

        args = MagicMock(
            set_schedule=False,
            print_schedule=False,
            power_on=True,  # Any action to trigger connection
            power_off=False,
            enable_schedule=False,
            disable_schedule=False,
            brew_boiler_temp=False,
            steam_boiler_temp=False,
            address=None,
        )

        await controller.async_main(args)

        self.mock_select_device_address.assert_called_once_with(None)
        self.mock_coffee_machine.assert_called_once_with("AA:BB:CC:DD:EE:FF")
        self.mock_machine_instance.connect.assert_called_once()
        self.mock_machine_instance.power_on.assert_not_called()
        self.mock_machine_instance.disconnect.assert_called_once()

    @patch("controller.argparse.ArgumentParser")
    @patch("controller.asyncio.run")
    @patch("sys.argv", ["controller.py"])
    @patch("sys.stdout", new_callable=StringIO)
    def test_main_no_args_prints_help(
        self, mock_stdout, mock_asyncio_run, mock_argparse
    ):
        # Test case: main function called with no arguments (should print help)
        mock_parser_instance = mock_argparse.return_value
        mock_parser_instance.parse_args.return_value = (
            MagicMock()
        )  # Return a mock args object
        mock_parser_instance.print_help = MagicMock()

        controller.main()

        mock_parser_instance.print_help.assert_called_once()
        mock_asyncio_run.assert_not_called()  # async_main should not be run if help is printed

    @patch("controller.argparse.ArgumentParser")
    @patch("controller.async_main", new_callable=AsyncMock)  # Mock async_main directly
    @patch("sys.argv", ["controller.py", "--power-on"])
    def test_main_with_args_calls_async_main(self, mock_async_main, mock_argparse):
        # Test case: main function called with arguments (should call async_main)
        mock_parser_instance = mock_argparse.return_value
        mock_args = MagicMock(
            set_schedule=False,
            print_schedule=False,
            power_on=True,
            power_off=False,
            enable_schedule=False,
            disable_schedule=False,
            brew_boiler_temp=False,
            steam_boiler_temp=False,
            address=None,
        )
        mock_parser_instance.parse_args.return_value = mock_args
        mock_parser_instance.print_help = MagicMock()

        controller.main()

        mock_parser_instance.print_help.assert_not_called()
        mock_async_main.assert_called_once_with(
            mock_args
        )  # Now we can directly check if async_main was called with mock_args


if __name__ == "__main__":
    unittest.main()
