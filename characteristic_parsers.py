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

# Parser registry
PARSERS = {
    "acab0005-67f5-479e-8711-b3b99198ce6c": DateTimeParser("(?) Last Synchronized Timestamp"),
    "acab0004-67f5-479e-8711-b3b99198ce6c": DateTimeParser("Current Time"),
    "acab0002-67f5-479e-8711-b3b99198ce6c": TimerStateParser(),
}

def get_parser(uuid):
    """Returns a parser instance for the given UUID, if one exists."""
    return PARSERS.get(uuid.lower())