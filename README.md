# Lucca A53 Mini BT LE Sniffer

**UNDER DEVELOPMENT**

This project allows you to interact with S1 v.02.07 BLE devices, 
which is the timer installed in [Lucca A53 Mini](https://clivecoffee.com/products/lucca-a53-mini-espresso-machine-by-la-spaziale?variant=39948235440216) Espresso machines.

The A53 is a custom built variant of the [La Spaziale Mini Vivaldi II](https://clivecoffee.com/products/la-spaziale-mini-vivaldi-ii-espresso-machine),
developed for Clive Coffee.

The official app is the S1 Timer, which is very bare-bones.

## Contents

*   [Setup](#setup)
*   [Usage](#usage)
*   [Protocol Details](#protocol-details)

## Setup

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/d4rk/lucca-a53-mini
    cd lucca-a53-mini
    ```

2.  **Install dependencies:**

    It is recommended to use a virtual environment.

    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    pip install -r requirements.txt
    ```

## Usage

To run the program, execute `main.py`:

```bash
python3 main.py
```

### Arguments:

*   `--poll <interval>`: Enables continuous polling of BLE characteristics at the specified interval in seconds. If omitted, the characteristics will be read only once.

    Example (one-time read):
    ```bash
    python3 main.py
    ```

    Example (poll every second):
    ```bash
    python3 main.py --poll 1
    ```

### Device Selection:

Upon running `main.py`, the program will attempt to discover S1 devices. If multiple devices are found, you will be prompted to select a device by its index or to manually enter a BLE address.

If only one S1 device is found, it will automatically connect to it.

### Interactive Polling Display:

When using the `--poll` argument, an interactive curses-based display will be used to show the polled data in real-time. Press `q` to quit the polling display.

## Protocol Details

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

