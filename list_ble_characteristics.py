
import asyncio
import argparse
from bleak import BleakClient, BleakScanner


async def list_characteristics(address, poll_interval=0):
    async with BleakClient(address) as client:
        print(f"Connected: {client.is_connected}")
        await client.connect()
        services = client.services
        if services is None:
            print("No services found or failed to fetch services.")
            return

        async def read_all_characteristics():
            for service in services:
                print(f"Service: {service.uuid} ({service.description})")
                for char in service.characteristics:
                    print(f"  Characteristic: {char.uuid} ({char.description})")
                    print(f"    Properties: {char.properties}")
                    if 'read' in char.properties:
                        try:
                            value = await client.read_gatt_char(char.uuid)
                            hex_str = value.hex()
                            # Group into 2-byte (4 hex chars) chunks
                            chunks = [hex_str[i:i+4] for i in range(0, len(hex_str), 4)]
                            # Print 8 chunks per line, space separated
                            print("    Value (hex, 2 bytes per group, 8 per line):")
                            for i in range(0, len(chunks), 8):
                                line = ' '.join(chunks[i:i+8])
                                print(f"      {line}")
                            # If this is the likely date/time characteristic, parse and print it
                            if char.uuid.lower() == 'acab0005-67f5-479e-8711-b3b99198ce6c':
                                if len(value) >= 6:
                                    year = value[0] + 2000
                                    month = value[1]
                                    day = value[2]
                                    unknown = value[3]  # Seems to be 06, maybe timezone. 
                                    hour = value[4]
                                    minute = value[5]
                                    second = value[6]
                                    print(f"    Parsed Date/Time: {year:04d}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}")
                        except Exception as e:
                            print(f"    Could not read value: {e}")
                    else:
                        print(f"    Value: <not readable>")

        if poll_interval and poll_interval > 0:
            print(f"Polling all readable characteristics every {poll_interval} seconds. Press Ctrl+C to stop.")
            try:
                while True:
                    await read_all_characteristics()
                    await asyncio.sleep(poll_interval)
            except KeyboardInterrupt:
                print("Polling stopped by user.")
        else:
            await read_all_characteristics()


async def discover_s1_devices():
    print("Scanning for 'S1 v.02.07'")
    devices = await BleakScanner.discover()
    s1_devices = [d for d in devices if d.name and "S1 v.02.07" in d.name]
    if not s1_devices:
        print("No S1 v.02.07 devices found.")
        return []
    print("Found devices:")
    for idx, d in enumerate(s1_devices):
        print(f"  [{idx}] {d.name} ({d.address})")
    return s1_devices


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
