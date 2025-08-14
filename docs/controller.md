# Lucca A53 Controller (`controller.py`)

This script provides a command-line interface (CLI) to control a Lucca A53 Mini espresso machine via Bluetooth Low Energy (BLE).

## Features

- **Power Control:** Power the machine on or off.
- **Schedule Management:** Enable, disable, set, or print the auto-on/off schedule.
- **Temperature Monitoring:** Read the current temperature of the brew and steam boilers.
- **Device Discovery:** Automatically discovers and lists available S1 devices if an address is not provided.

## Usage

The script is executed from the command line and accepts various arguments to perform different actions.

```bash
python controller.py [OPTIONS]
```

### Options

- `--address <BLE_address>`: The BLE address of the S1 device. If not provided, the script will scan for devices.
- `--power-on`: Powers on the coffee machine. This will also disable the power schedule.
- `--power-off`: Powers off the coffee machine. This will also disable the power schedule.

    > **Note on Power Control**: Powering on and off is **hacky** because the S1 doesn't actually provide
    > any direct commands to control it.
    > So what the tool does is it creates a temporary schedule at a fixed time, and then set the machine's clock within or outside that schedule to trigger the desired power state.
    > It _mostly_ works. Definitely open to other ideas.

- `--enable-schedule`: Enables the power schedule.
- `--disable-schedule`: Disables the power schedule.
- `--print-schedule`: Prints the current schedule in JSON format.
- `--set-schedule`: Reads a JSON schedule from standard input and applies it to the machine.
- `--brew-boiler-temp`: Prints the brew boiler temperature.
- `--steam-boiler-temp`: Prints the steam boiler temperature.

### Examples

**Power on the machine:**

```bash
python controller.py --power-on
```

**Set a new schedule:**

```bash
cat new_schedule.json | python controller.py --set-schedule
```

**Get the brew boiler temperature:**

```bash
python controller.py --brew-boiler-temp
```

## How it Works

1.  **Argument Parsing:** The script starts by parsing the command-line arguments to determine the requested action.
2.  **Device Discovery/Selection:** If a BLE address is not provided via the `--address` flag, it discovers nearby S1-compatible devices and prompts the user to select one.
3.  **Connection:** It establishes a BLE connection to the specified or selected coffee machine.
4.  **Command Execution:** Based on the provided arguments, it reads or writes the corresponding BLE characteristics to control the machine. For example, to power on the machine, it writes a specific value to the power characteristic.
5.  **Data Formatting:** When retrieving information like the schedule or temperatures, it parses the raw data received from the BLE characteristics and prints it in a human-readable format (JSON).
6.  **Disconnection:** The script disconnects from the machine before exiting.