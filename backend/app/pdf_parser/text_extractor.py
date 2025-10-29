import logging
import re
import unicodedata
from typing import Dict, List

logger = logging.getLogger(__name__)

ENCODING_UTF16_BE = "utf-16-be"
ENCODING_UTF16_LE = "utf-16-le"
ENCODING_UTF8 = "utf-8"
ENCODING_CP1252 = "cp1252"
ENCODING_LATIN1 = "latin-1"
ENCODING_ASCII = "ascii"

BOM_UTF16_BE = b"\xfe\xff"
BOM_UTF16_LE = b"\xff\xfe"

SPACING_THRESHOLD = -100
DEBUG_OUTPUT_LIMIT = 50
FONT_ADVANCE_TOKENS = 3


def _extract_text_from_stream(stream: bytes) -> str:
    extracted_text = []

    # Pattern 1: Literal strings (text) Tj
    literal_pattern = rb"\(([^)]*)\)\s*Tj"
    matches = list(re.finditer(literal_pattern, stream))

    for match in matches:
        text_bytes = match.group(1)
        text = text_bytes.decode(ENCODING_UTF8, errors="ignore")
        text = text.replace("\x00", "")
        text = text.replace("\\(", "(").replace("\\)", ")").replace("\\\\", "\\")

        if text.strip():
            extracted_text.append(text)

    # Pattern 2: Hex strings <hex> Tj
    hex_pattern = rb"<([0-9A-Fa-f]+)>\s*Tj"
    for match in re.finditer(hex_pattern, stream):
        hex_bytes = match.group(1)
        try:
            hex_str = hex_bytes.decode(ENCODING_ASCII, errors="ignore")
            if len(hex_str) % 2 != 0:
                hex_str = hex_str[:-1]
            text_bytes = bytes.fromhex(hex_str)
            text = _decode_pdf_text(text_bytes)
            text = text.replace("\x00", "")
            if text and text.strip():
                extracted_text.append(text)
        except (ValueError, UnicodeDecodeError) as e:
            logger.debug(f"Failed to decode hex string: {e}")
            continue

    # Pattern 3: Arrays [...] TJ
    array_pattern = rb"\[(.*?)\]\s*TJ"
    for match in re.finditer(array_pattern, stream, re.DOTALL):
        array_content = match.group(1)

        # Extract literal strings from array
        str_pattern = rb"\(([^)]*)\)"
        for str_match in re.finditer(str_pattern, array_content):
            text = str_match.group(1).decode(ENCODING_UTF8, errors="ignore")
            text = text.replace("\x00", "")
            text = text.replace("\\(", "(").replace("\\)", ")").replace("\\\\", "\\")
            if text.strip():
                extracted_text.append(text)

        # Extract hex strings from array
        hex_in_array = rb"<([0-9A-Fa-f]+)>"
        for hex_match in re.finditer(hex_in_array, array_content):
            try:
                hex_str = hex_match.group(1).decode(ENCODING_ASCII, errors="ignore")
                if len(hex_str) % 2 != 0:
                    hex_str = hex_str[:-1]
                text_bytes = bytes.fromhex(hex_str)
                text = _decode_pdf_text(text_bytes)
                text = text.replace("\x00", "")
                if text and text.strip():
                    extracted_text.append(text)
            except (ValueError, UnicodeDecodeError) as e:
                logger.debug(f"Failed to decode hex string in array: {e}")
                continue

    # Pattern 4: Binary text (UTF-16)
    _extract_binary_text(stream, extracted_text)

    return " ".join(extracted_text)


def _extract_text_from_stream_advanced(
    stream: bytes, font_mappings: Dict[str, Dict[str, str]]
) -> str:
    extracted_text = []
    current_font = None
    current_map = {}

    # Tokenize stream into elements: <...>, (...), /Fxx, numbers, operators
    tokens = re.findall(
        rb"(<[0-9A-Fa-f]+>|\(.*?\)|/[A-Za-z0-9]+|\S+)", stream, re.DOTALL
    )

    i = 0
    while i < len(tokens):
        tok = tokens[i]

        # Font change: /F1 12 Tf
        if tok.startswith(b"/F"):
            current_font = tok[1:].decode(ENCODING_LATIN1, errors="ignore")

            # Try to find mapping for this font
            if current_font in font_mappings:
                current_map = font_mappings[current_font]
            else:
                # Heuristic: match by font name fragment
                for font_name, mapping in font_mappings.items():
                    if current_font in font_name or font_name in current_font:
                        current_map = mapping
                        break

            i += FONT_ADVANCE_TOKENS  # Skip size and 'Tf'
            continue

        # Hex string + Tj operator
        if tok == b"Tj" and i > 0 and tokens[i - 1].startswith(b"<"):
            hex_str = tokens[i - 1].strip(b"<>").decode(ENCODING_ASCII)
            text = _decode_hex_string(hex_str, current_map)
            if text:
                extracted_text.append(text)

        # Literal string + Tj operator
        if tok == b"Tj" and i > 0 and tokens[i - 1].startswith(b"("):
            lit = tokens[i - 1][1:-1].decode(ENCODING_LATIN1, errors="ignore")
            extracted_text.append(lit)

        # TJ array operator
        if tok == b"TJ" and i > 0 and tokens[i - 1].startswith(b"["):
            array_content = tokens[i - 1][1:-1]
            parts = re.findall(rb"<([0-9A-Fa-f]+)>|(-?\d+)", array_content)
            block = []

            for hex_str, spacing in parts:
                if hex_str:
                    text = _decode_hex_string(
                        hex_str.decode(ENCODING_ASCII), current_map
                    )
                    if text:
                        block.append(text)
                elif spacing and int(spacing) < SPACING_THRESHOLD:
                    # Negative spacing indicates word break
                    block.append(" ")

            if block:
                extracted_text.append("".join(block))

        i += 1

    return " ".join(extracted_text)


