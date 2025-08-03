from bleak import BleakClient
import asyncio

async def read_all_characteristics(client, services):
    for service in services:
        print(f"Service: {service.uuid} ({service.description})")
        for char in service.characteristics:
            print(f"  Characteristic: {char.uuid} ({char.description})")
            print(f"    Properties: {char.properties}")
            if 'read' in char.properties:
                try:
                    value = await client.read_gatt_char(char.uuid)
                    hex_str = value.hex()
                    chunks = [hex_str[i:i+4] for i in range(0, len(hex_str), 4)]
                    print("    Value (hex, 2 bytes per group, 8 per line):")
                    for i in range(0, len(chunks), 8):
                        line = ' '.join(chunks[i:i+8])
                        print(f"      {line}")
                    if char.uuid.lower() == 'acab0005-67f5-479e-8711-b3b99198ce6c':
                        if len(value) >= 6:
                            year = value[0] + 2000
                            month = value[1]
                            day = value[2]
                            unknown = value[3]
                            hour = value[4]
                            minute = value[5]
                            second = value[6]
                            print(f"    Parsed Date/Time: {year:04d}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}")
                except Exception as e:
                    print(f"    Could not read value: {e}")
            else:
                print(f"    Value: <not readable>")

async def list_characteristics(address, poll_interval=0):
    async with BleakClient(address) as client:
        print(f"Connected: {client.is_connected}")
        await client.connect()
        services = client.services
        if services is None:
            print("No services found or failed to fetch services.")
            return
        if poll_interval and poll_interval > 0:
            print(f"Polling all readable characteristics every {poll_interval} seconds. Press Ctrl+C to stop.")
            try:
                while True:
                    await read_all_characteristics(client, services)
                    await asyncio.sleep(poll_interval)
            except KeyboardInterrupt:
                print("Polling stopped by user.")
        else:
            await read_all_characteristics(client, services)
