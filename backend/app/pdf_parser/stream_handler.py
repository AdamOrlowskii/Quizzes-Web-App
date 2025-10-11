import re
import zlib
from typing import List, Optional


def _handle_object_streams(pdf_bytes: bytes, xref_table: dict):
    objstm_pattern = rb"(\d+)\s+\d+\s+obj[^>]*?/Type\s*/ObjStm.*?endobj"

    for match in re.finditer(objstm_pattern, pdf_bytes, re.DOTALL):
        stream_obj_num = int(match.group(1))
        obj_content = match.group(0)

        n_match = re.search(rb"/N\s+(\d+)", obj_content)
        first_match = re.search(rb"/First\s+(\d+)", obj_content)

        if not n_match or not first_match:
            continue

        n = int(n_match.group(1))
        first = int(first_match.group(1))

        stream_data = _extract_stream_from_object(obj_content)
        if not stream_data:
            continue

        index_data = stream_data[:first]
        objects_data = stream_data[first:]

        try:
            index_str = index_data.decode("latin-1", errors="ignore")
        except:
            continue

        numbers = re.findall(r"\d+", index_str)

        for i in range(0, len(numbers), 2):
            if i + 1 < len(numbers):
                obj_num = int(numbers[i])
                offset = int(numbers[i + 1])

                if i + 3 < len(numbers):
                    next_offset = int(numbers[i + 3])
                    obj_data = objects_data[offset:next_offset]
                else:
                    obj_data = objects_data[offset:]

                if obj_num not in xref_table:
                    xref_table[obj_num] = -stream_obj_num


def _extract_stream_from_object(obj_content: bytes) -> Optional[bytes]:
    """Extract and decompress stream from an object"""
    # Find stream boundaries
    stream_start = obj_content.find(b"stream")
    stream_end = obj_content.find(b"endstream")

    if stream_start == -1 or stream_end == -1:
        return None

    # Move past 'stream' and any newlines
    stream_start += 6  # len('stream')
    if stream_start < len(obj_content) and obj_content[
        stream_start : stream_start + 2
    ] in (b"\r\n", b"\n\r"):
        stream_start += 2
    elif stream_start < len(obj_content) and obj_content[
        stream_start : stream_start + 1
    ] in (b"\n", b"\r"):
        stream_start += 1

    stream_data = obj_content[stream_start:stream_end]

    # IMPORTANT: Apply decompression in the right order!
    # Check for ASCII85 first
    if b"/ASCII85Decode" in obj_content:
        if stream_data.endswith(b"~>"):
            stream_data = stream_data[:-2]
        import base64

        stream_data = base64.a85decode(stream_data)

    # Then apply FlateDecode
    if b"/FlateDecode" in obj_content:
        import zlib

        stream_data = zlib.decompress(stream_data)

    return stream_data  # Return the DECOMPRESSED data


def _extract_all_streams(xref_table: dict, pdf_bytes: bytes, objects) -> List[bytes]:
    streams = []

    for obj_num, offset in xref_table.items():
        obj_content = _extract_object(obj_num, offset, pdf_bytes, objects)
        if obj_content:
            stream = _extract_stream_from_object(obj_content)
            if stream:
                streams.append(stream)

    stream_pattern = rb"stream\r?\n(.*?)endstream"
    for match in re.finditer(stream_pattern, pdf_bytes, re.DOTALL):
        stream_content = match.group(1)
        if stream_content.startswith(b"x\x9c") or stream_content.startswith(b"x\xda"):
            try:
                decompressed = zlib.decompress(stream_content)
                streams.append(decompressed)
            except:
                streams.append(stream_content)
        else:
            streams.append(stream_content)

    return streams


def _extract_object(
    obj_num: int, offset: int, pdf_bytes: bytes, objects: dict
) -> Optional[bytes]:
    if obj_num in objects:
        return objects[obj_num]

    start = offset

    endobj_pos = pdf_bytes.find(b"endobj", start)
    if endobj_pos == 1:
        return None

    obj_content = pdf_bytes[start : endobj_pos + 6]

    objects[obj_num] = obj_content

    return obj_content


def debug_stream_content(stream: bytes):
    print("\n=== Stream Debug ===")
    print(f"Stream length: {len(stream)} bytes")
    print(f"First 200 bytes raw: {stream[:200]}")

    # Check for different text patterns
    if b"Tj" in stream:
        print("Found Tj operators")
    if b"TJ" in stream:
        print("Found TJ operators")

    # Look for hex strings
    hex_pattern = rb"<([0-9A-Fa-f]+)>"
    hex_matches = list(re.finditer(hex_pattern, stream))
    print(f"Found {len(hex_matches)} hex strings")
    if hex_matches:
        print(f"First hex: {hex_matches[0].group()}")

    # Look for literal strings
    literal_pattern = rb"\(([^)]+)\)"
    literal_matches = list(re.finditer(literal_pattern, stream))
    print(f"Found {len(literal_matches)} literal strings")
    if literal_matches:
        print(f"First literal: {literal_matches[0].group()}")
        # Show the byte values
        first_literal = literal_matches[0].group(1)
        print(f"Byte values: {[hex(b) for b in first_literal[:20]]}")
