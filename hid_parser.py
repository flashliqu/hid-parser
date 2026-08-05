#!/usr/bin/env python3
"""Parse a raw USB HID report descriptor into a collection tree and per-report
field tables, similar to a manual HID descriptor breakdown.

Usage:
    python3 hid_parser.py                      # parse the built-in sample descriptor
    python3 hid_parser.py my_descriptor.txt     # parse a file (C-style byte listing)
    python3 hid_parser.py my_descriptor.txt --html out.html

The input is the usual firmware-style byte listing, e.g.:

    0x05, 0x0d,              // USAGE_PAGE (Digitizers)
    0x09, 0x05,              // USAGE (Touch Pad)
    0xa1, 0x01,              // COLLECTION (Application)
    0x85, REPORTID_TOUCHPAD, //   REPORT_ID (Touch pad)
    ...

Symbolic REPORT_ID macros (all-caps identifiers like REPORTID_TOUCHPAD) are
supported directly -- they don't need to resolve to a numeric value, they're
used as-is to label and group reports, exactly like the macro names in a
device's own descriptor source.
"""

import argparse
import html
import re
import subprocess
import sys
import webbrowser
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# --------------------------------------------------------------------------
# Sample descriptor (a Windows Precision Touchpad style HID report descriptor)
# --------------------------------------------------------------------------

