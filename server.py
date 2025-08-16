import asyncio
from quart import Quart, jsonify, request
from a53.coffee_machine import CoffeeMachine
from a53.common.logging import get_logger

L = get_logger(__name__)
app = Quart(__name__)

# Global variable to hold the coffee machine instance
coffee_machine: CoffeeMachine = None
connection_lock = asyncio.Lock()
MACHINE_ADDRESS: str = None  # To store the discovered address


async def connect_to_machine():
    global coffee_machine, MACHINE_ADDRESS, connection_lock
    L.info("Attempting to connect to coffee machine...")
    async with connection_lock:
        try:
            if MACHINE_ADDRESS:
                L.info(f"Reusing previously selected address: {MACHINE_ADDRESS}")
            else:
                s1_devices = await CoffeeMachine.discover()
                if not s1_devices:
                    L.error("No S1 devices found. Cannot connect to coffee machine.")
                    return

                MACHINE_ADDRESS = s1_devices[0].address
                L.info(
                    f"Automatically selecting {s1_devices[0].name} ({MACHINE_ADDRESS})"
                )

            if not coffee_machine or not coffee_machine._is_connected:
                coffee_machine = CoffeeMachine(MACHINE_ADDRESS)
                await coffee_machine.connect()
        except Exception as e:
            L.error(f"Failed to connect to coffee machine: {e}")


async def ensure_connected():
    if coffee_machine and coffee_machine._is_connected:
        return True
    L.error("Coffee machine is not connected.")
    # Attempt to reconnect
    await connect_to_machine()
    if coffee_machine and coffee_machine._is_connected:
        return True
    return False


@app.route("/api/temperature", methods=["GET"])
async def get_temperatures():
    if not await ensure_connected():
        return jsonify({"error": "Coffee machine not connected."}), 503

    try:
        brew_temp = await coffee_machine.get_brew_boiler_temp()
        steam_temp = await coffee_machine.get_steam_boiler_temp()
        return jsonify({"brew_boiler": brew_temp, "steam_boiler": steam_temp})
    except Exception as e:
        L.error(f"Error fetching temperatures: {e}")
        return jsonify({"error": f"Error fetching temperatures: {e}"}), 500


@app.route("/api/power/on", methods=["POST"])
async def power_on_machine():
    if not await ensure_connected():
        return jsonify({"error": "Coffee machine not connected."}), 503
    try:
        await coffee_machine.power_on()
        return jsonify({"status": "success", "message": "Coffee machine powered on."})
    except Exception as e:
        L.error(f"Error powering on machine: {e}")
        return (
            jsonify({"status": "error", "message": f"Failed to power on machine: {e}"}),
            500,
        )


@app.route("/api/power/off", methods=["POST"])
async def power_off_machine():
    if not await ensure_connected():
        return jsonify({"error": "Coffee machine not connected."}), 503
    try:
        await coffee_machine.power_off()
        return jsonify({"status": "success", "message": "Coffee machine powered off."})
    except Exception as e:
        L.error(f"Error powering off machine: {e}")
        return (
            jsonify(
                {"status": "error", "message": f"Failed to power off machine: {e}"}
            ),
            500,
        )


@app.route("/api/schedule/enable", methods=["POST"])
async def enable_schedule():
    if not await ensure_connected():
        return jsonify({"error": "Coffee machine not connected."}), 503
    try:
        await coffee_machine.enable_schedule(True)
        return jsonify({"status": "success", "message": "Schedule enabled."})
    except Exception as e:
        L.error(f"Error enabling schedule: {e}")
        return (
            jsonify({"status": "error", "message": f"Failed to enable schedule: {e}"}),
            500,
        )


@app.route("/api/schedule/disable", methods=["POST"])
async def disable_schedule():
    if not await ensure_connected():
        return jsonify({"error": "Coffee machine not connected."}), 503
    try:
        await coffee_machine.enable_schedule(False)
        return jsonify({"status": "success", "message": "Schedule disabled."})
    except Exception as e:
        L.error(f"Error disabling schedule: {e}")
        return (
            jsonify({"status": "error", "message": f"Failed to disable schedule: {e}"}),
            500,
        )


@app.route("/api/schedule", methods=["GET"])
async def get_full_schedule():
    if not await ensure_connected():
        return jsonify({"error": "Coffee machine not connected."}), 503
    try:
        schedule = await coffee_machine.get_schedule()
        return jsonify({"status": "success", "schedule": schedule})
    except Exception as e:
        L.error(f"Error fetching schedule: {e}")
        return (
            jsonify({"status": "error", "message": f"Failed to fetch schedule: {e}"}),
            500,
        )


@app.route("/api/schedule/status", methods=["GET"])
async def get_schedule_status():
    if not await ensure_connected():
        return jsonify({"error": "Coffee machine not connected."}), 503
    try:
        enabled = await coffee_machine.get_timer_state()
        return jsonify({"status": "success", "enabled": enabled})
    except Exception as e:
        L.error(f"Error fetching schedule status: {e}")
        return (
            jsonify(
                {"status": "error", "message": f"Failed to fetch schedule status: {e}"}
            ),
            500,
        )


@app.route("/api/disconnect", methods=["POST"])
async def disconnect_machine():
    global coffee_machine
    if not coffee_machine or not coffee_machine._is_connected:
        return jsonify(
            {
                "status": "info",
                "message": "Coffee machine already disconnected or not connected.",
            }
        )
    try:
        await coffee_machine.disconnect()
        return jsonify({"status": "success", "message": "Coffee machine disconnected."})
    except Exception as e:
        L.error(f"Error disconnecting machine: {e}")
        return (
            jsonify(
                {"status": "error", "message": f"Failed to disconnect machine: {e}"}
            ),
            500,
        )


# To run this application, you will need an ASGI server like Hypercorn.
# Example: hypercorn server:app
if __name__ == "__main__":
    L.info("Starting Quart server...")
    app.run(host="127.0.0.1", port=8053, debug=True)
