import re
from .stream_handler import _extract_stream_from_object


def extract_fontfile2_cmap(obj_num, pdf_bytes: bytes):
    """Extract character mappings from embedded TrueType font using fonttools"""
    print(f"    ENTERING extract_fontfile2_cmap for object {obj_num}")
    
    # Get the FontFile2 stream
    obj_pattern = rb'%d\s+\d+\s+obj(.*?)endobj' % obj_num
    obj_match = re.search(obj_pattern, pdf_bytes, re.DOTALL)
    if not obj_match:
        print(f"    ERROR: Could not find object {obj_num}")
        return {}
    
    obj_content = obj_match.group(1)
    
    # Extract stream
    stream_match = re.search(rb'stream\r?\n?(.*?)\r?\n?endstream', obj_content, re.DOTALL)
    if not stream_match:
        print(f"    ERROR: No stream in object {obj_num}")
        return {}
    
    font_data = stream_match.group(1)
    print(f"    Raw font data size: {len(font_data)} bytes")
    
    # Decompress if needed
    if b'/FlateDecode' in obj_content:
        import zlib
        try:
            font_data = zlib.decompress(font_data)
            print(f"    Decompressed to: {len(font_data)} bytes")
        except Exception as e:
            print(f"    ERROR decompressing: {e}")
    
    # Parse with fonttools
    try:
        from fontTools.ttLib import TTFont
        from io import BytesIO
        
        # Load font from bytes
        ttfont = TTFont(BytesIO(font_data))
        print(f"    Font loaded successfully")
        
        # Get the cmap table
        if 'cmap' in ttfont:
            cmap = ttfont['cmap'].getBestCmap()
            
            if cmap:
                # Convert to your format: hex CID -> character
                char_map = {}
                for code_point, glyph_name in cmap.items():
                    # Convert code point to 4-digit hex string
                    hex_code = f"{code_point:04X}"
                    char = chr(code_point)
                    char_map[hex_code] = char
                
                print(f"    SUCCESS: Extracted {len(char_map)} characters from FontFile2")
                
                # Show sample mappings
                for hex_code, char in list(char_map.items())[:10]:
                    #print(f"      {hex_code} -> '{char}'")
                    pass
                
                ttfont.close()
                return char_map
            else:
                print(f"    ERROR: No suitable cmap found in font")
        else:
            print(f"    ERROR: No cmap table in font")
        
        ttfont.close()
    except Exception as e:
        print(f"    ERROR parsing TrueType font: {e}")
        import traceback
        traceback.print_exc()
    
    return {}


