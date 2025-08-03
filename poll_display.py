import curses
import queue

def format_ble_table(data, max_lines, max_cols):
    # Try to format the BLE data as a table
    lines = []
    if not isinstance(data, list):
        # fallback to string
        return str(data).splitlines()[:max_lines]
    for service in data:
        header = f"Service: {service.get('uuid', '')} ({service.get('description', '')})"
        lines.append(header[:max_cols])
        char_header = f"{'Characteristic':<40} {'Properties':<20} {'Value (hex)':<40} {'Parsed':<20}"
        lines.append(char_header[:max_cols])
        lines.append('-' * min(len(char_header), max_cols))
        for char in service.get('characteristics', []):
            char_name = f"{char.get('uuid', '')} ({char.get('description', '')})"
            props = ','.join(char.get('properties', []))
            if char.get('error'):
                value_str = f"Error: {char['error']}"
            elif char.get('value_chunks'):
                value_str = ' '.join(char['value_chunks'])
            else:
                value_str = '<not readable>'
            
            parsed = ''
            raw_value = char.get('value')
            if raw_value and char.get('uuid', '').lower() == 'acab0005-67f5-479e-8711-b3b99198ce6c':
                if len(raw_value) >= 7:
                    year = raw_value[0] + 2000
                    month = raw_value[1]
                    day = raw_value[2]
                    hour = raw_value[4]
                    minute = raw_value[5]
                    second = raw_value[6]
                    parsed = f"{year:04d}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}"

            # Truncate each field to fit
            char_name = char_name[:40]
            props = props[:20]
            value_str = value_str[:40]
            parsed = parsed[:20]
            row = f"{char_name:<40} {props:<20} {value_str:<40} {parsed:<20}"
            lines.append(row[:max_cols])
        lines.append('')
        if len(lines) >= max_lines:
            break
    return lines[:max_lines]

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
    curses.wrapper(poll_loop)