SAMPLE_DESCRIPTOR = r"""
//TOUCH PAD input TLC
    0x05, 0x0d,                         // USAGE_PAGE (Digitizers)
    0x09, 0x05,                         // USAGE (Touch Pad)
    0xa1, 0x01,                         // COLLECTION (Application)
    0x85, REPORTID_TOUCHPAD,            //   REPORT_ID (Touch pad)
    0x09, 0x22,                         //   USAGE (Finger)
    0xa1, 0x02,                         //   COLLECTION (Logical)
    0x15, 0x00,                         //       LOGICAL_MINIMUM (0)
    0x25, 0x01,                         //       LOGICAL_MAXIMUM (1)
    0x09, 0x47,                         //       USAGE (Confidence)
    0x09, 0x42,                         //       USAGE (Tip switch)
    0x95, 0x02,                         //       REPORT_COUNT (2)
    0x75, 0x01,                         //       REPORT_SIZE (1)
    0x81, 0x02,                         //       INPUT (Data,Var,Abs)
    0x95, 0x01,                         //       REPORT_COUNT (1)
    0x75, 0x02,                         //       REPORT_SIZE (2)
    0x25, 0x02,                         //       LOGICAL_MAXIMUM (2)
    0x09, 0x51,                         //       USAGE (Contact Identifier)
    0x81, 0x02,                         //       INPUT (Data,Var,Abs)
    0x75, 0x01,                         //       REPORT_SIZE (1)
    0x95, 0x04,                         //       REPORT_COUNT (4)
    0x81, 0x03,                         //       INPUT (Cnst,Var,Abs)
    0x05, 0x01,                         //       USAGE_PAGE (Generic Desk..
    0x15, 0x00,                         //       LOGICAL_MINIMUM (0)
    0x26, 0xff, 0x0f,                   //       LOGICAL_MAXIMUM (4095)
    0x75, 0x10,                         //       REPORT_SIZE (16)
    0x55, 0x0e,                         //       UNIT_EXPONENT (-2)
    0x65, 0x13,                         //       UNIT(Inch,EngLinear)
    0x09, 0x30,                         //       USAGE (X)
    0x35, 0x00,                         //       PHYSICAL_MINIMUM (0)
    0x46, 0x90, 0x01,                   //       PHYSICAL_MAXIMUM (400)
    0x95, 0x01,                         //       REPORT_COUNT (1)
    0x81, 0x02,                         //       INPUT (Data,Var,Abs)
    0x46, 0x13, 0x01,                   //       PHYSICAL_MAXIMUM (275)
    0x09, 0x31,                         //       USAGE (Y)
    0x81, 0x02,                         //       INPUT (Data,Var,Abs)
    0xc0,                               //    END_COLLECTION
    0x55, 0x0C,                         //    UNIT_EXPONENT (-4)
    0x66, 0x01, 0x10,                   //    UNIT (Seconds)
    0x47, 0xff, 0xff, 0x00, 0x00,       //    PHYSICAL_MAXIMUM (65535)
    0x27, 0xff, 0xff, 0x00, 0x00,       //    LOGICAL_MAXIMUM (65535)
    0x75, 0x10,                         //    REPORT_SIZE (16)
    0x95, 0x01,                         //    REPORT_COUNT (1)
    0x05, 0x0d,                         //    USAGE_PAGE (Digitizers)
    0x09, 0x56,                         //    USAGE (Scan Time)
    0x81, 0x02,                         //    INPUT (Data,Var,Abs)
    0x09, 0x54,                         //    USAGE (Contact count)
    0x25, 0x7f,                         //    LOGICAL_MAXIMUM (127)
    0x95, 0x01,                         //    REPORT_COUNT (1)
    0x75, 0x08,                         //    REPORT_SIZE (8)
    0x81, 0x02,                         //    INPUT (Data,Var,Abs)
    0x05, 0x09,                         //    USAGE_PAGE (Button)
    0x09, 0x01,                         //    USAGE_(Button 1)
    0x09, 0x02,                         //    USAGE_(Button 2)
    0x09, 0x03,                         //    USAGE_(Button 3)
    0x25, 0x01,                         //    LOGICAL_MAXIMUM (1)
    0x75, 0x01,                         //    REPORT_SIZE (1)
    0x95, 0x03,                         //    REPORT_COUNT (3)
    0x81, 0x02,                         //    INPUT (Data,Var,Abs)
    0x95, 0x05,                         //    REPORT_COUNT (5)
    0x81, 0x03,                         //    INPUT (Cnst,Var,Abs)
    0x05, 0x0d,                         //    USAGE_PAGE (Digitizer)
    0x85, REPORTID_MAX_COUNT,           //   REPORT_ID (Feature)
    0x09, 0x55,                         //    USAGE (Contact Count Maximum)
    0x09, 0x59,                         //    USAGE (Pad TYpe)
    0x75, 0x04,                         //    REPORT_SIZE (4)
    0x95, 0x02,                         //    REPORT_COUNT (2)
    0x25, 0x0f,                         //    LOGICAL_MAXIMUM (15)
    0xb1, 0x02,                         //    FEATURE (Data,Var,Abs)
    0x06, 0x00, 0xff,                   //    USAGE_PAGE (Vendor Defined)
    0x85, REPORTID_PTPHQA,              //    REPORT_ID (PTPHQA)
    0x09, 0xC5,                         //    USAGE (Vendor Usage 0xC5)
    0x15, 0x00,                         //    LOGICAL_MINIMUM (0)
    0x26, 0xff, 0x00,                   //    LOGICAL_MAXIMUM (0xff)
    0x75, 0x08,                         //    REPORT_SIZE (8)
    0x96, 0x00, 0x01,                   //    REPORT_COUNT (0x100 (256))
    0xb1, 0x02,                         //    FEATURE (Data,Var,Abs)
    0xc0,                               // END_COLLECTION
    //CONFIG TLC
    0x05, 0x0d,                         //    USAGE_PAGE (Digitizer)
    0x09, 0x0E,                         //    USAGE (Configuration)
    0xa1, 0x01,                         //   COLLECTION (Application)
    0x85, REPORTID_FEATURE,             //   REPORT_ID (Feature)
    0x09, 0x22,                         //   USAGE (Finger)
    0xa1, 0x02,                         //   COLLECTION (logical)
    0x09, 0x52,                         //    USAGE (Input Mode)
    0x15, 0x00,                         //    LOGICAL_MINIMUM (0)
    0x25, 0x0a,                         //    LOGICAL_MAXIMUM (10)
    0x75, 0x08,                         //    REPORT_SIZE (8)
    0x95, 0x01,                         //    REPORT_COUNT (1)
    0xb1, 0x02,                         //    FEATURE (Data,Var,Abs
    0xc0,                               //   END_COLLECTION
    0x09, 0x22,                         //   USAGE (Finger)
    0xa1, 0x00,                         //   COLLECTION (physical)
    0x85, REPORTID_FUNCTION_SWITCH,     //     REPORT_ID (Feature)
    0x09, 0x57,                         //     USAGE(Surface switch)
    0x09, 0x58,                         //     USAGE(Button switch)
    0x75, 0x01,                         //     REPORT_SIZE (1)
    0x95, 0x02,                         //     REPORT_COUNT (2)
    0x25, 0x01,                         //     LOGICAL_MAXIMUM (1)
    0xb1, 0x02,                         //     FEATURE (Data,Var,Abs)
    0x95, 0x06,                         //     REPORT_COUNT (6)
    0xb1, 0x03,                         //     FEATURE (Cnst,Var,Abs)
    0xc0,                               //   END_COLLECTION
    0xc0,                               // END_COLLECTION
    //MOUSE TLC
    0x05, 0x01,                         // USAGE_PAGE (Generic Desktop)
    0x09, 0x02,                         // USAGE (Mouse)
    0xa1, 0x01,                         // COLLECTION (Application)
    0x85, REPORTID_MOUSE,               //   REPORT_ID (Mouse)
    0x09, 0x01,                         //   USAGE (Pointer)
    0xa1, 0x00,                         //   COLLECTION (Physical)
    0x05, 0x09,                         //     USAGE_PAGE (Button)
    0x19, 0x01,                         //     USAGE_MINIMUM (Button 1)
    0x29, 0x02,                         //     USAGE_MAXIMUM (Button 2)
    0x25, 0x01,                         //     LOGICAL_MAXIMUM (1)
    0x75, 0x01,                         //     REPORT_SIZE (1)
    0x95, 0x02,                         //     REPORT_COUNT (2)
    0x81, 0x02,                         //     INPUT (Data,Var,Abs)
    0x95, 0x06,                         //     REPORT_COUNT (6)
    0x81, 0x03,                         //     INPUT (Cnst,Var,Abs)
    0x05, 0x01,                         //     USAGE_PAGE (Generic Desktop)
    0x09, 0x30,                         //     USAGE (X)
    0x09, 0x31,                         //     USAGE (Y)
    0x75, 0x10,                         //     REPORT_SIZE (16)
    0x95, 0x02,                         //     REPORT_COUNT (2)
    0x25, 0x0a,                         //     LOGICAL_MAXIMUM (10)
    0x81, 0x06,                         //     INPUT (Data,Var,Rel)
    0xc0,                               //   END_COLLECTION
    0xc0,                                //END_COLLECTION
"""