def _decode_pdf_text(text_bytes: bytes) -> str:
    # Try UTF-16 BE with BOM
    if text_bytes.startswith(BOM_UTF16_BE):
        try:
            return text_bytes[2:].decode(ENCODING_UTF16_BE, errors="ignore")
        except UnicodeDecodeError:
            pass

    # Try UTF-16 LE with BOM
    if text_bytes.startswith(BOM_UTF16_LE):
        try:
            return text_bytes[2:].decode(ENCODING_UTF16_LE, errors="ignore")
        except UnicodeDecodeError:
            pass

    # Detect UTF-16 without BOM (by null byte pattern)
    if len(text_bytes) % 2 == 0 and len(text_bytes) >= 2:
        if all(b == 0 for b in text_bytes[1::2]) or all(
            b == 0 for b in text_bytes[::2]
        ):
            try:
                return text_bytes.decode(ENCODING_UTF16_BE, errors="ignore")
            except UnicodeDecodeError:
                try:
                    return text_bytes.decode(ENCODING_UTF16_LE, errors="ignore")
                except UnicodeDecodeError:
                    pass

    # Try UTF-8
    try:
        return text_bytes.decode(ENCODING_UTF8)
    except UnicodeDecodeError:
        pass

    # Try CP1252 (Windows encoding)
    try:
        return text_bytes.decode(ENCODING_CP1252)
    except UnicodeDecodeError:
        pass

    # Fallback to Latin-1 (never fails)
    return text_bytes.decode(ENCODING_LATIN1, errors="ignore")


def _extract_binary_text(stream: bytes, output: List[str]) -> None:
    bt_pattern = rb"BT(.*?)ET"

    for match in re.finditer(bt_pattern, stream, re.DOTALL):
        text_block = match.group(1)

        if BOM_UTF16_BE in text_block:
            utf16_pattern = rb"\xfe\xff((?:[\x00-\xff][\x00-\xff])+)"
            for utf16_match in re.finditer(utf16_pattern, text_block):
                try:
                    text = utf16_match.group(1).decode(
                        ENCODING_UTF16_BE, errors="ignore"
                    )
                    text = text.replace("\x00", "")
                    if text.strip():
                        output.append(text)
                except UnicodeDecodeError as e:
                    logger.warning(f"Failed to extract binary text: {e}")


def _decode_hex_string(hex_str: str, encoding_map: Dict[str, str] = None) -> str:
    hex_str = hex_str.replace(" ", "").upper()
    if len(hex_str) % 2 != 0:
        hex_str = hex_str[:-1]

    result = []
    missing_cids = []

    if not encoding_map:
        return ""

    i = 0
    while i < len(hex_str):
        decoded = False

        # Try 4-byte CID first
        if i + 4 <= len(hex_str):
            cid = hex_str[i : i + 4]
            if cid in encoding_map:
                result.append(encoding_map[cid])
                i += 4
                decoded = True

        # Try 2-byte CID
        if not decoded and i + 2 <= len(hex_str):
            cid = hex_str[i : i + 2]
            if cid in encoding_map:
                result.append(encoding_map[cid])
                i += 2
                decoded = True

        # Track missing CIDs
        if not decoded:
            if i + 4 <= len(hex_str):
                cid = hex_str[i : i + 4]
                missing_cids.append(cid)
                result.append("?")
                i += 4
            else:
                i += 2

    # Debug output for first few strings (to avoid spam)
    if missing_cids and len(result) < DEBUG_OUTPUT_LIMIT:
        text = "".join(result)
        logger.debug(f"Text: '{text}'")
        logger.debug(f"Missing CIDs: {missing_cids}")

        # Provide hints based on expected patterns
        if text.startswith("?l"):
            logger.debug(f"-> CID {missing_cids[0]} should be 'A'")
        if "?a" in text[:10] and len(missing_cids) > 1:
            logger.debug(f"-> CID {missing_cids[1]} should be 'm'")

    return "".join(result)


def _clean_extracted_text(text: str) -> str:
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)

    # Remove null bytes and non-breaking spaces
    text = text.replace("\x00", "")
    text = text.replace("\u00a0", " ")

    # Remove control characters except newlines, returns, and tabs
    cleaned = []
    for char in text:
        category = unicodedata.category(char)
        if category[0] not in ["C"]:  # Not a control character
            cleaned.append(char)
        elif char in "\n\r\t":  # Keep these control characters
            cleaned.append(" ")

    return "".join(cleaned).strip()
