class ScheduleCoder:
    DAYS_OF_WEEK_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

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

                    # Reconstruct the 4-byte slot data based on our understanding
                    # Byte 0: End Minute
                    # Byte 1: End Hour
                    # Byte 2: Start Minute
                    # Byte 3: Start Hour (lower 7 bits) + Boiler On (MSB)

                    encoded_bytes[offset] = end_minute
                    encoded_bytes[offset + 1] = end_hour
                    encoded_bytes[offset + 2] = start_minute
                    
                    start_hour_byte = start_hour & 0x7F # Mask out MSB
                    if boiler_on:
                        start_hour_byte |= 0x80 # Set MSB for boiler on
                    encoded_bytes[offset + 3] = start_hour_byte
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

                end_minute = slot_data[0]
                end_hour = slot_data[1]
                start_minute = slot_data[2]
                start_hour_byte = slot_data[3]

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