# --------------------------------------------------------------------------
# HID item tag tables
# --------------------------------------------------------------------------

MAIN_TAGS = {0x8: "Input", 0x9: "Output", 0xA: "Collection", 0xB: "Feature", 0xC: "EndCollection"}
GLOBAL_TAGS = {
    0x0: "UsagePage", 0x1: "LogicalMinimum", 0x2: "LogicalMaximum",
    0x3: "PhysicalMinimum", 0x4: "PhysicalMaximum", 0x5: "UnitExponent",
    0x6: "Unit", 0x7: "ReportSize", 0x8: "ReportID", 0x9: "ReportCount",
    0xA: "Push", 0xB: "Pop",
}
LOCAL_TAGS = {
    0x0: "Usage", 0x1: "UsageMinimum", 0x2: "UsageMaximum",
    0x3: "DesignatorIndex", 0x4: "DesignatorMinimum", 0x5: "DesignatorMaximum",
    0x7: "StringIndex", 0x8: "StringMinimum", 0x9: "StringMaximum", 0xA: "Delimiter",
}
COLLECTION_TYPES = {
    0x00: "Physical", 0x01: "Application", 0x02: "Logical",
    0x03: "Report", 0x04: "Named Array", 0x05: "Usage Switch", 0x06: "Usage Modifier",
}

USAGE_NAMES = {
    0x01: {0x01: "Pointer", 0x02: "Mouse", 0x30: "X", 0x31: "Y"},
    0x0D: {
        0x05: "Touch Pad", 0x0E: "Configuration", 0x22: "Finger",
        0x30: "Pressure", 0x3F: "Azimuth",
        0x42: "Tip Switch", 0x47: "Confidence", 0x48: "Width", 0x49: "Height",
        0x51: "Contact Identifier", 0x52: "Input Mode", 0x54: "Contact Count",
        0x55: "Contact Count Maximum", 0x56: "Scan Time", 0x57: "Surface Switch",
        0x58: "Button Switch", 0x59: "Pad Type", 0x60: "Latency Mode",
        0xB0: "Button Press Threshold",
    },
    0x0E: {0x01: "Simple Haptics Controller", 0x23: "Intensity"},
    0x20: {0x0494: "Mechanical Force"},
}

# Well-known vendor-defined usages from Microsoft's Precision Touchpad
# "PTPHQA" device-certification report -- not part of the HID spec, but a
# documented convention worth naming instead of a generic "Vendor Data".
PTPHQA_VENDOR_USAGES = {0xC5: "Vendor Data (PTPHQA Blob)", 0xC6: "Segment Number", 0xC7: "Segment Data"}

UNIT_SYMBOL_NAMES = {"in": "Inch", "s": "Seconds", "g": "Gram"}

PALETTE = [
    ("#e4ecdd", "#7f9d68", "#33471f"),  # touchpad input - sage
    ("#f5ead2", "#c69641", "#5a3f0c"),  # feature (max count) - amber
    ("#f5e0da", "#c06a52", "#5c2717"),  # feature (ptphqa) - clay
    ("#dfe8f2", "#5081b3", "#1c3550"),  # feature (config) - steel blue
    ("#e9e0f0", "#8c68b0", "#3c2652"),  # feature (function switch) - violet
    ("#dcebee", "#4791a3", "#153b43"),  # mouse input - teal
]

TOKEN_RE = re.compile(
    r"0[xX][A-Za-z0-9_]*|[0-9]+[A-Za-z_][A-Za-z0-9_]*|[0-9]+|[A-Za-z_][A-Za-z0-9_]*"
)
HEX_BYTE_RE = re.compile(
    r"0[xX]([0-9a-fA-F]+)(?:[uU](?:ll|LL|[lL])?|(?:ll|LL|[lL])[uU]?)?"
)


# --------------------------------------------------------------------------
# Tokenizer
# --------------------------------------------------------------------------

@dataclass
class Token:
    kind: str  # 'num' or 'sym'
    value: object
    line: int = 0


def descriptor_error(message: str, line: int) -> ValueError:
    return ValueError(f"Line {line}: {message}" if line else message)


def tokenize(text: str) -> list:
    tokens = []
    source_lines = [line.split("//", 1)[0] for line in text.splitlines()]
    has_initializer = any("{" in line for line in source_lines)
    brace_depth = 0
    for ln, source_line in enumerate(source_lines, start=1):
        if has_initializer:
            chars = []
            for char in source_line:
                if char == "{":
                    brace_depth += 1
                elif char == "}":
                    brace_depth = max(brace_depth - 1, 0)
                elif brace_depth:
                    chars.append(char)
            code = "".join(chars)
        else:
            code = source_line
        for m in TOKEN_RE.finditer(code):
            tok = m.group(0)
            if tok[:2] in ("0x", "0X"):
                hex_match = HEX_BYTE_RE.fullmatch(tok)
                if not hex_match:
                    raise descriptor_error(f"Malformed hexadecimal byte: {tok}", ln)
                value = int(hex_match.group(1), 16)
                if value > 0xFF:
                    raise descriptor_error(f"Expected a byte, got {tok}", ln)
                tokens.append(Token("num", value, ln))
            elif tok[0].isdigit():
                if not tok.isdigit():
                    raise descriptor_error(f"Malformed decimal byte: {tok}", ln)
                raise descriptor_error(f"Decimal byte literals are not supported: {tok}", ln)
            elif re.match(r"^[A-Z][A-Z0-9_]*$", tok):
                tokens.append(Token("sym", tok, ln))
    return tokens


