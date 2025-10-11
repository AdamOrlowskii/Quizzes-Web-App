import re
from typing import Optional


def parse_xref_table(pdf_bytes: bytes, xref_table: dict):
    xref_offset = find_xref_offset(pdf_bytes)

    if xref_offset:
        parse_traditional_xref(pdf_bytes, xref_offset, xref_table)

    scan_for_objects(pdf_bytes, xref_table)


def find_xref_offset(pdf_bytes: bytes) -> Optional[int]:
    tail = pdf_bytes[-1024:]

    match = re.search(rb"startxref\s+(\d+)", tail)
    if match:
        return int(match.group(1))

    return None


def parse_traditional_xref(pdf_bytes: bytes, offset: int, xref_table: dict):
    xref_section = pdf_bytes[offset:]

    lines = xref_section.split(b"\n")
    i = 0

    if lines[i].strip() == b"xref":
        i += 1

    while i < len(lines):
        line = lines[i].strip()

        match = re.match(rb"(\d+)\s+(\d+)$", line)
        if match:
            start_obj = int(match.group(1))
            num_objs = int(match.group(2))
            i += 1

            for j in range(num_objs):
                if i < len(lines):
                    entry = lines[i].strip()

                    entry_match = re.match(rb"(\d{10})\s+(\d{5})\s+([fn])", entry)
                    if entry_match:
                        offset = int(entry_match.group(1))
                        generation = int(entry_match.group(2))
                        in_use = entry_match.group(3) == b"n"

                        if in_use and offset > 0:
                            obj_num = start_obj + j
                            xref_table[obj_num] = offset

                    i += 1

        elif line == b"trailer":
            break
        else:
            i += 1


def scan_for_objects(pdf_bytes: bytes, xref_table: dict):
    pattern = rb"(\d+)\s+(\d+)\s+obj"

    for match in re.finditer(pattern, pdf_bytes):
        obj_num = int(match.group(1))
        generation = int(match.group(2))
        offset = match.start()

        if obj_num not in xref_table:
            xref_table[obj_num] = offset
