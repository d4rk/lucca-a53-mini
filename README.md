# La Spaziale Vivaldi / LUCCA A53 Automation Tools

> *_STILL UNDER DEVELOPMENT_*

This project allows you to interact with S1 v.02.07 BLE devices,
which is the timer installed in [LUCCA A53 Mini](https://clivecoffee.com/products/lucca-a53-mini-espresso-machine-by-la-spaziale?variant=39948235440216) Espresso machines.

The A53 is a custom built variant of the [La Spaziale Mini Vivaldi II](https://clivecoffee.com/products/la-spaziale-mini-vivaldi-ii-espresso-machine),
developed for Clive Coffee.

The official app is the S1 Timer, which is very bare-bones.

> **Disclaimer**: This project is provided as-is, without any warranty. Use at your own risk. Incorrect usage may damage your machine. This project was developed through reverse-engineering and "vibe coding," and may not be entirely accurate or complete.

## Contents

*   [Setup](#setup)
*   [Documentation](#documentation)
*   [Usage](#usage)
*   [Protocol Details](#protocol-details)

![image of the A53 Mini](images/a53.jpg?raw=true)

## Setup

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/d4rk/lucca-a53-mini
    cd lucca-a53-mini
    ```

2.  **Install dependencies:**

    You can install the dependencies using a virtual environment or directly.

    **Using a virtual environment (recommended):**

    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

    **Direct installation:**

    ```bash
    pip install -r requirements.txt
    ```

## Documentation

This project has three main programs:

1.  [`scanner.py`](docs/scanner.md): A command-line tool to scan for and display information from the coffee machine.
2.  [`controller.py`](docs/controller.md): A command-line tool to control the coffee machine's settings.
3.  [`server.py`](docs/server.md): A web server that exposes a RESTful API to control the coffee machine.

Detailed documentation for each program is available in the `docs/` directory.

## Usage

For detailed usage instructions, please refer to the documentation for each program:

*   [**`scanner.py`**](docs/scanner.md)
*   [**`controller.py`**](docs/controller.md)
*   [**`server.py`**](docs/server.md)

## Bluetooth Protocol Details

The S1 device communicates over Bluetooth Low Energy (BLE) using custom characteristics. Below are the UUIDs and their known data formats:

### Characteristic UUIDs

*   `acab0002-67f5-479e-8711-b3b99198ce6c` (Schedule Timer State)
    *   **Description**: Controls whether the schedule timer is enabled or disabled.
    *   **Format**: 1 byte
        *   `0x01`: Timer Enabled
        *   `0x00`: Timer Disabled

*   `acab0003-67f5-479e-8711-b3b99198ce6c` (Schedule)
    *   **Description**: Stores the weekly schedule for the machine.
    *   **Format**: 84 bytes (7 days * 3 slots/day * 4 bytes/slot)
        Each 4-byte slot represents a time period and boiler state:
        *   Byte 0: End Minute (0-59)
        *   Byte 1: End Hour (0-23)
        *   Byte 2: Start Minute (0-59)
        *   Byte 3: Start Hour (0-23, lower 7 bits) + Boiler On (Most Significant Bit)
            *   MSB (bit 7) = `1`: Boiler ON during this slot
            *   MSB (bit 7) = `0`: Boiler OFF during this slot

*   `acab0005-67f5-479e-8711-b3b99198ce6c` (Current Time)
    *   **Description**: Current date and time of the machine.
    *   **Format**: 7 bytes
        *   Byte 0: Year (since 2000)
        *   Byte 1: Month (1-12)
        *   Byte 2: Day (1-31)
        *   Byte 3: Unknown/Reserved
        *   Byte 4: Hour (0-23)
        *   Byte 5: Minute (0-59)
        *   Byte 6: Second (0-59)

*   `acab0004-67f5-479e-8711-b3b99198ce6c` (Last Sync Time?)
    *   **Description**: Possible the last time the time was synced to the device.
    *   **Format**: Same as Current Time (7 bytes)

*   `acab0002-77f5-479e-8711-b3b99198ce6c` (Brew Boiler)
    *   **Description**: Status and temperature of the brew boiler.
    *   **Format**: 4 bytes
        *   Bytes 0-1: Temperature (little-endian, value / 10.0 for °C)
        *   Byte 2: Status code? (ranges from 0-3 as temp goes up)
        *   Byte 3: Unknown/Reserved

*   `acab0003-77f5-479e-8711-b3b99198ce6c` (Steam Boiler)
    *   **Description**: Status and temperature of the steam boiler.
    *   **Format**: 4 bytes
        *   Bytes 0-1: Temperature (little-endian, value / 10.0 for °C)
        *   Byte 2: Status code? (ranges from 0-4 as temp goes up)
        *   Byte 3: Unknown/Reserved

> [!NOTE]
> The temperature readings are a bit interesting. Byte 2 in both cases return a "range", that goes from 0-3 or 0-4. When it's 0, the temperature readings are in single digit celsius, which seems wrong. When it's between 1-3/4, it seems accurate. So I'm not sure what the 0 state indicates, and what the corresponding temperature values in that state mean.