# --------------------------------------------------------------------------
# Field / collection data model
# --------------------------------------------------------------------------

@dataclass
class FieldRow:
    name: str
    usage_page: Optional[int]
    usage_id: Optional[int]
    size: int
    count: int
    logical_min: int
    logical_max: int
    physical_min: Optional[int]
    physical_max: Optional[int]
    unit_label: Optional[str]
    type_label: str
    usage_id_max: Optional[int] = None
    usage_text: Optional[str] = None


@dataclass
class CollectionNode:
    ctype: str
    usage_page: Optional[int]
    usage_id: Optional[int]
    children: list = field(default_factory=list)
    fields: list = field(default_factory=list)
    is_app: bool = False


@dataclass
class ReportGroup:
    order: int
    report_id: str
    main_type: str
    app_name: str
    rows: list = field(default_factory=list)


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def sign_extend(raw: int, nbytes: int) -> int:
    if nbytes == 1 and raw >= 0x80:
        return raw - 0x100
    if nbytes == 2 and raw >= 0x8000:
        return raw - 0x10000
    if nbytes == 4 and raw >= 0x80000000:
        return raw - 0x100000000
    return raw


def page_str(page: Optional[int]) -> str:
    if page is None:
        return "—"
    return f"0x{page:04X}" if page > 0xFF else f"0x{page:02X}"


def usage_str(uid: Optional[int]) -> str:
    if uid is None:
        return "—"
    return f"0x{uid:02X}"


def usage_display_name(page: Optional[int], uid: Optional[int]) -> str:
    if uid is None:
        return "Padding"
    if page == 0x09:
        return f"Button {uid}"
    if page is not None and page >= 0xFF00:
        return PTPHQA_VENDOR_USAGES.get(uid, "Vendor Data")
    return USAGE_NAMES.get(page, {}).get(uid, f"Usage 0x{uid:02X}")


def usage_range_name(page: Optional[int], uid: Optional[int], uid_max: Optional[int]) -> str:
    if uid_max is None:
        return usage_display_name(page, uid)
    min_name = usage_display_name(page, uid)
    max_name = usage_display_name(page, uid_max)
    return min_name if min_name == max_name else f"{min_name} – {max_name}"


def collection_usage_name(page: Optional[int], uid: Optional[int]) -> str:
    if uid is None:
        return f"Usage Page {page_str(page)}" if page is not None else ""
    return usage_display_name(page, uid)


def decode_unit(unit_val: int, exponent: int) -> Optional[str]:
    if not unit_val:
        return None
    system_code = unit_val & 0xF
    systems = {1: "SI Linear", 2: "SI Rotation", 3: "English Linear", 4: "English Rotation"}
    system = systems.get(system_code)
    if not system:
        return f"0x{unit_val:X} (10^{exponent})" if exponent else f"0x{unit_val:X}"
    symbols = {
        "SI Linear": ["cm", "g", "s", "K", "A", "cd"],
        "SI Rotation": ["rad", "g", "s", "K", "A", "cd"],
        "English Linear": ["in", "slug", "s", "F", "A", "cd"],
        "English Rotation": ["deg", "slug", "s", "F", "A", "cd"],
    }[system]
    parts = []
    for idx in range(6):
        nibble = (unit_val >> (4 * (idx + 1))) & 0xF
        if nibble == 0:
            continue
        exp = nibble - 16 if nibble > 7 else nibble
        parts.append(symbols[idx] if exp == 1 else f"{symbols[idx]}^{exp}")
    label = "·".join(parts)
    label = UNIT_SYMBOL_NAMES.get(label, label)
    if not label:
        return None
    if exponent:
        label += f" (10^{exponent})"
    return label


def type_label(main_name: str, flags: int) -> str:
    is_const = bool(flags & 0x1)
    is_rel = bool(flags & 0x4)
    if main_name == "Feature":
        return "Feature (Const)" if is_const else "Feature"
    label = "Const" if is_const else "Data"
    if is_rel and not is_const:
        label += " (Relative)"
    return label


# Local usage state is an ordered list of entries, so that a Main item sees its
# usages in the order the descriptor declared them -- the order the HID spec
# assigns them to fields. Each entry is one of:
#     ("single", (page, uid))
#     ["range", (page, uid), (page, uid) or None]   # None until Usage Maximum
def usage_entry_value(raw_value: int, size: int, current_page: Optional[int]):
    """Resolve a Usage/Usage Minimum/Usage Maximum item to a (page, uid) pair."""
    if size == 4:  # extended usage: the page is embedded in the high half
        return ((raw_value >> 16) & 0xFFFF, raw_value & 0xFFFF)
    return (current_page, raw_value)


def start_usage_range(entries: list, value) -> None:
    entries.append(["range", value, None])


