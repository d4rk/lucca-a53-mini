import argparse
import asyncio
from characteristics import list_characteristics
from ble_utils import discover_s1_devices

def main():
    parser = argparse.ArgumentParser(description="List or poll BLE characteristics for S1 v.02.07 devices.")
    parser.add_argument('--poll', type=float, default=0, help='Polling interval in seconds (0 = one-time read)')
    args = parser.parse_args()

    async def runner():
        s1_devices = await discover_s1_devices()
        if not s1_devices:
            return
        if len(s1_devices) == 1:
            address = s1_devices[0].address
            print(f"Automatically connecting to {s1_devices[0].name} ({address})")
        else:
            idx = input("Select device index to connect (or enter address manually): ")
            try:
                idx = int(idx)
                address = s1_devices[idx].address
            except (ValueError, IndexError):
                address = idx  # treat input as address
        await list_characteristics(address, poll_interval=args.poll)
    asyncio.run(runner())

if __name__ == "__main__":
    main()
