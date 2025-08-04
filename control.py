import asyncio
import argparse
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

async def main():
    parser = argparse.ArgumentParser(description="Connect to S1 device and display status.")
    parser.add_argument('--address', type=str, help='BLE address of the S1 device.')
    parser.add_argument('--power-on', action='store_true', help='Power on the coffee machine.')

    args = parser.parse_args()

    address = await _select_device_address(args.address)
    if not address:
        print("No device selected or address provided. Exiting.")
        return

    machine = CoffeeMachine(address)
    try:
        await machine.connect()
        print("Connected.")

        current_time = await machine.get_current_time()
        print(f"Current machine time: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")

        if args.power_on:
            await machine.power_on()

    except ConnectionError as e:
        print(f"Connection error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if machine._is_connected:
            print("Disconnecting...")
            await machine.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