def finish_usage_range(entries: list, value) -> None:
    # A Usage Maximum with no preceding Minimum is malformed. Like a dangling
    # Minimum (dropped in expand_fields), it's exactly the kind of real-world
    # anomaly this tool exists to surface, so ignore the stray item rather than
    # aborting the whole parse.
    for entry in reversed(entries):
        if entry[0] == "range" and entry[2] is None:
            entry[2] = value
            return


def first_usage(entries: list):
    """The usage a Collection item takes its identity from, or None."""
    return entries[0][1] if entries else None


def entry_page(entry, current_page: Optional[int]) -> Optional[int]:
    if entry[0] == "single":
        return entry[1][0]
    min_page, max_page = entry[1][0], entry[2][0]
    return min_page if min_page == max_page else current_page


def usage_entry_name(entry, current_page: Optional[int]) -> str:
    page = entry_page(entry, current_page)
    if entry[0] == "single":
        return usage_display_name(page, entry[1][1])
    return usage_range_name(page, entry[1][1], entry[2][1])


def usage_entry_text(entry, current_page: Optional[int]) -> str:
    page = entry_page(entry, current_page)
    if entry[0] == "single":
        return f"({page_str(page)}) {usage_str(entry[1][1])}"
    return f"({page_str(page)}) {usage_str(entry[1][1])}–{usage_str(entry[2][1])}"


def expanded_usages(entries: list, count: int, current_page: Optional[int]) -> list:
    """Flatten the entries into one (page, uid) per report slot, in order."""
    values = []
    for entry in entries:
        if entry[0] == "single":
            values.append(entry[1])
        else:
            page = entry_page(entry, current_page)
            for uid in range(entry[1][1], entry[2][1] + 1):
                if len(values) >= count:
                    break
                values.append((page, uid))
        if len(values) >= count:
            break
    if not values:
        return []
    while len(values) < count:  # last usage repeats for any extra slots
        values.append(values[-1])
    return values[:count]


def padding_row(count: int) -> dict:
    return {"usage_page": None, "usage_id": None, "usage_id_max": None,
            "usage_text": None, "name": "Padding", "count": count}


def expand_fields(usage_entries: list, count: int, current_page, is_array: bool) -> list:
    """Split a Main item's REPORT_COUNT slots across the usages declared for it.

    Variable items (is_array=False) mirror how these descriptors are conventionally
    read: one usage per bit slot when usages line up with the count (Button 1/2/3),
    the last usage repeated for any extra slots per the HID spec.

    Array items (is_array=True) are semantically different: REPORT_COUNT is the
    number of simultaneous index slots (e.g. up to 6 concurrent keycodes), and
    each slot can independently hold any value in the declared usage set at
    runtime -- it is one field-group, not one distinct control per slot. Splitting
    those per slot (like a Variable item) would fabricate `count` fake fields out
    of what is really a single ranged array, e.g. truncating a 0x00-0x65 keycode
    array down to just its first few values. So an Array item always collapses to
    a single row spanning the whole REPORT_COUNT, listing every declared usage.
    Only a lone range collapses to usage_id/usage_id_max: a range mixed with
    discrete usages is not contiguous, and folding it into one min-max span would
    claim the gaps between them are declared usages when they are not.

    A single aggregated "Padding" row is returned when no usage was declared at
    all (pure constant filler), regardless of Array/Variable.
    """
    # Drop a Minimum that no Maximum ever closed (e.g. the HID 1.11 spec's own
    # Appendix D.1 joystick example) instead of aborting the whole parse.
    entries = [e for e in usage_entries if e[0] == "single" or e[2] is not None]

    if is_array:
        if not entries:
            return [padding_row(count)]
        first = entries[0]
        lone_range = first if len(entries) == 1 and first[0] == "range" else None
        return [{
            "usage_page": entry_page(first, current_page),
            "usage_id": first[1][1],
            "usage_id_max": lone_range[2][1] if lone_range else None,
            "usage_text": ", ".join(usage_entry_text(e, current_page) for e in entries),
            "name": ", ".join(usage_entry_name(e, current_page) for e in entries),
            "count": count,
        }]

    values = expanded_usages(entries, count, current_page)
    if not values:
        return [padding_row(count)]
    rows = []
    i = 0
    while i < len(values):
        j = i
        while j + 1 < len(values) and values[j + 1] == values[i]:
            j += 1
        page, uid = values[i]
        rows.append({
            "usage_page": page,
            "usage_id": uid,
            "usage_id_max": None,
            "usage_text": f"({page_str(page)}) {usage_str(uid)}",
            "name": usage_display_name(page, uid),
            "count": j - i + 1,
        })
        i = j + 1
    return rows


# --------------------------------------------------------------------------
# Main parser
# --------------------------------------------------------------------------

class ParseResult:
    def __init__(self):
        self.root = []
        self.groups = []


