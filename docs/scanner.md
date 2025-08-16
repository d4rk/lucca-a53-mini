# Lucca A53 BLE Scanner (`scanner.py`)

This script is a utility for scanning and displaying Bluetooth Low Energy (BLE) characteristics of a Lucca A53 Mini or other S1-compatible espresso machines.

![screenshot of scanner.py](../images/screenshot_scanner.png?raw=true)

## Features

- **Device Discovery:** Scans for and lists available S1 devices.
- **Characteristic Listing:** Connects to a device and lists all its BLE characteristics and their current values.
- **Polling:** Can continuously poll the characteristics at a specified interval and update the display in place.

## Usage

```bash
python scanner.py [--poll <interval>]
```

### Options

- `--poll <interval>`: The polling interval in seconds. If set to 0 (the default), the script will perform a one-time read of the characteristics. If greater than 0, it will continuously poll and refresh the display.

### Examples

**One-time scan:**

```bash
python scanner.py
```

**Poll every 5 seconds:**

```bash
python scanner.py --poll 5
```

## How it Works

1.  **Discover Devices:** The script begins by discovering nearby S1-compatible BLE devices.
2.  **Select Device:** If one device is found, it connects automatically. If multiple are found, it prompts the user to select one.
3.  **Connect:** It establishes a BLE connection to the selected device.
4.  **Read Characteristics:** It iterates through all the services and characteristics of the connected device, reading the value of each one.
5.  **Format and Display:** The script formats the retrieved characteristics and their values into a readable table.
6.  **Poll (Optional):** If the `--poll` option is used, the script will repeat the read and display steps at the specified interval, clearing the screen each time to provide a live view of the machine's state.

    When using the `--poll` argument, an interactive curses-based display will be used to show the polled data in real-time. Press `q` to quit the polling display.