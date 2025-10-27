import re


def analyze_pdf(pdf_bytes: bytes) -> dict:
    analysis = {
        "type": "unknown",
        "has_literal_text": False,
        "has_hex_text": False,
        "has_tounicode": False,
        "has_object_streams": False,
        "fonts": [],
        "encoding_type": None,
    }

    if re.search(rb"\([^)]+\)\s*Tj", pdf_bytes):
        analysis["has_literal_text"] = True
        analysis["type"] = "simple"

    if re.search(rb"<[0-9A-Fa-f]{4,}>", pdf_bytes):
        analysis["has_hex_text"] = True
        analysis["type"] = "complex"

    if b"/ToUnicode" in pdf_bytes:
        analysis["has_tounicode"] = True

    if b"/ObjStm" in pdf_bytes or b"/Type/ObjStm" in pdf_bytes:
        analysis["has_object_streams"] = True

    font_pattern = rb"/BaseFont\s*/([^\s/>]+)"
    for match in re.finditer(font_pattern, pdf_bytes):
        font_name = match.group(1).decode("latin-1", errors="ignore")
        analysis["fonts"].append(font_name)

    if b"Microsoft" in pdf_bytes or b"Word" in pdf_bytes:
        analysis["type"] = "microsoft"
    elif b"PowerPoint" in pdf_bytes or b"powerpoint" in pdf_bytes:
        analysis["type"] = "powerpoint"

    # Also check for Producer/Creator fields
    if b"/Producer" in pdf_bytes or b"/Creator" in pdf_bytes:
        if b"PowerPoint" in pdf_bytes:
            analysis["type"] = "powerpoint"

    return analysis