def parse_descriptor(text: str) -> ParseResult:
    tokens = tokenize(text)

    usage_page = None
    logical_min = 0
    logical_max_raw = 0
    logical_max_size = 0
    physical_min = 0
    physical_max_raw = 0
    physical_max_size = 0
    unit_exponent = 0
    unit = 0
    report_size = 0
    report_count = 0
    report_id = None
    physical_min_defined = False
    physical_max_defined = False
    unit_defined = False

    global_stack = []
    usages: list = []
    collection_stack: list = []
    root: list = []
    app_name_stack: list = []
    report_groups: dict = {}
    group_order: list = []

    def current_parent():
        return collection_stack[-1].children if collection_stack else root

    def reset_local():
        nonlocal usages
        usages = []

    i = 0
    n = len(tokens)
    while i < n:
        prefix_tok = tokens[i]
        i += 1
        if prefix_tok.kind != "num":
            continue
        prefix = prefix_tok.value

        if prefix == 0xFE:  # long item, rare - skip
            data_size = tokens[i].value if i < n else 0
            i += 2  # data-size byte + long-item tag byte
            i += data_size
            continue

        size_code = prefix & 0x03
        size = (0, 1, 2, 4)[size_code]
        type_code = (prefix >> 2) & 0x03
        tag = (prefix >> 4) & 0x0F

        data_toks = tokens[i:i + size]
        i += size

        raw_value = 0
        symbol = None
        if size > 0:
            if len(data_toks) == 1 and data_toks[0].kind == "sym":
                symbol = data_toks[0].value
            else:
                for k, t in enumerate(data_toks):
                    raw_value += (t.value or 0) * (256 ** k)

        if type_code == 1:  # Global
            name = GLOBAL_TAGS.get(tag)
            if name == "UsagePage":
                usage_page = raw_value
            elif name == "LogicalMinimum":
                logical_min = sign_extend(raw_value, size)
            elif name == "LogicalMaximum":
                logical_max_raw = raw_value
                logical_max_size = size
            elif name == "PhysicalMinimum":
                physical_min = sign_extend(raw_value, size)
                physical_min_defined = True
            elif name == "PhysicalMaximum":
                physical_max_raw = raw_value
                physical_max_size = size
                physical_max_defined = True
            elif name == "UnitExponent":
                v = raw_value & 0xF
                if v > 7:
                    v -= 16
                unit_exponent = v
                unit_defined = True
            elif name == "Unit":
                unit = raw_value
                unit_defined = True
            elif name == "ReportSize":
                report_size = raw_value
            elif name == "ReportCount":
                report_count = raw_value
            elif name == "ReportID":
                report_id = symbol if symbol is not None else raw_value
            elif name == "Push":
                global_stack.append((usage_page, logical_min, logical_max_raw,
                                      logical_max_size, physical_min,
                                      physical_max_raw, physical_max_size,
                                      unit_exponent, unit, report_size,
                                      report_count, report_id, physical_min_defined,
                                      physical_max_defined,
                                      unit_defined))
            elif name == "Pop":
                if global_stack:
                    (usage_page, logical_min, logical_max_raw, logical_max_size,
                     physical_min, physical_max_raw, physical_max_size, unit_exponent,
                     unit, report_size, report_count, report_id,
                     physical_min_defined, physical_max_defined,
                     unit_defined) = global_stack.pop()

        elif type_code == 2:  # Local
            name = LOCAL_TAGS.get(tag)
            if name == "Usage":
                usages.append(("single", usage_entry_value(raw_value, size, usage_page)))
            elif name == "UsageMinimum":
                start_usage_range(usages, usage_entry_value(raw_value, size, usage_page))
            elif name == "UsageMaximum":
                finish_usage_range(usages, usage_entry_value(raw_value, size, usage_page))

        elif type_code == 0:  # Main
            name = MAIN_TAGS.get(tag)
            if name == "Collection":
                ctype_name = COLLECTION_TYPES.get(raw_value, f"Reserved (0x{raw_value:X})")
                first = first_usage(usages)
                node_page, node_uid = first if first is not None else (None, None)
                node = CollectionNode(ctype=ctype_name, usage_page=node_page, usage_id=node_uid)
                current_parent().append(node)
                collection_stack.append(node)
                if ctype_name == "Application":
                    node.is_app = True
                    app_name_stack.append(collection_usage_name(node_page, node_uid))
                reset_local()

            elif name == "EndCollection":
                node = collection_stack.pop() if collection_stack else None
                if node and node.is_app:
                    app_name_stack.pop()
                reset_local()

            elif name in ("Input", "Output", "Feature"):
                flags = raw_value
                is_array = not (flags & 0x02)
                rows = expand_fields(usages, report_count, usage_page, is_array)
                unit_valid = unit_defined
                logical_max = (
                    sign_extend(logical_max_raw, logical_max_size)
                    if logical_min < 0 else logical_max_raw
                )
                physical_max = (
                    sign_extend(physical_max_raw, physical_max_size)
                    if physical_min < 0 else physical_max_raw
                )
                # HID 1.11 section 6.2.2.7: if either physical extent is
                # undefined, or both are zero, the pair reverts to the logical
                # extents -- a lone Physical Maximum does not stand on its own.
                physical_valid = (
                    physical_min_defined and physical_max_defined
                    and not (physical_min == 0 and physical_max == 0)
                )
                field_rows = []
                for row in rows:
                    field_rows.append(FieldRow(
                        name=row["name"],
                        usage_page=row["usage_page"],
                        usage_id=row["usage_id"],
                        usage_id_max=row["usage_id_max"],
                        usage_text=row["usage_text"],
                        size=report_size,
                        count=row["count"],
                        logical_min=logical_min,
                        logical_max=logical_max,
                        physical_min=physical_min if physical_valid else logical_min,
                        physical_max=physical_max if physical_valid else logical_max,
                        unit_label=decode_unit(unit, unit_exponent) if unit_valid else None,
                        type_label=type_label(name, flags),
                    ))
                id_label = "—" if report_id is None else (
                    report_id if isinstance(report_id, str) else usage_str(report_id))
                group_key = (id_label, name)
                if group_key not in report_groups:
                    grp = ReportGroup(
                        order=len(group_order) + 1,
                        report_id=id_label,
                        main_type=name,
                        app_name=app_name_stack[-1] if app_name_stack else "",
                    )
                    report_groups[group_key] = grp
                    group_order.append(group_key)
                report_groups[group_key].rows.extend(field_rows)

                parent_node = collection_stack[-1] if collection_stack else None
                if parent_node is not None:
                    parent_node.fields.extend(
                        (r.name, r.size, r.count) for r in field_rows
                    )
                reset_local()

    result = ParseResult()
    result.root = root
    result.groups = [report_groups[k] for k in group_order]
    return result


