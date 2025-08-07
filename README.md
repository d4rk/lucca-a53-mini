# Lucca A53 Mini BT LE Controller / Sniffer

> *_STILL UNDER DEVELOPMENT_*

This project allows you to interact with S1 v.02.07 BLE devices,
which is the timer installed in [Lucca A53 Mini](https://clivecoffee.com/products/lucca-a53-mini-espresso-machine-by-la-spaziale?variant=39948235440216) Espresso machines.

The A53 is a custom built variant of the [La Spaziale Mini Vivaldi II](https://clivecoffee.com/products/la-spaziale-mini-vivaldi-ii-espresso-machine),
developed for Clive Coffee.

The official app is the S1 Timer, which is very bare-bones.

## Contents

*   [Setup](#setup)
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

    It is recommended to use a virtual environment.

    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    pip install -r requirements.txt
    ```

## Usage

This project has two main programs:

1.  `scanner.py`: A command-line tool to scan for and display information from the coffee machine.
2.  `controller.py`: A command-line tool to control the coffee machine's settings.

### `scanner.py`

To run the scanner, execute `scanner.py`:

```bash
python3 scanner.py
```

**Arguments:**

*   `--poll <interval>`: Enables continuous polling of BLE characteristics at the specified interval in seconds. If omitted, the characteristics will be read only once.

    Example (one-time read):
    ```bash
    python3 scanner.py
    ```

    Example (poll every second):
    ```bash
    python3 scanner.py --poll 1
    ```

**Device Selection:**

Upon running `scanner.py`, the program will attempt to discover S1 devices. If multiple devices are found, you will be prompted to select a device by its index or to manually enter a BLE address.

If only one S1 device is found, it will automatically connect to it.

**Interactive Polling Display:**

When using the `--poll` argument, an interactive curses-based display will be used to show the polled data in real-time. Press `q` to quit the polling display.

### `controller.py`

To run the controller, execute `controller.py` with one of the available arguments:

```bash
python3 controller.py [argument]
```

**Arguments:**

*   `--power-on`: Powers on the coffee machine. This will also disable the power schedule.
    * Powering on and off is **hacky** because the S1 doesn't actually provide
      any direct [commands](#protocol-details) to control it.
    * So what the tool does is it creates a temporary schedule at a fixed time, and then set the machine's clock within or outside that schedule to trigger the desired power state.
    * It _mostly_ works. Definitely open to other ideas.
*   `--power-off`: Powers off the coffee machine. This will also disable the power schedule.
*   `--enable-schedule`: Enables the power schedule previously set on the machine.
*   `--disable-schedule`: Disables the power schedule previously set on the machine.
*   `--print-schedule`: Prints the schedule in formatted JSON.
*   `--set-schedule`: Reads JSON from standard input and sets the schedule.
*   `--brew-boiler-temp`: Prints the brew boiler temperature and state.
*   `--steam-boiler-temp`: Prints the steam boiler temperature and state.
*   `--address <address>`: Optional BLE address of the S1 device. If not provided, it will auto discover the device.

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

> [!NOTE]
> The temperature readings are a bit interesting. Byte 2 in both cases return a "range", that goes from 0-3 or 0-4. When it's 0, the temperature readings are in single digit celsius, which seems wrong. When it's between 1-3/4, it seems accurate. So I'm not sure what the 0 state indicates, and what the corresponding temperature values in that state mean.