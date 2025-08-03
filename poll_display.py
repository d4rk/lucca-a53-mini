import curses
import queue
from characteristic_parsers import get_parser

def format_ble_table(data, max_lines=None, max_cols=None):
    lines = []
    if not isinstance(data, list):
        s_lines = str(data).splitlines()
        return s_lines if max_lines is None else s_lines[:max_lines]

    for service in data:
        header = f"Service: {service.get('uuid', '')} ({service.get('description', '')})"
        lines.append(header if max_cols is None else header[:max_cols])

        char_list_data = []
        for char in service.get('characteristics', []):
            char_uuid = char.get('uuid', '')
            char_name = f"{char_uuid} ({char.get('description', '')})"
            props = ','.join(char.get('properties', []))
            if char.get('error'):
                value_str = f"Error: {char['error']}"
            elif char.get('value_chunks'):
                value_str = ' '.join(char['value_chunks'])
            else:
                value_str = '<not readable>'
            
            parsed_list = []
            raw_value = char.get('value')
            if raw_value:
                parser = get_parser(char_uuid)
                if parser:
                    parsed_value = parser.parse_value(raw_value)
                    if parsed_value:
                        parsed_list = parsed_value

            char_list_data.append({'name': char_name, 'props': props, 'value': value_str, 'parsed': parsed_list})

        if max_cols is None:
            for char_data in char_list_data:
                lines.append(f"  Characteristic: {char_data['name']}")
                lines.append(f"    Properties: {char_data['props']}")
                lines.append(f"    Value (hex): {char_data['value']}")
                if char_data['parsed']:
                    for desc, val in char_data['parsed']:
                        lines.append(f"    {desc}: {val}")
            lines.append('')
        else:
            char_header = f"{'Characteristic':<40} {'Properties':<20} {'Value (hex)':<40} {'Parsed':<20}"
            lines.append(char_header[:max_cols])
            lines.append('-' * min(len(char_header), max_cols))
            for char_data in char_list_data:
                char_name = char_data['name'][:40]
                props = char_data['props'][:20]
                value_str = char_data['value'][:40]
                parsed_str = ", ".join([val for desc, val in char_data['parsed']])
                parsed = parsed_str[:20]
                row = f"{char_name:<40} {props:<20} {value_str:<40} {parsed:<20}"
                lines.append(row[:max_cols])
            lines.append('')

        if max_lines is not None and len(lines) >= max_lines:
            return lines[:max_lines]
            
    return lines

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