# --------------------------------------------------------------------------
# Text output
# --------------------------------------------------------------------------

def fmt_cell(v) -> str:
    return "—" if v is None else str(v)


COLUMNS = ["Field", "Usage (Page)", "Size (bits)", "Count", "Logical Min",
           "Logical Max", "Physical Min", "Physical Max", "Unit", "Type"]


def row_cells(r: FieldRow):
    return [
        r.name, fmt_cell(r.usage_text), str(r.size), str(r.count),
        fmt_cell(r.logical_min), fmt_cell(r.logical_max),
        fmt_cell(r.physical_min), fmt_cell(r.physical_max),
        fmt_cell(r.unit_label), r.type_label,
    ]


def print_table(rows):
    widths = [len(c) for c in COLUMNS]
    all_rows = [row_cells(r) for r in rows]
    for cells in all_rows:
        for idx, c in enumerate(cells):
            widths[idx] = max(widths[idx], len(c))

    def fmt_line(cells):
        return " | ".join(c.ljust(widths[idx]) for idx, c in enumerate(cells))

    print(fmt_line(COLUMNS))
    print("-+-".join("-" * w for w in widths))
    for cells in all_rows:
        print(fmt_line(cells))


def print_tree(nodes, depth=0):
    for node in nodes:
        label = f"{node.ctype} Collection"
        if node.usage_id is not None:
            label += f" — ({page_str(node.usage_page)}) {usage_str(node.usage_id)} · {collection_usage_name(node.usage_page, node.usage_id)}"
        print("  " * depth + label)
        for fname, fsize, fcount in node.fields:
            suffix = f" x{fcount}" if fcount > 1 else ""
            print("  " * (depth + 1) + f"- {fname} ({fsize} bit{'s' if fsize != 1 else ''}{suffix})")
        print_tree(node.children, depth + 1)


def print_text_report(result: ParseResult):
    print("=" * 70)
    print("COLLECTION TREE")
    print("=" * 70)
    print_tree(result.root)
    print()
    for g in result.groups:
        title = f"{g.app_name + ' ' if g.app_name else ''}{g.main_type.upper()} REPORT"
        print("=" * 70)
        print(f"{g.order}) {title}  (Report ID: {g.report_id})")
        print("=" * 70)
        print_table(g.rows)
        print()


# --------------------------------------------------------------------------
# HTML output
# --------------------------------------------------------------------------

def render_tree_html(nodes) -> str:
    out = []
    for node in nodes:
        label = f"<b>{html.escape(node.ctype)} Collection</b>"
        if node.usage_id is not None:
            label += (f' <span class="dim">&mdash; ({html.escape(page_str(node.usage_page))}) '
                      f'{html.escape(usage_str(node.usage_id))} &middot; '
                      f'{html.escape(collection_usage_name(node.usage_page, node.usage_id))}</span>')
        fields_html = ""
        if node.fields:
            items = "".join(
                f'<li><b>{html.escape(n)}</b> <span class="dim">({s} bit{"s" if s != 1 else ""}'
                f'{f" &times;{c}" if c > 1 else ""})</span></li>'
                for n, s, c in node.fields
            )
            fields_html = f'<ul class="fields">{items}</ul>'
        children_html = render_tree_html(node.children)
        out.append(f'<div class="node"><div class="node-label">{label}</div>{fields_html}{children_html}</div>')
    return "".join(out)


