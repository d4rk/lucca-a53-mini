from bleak import BleakScanner
from a53.common.logging import get_logger

L = get_logger(__name__)

async def discover_s1_devices():
    L.info("Scanning for 'S1 v.02.07'")
    devices = await BleakScanner.discover()
    s1_devices = [d for d in devices if d.name and "S1 v.02.07" in d.name]
    if not s1_devices:
        L.info("No S1 v.02.07 devices found.")
        return []
    L.info("Found devices:")
    for idx, d in enumerate(s1_devices):
        L.info(f"  [{idx}] {d.name} ({d.address})")
    return s1_devices
