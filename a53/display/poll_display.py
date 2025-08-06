import curses
import queue
from a53.parsers.characteristic_parsers import get_parser

def format_ble_table(data, max_lines=None, max_cols=None):
    if not isinstance(data, list):
        s_lines = str(data).splitlines()
        return s_lines if max_lines is None else s_lines[:max_lines]

    if max_cols is None:
        return _format_console_output(data)
    else:
        return _format_curses_output(data, max_lines, max_cols)

def curses_polling(result_queue):
    def poll_loop(stdscr):
        stdscr.nodelay(True)
        stdscr.clear()
        while True:
            try:
                data = result_queue.get(timeout=0.1)
            except queue.Empty:
                data = None
            if data is not None:
                stdscr.erase()
                max_lines, max_cols = curses.LINES - 2, curses.COLS - 1
                lines = format_ble_table(data, max_lines, max_cols)
                for idx, line in enumerate(lines):
                    if idx >= max_lines:
                        break
                    stdscr.addstr(idx, 0, line)
                stdscr.addstr(curses.LINES-1, 0, "Press 'q' to quit.")
                stdscr.refresh()
            try:
                c = stdscr.getch()
                if c == ord('q'):
                    break
            except Exception:
                pass
    curses.wrapper( poll_loop)

def _wrap_text(text, width):
    """Wraps text to a given width, returning a list of lines."""
    lines = []
    if not text:
        return [""]
    current_text = text
    while current_text:
        lines.append(current_text[:width])
        current_text = current_text[width:]
    return lines

def _prepare_characteristic_data(char):
    """Extracts and pre-processes data for a single characteristic."""
    char_uuid = char.get('uuid', '')
    char_name = f"{char_uuid} ({char.get('description', '')})"
    
    # Condense properties
    props_list = char.get('properties', [])
    condensed_props = []
    if 'read' in props_list and 'write' in props_list:
        condensed_props.append('rw')
    elif 'read' in props_list:
        condensed_props.append('ro')
    elif 'write' in props_list:
        condensed_props.append('wo')
    props = ','.join(condensed_props)

    value_chunks = char.get('value_chunks', [])
    if char.get('error'):
        value_str = f"Error: {char['error']}"
    elif value_chunks:
        value_str = ' '.join(value_chunks)
    else:
        value_str = '<not readable>'
    
    parsed_list = []
    raw_value = char.get('value')
    if raw_value:
        parser = get_parser(char_uuid)
        if parser:
            try:
                parsed_value = parser.parse_value(raw_value)
                if parsed_value:
                    # Check if parsed_value is a dictionary (for schedule)
                    if isinstance(parsed_value, dict):
                        for day, slots in parsed_value.items():
                            for slot in slots:
                                parsed_list.append((
                                    f"{day} {slot['start']}-{slot['end']}",
                                    f"Boiler: {'ON' if slot['boiler_on'] else 'OFF'}"
                                ))
                    else:
                        parsed_list = parsed_value
            except Exception:
                parsed_list.append(("** Parsing failed **", ""))

    return {
        'name': char_name,
        'props': props,
        'value': value_str,
        'parsed': parsed_list,
        'value_chunks': value_chunks
    }

def _format_console_output(data):
    """Formats data for detailed console output."""
    lines = []
    for service in data:
        header = f"Service: {service.get('uuid', '')} ({service.get('description', '')})"
        lines.append(header)

        for char in service.get('characteristics', []):
            char_data = _prepare_characteristic_data(char)
            lines.append(f"  Characteristic: {char_data['name']}")
            lines.append(f"    Properties: {char_data['props']}")
            lines.append(f"    Value (hex):")
            if char_data['value_chunks']:
                for i in range(0, len(char_data['value_chunks']), 8):
                    line = ' '.join(char_data['value_chunks'][i:i+8])
                    lines.append(f"      {line}")
            else:
                lines.append(f"      {char_data['value']}")
            if char_data['parsed']:
                lines.append(f"    Parsed Values:")
                for desc, val in char_data['parsed']:
                    lines.append(f"      {desc}: {val}")
            lines.append('')
    return lines

def _format_curses_output(data, max_lines, max_cols):
    """Formats data for tabulated curses output."""
    lines = []
    COL_WIDTHS = {
        'name': 36,
        'props': 10,
        'value': 40,
        'parsed': max_cols - 36 - 10 - 40 - 3 # Remaining width after other columns and spaces
    }
    char_header = f"{'Characteristic':<{COL_WIDTHS['name']}} | {'Properties':<{COL_WIDTHS['props']}} | {'Value (hex)':<{COL_WIDTHS['value']}} | {'Parsed':<{COL_WIDTHS['parsed']}}"
    lines.append(char_header[:max_cols])
    lines.append('-' * min(len(char_header), max_cols))

    for service in data:
        header = f"Service: {service.get('uuid', '')} ({service.get('description', '')})"
        lines.append(header[:max_cols])

        for char in service.get('characteristics', []):
            char_data = _prepare_characteristic_data(char)

            # Prepare content for each column, wrapped to column width
            name_wrapped = _wrap_text(char_data['name'], COL_WIDTHS['name'])
            props_wrapped = _wrap_text(char_data['props'], COL_WIDTHS['props'])

            hex_lines = []
            if char_data['value_chunks']:
                for i in range(0, len(char_data['value_chunks']), 8):
                    line = ' '.join(char_data['value_chunks'][i:i+8])
                    hex_lines.extend(_wrap_text(line, COL_WIDTHS['value']))
            else:
                hex_lines.extend(_wrap_text(char_data['value'], COL_WIDTHS['value']))

            parsed_lines = []
            if char_data['parsed']:
                for desc, val in char_data['parsed']:
                    parsed_lines.extend(_wrap_text(f"{desc}: {val}", COL_WIDTHS['parsed']))
            else:
                parsed_lines.append("")

            # Determine max height for this logical row
            max_row_height = max(len(name_wrapped), len(props_wrapped), len(hex_lines), len(parsed_lines))

            # Construct the physical rows
            for i in range(max_row_height):
                name_part = name_wrapped[i] if i < len(name_wrapped) else ""
                props_part = props_wrapped[i] if i < len(props_wrapped) else ""
                hex_part = hex_lines[i] if i < len(hex_lines) else ""
                parsed_part = parsed_lines[i] if i < len(parsed_lines) else ""

                row = f"{name_part:<{COL_WIDTHS['name']}} | {props_part:<{COL_WIDTHS['props']}} | {hex_part:<{COL_WIDTHS['value']}} | {parsed_part:<{COL_WIDTHS['parsed']}}"
                lines.append(row[:max_cols]) # Ensure it doesn't exceed total max_cols

            lines.append('') # Add an empty line for separation between characteristics

            if max_lines is not None and len(lines) >= max_lines:
                return lines[:max_lines]
            
    return lines