import asyncio
import argparse
import json
import sys
from typing import Optional
from coffee_machine import CoffeeMachine
from datetime import datetime

from parsers.characteristic_parsers import get_parser

async def _select_device_address(initial_address: Optional[str]) -> Optional[str]:
    address = initial_address
    if not address:
        print("Discovering S1 devices...")
        s1_devices = await CoffeeMachine.discover()
        if not s1_devices:
            print("No S1 devices found.")
            return None

        if len(s1_devices) == 1:
            address = s1_devices[0].address
            print(f"Automatically selecting {s1_devices[0].name} ({address})")
        else:
            print("Multiple S1 devices found:")
            for i, device in enumerate(s1_devices):
                print(f"  [{i}] {device.name} ({device.address})")

            while True:
                try:
                    idx = input("Select device index to connect: ")
                    idx = int(idx)
                    if 0 <= idx < len(s1_devices):
                        address = s1_devices[idx].address
                        break
                    else:
                        print("Invalid index. Please try again.")
                except ValueError:
                    print("Invalid input. Please enter a number.")
    return address

def main():
    parser = argparse.ArgumentParser(description="Connects and controls the Lucca A53 espresso machine.", allow_abbrev=False)
    parser.add_argument('--address', type=str, help='Optional BLE address of the S1 device. If not provided, it will auto discover the device.')
    power_on_group = parser.add_mutually_exclusive_group()
    power_on_group.add_argument('--power-on', action='store_true', help='Powers on the coffee machine. This will also disable the power schedule.')
    power_on_group.add_argument('--power-off', action='store_true', help='Powers off the coffee machine. This will also disable the power schedule.')
    schedule_group = parser.add_mutually_exclusive_group()
    schedule_group.add_argument('--enable-schedule', action='store_true', help='Enables the power schedule previously set on the machine.')
    schedule_group.add_argument('--disable-schedule', action='store_true', help='Disable the power schedule previously set on the machine.')
    parser.add_argument('--print-schedule', action='store_true', help='Prints the schedule in formatted JSON.')
    parser.add_argument('--set-schedule', action='store_true', help='Reads JSON from standard input and sets the schedule.')
    parser.add_argument('--brew-boiler-temp', action='store_true', help='Prints the brew boiler temperature and state.')
    parser.add_argument('--steam-boiler-temp', action='store_true', help='Prints the steam boiler temperature and state.')

    args = parser.parse_args()
    if len(sys.argv) == 1:
        parser.print_help()
        return

    asyncio.run(async_main(args))

async def async_main(args):
    schedule_data = None
    if args.set_schedule:
        try:
            print("Reading schedule from standard input...")
            schedule_data = json.load(sys.stdin)
            print(f'Schedule data read: {schedule_data}')
        except json.JSONDecodeError:
            print("Error: Invalid JSON format in standard input.")
            return

    address = await _select_device_address(args.address)
    if not address:
        print("No device selected or address provided. Exiting.")
        return

    machine = CoffeeMachine(address)
    print("Connected.")
    try:
        await machine.connect()

        if schedule_data:
            await machine.set_schedule(schedule_data)
            print("Schedule set successfully.")

        if args.print_schedule:
            schedule = await machine.get_schedule()
            print(json.dumps(schedule, indent=4))
        elif not args.set_schedule:
            current_time = await machine.get_current_time()
            print(f"Current machine time: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")

        if args.power_on:
            await machine.power_on()
        if args.power_off:
            await machine.power_off()
        if args.enable_schedule:
            await machine.set_timer_state(True)
        if args.disable_schedule:
            await machine.set_timer_state(False)
        if args.print_brew_boiler_temp:
            temp = await machine.get_brew_boiler_temp()
            print(json.dumps(temp, indent=4))
        if args.print_steam_boiler_temp:
            temp = await machine.get_steam_boiler_temp()
            print(json.dumps(temp, indent=4))

    except ConnectionError as e:
        print(f"Connection error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if machine._is_connected:
            print("Disconnecting...")
            await machine.disconnect()

if __name__ == "__main__":
    main()