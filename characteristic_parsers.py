class CharacteristicParser:
    """Base class for characteristic parsers."""
    def parse_value(self, value):
        """Parses the raw value of a characteristic.

        Returns:
            A list of (description, value) tuples, or None.
        """
        raise NotImplementedError

class DateTimeParser(CharacteristicParser):
    """Parses the datetime characteristic."""
    def __init__(self, description):
        self.description = description

    def parse_value(self, value):
        if len(value) >= 7:
            year = value[0] + 2000
            month = value[1]
            day = value[2]
            # value[3] is unknown
            hour = value[4]
            minute = value[5]
            second = value[6]
            dt_str = f"{year:04d}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}"
            return [(self.description, dt_str)]
        return None

class TimerStateParser(CharacteristicParser):
    """Parses the timer state characteristic."""
    def parse_value(self, value):
        if not value:
            return None
        state = "Enabled" if value[0] == 0x01 else "Disabled"
        return [("Timer State", state)]

class ScheduleParser(CharacteristicParser):
    """Parses the weekly schedule characteristic based on a 4-byte slot structure."""
    DAYS_OF_WEEK = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    def parse_value(self, value):
        if len(value) < 84:
            return None

        parsed_schedule = []
        for day_index in range(7):
            day_name = self.DAYS_OF_WEEK[day_index]
            day_schedule = []
            for slot_index in range(3):
                offset = (day_index * 3 + slot_index) * 4
                slot_data = value[offset:offset+4]

                # Slot is disabled if all bytes are zero
                if not any(slot_data):
                    continue

                end_minute = slot_data[0]
                end_hour = slot_data[1]
                start_minute = slot_data[2]
                start_hour_byte = slot_data[3]

                start_hour = start_hour_byte & 0x7F  # Lower 7 bits are the hour
                boiler_on = (start_hour_byte & 0x80) != 0 # MSB is boiler flag

                time_range = f"{start_hour:02d}:{start_minute:02d} - {end_hour:02d}:{end_minute:02d}"
                boiler_status = " (Boiler ON)" if boiler_on else ""
                day_schedule.append(f"{time_range}{boiler_status}")
            
            if day_schedule:
                parsed_schedule.append((day_name, ", ".join(day_schedule)))

        return parsed_schedule

class PowerAndTempParser(CharacteristicParser):
    """Parses the power and temperature characteristic."""
    def parse_value(self, value):
        if len(value) < 4:
            return None

        power_state = "On" if value[1] == 0x03 else "Off"
        temp_raw = int.from_bytes(value[0:2], 'little')
        temperature = temp_raw / 10.0

        return [
            ("Power State", power_state),
            ("Temperature", f"{temperature} °C"),
        ]

# Parser registry
PARSERS = {
    "acab0005-67f5-479e-8711-b3b99198ce6c": DateTimeParser("Current Time"),
    "acab0004-67f5-479e-8711-b3b99198ce6c": DateTimeParser("Timer Time"),
    "acab0003-67f5-479e-8711-b3b99198ce6c": ScheduleParser(),
    "acab0002-67f5-479e-8711-b3b99198ce6c": TimerStateParser(),
    "acab0002-77f5-479e-8711-b3b99198ce6c": PowerAndTempParser(),
}

def get_parser(uuid):
    """Returns a parser instance for the given UUID, if one exists."""
    return PARSERS.get(uuid.lower())
