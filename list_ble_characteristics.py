import asyncio
from bleak import BleakClient, BleakScanner

async def list_characteristics(address):
    async with BleakClient(address) as client:
        print(f"Connected: {client.is_connected}")
        await client.connect()
        services = client.services
        if services is None:
            print("No services found or failed to fetch services.")
            return
        for service in services:
            print(f"Service: {service.uuid} ({service.description})")
            for char in service.characteristics:
                print(f"  Characteristic: {char.uuid} ({char.description})")
                print(f"    Properties: {char.properties}")


async def discover_s1_devices():
    print("Scanning for BLE devices with 'S1' in the name...")
    devices = await BleakScanner.discover()
    s1_devices = [d for d in devices if d.name and "S1" in d.name]
    if not s1_devices:
        print("No devices with 'S1' in the name found.")
        return []
    print("Found devices:")
    for idx, d in enumerate(s1_devices):
        print(f"  [{idx}] {d.name} ({d.address})")
    return s1_devices

def main():
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
        await list_characteristics(address)
    asyncio.run(runner())

if __name__ == "__main__":
    main()
