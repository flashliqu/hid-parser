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


if __name__ == "__main__":
    unittest.main()