def _extract_font_mappings(pdf_bytes: bytes, xref_table: dict) -> dict:
    font_mappings = {}
    
    # STEP 1: Find ALL ToUnicode references in the entire PDF
    all_tounicode_refs = {}
    tounicode_pattern = rb'/ToUnicode\s+(\d+)\s+(\d+)\s+R'
    for match in re.finditer(tounicode_pattern, pdf_bytes):
        obj_num = int(match.group(1))
        gen_num = int(match.group(2))
        all_tounicode_refs[obj_num] = gen_num
    
    print(f"Found {len(all_tounicode_refs)} ToUnicode references in PDF")
    
    # STEP 2: Extract ALL ToUnicode CMaps
    all_cmaps = {}
    for obj_num, gen_num in all_tounicode_refs.items():
        cmap = _extract_tounicode_cmap(obj_num, pdf_bytes, xref_table)
        if cmap:
            all_cmaps[obj_num] = cmap
            print(f"  ToUnicode object {obj_num}: {len(cmap)} mappings")
    
    # STEP 3: Find font-to-CMap relationships
    font_pattern = rb'(\d+)\s+\d+\s+obj[^>]*?/Type\s*/Font.*?endobj'
    font_objects = []
    
    for match in re.finditer(font_pattern, pdf_bytes, re.DOTALL):
        obj_num = int(match.group(1))
        obj_content = match.group(0)
        font_objects.append((obj_num, obj_content))
    
    print(f"Found {len(font_objects)} font objects")
    
    # STEP 4: Look for DescendantFonts which might have the actual mappings
    for obj_num, font_obj in font_objects:
        # Check for DescendantFonts (Type 0 fonts use these)
        descendant_match = re.search(rb'/DescendantFonts\s*\[\s*(\d+)\s+\d+\s+R\s*\]', font_obj)
        if descendant_match:
            desc_obj = int(descendant_match.group(1))
            print(f"  Font {obj_num} has DescendantFont at {desc_obj}")
            
            # Get the descendant font object
            desc_pattern = rb'%d\s+\d+\s+obj(.*?)endobj' % desc_obj
            desc_match = re.search(desc_pattern, pdf_bytes, re.DOTALL)
            if desc_match:
                desc_content = desc_match.group(1)
                # Check if descendant has ToUnicode
                desc_tounicode = re.search(rb'/ToUnicode\s+(\d+)\s+\d+\s+R', desc_content)
                if desc_tounicode:
                    tounicode_obj = int(desc_tounicode.group(1))
                    if tounicode_obj in all_cmaps:
                        print(f"    Found ToUnicode in descendant: {len(all_cmaps[tounicode_obj])} mappings")
    
    # STEP 5: Also check for CIDToGIDMap which might help
    cidtogid_pattern = rb'/CIDToGIDMap\s+(\d+)\s+\d+\s+R'
    for match in re.finditer(cidtogid_pattern, pdf_bytes):
        obj_num = int(match.group(1))
        print(f"  Found CIDToGIDMap at object {obj_num}")

        # EXTRACT the actual CIDToGIDMap stream
        obj_pattern = rb'%d\s+\d+\s+obj(.*?)endobj' % obj_num
        obj_match = re.search(obj_pattern, pdf_bytes, re.DOTALL)
        if obj_match:
            obj_content = obj_match.group(1)
            
            # Extract the stream
            stream_match = re.search(rb'stream\r?\n?(.*?)\r?\n?endstream', obj_content, re.DOTALL)
            if stream_match:
                stream_data = stream_match.group(1)
                
                # Check if compressed
                if b'/Filter' in obj_content and b'/FlateDecode' in obj_content:
                    import zlib
                    try:
                        stream_data = zlib.decompress(stream_data)
                    except:
                        pass
                
                # CIDToGIDMap is binary: each CID (2 bytes) maps to a GID (2 bytes)
                print(f"    CIDToGIDMap stream length: {len(stream_data)} bytes")
                
                # Parse it: CID -> GID mapping
                for i in range(0, len(stream_data)-1, 2):
                    cid = i // 2
                    gid = (stream_data[i] << 8) | stream_data[i+1]
                    if gid != 0:  # GID 0 means undefined
                        # Now you have CID -> GID mapping
                        # You need to combine this with font data to get actual characters
                        pass
    
    # STEP 5.5: Extract FontFile2 CMaps
    # Find all FontFile2 references and extract character mappings
    fontfile2_pattern = rb'/FontFile2\s+(\d+)\s+\d+\s+R'
    fontfile2_cmaps = []
    
    for match in re.finditer(fontfile2_pattern, pdf_bytes):
        ff2_obj = int(match.group(1))
        print(f"  Found FontFile2 at object {ff2_obj}")
        
        ff2_cmap = extract_fontfile2_cmap(ff2_obj, pdf_bytes)
        if ff2_cmap:
            fontfile2_cmaps.append(ff2_cmap)
            print(f"    Extracted {len(ff2_cmap)} mappings from FontFile2")
    
    # STEP 6: Merge ALL CMaps into one comprehensive mapping
    merged_cmap = {}
    
    # First add ToUnicode mappings
    for obj_num, cmap in all_cmaps.items():
        for k, v in cmap.items():
            if k not in merged_cmap:
                merged_cmap[k] = v
    
    # Then add FontFile2 mappings (these fill in the gaps)
    for ff2_cmap in fontfile2_cmaps:
        for k, v in ff2_cmap.items():
            if k not in merged_cmap:
                merged_cmap[k] = v
            # Don't overwrite existing ToUnicode mappings
    ff2_cmap = extract_fontfile2_cmap(ff2_obj, pdf_bytes)
    print(f"    extract_fontfile2_cmap returned {len(ff2_cmap)} mappings")  # Add this
    if ff2_cmap:
        fontfile2_cmaps.append(ff2_cmap)
        print(f"    Added to fontfile2_cmaps list")
    
    print(f"FINAL: Merged CMap has {len(merged_cmap)} total unique mappings")
    
    # Show what we have
    if merged_cmap:
        # Check coverage
        mapped_chars = set(merged_cmap.values())
        basic_chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
        missing = [c for c in basic_chars if c not in mapped_chars]
        if missing:
            print(f"  Still missing: {''.join(missing)}")
    
    # STEP 7: Build alias -> basefont mapping
    alias_to_basefont = {}
    resource_pattern = rb'/Font\s*<<(.+?)>>'
    for match in re.finditer(resource_pattern, pdf_bytes, re.DOTALL):
        font_block = match.group(1)
        for alias, obj_num in re.findall(rb'/([Ff]\d+)\s+(\d+)\s+0\s+R', font_block):
            alias = alias.decode()
            obj_num = int(obj_num)
            # szukamy definicji obiektu fontu
            obj_pattern = rb'%d\s+\d+\s+obj(.*?)endobj' % obj_num
            obj_match = re.search(obj_pattern, pdf_bytes, re.DOTALL)
            if obj_match:
                obj_content = obj_match.group(1)
                basefont_match = re.search(rb'/BaseFont/([^\s/]+)', obj_content)
                if basefont_match:
                    basefont = basefont_match.group(1).decode()
                    alias_to_basefont[alias] = basefont
                    #print(f"Alias {alias} -> {basefont}")
    
    # STEP 8: Apply CMap to each alias based on its BaseFont
    for alias, basefont in alias_to_basefont.items():
        if basefont in font_mappings:
            font_mappings[alias] = font_mappings[basefont]
        else:
            # fallback: przypnij alias bezpośrednio do merged_cmap
            font_mappings[alias] = merged_cmap
    
    # Also add common names
    font_mappings['Aptos'] = merged_cmap
    font_mappings['BCDEEE+Aptos'] = merged_cmap
    font_mappings['BCDFEE+Aptos'] = merged_cmap
    
    return font_mappings


