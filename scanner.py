import argparse
import asyncio
from bleak import BleakClient
from a53.bt.ble_utils import discover_s1_devices
from a53.display.poll_display import curses_polling, format_ble_table
from a53.common.logging import get_logger
from a53.bt.characteristics import list_characteristics

L = get_logger(__name__)

async def main():
    parser = argparse.ArgumentParser(description="List or poll BLE characteristics for S1 v.02.07 devices.")
    parser.add_argument('--poll', type=float, default=0, help='Polling interval in seconds (0 = one-time read). Enables in-place display.')
    args = parser.parse_args()

    s1_devices = await discover_s1_devices()
    if not s1_devices:
        return
    if len(s1_devices) == 1:
        address = s1_devices[0].address
        L.info(f"Automatically connecting to {s1_devices[0].name} ({address})")
    else:
        for i, device in enumerate(s1_devices):
            print(f"[{i}] {device.name} ({device.address})")
        idx = input("Select device index to connect (or enter address manually): ")
        try:
            idx = int(idx)
            address = s1_devices[idx].address
        except (ValueError, IndexError):
            address = idx  # treat input as address

    async with BleakClient(address) as client:
        if not client.is_connected:
            L.error(f"Failed to connect to {address}")
            return

        if args.poll > 0:
            # The curses_polling function is not async, so we can't use it directly here.
            # This would require a more significant refactoring of the display logic.
            # For now, we will just poll and print to the console.
            L.info(f"Polling characteristics every {args.poll} seconds. Press Ctrl+C to stop.")
            try:
                while True:
                    result = await list_characteristics(client)
                    lines = format_ble_table(result)
                    # Clear the screen before printing
                    print("\033[H\033[J", end="")
                    for line in lines:
                        print(line)
                    await asyncio.sleep(args.poll)
            except asyncio.CancelledError:
                pass
        else:
            result = await list_characteristics(client)
            lines = format_ble_table(result)
            for line in lines:
                print(line)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass