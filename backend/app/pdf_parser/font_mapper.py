import logging
import re
import traceback
import zlib
from io import BytesIO
from typing import Dict

logger = logging.getLogger(__name__)

SAMPLE_MAPPINGS_COUNT = 10
MAX_RANGE_SIZE = 256
MAX_UNICODE = 0x110000
CID_TO_GID_ENTRY_SIZE = 2


def extract_fontfile2_cmap(obj_num: int, pdf_bytes: bytes) -> Dict[str, str]:
    logger.info(f"Extracting FontFile2 CMap for object {obj_num}")

    # Get the FontFile2 stream
    obj_pattern = rf"{obj_num}\s+\d+\s+obj(.*?)endobj".encode()
    obj_match = re.search(obj_pattern, pdf_bytes, re.DOTALL)

    if not obj_match:
        logger.error(f"Could not find object {obj_num}")
        return {}

    obj_content = obj_match.group(1)

    # Extract stream
    stream_match = re.search(
        rb"stream\r?\n?(.*?)\r?\n?endstream", obj_content, re.DOTALL
    )
    if not stream_match:
        logger.error(f"No stream in object {obj_num}")
        return {}

    font_data = stream_match.group(1)
    logger.debug(f"Raw font data size: {len(font_data)} bytes")

    # Decompress if needed
    if b"/FlateDecode" in obj_content:
        try:
            font_data = zlib.decompress(font_data)
            logger.debug(f"Decompressed to: {len(font_data)} bytes")
        except zlib.error as e:
            logger.error(f"Error decompressing: {e}")
            return {}

    # Parse with fonttools
    try:
        from fontTools.ttLib import TTFont

        # Load font from bytes
        ttfont = TTFont(BytesIO(font_data))
        logger.debug("Font loaded successfully")

        # Get the cmap table
        if "cmap" not in ttfont:
            logger.error("No cmap table in font")
            ttfont.close()
            return {}

        cmap = ttfont["cmap"].getBestCmap()

        if not cmap:
            logger.error("No suitable cmap found in font")
            ttfont.close()
            return {}

        # Convert to format: hex CID -> character
        char_map = {}
        for code_point, _glyph_name in cmap.items():
            # Convert code point to 4-digit hex string
            hex_code = f"{code_point:04X}"
            char = chr(code_point)
            char_map[hex_code] = char

        logger.info(f"Extracted {len(char_map)} characters from FontFile2")

        ttfont.close()
        return char_map

    except ImportError:
        logger.error(
            "fontTools library not available. Install with: pip install fonttools"
        )
        return {}
    except Exception as e:
        logger.error(f"Error parsing TrueType font: {e}")
        logger.debug(traceback.format_exc())
        return {}


def _extract_font_mappings(
    pdf_bytes: bytes, xref_table: Dict[int, int]
) -> Dict[str, Dict[str, str]]:
    font_mappings = {}

    # STEP 1: Find all ToUnicode references
    all_tounicode_refs = {}
    tounicode_pattern = rb"/ToUnicode\s+(\d+)\s+(\d+)\s+R"

    for match in re.finditer(tounicode_pattern, pdf_bytes):
        obj_num = int(match.group(1))
        gen_num = int(match.group(2))
        all_tounicode_refs[obj_num] = gen_num

    logger.info(f"Found {len(all_tounicode_refs)} ToUnicode references in PDF")

    # STEP 2: Extract all ToUnicode CMaps
    all_cmaps = {}
    for obj_num, _gen_num in all_tounicode_refs.items():
        cmap = _extract_tounicode_cmap(obj_num, pdf_bytes, xref_table)
        if cmap:
            all_cmaps[obj_num] = cmap
            logger.debug(f"ToUnicode object {obj_num}: {len(cmap)} mappings")

    # STEP 3: Find font objects
    font_pattern = rb"(\d+)\s+\d+\s+obj[^>]*?/Type\s*/Font.*?endobj"
    font_objects = []

    for match in re.finditer(font_pattern, pdf_bytes, re.DOTALL):
        obj_num = int(match.group(1))
        obj_content = match.group(0)
        font_objects.append((obj_num, obj_content))

    logger.info(f"Found {len(font_objects)} font objects")

    # STEP 4: Look for DescendantFonts (Type 0 fonts)
    for obj_num, font_obj in font_objects:
        descendant_match = re.search(
            rb"/DescendantFonts\s*\[\s*(\d+)\s+\d+\s+R\s*\]", font_obj
        )
        if descendant_match:
            desc_obj = int(descendant_match.group(1))
            logger.debug(f"Font {obj_num} has DescendantFont at {desc_obj}")

            # Get the descendant font object
            desc_pattern = rf"{desc_obj}\s+\d+\s+obj(.*?)endobj".encode()
            desc_match = re.search(desc_pattern, pdf_bytes, re.DOTALL)

            if desc_match:
                desc_content = desc_match.group(1)
                # Check if descendant has ToUnicode
                desc_tounicode = re.search(
                    rb"/ToUnicode\s+(\d+)\s+\d+\s+R", desc_content
                )
                if desc_tounicode:
                    tounicode_obj = int(desc_tounicode.group(1))
                    if tounicode_obj in all_cmaps:
                        logger.debug(
                            f"Found ToUnicode in descendant: {len(all_cmaps[tounicode_obj])} mappings"
                        )

    # STEP 5: Process CIDToGIDMap (if present)
    _process_cidtogid_maps(pdf_bytes)

    # STEP 6: Extract FontFile2 CMaps
    fontfile2_cmaps = []
    fontfile2_pattern = rb"/FontFile2\s+(\d+)\s+\d+\s+R"

    for match in re.finditer(fontfile2_pattern, pdf_bytes):
        ff2_obj = int(match.group(1))
        logger.debug(f"Found FontFile2 at object {ff2_obj}")

        ff2_cmap = extract_fontfile2_cmap(ff2_obj, pdf_bytes)
        if ff2_cmap:
            fontfile2_cmaps.append(ff2_cmap)
            logger.info(f"Extracted {len(ff2_cmap)} mappings from FontFile2")

    # STEP 7: Merge all CMaps
    merged_cmap = {}

    # First add ToUnicode mappings (higher priority)
    for _obj_num, cmap in all_cmaps.items():
        for k, v in cmap.items():
            if k not in merged_cmap:
                merged_cmap[k] = v

    # Then add FontFile2 mappings (fill gaps)
    for ff2_cmap in fontfile2_cmaps:
        for k, v in ff2_cmap.items():
            if k not in merged_cmap:
                merged_cmap[k] = v

    logger.info(f"Merged CMap has {len(merged_cmap)} total unique mappings")

    # Check coverage
    if merged_cmap:
        _check_character_coverage(merged_cmap)

    # STEP 8: Build alias -> basefont mapping
    alias_to_basefont = _build_font_aliases(pdf_bytes)

    # STEP 9: Apply CMap to each alias based on its BaseFont
    for alias, basefont in alias_to_basefont.items():
        if basefont in font_mappings:
            font_mappings[alias] = font_mappings[basefont]
        else:
            # Fallback: assign merged_cmap directly
            font_mappings[alias] = merged_cmap

    # Add common font names
    font_mappings["Aptos"] = merged_cmap
    font_mappings["BCDEEE+Aptos"] = merged_cmap
    font_mappings["BCDFEE+Aptos"] = merged_cmap

    return font_mappings


def _process_cidtogid_maps(pdf_bytes: bytes) -> None:
    cidtogid_pattern = rb"/CIDToGIDMap\s+(\d+)\s+\d+\s+R"

    for match in re.finditer(cidtogid_pattern, pdf_bytes):
        obj_num = int(match.group(1))
        logger.debug(f"Found CIDToGIDMap at object {obj_num}")

        # Extract the CIDToGIDMap stream
        obj_pattern = rf"{obj_num}\s+\d+\s+obj(.*?)endobj".encode()
        obj_match = re.search(obj_pattern, pdf_bytes, re.DOTALL)

        if not obj_match:
            continue

        obj_content = obj_match.group(1)

        # Extract stream
        stream_match = re.search(
            rb"stream\r?\n?(.*?)\r?\n?endstream", obj_content, re.DOTALL
        )
        if not stream_match:
            continue

        stream_data = stream_match.group(1)

        # Decompress if needed
        if b"/Filter" in obj_content and b"/FlateDecode" in obj_content:
            try:
                stream_data = zlib.decompress(stream_data)
            except zlib.error as e:
                logger.warning(f"Failed to decompress CIDToGIDMap: {e}")
                continue

        # CIDToGIDMap is binary: each CID (2 bytes) maps to a GID (2 bytes)
        logger.debug(f"CIDToGIDMap stream length: {len(stream_data)} bytes")

        # Parse CID -> GID mapping
        for i in range(0, len(stream_data) - 1, CID_TO_GID_ENTRY_SIZE):
            _cid = i // CID_TO_GID_ENTRY_SIZE
            gid = (stream_data[i] << 8) | stream_data[i + 1]

            if gid != 0:  # GID 0 means undefined
                # Note: This mapping would need to be combined with font data
                # to get actual characters (not implemented here)
                pass


def _build_font_aliases(pdf_bytes: bytes) -> Dict[str, str]:
    alias_to_basefont = {}
    resource_pattern = rb"/Font\s*<<(.+?)>>"

    for match in re.finditer(resource_pattern, pdf_bytes, re.DOTALL):
        font_block = match.group(1)

        for alias, obj_num in re.findall(rb"/([Ff]\d+)\s+(\d+)\s+0\s+R", font_block):
            alias_str = alias.decode()
            obj_num_int = int(obj_num)

            # Find font object definition
            obj_pattern = rf"{obj_num_int}\s+\d+\s+obj(.*?)endobj".encode()
            obj_match = re.search(obj_pattern, pdf_bytes, re.DOTALL)

            if obj_match:
                obj_content = obj_match.group(1)
                basefont_match = re.search(rb"/BaseFont/([^\s/]+)", obj_content)

                if basefont_match:
                    basefont = basefont_match.group(1).decode()
                    alias_to_basefont[alias_str] = basefont
                    logger.debug(f"Font alias {alias_str} -> {basefont}")

    return alias_to_basefont


def _check_character_coverage(char_map: Dict[str, str]) -> None:
    mapped_chars = set(char_map.values())
    basic_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    missing = [c for c in basic_chars if c not in mapped_chars]

    if missing:
        logger.warning(f"Missing basic characters: {''.join(missing)}")


def _extract_tounicode_cmap(
    obj_num: int, pdf_bytes: bytes, xref_table: Dict[int, int]
) -> Dict[str, str]:
    from app.pdf_parser.stream_handler import _extract_stream_from_object

    char_map = {}

    # Find object offset
    obj_offset = xref_table.get(obj_num, 0)
    if not obj_offset:
        pattern = rf"{obj_num}\s+\d+\s+obj".encode()
        match = re.search(pattern, pdf_bytes)
        if match:
            obj_offset = match.start()

    if not obj_offset:
        return char_map

    # Extract object content
    obj_end = pdf_bytes.find(b"endobj", obj_offset)
    if obj_end == -1:
        return char_map

    obj_content = pdf_bytes[obj_offset : obj_end + 6]

    # Extract and decompress stream
    stream_data = _extract_stream_from_object(obj_content)
    if not stream_data:
        return char_map

    # Decode stream to text
    try:
        cmap_text = stream_data.decode("utf-8", errors="ignore")
    except UnicodeDecodeError:
        cmap_text = stream_data.decode("latin-1", errors="ignore")

    # Parse CMap sections
    _parse_bfchar_sections(cmap_text, char_map)
    _parse_bfrange_sections(cmap_text, char_map)

    if char_map:
        logger.info(f"CMap loaded with {len(char_map)} mappings")
        _log_character_analysis(char_map)

    return char_map


def _log_character_analysis(char_map: Dict[str, str]) -> None:
    basic_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    polish_chars = "ąćęłńóśźżĄĆĘŁŃÓŚŹŻ"

    mapped_values = set(char_map.values())

    mapped_basic = [c for c in basic_chars if c in mapped_values]
    missing_basic = [c for c in basic_chars if c not in mapped_values]
    mapped_polish = [c for c in polish_chars if c in mapped_values]
    missing_polish = [c for c in polish_chars if c not in mapped_values]

    logger.debug(f"Mapped basic letters: {''.join(mapped_basic)}")
    logger.debug(f"Missing basic letters: {''.join(missing_basic)}")
    logger.debug(f"Mapped Polish letters: {''.join(mapped_polish)}")
    logger.debug(f"Missing Polish letters: {''.join(missing_polish)}")

    # Show sample mappings
    for k, v in list(char_map.items())[:SAMPLE_MAPPINGS_COUNT]:
        logger.debug(f"{k} -> '{v}' (U+{ord(v):04X})")


def _parse_bfchar_sections(cmap_text: str, char_map: Dict[str, str]) -> None:
    bfchar_pattern = r"beginbfchar(.*?)endbfchar"

    for match in re.finditer(bfchar_pattern, cmap_text, re.DOTALL):
        section = match.group(1)
        pair_pattern = r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>"

        for pair_match in re.finditer(pair_pattern, section):
            src_hex = pair_match.group(1).upper()
            dst_hex = pair_match.group(2)

            try:
                # Decode destination hex to Unicode character
                if len(dst_hex) == 4:
                    unicode_char = chr(int(dst_hex, 16))
                elif len(dst_hex) > 4:
                    dst_bytes = bytes.fromhex(dst_hex)
                    unicode_char = dst_bytes.decode("utf-16-be", errors="ignore")
                else:
                    unicode_char = chr(int(dst_hex, 16))

                char_map[src_hex] = unicode_char

            except (ValueError, OverflowError) as e:
                logger.debug(
                    f"Failed to parse bfchar mapping {src_hex}->{dst_hex}: {e}"
                )


def _parse_bfrange_sections(cmap_text: str, char_map: Dict[str, str]) -> None:
    bfrange_pattern = r"beginbfrange(.*?)endbfrange"

    for match in re.finditer(bfrange_pattern, cmap_text, re.DOTALL):
        section = match.group(1)

        # Format 1: <start> <end> <base>
        range_pattern = r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>"

        for range_match in re.finditer(range_pattern, section):
            start_hex = range_match.group(1)
            end_hex = range_match.group(2)
            base_hex = range_match.group(3)

            try:
                start = int(start_hex, 16)
                end = int(end_hex, 16)
                base = int(base_hex, 16)

                # Limit range size to prevent excessive iterations
                for i in range(start, min(end + 1, start + MAX_RANGE_SIZE)):
                    char_code_hex = f"{i:04X}"
                    unicode_value = base + (i - start)

                    if unicode_value < MAX_UNICODE:
                        char_map[char_code_hex] = chr(unicode_value)

            except (ValueError, OverflowError) as e:
                logger.debug(f"Failed to parse bfrange {start_hex}-{end_hex}: {e}")

        # Format 2: <start> <end> [<val1> <val2> ...]
        array_pattern = r"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*\[(.*?)\]"

        for array_match in re.finditer(array_pattern, section):
            start_hex = array_match.group(1)
            end_hex = array_match.group(2)
            values = array_match.group(3)

            try:
                start = int(start_hex, 16)
                end = int(end_hex, 16)

                value_pattern = r"<([0-9A-Fa-f]+)>"
                value_matches = re.findall(value_pattern, values)

                for i, val_hex in enumerate(value_matches):
                    if start + i <= end:
                        char_code_hex = f"{start + i:04X}"

                        if len(val_hex) == 4:
                            unicode_char = chr(int(val_hex, 16))
                        else:
                            dst_bytes = bytes.fromhex(val_hex)
                            unicode_char = dst_bytes.decode(
                                "utf-16-be", errors="ignore"
                            )

                        char_map[char_code_hex] = unicode_char

            except (ValueError, OverflowError) as e:
                logger.debug(
                    f"Failed to parse bfrange array {start_hex}-{end_hex}: {e}"
                )
