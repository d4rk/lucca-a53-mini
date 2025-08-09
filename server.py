import asyncio
from flask import Flask, jsonify, request
from a53.coffee_machine import CoffeeMachine
from a53.common.logging import get_logger
import sys

L = get_logger(__name__)
app = Flask(__name__)

# Global variable to hold the coffee machine instance
coffee_machine: CoffeeMachine = None
MACHINE_ADDRESS: str = None # To store the discovered address

connection_task = None # To hold the background connection task

async def connect_to_machine_background():
    global coffee_machine, MACHINE_ADDRESS
    L.info("Attempting to connect to coffee machine in background...")
    try:
        s1_devices = await CoffeeMachine.discover()
        if not s1_devices:
            L.error("No S1 devices found. Cannot connect to coffee machine.")
            return False

        MACHINE_ADDRESS = s1_devices[0].address
        L.info(f"Automatically selecting {s1_devices[0].name} ({MACHINE_ADDRESS})")

        coffee_machine = CoffeeMachine(MACHINE_ADDRESS)
        await coffee_machine.connect()
        L.info("Successfully connected to coffee machine.")
        return True
    except Exception as e:
        L.error(f"Failed to connect to coffee machine: {e}")
        # Optionally, schedule a retry after some delay
        return False

async def ensure_connected():
    global coffee_machine
    if coffee_machine and coffee_machine._is_connected:
        return True

    L.warning("Coffee machine not connected. Attempting to reconnect...")
    if coffee_machine is None: # First time connection or previous connection failed
        # This will attempt to discover and connect
        return await connect_to_machine_background()
    else: # Machine instance exists but is disconnected
        try:
            await coffee_machine.connect()
            L.info("Successfully reconnected to coffee machine.")
            return True
        except Exception as e:
            L.error(f"Failed to reconnect to coffee machine: {e}")
            return False

@app.route('/api/temperature', methods=['GET'])
async def get_temperatures():
    # Ensure connection before proceeding
    if not await ensure_connected():
        return jsonify({"error": "Coffee machine not connected and failed to reconnect."}), 503

    try:
        brew_temp = await coffee_machine.get_brew_boiler_temp()
        steam_temp = await coffee_machine.get_steam_boiler_temp()
        return jsonify({
            "brew_boiler": brew_temp,
            "steam_boiler": steam_temp
        })
    except Exception as e:
        L.error(f"Error fetching temperatures: {e}")
        return jsonify({"error": f"Error fetching temperatures: {e}"}), 500

@app.route('/api/power/on', methods=['POST'])
async def power_on_machine():
    if not await ensure_connected():
        return jsonify({"error": "Coffee machine not connected and failed to reconnect."}), 503
    try:
        await coffee_machine.power_on()
        return jsonify({"status": "success", "message": "Coffee machine powered on."})
    except Exception as e:
        L.error(f"Error powering on machine: {e}")
        return jsonify({"status": "error", "message": f"Failed to power on machine: {e}"}), 500

@app.route('/api/power/off', methods=['POST'])
async def power_off_machine():
    if not await ensure_connected():
        return jsonify({"error": "Coffee machine not connected and failed to reconnect."}), 503
    try:
        await coffee_machine.power_off()
        return jsonify({"status": "success", "message": "Coffee machine powered off."})
    except Exception as e:
        L.error(f"Error powering off machine: {e}")
        return jsonify({"status": "error", "message": f"Failed to power off machine: {e}"}), 500

@app.route('/api/schedule/enable', methods=['POST'])
async def enable_schedule():
    if not await ensure_connected():
        return jsonify({"error": "Coffee machine not connected and failed to reconnect."}), 503
    try:
        await coffee_machine.enable_schedule(True)
        return jsonify({"status": "success", "message": "Schedule enabled."})
    except Exception as e:
        L.error(f"Error enabling schedule: {e}")
        return jsonify({"status": "error", "message": f"Failed to enable schedule: {e}"}), 500

@app.route('/api/schedule/disable', methods=['POST'])
async def disable_schedule():
    if not await ensure_connected():
        return jsonify({"error": "Coffee machine not connected and failed to reconnect."}), 503
    try:
        await coffee_machine.enable_schedule(False)
        return jsonify({"status": "success", "message": "Schedule disabled."})
    except Exception as e:
        L.error(f"Error disabling schedule: {e}")
        return jsonify({"status": "error", "message": f"Failed to disable schedule: {e}"}), 500

@app.route('/api/schedule', methods=['GET'])
async def get_full_schedule():
    if not await ensure_connected():
        return jsonify({"error": "Coffee machine not connected and failed to reconnect."}), 503
    try:
        schedule = await coffee_machine.get_schedule()
        return jsonify({"status": "success", "schedule": schedule})
    except Exception as e:
        L.error(f"Error fetching schedule: {e}")
        return jsonify({"status": "error", "message": f"Failed to fetch schedule: {e}"}), 500

@app.route('/api/schedule/status', methods=['GET'])
async def get_schedule_status():
    if not await ensure_connected():
        return jsonify({"error": "Coffee machine not connected and failed to reconnect."}), 503
    try:
        enabled = await coffee_machine.get_timer_state()
        return jsonify({"status": "success", "enabled": enabled})
    except Exception as e:
        L.error(f"Error fetching schedule status: {e}")
        return jsonify({"status": "error", "message": f"Failed to fetch schedule status: {e}"}), 500

@app.route('/api/disconnect', methods=['POST'])
async def disconnect_machine():
    global coffee_machine
    if not coffee_machine or not coffee_machine._is_connected:
        return jsonify({"status": "info", "message": "Coffee machine already disconnected or not connected."})
    try:
        await coffee_machine.disconnect()
        return jsonify({"status": "success", "message": "Coffee machine disconnected."})
    except Exception as e:
        L.error(f"Error disconnecting machine: {e}")
        return jsonify({"status": "error", "message": f"Failed to disconnect machine: {e}"}), 500

if __name__ == '__main__':
    L.info("Starting Flask server...")
    # To run this Flask application with async views and background tasks, it's recommended to use an ASGI server
    # like Gunicorn with Uvicorn workers.
    # Example: gunicorn -w 1 -k uvicorn.workers.UvicornWorker server:app --bind 127.0.0.1:8053
    # For development, you can also use `flask run --host 127.0.0.1 --port 8053`
    # after installing `flask[async]` (`pip install "flask[async]"`).
    app.run(host='127.0.0.1', port=8053, debug=True)
