import re
from typing import List


def _extract_text_from_stream(stream: bytes) -> str:
    extracted_text = []

    # Pattern 1: Literal strings (text) Tj
    literal_pattern = rb"\(([^)]*)\)\s*Tj"

    matches = list(re.finditer(literal_pattern, stream))

    for match in matches:
        text_bytes = match.group(1)
        text = text_bytes.decode("utf-8", errors="ignore")
        text = text.replace("\x00", "")
        text = text.replace("\\(", "(").replace("\\)", ")").replace("\\\\", "\\")

        if text.strip():
            extracted_text.append(text)

    # Pattern 2: Hex strings <hex> Tj
    hex_pattern = rb"<([0-9A-Fa-f]+)>\s*Tj"
    for match in re.finditer(hex_pattern, stream):
        hex_bytes = match.group(1)
        try:
            hex_str = hex_bytes.decode("ascii", errors="ignore")
            if len(hex_str) % 2 != 0:
                hex_str = hex_str[:-1]
            text_bytes = bytes.fromhex(hex_str)
            text = _decode_pdf_text(text_bytes)
            text = text.replace("\x00", "")
            if text and text.strip():
                extracted_text.append(text)
        except:
            pass

    # Pattern 3: Arrays [...] TJ
    array_pattern = rb"\[(.*?)\]\s*TJ"
    for match in re.finditer(array_pattern, stream, re.DOTALL):
        array_content = match.group(1)

        str_pattern = rb"\(([^)]*)\)"
        for str_match in re.finditer(str_pattern, array_content):
            text = str_match.group(1).decode("utf-8", errors="ignore")
            text = text.replace("\x00", "")
            text = text.replace("\\(", "(").replace("\\)", ")").replace("\\\\", "\\")
            if text.strip():
                extracted_text.append(text)

        hex_in_array = rb"<([0-9A-Fa-f]+)>"
        for hex_match in re.finditer(hex_in_array, array_content):
            try:
                hex_str = hex_match.group(1).decode("ascii", errors="ignore")
                if len(hex_str) % 2 != 0:
                    hex_str = hex_str[:-1]
                text_bytes = bytes.fromhex(hex_str)
                text = _decode_pdf_text(text_bytes)
                text = text.replace("\x00", "")
                if text and text.strip():
                    extracted_text.append(text)
            except:
                pass

    # Pattern 4: Binary text (UTF-16)
    _extract_binary_text(stream, extracted_text)
    return " ".join(extracted_text)


def _extract_text_from_stream_advanced(stream: bytes, font_mappings: dict) -> str:
    extracted_text = []
    current_font = None
    current_map = {}

    # Tokenizujemy stream na elementy: <...>, (...), /Fxx, liczby, operatory
    tokens = re.findall(
        rb"(<[0-9A-Fa-f]+>|\(.*?\)|/[A-Za-z0-9]+|\S+)", stream, re.DOTALL
    )
    i = 0
    while i < len(tokens):
        tok = tokens[i]

        # Zmiana fontu: /F1 12 Tf
        if tok.startswith(b"/F"):
            current_font = tok[1:].decode("latin-1", errors="ignore")
            # spróbuj znaleźć mapping dla tego fontu
            if current_font in font_mappings:
                current_map = font_mappings[current_font]
            else:
                # heurystyka: dopasuj po fragmencie nazwy
                for font_name, mapping in font_mappings.items():
                    if current_font in font_name or font_name in current_font:
                        current_map = mapping
                        break
            i += 3  # przeskocz rozmiar i 'Tf'
            continue

        # Hex string + Tj
        if tok == b"Tj" and i > 0 and tokens[i - 1].startswith(b"<"):
            hex_str = tokens[i - 1].strip(b"<>").decode("ascii")
            text = _decode_hex_string(hex_str, current_map)
            if text:
                extracted_text.append(text)

        # Literal string + Tj
        if tok == b"Tj" and i > 0 and tokens[i - 1].startswith(b"("):
            lit = tokens[i - 1][1:-1].decode("latin-1", errors="ignore")
            extracted_text.append(lit)

        # Tablica TJ
        if tok == b"TJ" and i > 0 and tokens[i - 1].startswith(b"["):
            array_content = tokens[i - 1][1:-1]
            parts = re.findall(rb"<([0-9A-Fa-f]+)>|(-?\d+)", array_content)
            block = []
            for hex_str, spacing in parts:
                if hex_str:
                    text = _decode_hex_string(hex_str.decode("ascii"), current_map)
                    if text:
                        block.append(text)
                elif spacing and int(spacing) < -100:
                    block.append(" ")
            if block:
                extracted_text.append("".join(block))

        i += 1

    return " ".join(extracted_text)


def _decode_pdf_text(text_bytes: bytes) -> str:
    if text_bytes.startswith(b"\xfe\xff"):
        try:
            return text_bytes[2:].decode("utf-16-be", errors="ignore")
        except:
            pass

    if text_bytes.startswith(b"\xff\xfe"):
        try:
            return text_bytes[2:].decode("uft-16-le", errors="ignore")
        except:
            pass

    if len(text_bytes) % 2 == 0 and len(text_bytes) >= 2:
        if all(b == 0 for b in text_bytes[1::2]) or all(
            b == 0 for b in text_bytes[::2]
        ):
            try:
                return text_bytes.decode("utf-16-be", errors="ignore")
            except:
                try:
                    return text_bytes.decode("utf-16-le", errors="ignore")
                except:
                    pass

    try:
        return text_bytes.decode("utf-8")
    except:
        pass

    try:
        return text_bytes.decode("cp1252")
    except:
        pass

    return text_bytes.decode("latin-1", errors="ignore")


def _extract_binary_text(stream: bytes, output: List[str]):
    bt_pattern = rb"BT(.*?)ET"

    for match in re.finditer(bt_pattern, stream, re.DOTALL):
        text_block = match.group(1)

        if b"\xfe\xff" in text_block:
            utf16_pattern = rb"\xfe\xff((?:[\x00-\xff][\x00-\xff])+)"
            for utf16_match in re.finditer(utf16_pattern, text_block):
                try:
                    text = utf16_match.group(1).decode("utf-16-be", errors="ignore")
                    text = text.replace("\00", "")
                    if text.strip():
                        output.append(text)
                except:
                    print("extract binary text error")
                    pass


def _decode_hex_string(hex_str: str, encoding_map: dict = None) -> str:
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

        # Try 4-byte CID
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

        if not decoded:
            # Track what's missing
            if i + 4 <= len(hex_str):
                cid = hex_str[i : i + 4]
                missing_cids.append(cid)
                result.append("?")
                i += 4
            else:
                i += 2

    # Debug output for first few strings
    if missing_cids and len(result) < 50:
        text = "".join(result)
        print(f"      Text: '{text}'")
        print(f"      Missing CIDs: {missing_cids}")
        # Based on expected text "Ala ma kota"
        if text.startswith("?l"):
            print(f"      -> CID {missing_cids[0]} should be 'A'")
        if "?a" in text[:10]:
            print(
                f"      -> CID {missing_cids[1] if len(missing_cids) > 1 else '????'} should be 'm'"
            )

    return "".join(result)


def _clean_extracted_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text)

    text = text.replace("\x00", "")
    text = text.replace("\u00a0", " ")

    import unicodedata

    cleaned = []
    for char in text:
        if unicodedata.category(char)[0] not in ["C"]:
            cleaned.append(char)
        elif char in "\n\r\t":
            cleaned.append(" ")

    return "".join(cleaned).strip()
