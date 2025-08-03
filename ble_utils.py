from bleak import BleakScanner

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
