# Lucca A53 Web Server (`server.py`)

This script runs a web server that exposes a RESTful API to control the Lucca A53 Mini espresso machine. This allows for easy integration with other applications, home automation systems, or web interfaces.

## Features

- **RESTful API:** Provides a simple API for controlling the coffee machine.
- **Connects Automatically:** Automatically discovers and connects to the first available S1 device.
- **Connection Management:** Handles connection and reconnection logic.

## API Endpoints

- `GET /api/temperature`: Returns the brew and steam boiler temperatures.
- `GET /api/power/status`: Returns the power status of the brew and steam boilers.
- `POST /api/power/on`: Powers on the machine.
- `POST /api/power/off`: Powers off the machine.
- `POST /api/schedule/enable`: Enables the power schedule.
- `POST /api/schedule/disable`: Disables the power schedule.
- `GET /api/schedule`: Returns the full power schedule.
- `GET /api/schedule/status`: Returns the status of the power schedule (enabled/disabled).
- `POST /api/disconnect`: Disconnects from the machine.

## Usage

To run the server, you need an ASGI server like Hypercorn or Uvicorn.

```bash
hypercorn server:app
```

Or for development:

```bash
python server.py
```

This will start the server on `127.0.0.1:8053` by default.

### Example cURL Requests

**Get temperatures:**

```bash
curl http://127.0.0.1:8053/api/temperature
```

**Get power status:**

```bash
curl http://127.0.0.1:8053/api/power/status
```

**Power on the machine:**

```bash
curl -X POST http://1.0.0.1:8053/api/power/on
```

## How it Works

1.  **Web Server:** The script uses the Quart web framework to create an asynchronous web server.
2.  **Startup Connection:** Before the server starts handling requests, it attempts to discover and connect to an S1 device.
3.  **Request Handling:** Each API endpoint is mapped to a Python function that interacts with the `CoffeeMachine` object.
4.  **Connection Management:** The server uses a lock to prevent multiple concurrent connection attempts. It also has a mechanism to try and reconnect if the connection is lost.
5.  **JSON Responses:** The API endpoints return data in JSON format, making it easy to consume by other applications.
