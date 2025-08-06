class CharacteristicParser:
    """Base class for characteristic parsers."""
    def parse_value(self, value):
        """Parses the raw value of a characteristic.

        Returns:
            A list of (description, value) tuples, or None.
        """
        raise NotImplementedError

    def encode_value(self, value):
        """Encodes a value for a characteristic.

        Returns:
            A bytearray, or None.
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

    def encode_value(self, dt):
        """Encodes a datetime object into a bytearray."""
        return bytearray([
            dt.year - 2000,
            dt.month,
            dt.day,
            0,  # Unknown byte
            dt.hour,
            dt.minute,
            dt.second
        ])


class TimerStateParser(CharacteristicParser):
    """Parses the timer state characteristic."""
    def parse_value(self, value):
        if not value:
            return None
        state = "Enabled" if value[0] == 0x01 else "Disabled"
        return [("Schedule Enabled", state)]

    def encode_value(self, enabled):
        """Encodes a boolean state into a bytearray."""
        return bytearray([0x01 if enabled else 0x00])


from parsers.schedule_coder import ScheduleCoder

class ScheduleParser(CharacteristicParser):
    """Parses the weekly schedule characteristic based on a 4-byte slot structure."""
    def parse_value(self, value):
        return ScheduleCoder.decode_schedule(value)

    def encode_value(self, schedule_data):
        """Encodes schedule data into a bytearray."""
        return ScheduleCoder.encode_schedule(schedule_data)


class BoilerParser(CharacteristicParser):
    """Parses a boiler's temperature and state characteristic."""
    def __init__(self, name):
        self.name = name

    def parse_value(self, value):
        if len(value) < 4:
            return None

        results = []

        # Temperature is always present
        temp_raw = int.from_bytes(value[0:2], 'little')
        temperature = temp_raw / 10.0
        results.append((f"{self.name} Boiler Temp", f"{temperature} C"))

        # Boiler Status as percentage
        status_code_byte = value[1]
        percentage = 0.0
        if self.name == "Brew":
            max_val = 3.0
            percentage = (status_code_byte / max_val) * 100 if max_val > 0 else 0
        elif self.name == "Steam":
            max_val = 4.0
            percentage = (status_code_byte / max_val) * 100 if max_val > 0 else 0

        results.insert(0, (f"{self.name} Boiler Status", f"{percentage:.0f}%"))

        return results

    def encode_value(self, value):
        """Boiler characteristics are read-only."""
        raise NotImplementedError("Boiler characteristics are read-only.")

# Parser registry
PARSERS = {
    "acab0005-67f5-479e-8711-b3b99198ce6c": DateTimeParser("Current Time"),
    "acab0004-67f5-479e-8711-b3b99198ce6c": DateTimeParser("Last Sync Time"),
    "acab0003-67f5-479e-8711-b3b99198ce6c": ScheduleParser(),
    "acab0002-67f5-479e-8711-b3b99198ce6c": TimerStateParser(),
    "acab0002-77f5-479e-8711-b3b99198ce6c": BoilerParser("Brew"),
    "acab0003-77f5-479e-8711-b3b99198ce6c": BoilerParser("Steam"),
}

def get_parser(uuid):
    """Returns a parser instance for the given UUID, if one exists."""
    return PARSERS.get(uuid.lower())