def render_group_html(g: ReportGroup) -> str:
    bg, line, ink = PALETTE[(g.order - 1) % len(PALETTE)]
    title = f"{g.app_name.upper() + ' ' if g.app_name else ''}{g.main_type.upper()} REPORT"
    rows_html = []
    for r in g.rows:
        is_pad = r.usage_id is None
        usage_col = "&mdash;" if r.usage_text is None else html.escape(r.usage_text)
        rows_html.append(
            "<tr>"
            f'<td class="field-name{" pad" if is_pad else ""}">{html.escape(r.name)}</td>'
            f"<td>{usage_col}</td>"
            f"<td>{r.size}</td><td>{r.count}</td>"
            f"<td>{html.escape(fmt_cell(r.logical_min))}</td><td>{html.escape(fmt_cell(r.logical_max))}</td>"
            f"<td>{html.escape(fmt_cell(r.physical_min))}</td><td>{html.escape(fmt_cell(r.physical_max))}</td>"
            f"<td>{html.escape(fmt_cell(r.unit_label))}</td><td>{html.escape(r.type_label)}</td>"
            "</tr>"
        )
    return f"""
    <div class="card" style="--bg:{bg}; --line:{line}; --ink:{ink};">
      <div class="card-head">
        <span>{g.order}) {html.escape(title)}</span>
        <span class="rid">Report ID: {html.escape(g.report_id)}</span>
      </div>
      <div class="table-scroll">
        <table>
          <thead><tr>{"".join(f"<th>{c}</th>" for c in COLUMNS)}</tr></thead>
          <tbody>{"".join(rows_html)}</tbody>
        </table>
      </div>
    </div>"""


HTML_TEMPLATE = """<!doctype html>
<html><head><meta charset="utf-8"><title>HID Report Descriptor (Parsed)</title>
<style>
body {{ font-family: -apple-system, "Segoe UI", Arial, sans-serif; background:#eef1f0; color:#151a19; margin:0; padding:24px; }}
h1 {{ font-size:1.2rem; margin:0 0 18px; }}
.tree {{ border:1px solid #c9d1cd; border-radius:8px; background:#fff; padding:14px 16px; margin-bottom:24px; }}
.node {{ border-left:2px solid #c9d1cd; margin-left:6px; padding-left:12px; margin-top:8px; font-family: ui-monospace, Consolas, monospace; font-size:.8rem; }}
.node-label {{ }}
.dim {{ color:#6b7570; }}
ul.fields {{ list-style:none; margin:6px 0 0; padding:0; font-size:.75rem; color:#6b7570; }}
.cards {{ display:flex; flex-direction:column; gap:18px; }}
.card {{ border:1px solid var(--line); border-radius:8px; overflow:hidden; background:#fff; }}
.card-head {{ background:var(--bg); color:var(--ink); border-bottom:1px solid var(--line);
  padding:9px 14px; font-weight:700; font-size:.85rem; display:flex; justify-content:space-between; gap:10px; }}
.rid {{ font-family: ui-monospace, Consolas, monospace; font-weight:600; font-size:.75rem; opacity:.85; }}
.table-scroll {{ overflow-x:auto; }}
table {{ width:100%; border-collapse:collapse; font-size:.78rem; }}
thead th {{ text-align:left; padding:7px 10px; font-size:.68rem; text-transform:uppercase; letter-spacing:.04em;
  color:#6b7570; border-bottom:1px solid #c9d1cd; white-space:nowrap; }}
tbody td {{ padding:6px 10px; border-bottom:1px solid #e3e7e4; font-family: ui-monospace, Consolas, monospace; white-space:nowrap; }}
td.field-name {{ font-family:inherit; font-weight:600; white-space:normal; }}
td.field-name.pad {{ font-style:italic; font-weight:500; color:#6b7570; }}
</style></head>
<body>
<h1>HID Report Descriptor (Parsed)</h1>
<div class="tree">{tree}</div>
<div class="cards">{cards}</div>
</body></html>
"""


def render_html(result: ParseResult) -> str:
    tree_html = render_tree_html(result.root)
    cards_html = "".join(render_group_html(g) for g in result.groups)
    return HTML_TEMPLATE.format(tree=tree_html, cards=cards_html)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def is_wsl() -> bool:
    try:
        return "microsoft" in Path("/proc/version").read_text().lower()
    except OSError:
        return False


def open_in_browser(path: Path):
    """Open a local HTML file in the default browser, including from WSL
    (which has no GUI browser of its own -- shell out to explorer.exe)."""
    if is_wsl():
        win_path = subprocess.run(
            ["wslpath", "-w", str(path)], capture_output=True, text=True, check=True
        ).stdout.strip()
        subprocess.run(["explorer.exe", win_path])
    else:
        webbrowser.open(path.resolve().as_uri())


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("infile", nargs="?", help="path to a descriptor byte listing (defaults to the built-in sample)")
    parser.add_argument("--html", metavar="PATH", help="also write a colored HTML report to PATH")
    parser.add_argument("--no-text", action="store_true", help="skip the console table output")
    parser.add_argument("--ui", action="store_true",
                         help="open the interactive paste-and-parse UI (hid_ui.html) in your browser")
    args = parser.parse_args()

    if args.ui:
        ui_path = Path(__file__).resolve().parent / "hid_ui.html"
        if not ui_path.exists():
            sys.exit(f"error: {ui_path} not found")
        open_in_browser(ui_path)
        return

    if args.infile:
        with open(args.infile, "r") as f:
            text = f.read()
    else:
        text = SAMPLE_DESCRIPTOR

    try:
        result = parse_descriptor(text)
    except ValueError as e:
        sys.exit(f"error: {e}")

    if not args.no_text:
        print_text_report(result)

    if args.html:
        with open(args.html, "w") as f:
            f.write(render_html(result))
        print(f"Wrote HTML report to {args.html}")


if __name__ == "__main__":
    main()
