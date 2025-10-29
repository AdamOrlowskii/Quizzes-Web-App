import base64
import logging
import re
import zlib
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

STREAM_KEYWORD_LENGTH = 6
DEBUG_BYTES_PREVIEW = 200
ZLIB_HEADER_DEFAULT = b"x\x9c"
ZLIB_HEADER_BEST = b"x\xda"


def _handle_object_streams(pdf_bytes: bytes, xref_table: Dict[int, int]) -> None:

    objstm_pattern = rb"(\d+)\s+\d+\s+obj[^>]*?/Type\s*/ObjStm.*?endobj"

    for match in re.finditer(objstm_pattern, pdf_bytes, re.DOTALL):
        stream_obj_num = int(match.group(1))
        obj_content = match.group(0)

        # Extract /N (number of objects) and /First (byte offset of first object)
        n_match = re.search(rb"/N\s+(\d+)", obj_content)
        first_match = re.search(rb"/First\s+(\d+)", obj_content)

        if not n_match or not first_match:
            logger.warning(f"Object stream {stream_obj_num} missing /N or /First")
            continue

        _n = int(n_match.group(1))  # Number of objects (for potential validation)
        first = int(first_match.group(1))

        stream_data = _extract_stream_from_object(obj_content)
        if not stream_data:
            logger.warning(f"Could not extract stream data from object {stream_obj_num}")
            continue

        # Split stream into index section and objects section
        index_data = stream_data[:first]
        objects_data = stream_data[first:]

        try:
            index_str = index_data.decode("latin-1", errors="ignore")
        except UnicodeDecodeError as e:
            logger.warning(f"Failed to decode index data: {e}")
            continue

        # Parse index: alternating object numbers and offsets
        numbers = re.findall(r"\d+", index_str)

        for i in range(0, len(numbers), 2):
            if i + 1 < len(numbers):
                obj_num = int(numbers[i])
                offset = int(numbers[i + 1])

                # Determine object data boundaries (extracted for potential future use)
                if i + 3 < len(numbers):
                    next_offset = int(numbers[i + 3])
                    _obj_data = objects_data[offset:next_offset]
                else:
                    _obj_data = objects_data[offset:]

                # Store negative stream number to indicate compressed object
                if obj_num not in xref_table:
                    xref_table[obj_num] = -stream_obj_num
                    logger.debug(f"Object {obj_num} is in stream {stream_obj_num}")


def _extract_stream_from_object(obj_content: bytes) -> Optional[bytes]:

    # Find stream boundaries
    stream_start = obj_content.find(b"stream")
    stream_end = obj_content.find(b"endstream")

    if stream_start == -1 or stream_end == -1:
        return None

    # Move past 'stream' keyword and any newlines
    stream_start += STREAM_KEYWORD_LENGTH
    
    # Skip CR+LF, LF+CR, LF, or CR after 'stream'
    if stream_start < len(obj_content) and obj_content[
        stream_start : stream_start + 2
    ] in (b"\r\n", b"\n\r"):
        stream_start += 2
    elif stream_start < len(obj_content) and obj_content[
        stream_start : stream_start + 1
    ] in (b"\n", b"\r"):
        stream_start += 1

    stream_data = obj_content[stream_start:stream_end]

    # Apply decompression filters in order
    # 1. ASCII85Decode first
    if b"/ASCII85Decode" in obj_content:
        # Remove end marker if present
        if stream_data.endswith(b"~>"):
            stream_data = stream_data[:-2]
        
        try:
            stream_data = base64.a85decode(stream_data)
        except (ValueError, base64.binascii.Error) as e:
            logger.warning(f"Failed to decode ASCII85: {e}")
            return None

    # 2. Then FlateDecode
    if b"/FlateDecode" in obj_content:
        try:
            stream_data = zlib.decompress(stream_data)
        except zlib.error as e:
            logger.warning(f"Failed to decompress FlateDecode: {e}")
            return None

    return stream_data


def _extract_all_streams(
    xref_table: Dict[int, int], pdf_bytes: bytes, objects: Dict[int, bytes]
) -> List[bytes]:

    streams = []

    # Extract streams from objects in xref table
    for obj_num, offset in xref_table.items():
        obj_content = _extract_object(obj_num, offset, pdf_bytes, objects)
        if obj_content:
            stream = _extract_stream_from_object(obj_content)
            if stream:
                streams.append(stream)
                logger.debug(f"Extracted stream from object {obj_num}")

    # Fallback: scan entire PDF for streams
    stream_pattern = rb"stream\r?\n(.*?)endstream"
    for match in re.finditer(stream_pattern, pdf_bytes, re.DOTALL):
        stream_content = match.group(1)
        
        # Check for zlib compression headers
        if stream_content.startswith((ZLIB_HEADER_DEFAULT, ZLIB_HEADER_BEST)):
            try:
                decompressed = zlib.decompress(stream_content)
                streams.append(decompressed)
            except zlib.error as e:
                logger.debug(f"Failed to decompress stream: {e}")
                streams.append(stream_content)
        else:
            streams.append(stream_content)

    logger.info(f"Extracted {len(streams)} streams total")
    return streams


def _extract_object(
    obj_num: int, offset: int, pdf_bytes: bytes, objects: Dict[int, bytes]
) -> Optional[bytes]:

    # Check cache first
    if obj_num in objects:
        return objects[obj_num]

    start = offset

    # Find end of object
    endobj_pos = pdf_bytes.find(b"endobj", start)
    if endobj_pos == -1:
        logger.warning(f"Could not find endobj for object {obj_num}")
        return None

    # Extract object content including 'endobj'
    obj_content = pdf_bytes[start : endobj_pos + 6]

    # Cache the result
    objects[obj_num] = obj_content

    return obj_content


def debug_stream_content(stream: bytes) -> None:

    logger.debug("=== Stream Debug ===")
    logger.debug(f"Stream length: {len(stream)} bytes")
    logger.debug(f"First {DEBUG_BYTES_PREVIEW} bytes raw: {stream[:DEBUG_BYTES_PREVIEW]}")

    # Check for text operators
    if b"Tj" in stream:
        logger.debug("Found Tj operators")
    if b"TJ" in stream:
        logger.debug("Found TJ operators")

    # Look for hex strings
    hex_pattern = rb"<([0-9A-Fa-f]+)>"
    hex_matches = list(re.finditer(hex_pattern, stream))
    logger.debug(f"Found {len(hex_matches)} hex strings")
    if hex_matches:
        logger.debug(f"First hex: {hex_matches[0].group()}")

    # Look for literal strings
    literal_pattern = rb"\(([^)]+)\)"
    literal_matches = list(re.finditer(literal_pattern, stream))
    logger.debug(f"Found {len(literal_matches)} literal strings")
    if literal_matches:
        first_literal_full = literal_matches[0].group()
        first_literal_content = literal_matches[0].group(1)
        logger.debug(f"First literal: {first_literal_full}")
        
        # Show byte values for debugging encoding issues
        byte_values = [hex(b) for b in first_literal_content[:20]]
        logger.debug(f"Byte values: {byte_values}")