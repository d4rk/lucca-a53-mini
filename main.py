import argparse
import asyncio
from ble_utils import discover_s1_devices

from ble_worker import BLEWorker
from poll_display import curses_polling, format_ble_table

def main():

    parser = argparse.ArgumentParser(description="List or poll BLE characteristics for S1 v.02.07 devices.")
    parser.add_argument('--poll', type=float, default=0, help='Polling interval in seconds (0 = one-time read). Enables in-place display.')
    args = parser.parse_args()

    async def get_devices():
        return await discover_s1_devices()

    s1_devices = asyncio.run(get_devices())
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

    ble_worker = BLEWorker()
    ble_worker.start()

    # Connect to the device
    connect_q = ble_worker.connect_device(address)
    connect_result = connect_q.get()
    if not connect_result.get("success"):
        print(f"Failed to connect to {address}: {connect_result.get('error', 'Unknown error')}")
        ble_worker.stop()
        return

    result_queue = ble_worker.list_characteristics(address, poll_interval=args.poll)
    if args.poll > 0:
        curses_polling(result_queue)
    else:
        result = result_queue.get()  # Blocking wait for result
        if isinstance(result, dict) and 'error' in result:
            print(f"An error occurred: {result['error']}")
        else:
            lines = format_ble_table(result)
            for line in lines:
                print(line)
    ble_worker.stop()

if __name__ == "__main__":
    main()