import struct

class ScheduleCoder:
    DAYS_OF_WEEK_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    # Format string for a single 4-byte schedule slot: End Minute, End Hour, Start Minute, Start Hour (with boiler bit)
    # Using little-endian byte order (not strictly necessary for single bytes, but good practice)
    _SLOT_FORMAT = '<BBBB' 

    @staticmethod
    def encode_schedule(schedule_data: dict) -> bytearray:
        """
        Encodes the high-level schedule dictionary into the 84-byte bytearray format.
        """
        encoded_bytes = bytearray(84)
        
        for day_index, day_name in enumerate(ScheduleCoder.DAYS_OF_WEEK_ORDER):
            slots = schedule_data.get(day_name, [])
            for slot_index in range(3): # Max 3 slots per day
                offset = (day_index * 3 + slot_index) * 4
                
                if slot_index < len(slots):
                    slot = slots[slot_index]
                    start_time_str = slot.get("start", "00:00")
                    end_time_str = slot.get("end", "00:00")
                    boiler_on = slot.get("boiler_on", False)

                    start_hour, start_minute = map(int, start_time_str.split(':'))
                    end_hour, end_minute = map(int, end_time_str.split(':'))

                    start_hour_byte = start_hour & 0x7F # Mask out MSB
                    if boiler_on:
                        start_hour_byte |= 0x80 # Set MSB for boiler on

                    # Pack the data into 4 bytes
                    packed_slot = struct.pack(ScheduleCoder._SLOT_FORMAT,
                                              end_minute,
                                              end_hour,
                                              start_minute,
                                              start_hour_byte)
                    encoded_bytes[offset:offset+4] = packed_slot
                else:
                    # If slot is not provided, ensure it's all zeros (disabled)
                    encoded_bytes[offset:offset+4] = bytearray([0x00, 0x00, 0x00, 0x00])
        
        return encoded_bytes

    @staticmethod
    def decode_schedule(value: bytearray) -> dict:
        """
        Decodes the 84-byte bytearray into the high-level schedule dictionary format.
        """
        if len(value) < 84:
            return {}

        parsed_schedule_dict = {}
        for day_index in range(7):
            day_name = ScheduleCoder.DAYS_OF_WEEK_ORDER[day_index]
            day_slots = []
            for slot_index in range(3):
                offset = (day_index * 3 + slot_index) * 4
                slot_data = value[offset:offset+4]

                # If all bytes in the slot are zero, it means the slot is not set
                if not any(slot_data):
                    continue

                # Unpack the 4 bytes
                end_minute, end_hour, start_minute, start_hour_byte = struct.unpack(ScheduleCoder._SLOT_FORMAT, slot_data)

                start_hour = start_hour_byte & 0x7F
                boiler_on = (start_hour_byte & 0x80) != 0

                day_slots.append({
                    "start": f"{start_hour:02d}:{start_minute:02d}",
                    "end": f"{end_hour:02d}:{end_minute:02d}",
                    "boiler_on": boiler_on
                })
            
            if day_slots:
                parsed_schedule_dict[day_name] = day_slots

        return parsed_schedule_dict