def _extract_tounicode_cmap(obj_num: int, pdf_bytes: bytes, xref_table: dict) -> dict:

    char_map = {}

    obj_offset = xref_table.get(obj_num, 0)
    if not obj_offset:
        pattern = rb'%d\s+\d+\s+obj' % obj_num
        match = re.search(pattern, pdf_bytes)
        if match:
            obj_offset = match.start()
    
    if not obj_offset:
        return char_map
    
    obj_end = pdf_bytes.find(b'endobj', obj_offset)
    if obj_end == -1:
        return char_map
    
    obj_content = pdf_bytes[obj_offset:obj_end + 6]

    stream_data = _extract_stream_from_object(obj_content)
    if not stream_data:
        return char_map
    
    try:
        cmap_text = stream_data.decode('utf-8', errors='ignore')
    except:
        cmap_text = stream_data.decode('latin-1', errors='ignore')
    
    _parse_bfchar_sections(cmap_text, char_map)
    _parse_bfrange_sections(cmap_text, char_map)

    if char_map:
        print(f"CMap loaded with {len(char_map)} mappings")
        
        # Check which basic Latin letters are present
        basic_chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
        polish_chars = 'ąćęłńóśźżĄĆĘŁŃÓŚŹŻ'
        
        mapped_basic = []
        missing_basic = []
        mapped_polish = []
        missing_polish = []
        
        # Check what's in the map
        mapped_values = set(char_map.values())
        
        for char in basic_chars:
            if char in mapped_values:
                mapped_basic.append(char)
            else:
                missing_basic.append(char)
        
        for char in polish_chars:
            if char in mapped_values:
                mapped_polish.append(char)
            else:
                missing_polish.append(char)
        
        print(f"  Mapped basic letters: {''.join(mapped_basic)}")
        print(f"  MISSING basic letters: {''.join(missing_basic)}")
        print(f"  Mapped Polish letters: {''.join(mapped_polish)}")
        print(f"  MISSING Polish letters: {''.join(missing_polish)}")
        
        # Show first 10 mappings
        for i, (k, v) in enumerate(list(char_map.items())[:10]):
            print(f"  {k} -> '{v}' (U+{ord(v):04X})")

    return char_map


def _parse_bfchar_sections(cmap_text: str, char_map: dict):

    bfchar_pattern = r'beginbfchar(.*?)endbfchar'

    for match in re.finditer(bfchar_pattern, cmap_text, re.DOTALL):
        section = match.group(1)

        pair_pattern = r'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>'

        for pair_match in re.finditer(pair_pattern, section):
            src_hex = pair_match.group(1).upper()
            dst_hex = pair_match.group(2)

            try:
                # src_code = int(src_hex, 16)

                if len(dst_hex) == 4:
                    unicode_char = chr(int(dst_hex, 16))
                elif len(dst_hex) > 4:
                    dst_bytes = bytes.fromhex(dst_hex)
                    unicode_char = dst_bytes.decode('utf-16-be', errors='ignore')
                else:
                    unicode_char = chr(int(dst_hex, 16))
                
                char_map[src_hex] = unicode_char
            
            except Exception as e:
                continue


def _parse_bfrange_sections(cmap_text: str, char_map: dict):
    
    bfrange_pattern = r'beginbfrange(.*?)endbfrange'

    for match in re.finditer(bfrange_pattern, cmap_text, re.DOTALL):
        section = match.group(1)

        range_pattern = r'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>'

        for range_match in re.finditer(range_pattern, section):
            start_hex = range_match.group(1)
            end_hex = range_match.group(2)
            base_hex = range_match.group(3)

            try:
                start = int(start_hex, 16)
                end = int(end_hex, 16)
                base = int(base_hex, 16)

                for i in range(start, min(end + 1, start + 256)):
                    char_code_hex = f"{i:04X}"
                    unicode_value = base + (i - start)

                    if unicode_value < 0x110000:
                        char_map[char_code_hex] = chr(unicode_value)
            
            except Exception as e:
                continue

        array_pattern = r'<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*\[(.*?)\]'
        
        for array_match in re.finditer(array_pattern, section):
            start_hex = array_match.group(1)
            end_hex = array_match.group(2)
            values = array_match.group(3)

            try:
                start = int(start_hex, 16)
                end = int(end_hex, 16)
                
                value_pattern = r'<([0-9A-Fa-f]+)>'
                value_matches = re.findall(value_pattern, values)

                for i, val_hex in enumerate(value_matches):
                    if start + i <= end:
                        char_code_hex = f"{start + i:04X}"

                        if len(val_hex) == 4:
                            unicode_char = chr(int(val_hex), 16)
                        else:
                            dst_bytes = bytes.fromhex(val_hex)
                            unicode_char = dst_bytes.decode('utf-16-be', errors='ignore')
                        
                        char_map[char_code_hex] = unicode_char
            
            except Exception as e:
                continue