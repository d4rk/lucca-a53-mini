# Lucca A53 Web Server (`server.py`)

This script runs a web server that exposes a RESTful API to control the Lucca A53 Mini espresso machine. This allows for easy integration with other applications, home automation systems, or web interfaces.

## Features

- **RESTful API:** Provides a simple API for controlling the coffee machine.
- **Connects Automatically:** Automatically discovers and connects to the first available S1 device.
- **Connection Management:** Handles connection and reconnection logic.

## API Endpoints

The base URL for all endpoints is `http://127.0.0.1:8053`.

---

### Get Temperatures

**GET** `/api/temperature`

Returns the current temperatures of the brew and steam boilers in Celsius.

**Responses**

-   **`200 OK`**: Successful response.
    ```json
    {
      "brew_boiler": 95,
      "steam_boiler": 125
    }
    ```

---

### Get Power Status

**GET** `/api/power/status`

Returns the power status of the brew and steam boilers.

**Responses**

-   **`200 OK`**: Successful response. The status can be one of `on`, `off`, `warming_up`, or `unknown`.
    ```json
    {
      "brew_boiler": "on",
      "steam_boiler": "warming_up"
    }
    ```

---

### Power On Machine

**POST** `/api/power/on`

Powers on the coffee machine.

**Responses**

-   **`200 OK`**: The machine was successfully powered on.
    ```json
    {
      "status": "success",
      "message": "Coffee machine powered on."
    }
    ```

---

### Power Off Machine

**POST** `/api/power/off`

Powers off the coffee machine.

**Responses**

-   **`200 OK`**: The machine was successfully powered off.
    ```json
    {
      "status": "success",
      "message": "Coffee machine powered off."
    }
    ```

---

### Enable Schedule

**POST** `/api/schedule/enable`

Enables the power-on/off schedule.

**Responses**

-   **`200 OK`**: The schedule was successfully enabled.
    ```json
    {
      "status": "success",
      "message": "Schedule enabled."
    }
    ```

---

### Disable Schedule

**POST** `/api/schedule/disable`

Disables the power-on/off schedule.

**Responses**

-   **`200 OK`**: The schedule was successfully disabled.
    ```json
    {
      "status": "success",
      "message": "Schedule disabled."
    }
    ```

---

### Get Schedule

**GET** `/api/schedule`

Returns the full power-on/off schedule.

**Responses**

-   **`200 OK`**: Successful response.
    ```json
    {
      "status": "success",
      "schedule": {
        "monday": {"on": "07:00", "off": "15:00"},
        "tuesday": {"on": "07:00", "off": "15:00"},
        "wednesday": {"on": "07:00", "off": "15:00"},
        "thursday": {"on": "07:00", "off": "15:00"},
        "friday": {"on": "07:00", "off": "15:00"},
        "saturday": {"on": "09:00", "off": "17:00"},
        "sunday": {"on": "09:00", "off": "17:00"}
      }
    }
    ```

---

### Get Schedule Status

**GET** `/api/schedule/status`

Returns whether the power-on/off schedule is currently enabled.

**Responses**

-   **`200 OK`**: Successful response.
    ```json
    {
      "status": "success",
      "enabled": true
    }
    ```

---

### Disconnect Machine

**POST** `/api/disconnect`

Disconnects from the coffee machine.

**Responses**

-   **`200 OK`**: The machine was successfully disconnected.
    ```json
    {
      "status": "success",
      "message": "Coffee machine disconnected."
    }
    ```
-   **`200 OK`**: The machine was already disconnected.
    ```json
    {
        "status": "info",
        "message": "Coffee machine already disconnected or not connected."
    }
    ```

## Common Errors

-   **`503 Service Unavailable`**: This error is returned when the server is unable to connect to the coffee machine.
    ```json
    {
      "error": "Coffee machine not connected."
    }
    ```
