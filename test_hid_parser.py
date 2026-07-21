import unittest

from hid_parser import parse_descriptor


class HidParserTests(unittest.TestCase):
    def test_unit_and_physical_globals_persist_until_changed(self):
        descriptor = """
            0x05, 0x01,        // Usage Page (Generic Desktop)
            0x09, 0x02,        // Usage (Mouse)
            0xa1, 0x01,        // Collection (Application)
            0x15, 0x00,        // Logical Minimum (0)
            0x26, 0xff, 0x0f,  // Logical Maximum (4095)
            0x75, 0x10,        // Report Size (16)
            0x95, 0x01,        // Report Count (1)
            0x55, 0x0e,        // Unit Exponent (-2)
            0x65, 0x13,        // Unit (Inch, English Linear)
            0x09, 0x30,        // Usage (X)
            0x35, 0x00,        // Physical Minimum (0)
            0x46, 0x90, 0x01,  // Physical Maximum (400)
            0x81, 0x02,        // Input (Data,Var,Abs)
            0x46, 0x13, 0x01,  // Physical Maximum (275)
            0x09, 0x31,        // Usage (Y)
            0x81, 0x02,        // Input (Data,Var,Abs)
            0xc0,              // End Collection
        """

        rows = parse_descriptor(descriptor).groups[0].rows

        self.assertEqual([row.name for row in rows], ["X", "Y"])
        self.assertEqual([row.unit_label for row in rows], ["Inch (10^-2)", "Inch (10^-2)"])
        self.assertEqual([row.physical_max for row in rows], [400, 275])

    def test_32_bit_usage_range_preserves_embedded_usage_page(self):
        descriptor = """
            0x05, 0x01,                  // Usage Page (Generic Desktop)
            0x09, 0x02,                  // Usage (Mouse)
            0xa1, 0x01,                  // Collection (Application)
            0x75, 0x01,                  // Report Size (1)
            0x95, 0x02,                  // Report Count (2)
            0x1b, 0x01, 0x00, 0x09, 0x00, // Usage Minimum (Button 1)
            0x2b, 0x02, 0x00, 0x09, 0x00, // Usage Maximum (Button 2)
            0x81, 0x02,                  // Input (Data,Var,Abs)
            0xc0,                        // End Collection
        """

        rows = parse_descriptor(descriptor).groups[0].rows

        self.assertEqual([row.name for row in rows], ["Button 1", "Button 2"])
        self.assertEqual([row.usage_page for row in rows], [0x09, 0x09])
        self.assertEqual([row.usage_id for row in rows], [0x01, 0x02])

    def test_array_item_with_usage_range_collapses_to_one_field(self):
        # HID 1.11 Appendix E.6: an Array Input (flags=0x00) over a Usage
        # Minimum/Maximum range represents Report Count independent index
        # slots that can each report *any* usage in the range at runtime --
        # it is one field-group, not one fixed-usage field per slot the way
        # a Variable item (flags bit 1 set) would be. Naively expanding it
        # per slot would fabricate distinct fields out of (and truncate) the
        # 0x00-0x65 keycode range down to its first 6 values.
        descriptor = """
            0x05, 0x01,        // Usage Page (Generic Desktop)
            0x09, 0x06,        // Usage (Keyboard)
            0xa1, 0x01,        // Collection (Application)
            0x95, 0x06,        // Report Count (6)
            0x75, 0x08,        // Report Size (8)
            0x15, 0x00,        // Logical Minimum (0)
            0x25, 0x65,        // Logical Maximum (101)
            0x05, 0x07,        // Usage Page (Key Codes)
            0x19, 0x00,        // Usage Minimum (0)
            0x29, 0x65,        // Usage Maximum (101)
            0x81, 0x00,        // Input (Data, Array)
            0xc0,              // End Collection
        """

        rows = parse_descriptor(descriptor).groups[0].rows

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].count, 6)
        self.assertEqual(rows[0].usage_id, 0x00)
        self.assertEqual(rows[0].usage_id_max, 0x65)

    def test_push_pop_restores_full_global_state(self):
        # HID 1.11 Appendix D.1 joystick example: Report Size/Count and
        # Logical Minimum/Maximum are changed several times between Push and
        # Pop (for a Hat Switch, then Buttons); Pop must restore every Global
        # item to its exact value at the time of Push, not just some of them.
        descriptor = """
            0x05, 0x01, 0x09, 0x04, 0xa1, 0x01,  // Usage Page/Usage(Joystick)/Collection(Application)
            0x15, 0x81, 0x25, 0x7f,              // Logical Minimum(-127), Maximum(127)
            0x75, 0x08, 0x95, 0x02,              // Report Size(8), Count(2)
            0xa4,                                // Push
            0x15, 0x00, 0x25, 0x03,              // Logical Minimum(0), Maximum(3)  -- Hat Switch range
            0x75, 0x04, 0x95, 0x01,              // Report Size(4), Count(1)
            0x09, 0x39, 0x81, 0x42,              // Usage(Hat switch), Input (Null State)
            0xb4,                                // Pop
            0x09, 0x3b,                          // Usage (0x3B, placeholder "Throttle")
            0x95, 0x01,                          // Report Count(1)
            0x81, 0x02,                          // Input (Data,Var,Abs)
            0xc0,                                // End Collection
        """

        rows = parse_descriptor(descriptor).groups[0].rows

        throttle = rows[-1]
        self.assertEqual(throttle.size, 8)
        self.assertEqual(throttle.logical_min, -127)
        self.assertEqual(throttle.logical_max, 127)


if __name__ == "__main__":
    unittest.main()
