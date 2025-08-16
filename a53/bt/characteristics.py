from bleak import BleakClient
import asyncio


async def read_all_characteristics(client):
    services_data = []
    for service in client.services:
        service_data = {
            "uuid": service.uuid,
            "description": service.description,
            "characteristics": [],
        }
        for char in service.characteristics:
            char_data = {
                "uuid": char.uuid,
                "description": char.description,
                "properties": char.properties,
            }
            if "read" in char.properties:
                try:
                    value = await client.read_gatt_char(char.uuid)
                    hex_str = value.hex()
                    char_data["value"] = value
                    char_data["value_chunks"] = [
                        hex_str[i : i + 4] for i in range(0, len(hex_str), 4)
                    ]
                except Exception as e:
                    char_data["error"] = str(e)
            service_data["characteristics"].append(char_data)
        services_data.append(service_data)
    return services_data


async def list_characteristics(client, result_queue=None, poll_interval=0):
    try:
        if not client or not client.is_connected:
            if result_queue:
                result_queue.put({"error": "Client not connected"})
            return

        services = client.services
        if services is None:
            if result_queue:
                result_queue.put(
                    {"error": "No services found or failed to fetch services."}
                )
            return

        if poll_interval and poll_interval > 0:
            if not result_queue:
                raise ValueError("A result_queue must be provided for polling.")
            while True:
                data = await read_all_characteristics(client)
                result_queue.put(data)
                await asyncio.sleep(poll_interval)
        else:
            data = await read_all_characteristics(client)
            if result_queue:
                result_queue.put(data)
            return data
    except Exception as e:
        if result_queue:
            result_queue.put({"error": str(e)})
        else:
            raise e
