import base64
import logging
import re

logger = logging.getLogger(__name__)

SAMPLE_LENGTH = 200


def find_font_resources(pdf_bytes: bytes) -> None:
    logger.info("=== FONT RESOURCE SCAN ===")

    # Find FontDescriptor objects
    fontdesc_pattern = rb"/FontDescriptor\s+(\d+)\s+\d+\s+R"
    for match in re.finditer(fontdesc_pattern, pdf_bytes):
        desc_obj = int(match.group(1))
        logger.info(f"FontDescriptor at object {desc_obj}")

        # Get the FontDescriptor object
        obj_pattern = rf"{desc_obj}\s+\d+\s+obj(.*?)endobj".encode()
        obj_match = re.search(obj_pattern, pdf_bytes, re.DOTALL)

        if obj_match:
            desc_content = obj_match.group(1)

            # Check for FontFile2 (TrueType fonts)
            if b"/FontFile2" in desc_content:
                ff2_match = re.search(rb"/FontFile2\s+(\d+)\s+\d+\s+R", desc_content)
                if ff2_match:
                    logger.info(
                        f"  -> Has FontFile2 at object {ff2_match.group(1).decode()}"
                    )

            # Check for FontFile (Type 1 fonts)
            elif b"/FontFile" in desc_content:
                ff_match = re.search(rb"/FontFile\s+(\d+)\s+\d+\s+R", desc_content)
                if ff_match:
                    logger.info(
                        f"  -> Has FontFile at object {ff_match.group(1).decode()}"
                    )

    # Find Encoding objects
    encoding_pattern = rb"/Encoding\s+(\d+)\s+\d+\s+R"
    for match in re.finditer(encoding_pattern, pdf_bytes):
        enc_obj = int(match.group(1))
        logger.info(f"Encoding at object {enc_obj}")

        # Get the encoding object
        obj_pattern = rf"{enc_obj}\s+\d+\s+obj(.*?)endobj".encode()
        obj_match = re.search(obj_pattern, pdf_bytes, re.DOTALL)

        if obj_match:
            enc_content = obj_match.group(1)

            if b"/Differences" in enc_content:
                logger.info("  -> Has Differences array")

                # Extract first few entries
                diff_match = re.search(
                    rb"/Differences\s*\[(.*?)\]", enc_content, re.DOTALL
                )
                if diff_match:
                    diff_content = diff_match.group(1)[:SAMPLE_LENGTH]
                    logger.info(f"    Sample: {diff_content}")

    # Find inline Differences
    inline_diff_pattern = rb"/Encoding\s*<<[^>]*?/Differences\s*\[(.*?)\]"
    for match in re.finditer(inline_diff_pattern, pdf_bytes):
        logger.info("Found inline Differences array")
        diff_content = match.group(1)[:SAMPLE_LENGTH]
        logger.info(f"  Sample: {diff_content}")


def _decode_ascii85(data: bytes) -> bytes:
    # Remove whitespace and newlines
    data = data.replace(b"\n", b"").replace(b"\r", b"").replace(b" ", b"")

    # Remove end marker if present
    if data.endswith(b"~>"):
        data = data[:-2]

    try:
        return base64.a85decode(data)
    except (ValueError, base64.binascii.Error) as e:
        logger.warning(f"Failed to decode ASCII85: {e}")
        return data


def _decode_ascii_hex(data: bytes) -> bytes:
    hex_str = data.decode("ascii", errors="ignore")
    hex_str = re.sub(r"\s+", "", hex_str)

    # Remove end marker if present
    if hex_str.endswith(">"):
        hex_str = hex_str[:-1]

    try:
        return bytes.fromhex(hex_str)
    except ValueError as e:
        logger.warning(f"Failed to decode ASCII hex: {e}")
        return data
