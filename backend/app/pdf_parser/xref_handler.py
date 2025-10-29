import logging
import re
from typing import Dict, Optional

logger = logging.getLogger(__name__)

PDF_TAIL_BYTES = 1024

STARTXREF_PATTERN = rb"startxref\s+(\d+)"
XREF_SUBSECTION_PATTERN = rb"(\d+)\s+(\d+)$"
XREF_ENTRY_PATTERN = rb"(\d{10})\s+(\d{5})\s+([fn])"
OBJECT_PATTERN = rb"(\d+)\s+(\d+)\s+obj"


def parse_xref_table(pdf_bytes: bytes, xref_table: Dict[int, int]) -> None:
    xref_offset = find_xref_offset(pdf_bytes)

    if xref_offset:
        parse_traditional_xref(pdf_bytes, xref_offset, xref_table)
    else:
        logger.warning("No xref offset found, will rely on object scanning")

    # Scan for any objects not in the xref table
    scan_for_objects(pdf_bytes, xref_table)


def find_xref_offset(pdf_bytes: bytes) -> Optional[int]:
    tail = pdf_bytes[-PDF_TAIL_BYTES:]
    match = re.search(STARTXREF_PATTERN, tail)

    if match:
        offset = int(match.group(1))
        logger.debug(f"Found xref at offset {offset}")
        return offset

    logger.warning("Could not find startxref in PDF trailer")
    return None


def parse_traditional_xref(
    pdf_bytes: bytes, offset: int, xref_table: Dict[int, int]
) -> None:
    xref_section = pdf_bytes[offset:]
    lines = xref_section.split(b"\n")

    line_idx = 0

    # Skip the 'xref' keyword if present
    if lines[line_idx].strip() == b"xref":
        line_idx += 1

    # Parse xref subsections
    while line_idx < len(lines):
        line = lines[line_idx].strip()

        # Check for subsection header: "<start_obj> <count>"
        subsection_match = re.match(XREF_SUBSECTION_PATTERN, line)

        if subsection_match:
            start_obj = int(subsection_match.group(1))
            num_objs = int(subsection_match.group(2))
            line_idx += 1

            # Parse entries in this subsection
            for obj_offset in range(num_objs):
                if line_idx < len(lines):
                    entry = lines[line_idx].strip()
                    entry_match = re.match(XREF_ENTRY_PATTERN, entry)

                    if entry_match:
                        byte_offset = int(entry_match.group(1))
                        _generation = int(entry_match.group(2))
                        in_use = entry_match.group(3) == b"n"

                        # Only store in-use objects with valid offsets
                        if in_use and byte_offset > 0:
                            obj_num = start_obj + obj_offset
                            xref_table[obj_num] = byte_offset
                            logger.debug(f"Object {obj_num}: offset {byte_offset}")

                    line_idx += 1

        elif line == b"trailer":
            # Reached end of xref table
            logger.debug("Reached trailer section")
            break

        else:
            # Skip unrecognized lines
            line_idx += 1


def scan_for_objects(pdf_bytes: bytes, xref_table: Dict[int, int]) -> None:
    found_count = 0

    for match in re.finditer(OBJECT_PATTERN, pdf_bytes):
        obj_num = int(match.group(1))
        _generation = int(match.group(2))
        byte_offset = match.start()

        # Only add if not already in xref table
        if obj_num not in xref_table:
            xref_table[obj_num] = byte_offset
            found_count += 1
            logger.debug(f"Scanned object {obj_num}: offset {byte_offset}")

    if found_count > 0:
        logger.info(f"Found {found_count} additional objects via scanning")
