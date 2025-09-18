import re
import zlib
from typing import List, Optional
import base64


class PDFParser:
    
    def __init__(self, pdf_bytes: bytes, debug):
        self.pdf_bytes = pdf_bytes
        self.objects = {}
        self.xref_table = {}
        self.debug = debug


    def analyze_pdf(self) -> dict:
        analysis = {
            'type': 'unknown',
            'has_literal_text': False,
            'has_hex_text': False,
            'has_tounicode': False,
            'has_object_streams': False,
            'fonts': [],
            'encoding_type': None
        }

        if re.search(rb'\([^)]+\)\s*Tj', self.pdf_bytes):
            analysis['has_literal_text'] = True
            analysis['type'] = 'simple'

        if re.search(rb'<[0-9A-Fa-f]{4,}>', self.pdf_bytes):
            analysis['has_hex_text'] = True
            analysis['type'] = 'complex'

        if b'/ToUnicode' in self.pdf_bytes:
            analysis['has_tounicode'] = True

        if b'/ObjStm' in self.pdf_bytes or b'/Type/ObjStm' in self.pdf_bytes:
            analysis['has_object_streams'] = True

        font_pattern = rb'/BaseFont\s*/([^\s/>]+)'
        for match in re.finditer(font_pattern, self.pdf_bytes):
            font_name = match.group(1).decode('latin-1', errors='ignore')
            analysis['fonts'].append(font_name)
        
        if b'Microsoft' in self.pdf_bytes or b'Word' in self.pdf_bytes:
            analysis['type'] = 'microsoft'
        elif b'PowerPoint' in self.pdf_bytes:
            analysis['type'] = 'powerpoint'
        
        return analysis
    

    def debug_stream_content(self, stream: bytes):
        print("\n=== Stream Debug ===")
        print(f"Stream length: {len(stream)} bytes")
        print(f"First 200 bytes raw: {stream[:200]}")
        
        # Check for different text patterns
        if b'Tj' in stream:
            print("Found Tj operators")
        if b'TJ' in stream:
            print("Found TJ operators")
        
        # Look for hex strings
        hex_pattern = rb'<([0-9A-Fa-f]+)>'
        hex_matches = list(re.finditer(hex_pattern, stream))
        print(f"Found {len(hex_matches)} hex strings")
        if hex_matches:
            print(f"First hex: {hex_matches[0].group()}")
        
        # Look for literal strings
        literal_pattern = rb'\(([^)]+)\)'
        literal_matches = list(re.finditer(literal_pattern, stream))
        print(f"Found {len(literal_matches)} literal strings")
        if literal_matches:
            print(f"First literal: {literal_matches[0].group()}")
            # Show the byte values
            first_literal = literal_matches[0].group(1)
            print(f"Byte values: {[hex(b) for b in first_literal[:20]]}")


    def _decode_hex_string(self, hex_str: str, encoding_map: dict = None) -> str:
        hex_str = hex_str.replace(' ', '').upper()
        if len(hex_str) % 2 != 0:
            hex_str = hex_str[:-1]
        
        result = []
        
        if not encoding_map:
            return ""
        
        i = 0
        while i < len(hex_str):
            # Safety check
            if i > len(hex_str) + 10:
                print(f"        ERROR: Loop safety triggered at i={i}")
                break
                
            # Try 4-byte CID
            if i + 4 <= len(hex_str):
                cid = hex_str[i:i+4]
                if cid in encoding_map:
                    char = encoding_map[cid]
                    result.append(char)
                    print(f"          {cid} -> '{char}'")
                    i += 4
                    continue
            
            # Try 2-byte CID
            if i + 2 <= len(hex_str):
                cid = hex_str[i:i+2]
                if cid in encoding_map:
                    char = encoding_map[cid]
                    result.append(char)
                    print(f"          {cid} -> '{char}'")
                    i += 2
                    continue
            
            # No match, skip 2 bytes
            print(f"          No match at pos {i}, skipping")
            i += 2
        
        decoded = ''.join(result)
        return decoded
    

    def _extract_font_mappings(self) -> dict:
        font_mappings = {}
        
        # STEP 1: Find ALL ToUnicode references in the entire PDF
        all_tounicode_refs = {}
        tounicode_pattern = rb'/ToUnicode\s+(\d+)\s+(\d+)\s+R'
        for match in re.finditer(tounicode_pattern, self.pdf_bytes):
            obj_num = int(match.group(1))
            gen_num = int(match.group(2))
            all_tounicode_refs[obj_num] = gen_num
        
        print(f"Found {len(all_tounicode_refs)} ToUnicode references in PDF")
        
        # STEP 2: Extract ALL ToUnicode CMaps
        all_cmaps = {}
        for obj_num, gen_num in all_tounicode_refs.items():
            cmap = self._extract_tounicode_cmap(obj_num)
            if cmap:
                all_cmaps[obj_num] = cmap
                print(f"  ToUnicode object {obj_num}: {len(cmap)} mappings")
        
        # STEP 3: Find font-to-CMap relationships
        font_pattern = rb'(\d+)\s+\d+\s+obj[^>]*?/Type\s*/Font.*?endobj'
        font_objects = []
        
        for match in re.finditer(font_pattern, self.pdf_bytes, re.DOTALL):
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
                desc_match = re.search(desc_pattern, self.pdf_bytes, re.DOTALL)
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
        for match in re.finditer(cidtogid_pattern, self.pdf_bytes):
            obj_num = int(match.group(1))
            print(f"  Found CIDToGIDMap at object {obj_num}")
        
        # STEP 6: Merge ALL CMaps into one comprehensive mapping
        merged_cmap = {}
        for obj_num, cmap in all_cmaps.items():
            for k, v in cmap.items():
                if k not in merged_cmap:
                    merged_cmap[k] = v
                else:
                    # If conflict, keep both somehow
                    print(f"    Warning: Duplicate mapping for {k}: {merged_cmap[k]} vs {v}")
        
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
        for match in re.finditer(resource_pattern, self.pdf_bytes, re.DOTALL):
            font_block = match.group(1)
            for alias, obj_num in re.findall(rb'/([Ff]\d+)\s+(\d+)\s+0\s+R', font_block):
                alias = alias.decode()
                obj_num = int(obj_num)
                # szukamy definicji obiektu fontu
                obj_pattern = rb'%d\s+\d+\s+obj(.*?)endobj' % obj_num
                obj_match = re.search(obj_pattern, self.pdf_bytes, re.DOTALL)
                if obj_match:
                    obj_content = obj_match.group(1)
                    basefont_match = re.search(rb'/BaseFont/([^\s/]+)', obj_content)
                    if basefont_match:
                        basefont = basefont_match.group(1).decode()
                        alias_to_basefont[alias] = basefont
                        print(f"Alias {alias} -> {basefont}")
        
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


    def _extract_tounicode_cmap(self, obj_num: int) -> dict:

        char_map = {}

        obj_offset = self.xref_table.get(obj_num, 0)
        if not obj_offset:
            pattern = rb'%d\s+\d+\s+obj' % obj_num
            match = re.search(pattern, self.pdf_bytes)
            if match:
                obj_offset = match.start()
        
        if not obj_offset:
            return char_map
        
        obj_end = self.pdf_bytes.find(b'endobj', obj_offset)
        if obj_end == -1:
            return char_map
        
        obj_content = self.pdf_bytes[obj_offset:obj_end + 6]

        stream_data = self._extract_stream_from_object(obj_content)
        if not stream_data:
            return char_map
        
        try:
            cmap_text = stream_data.decode('utf-8', errors='ignore')
        except:
            cmap_text = stream_data.decode('latin-1', errors='ignore')
        
        self._parse_bfchar_sections(cmap_text, char_map)
        self._parse_bfrange_sections(cmap_text, char_map)

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
    

    def _parse_bfchar_sections(self, cmap_text: str, char_map: dict):

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


    def _parse_bfrange_sections(self, cmap_text: str, char_map: dict):
        
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


    def parse(self) -> str:

        try:
            analysis = self.analyze_pdf()
            print(f"PDF Analysis: {analysis}")

            self._parse_xref_table()

            if analysis['has_object_streams']:
                print("Processing object streams...")
                self._handle_object_streams()

            font_mappings = {}
            if analysis['has_tounicode'] or analysis['has_hex_text']:
                print("Extracting font mapings...")
                font_mappings = self._extract_font_mappings()
                print(f"Found {len(font_mappings)} font mappings")
            
            streams = self._extract_all_streams()
            print(f"Found {len(streams)} content streams")

            seen_texts = set()
            all_text = []
            for i, stream in enumerate(streams):
                if i == 6:  # Debug stream 6 which has text
                    self.debug_stream_content(stream)
                if font_mappings or analysis['has_hex_text']:
                    print(f"Stream {i}: Using advanced extraction (has mappings: {len(font_mappings)})")
                    text = self._extract_text_from_stream_advanced(stream, font_mappings)
                else:
                    print(f"Stream {i}: Using basic extraction")
                    text = self._extract_text_from_stream(stream)

                if text and text.strip():
                    if text not in seen_texts:
                        seen_texts.add(text)
                        print(f"Stream {i}: extracted {len(text)} chars")
                        print(f"  Preview: {repr(text[:50])}")
                        all_text.append(text)
                    else:
                        print(f"Stream {i}: extracted {len(text)} chars (duplicate, skipping)")

            result = ' '.join(all_text)
            result = self._clean_extracted_text(result)

            print(f"Total extracted: {len(result)} characters")
            if result:
                print(f"Final preview: {repr(result[:100])}")
            return result

        except Exception as e:
            print(f"Error during parsing: {e}")
            import traceback
            traceback.print_exc()
            return ""
            

    def _clean_extracted_text(self, text: str) -> str:

        text = re.sub(r'\s+', ' ', text)

        text = text.replace('\x00', '')
        text = text.replace('\u00A0', ' ')

        import unicodedata
        cleaned = []
        for char in text:
            if unicodedata.category(char)[0] not in ['C']:
                cleaned.append(char)
            elif char in '\n\r\t':
                cleaned.append(' ')
                
        return ''.join(cleaned).strip()
    

    def _parse_xref_table(self):

        xref_offset = self._find_xref_offset()

        if xref_offset:
            self._parse_traditional_xref(xref_offset)

        self._scan_for_objects()
    

    def _find_xref_offset(self) -> Optional[int]:

        tail = self.pdf_bytes[-1024:]

        match = re.search(rb'startxref\s+(\d+)', tail)
        if match:
            return int(match.group(1))
        
        return None
    

    def _parse_traditional_xref(self, offset: int):

        xref_section = self.pdf_bytes[offset:]

        lines = xref_section.split(b'\n')
        i=0

        if lines[i].strip() == b'xref':
            i += 1
        
        while i < len(lines):
            line = lines[i].strip()

            match = re.match(rb'(\d+)\s+(\d+)$', line)
            if match:
                start_obj = int(match.group(1))
                num_objs = int(match.group(2))
                i += 1

                for j in range(num_objs):
                    if i < len(lines):
                        entry = lines[i].strip()

                        entry_match = re.match(rb'(\d{10})\s+(\d{5})\s+([fn])', entry)
                        if entry_match:
                            offset = int(entry_match.group(1))
                            generation = int(entry_match.group(2))
                            in_use = entry_match.group(3) == b'n'

                            if in_use and offset > 0:
                                obj_num = start_obj + j
                                self.xref_table[obj_num] = offset
                        
                        i += 1
            
            elif line == b'trailer':
                break
            else:
                i += 1


    def _scan_for_objects(self):
        
        pattern = rb'(\d+)\s+(\d+)\s+obj'

        for match in re.finditer(pattern, self.pdf_bytes):
            obj_num = int(match.group(1))
            generation = int(match.group(2))
            offset = match.start()

            if obj_num not in self.xref_table:
                self.xref_table[obj_num] = offset


    def _extract_all_streams(self) -> List[bytes]:

        streams = []

        for obj_num, offset in self.xref_table.items():
            obj_content = self._extract_object(obj_num, offset)
            if obj_content:
                stream = self._extract_stream_from_object(obj_content)
                if stream:
                    streams.append(stream)

        stream_pattern = rb'stream\r?\n(.*?)endstream'
        for match in re.finditer(stream_pattern, self.pdf_bytes, re.DOTALL):
            stream_content = match.group(1)
            if stream_content.startswith(b'x\x9c') or stream_content.startswith(b'x\xda'):
                try:
                    decompressed = zlib.decompress(stream_content)
                    streams.append(decompressed)
                except:
                    streams.append(stream_content)
            else:
                streams.append(stream_content)

        return streams


    def _extract_object(self, obj_num: int, offset: int) -> Optional[bytes]:

        if obj_num in self.objects:
            return self.objects[obj_num]
        
        start = offset

        endobj_pos = self.pdf_bytes.find(b'endobj', start)
        if endobj_pos == 1:
            return None
        
        obj_content = self.pdf_bytes[start:endobj_pos + 6]

        self.objects[obj_num] = obj_content

        return obj_content
        

    def _decode_ascii85(self, data: bytes) -> bytes:

        data = data.replace(b'\n', b'').replace(b'\r', b'').replace(b' ', b'')

        if data.endswith(b'~>'):
            data = data[:-2]

        try:
            return base64.a85decode(data)
        except:
            return data

    
    def _extract_stream_from_object(self, obj_content: bytes) -> Optional[bytes]:
        """Extract and decompress stream from an object"""
        # Find stream boundaries
        stream_start = obj_content.find(b'stream')
        stream_end = obj_content.find(b'endstream')
        
        if stream_start == -1 or stream_end == -1:
            return None
        
        # Move past 'stream' and any newlines
        stream_start += 6  # len('stream')
        if stream_start < len(obj_content) and obj_content[stream_start:stream_start+2] in (b'\r\n', b'\n\r'):
            stream_start += 2
        elif stream_start < len(obj_content) and obj_content[stream_start:stream_start+1] in (b'\n', b'\r'):
            stream_start += 1
        
        stream_data = obj_content[stream_start:stream_end]
        
        # IMPORTANT: Apply decompression in the right order!
        # Check for ASCII85 first
        if b'/ASCII85Decode' in obj_content:
            if stream_data.endswith(b'~>'):
                stream_data = stream_data[:-2]
            import base64
            stream_data = base64.a85decode(stream_data)
        
        # Then apply FlateDecode
        if b'/FlateDecode' in obj_content:
            import zlib
            stream_data = zlib.decompress(stream_data)
        
        return stream_data  # Return the DECOMPRESSED data


    def _decode_ascii_hex(self, data: bytes) -> bytes:

        hex_str = data.decode('ascii', errors='ignore')
        hex_str = re.sub(r'\s+', '', hex_str)

        if hex_str.endswith('>'):
            hex_str = hex_str[:-1]

        try:
            return bytes.fromhex(hex_str)
        except:
            return data


    def _extract_text_from_stream(self, stream: bytes) -> str:
            extracted_text = []
            
            # Pattern 1: Literal strings (text) Tj
            literal_pattern = rb'\(([^)]*)\)\s*Tj'
            
            matches = list(re.finditer(literal_pattern, stream))
            
            for match in matches:
                text_bytes = match.group(1)
                text = text_bytes.decode('utf-8', errors='ignore')
                text = text.replace('\x00', '')
                text = text.replace('\\(', '(').replace('\\)', ')').replace('\\\\', '\\')
                
                if text.strip():
                    extracted_text.append(text)
            
            # Pattern 2: Hex strings <hex> Tj
            hex_pattern = rb'<([0-9A-Fa-f]+)>\s*Tj'
            for match in re.finditer(hex_pattern, stream):
                hex_bytes = match.group(1)
                try:
                    hex_str = hex_bytes.decode('ascii', errors='ignore')
                    if len(hex_str) % 2 != 0:
                        hex_str = hex_str[:-1]
                    text_bytes = bytes.fromhex(hex_str)
                    text = self._decode_pdf_text(text_bytes)
                    text = text.replace('\x00', '')
                    if text and text.strip():
                        extracted_text.append(text)
                except:
                    pass
            
            # Pattern 3: Arrays [...] TJ
            array_pattern = rb'\[(.*?)\]\s*TJ'
            for match in re.finditer(array_pattern, stream, re.DOTALL):
                array_content = match.group(1)
                
                str_pattern = rb'\(([^)]*)\)'
                for str_match in re.finditer(str_pattern, array_content):
                    text = str_match.group(1).decode('utf-8', errors='ignore')
                    text = text.replace('\x00', '')
                    text = text.replace('\\(', '(').replace('\\)', ')').replace('\\\\', '\\')
                    if text.strip():
                        extracted_text.append(text)
                
                hex_in_array = rb'<([0-9A-Fa-f]+)>'
                for hex_match in re.finditer(hex_in_array, array_content):
                    try:
                        hex_str = hex_match.group(1).decode('ascii', errors='ignore')
                        if len(hex_str) % 2 != 0:
                            hex_str = hex_str[:-1]
                        text_bytes = bytes.fromhex(hex_str)
                        text = self._decode_pdf_text(text_bytes)
                        text = text.replace('\x00', '')
                        if text and text.strip():
                            extracted_text.append(text)
                    except:
                        pass

            # Pattern 4: Binary text (UTF-16)
            self._extract_binary_text(stream, extracted_text)
            return ' '.join(extracted_text)


    def _extract_text_from_stream_advanced(self, stream: bytes, font_mappings: dict) -> str:
        extracted_text = []
        current_font = None
        current_map = {}

        # Tokenizujemy stream na elementy: <...>, (...), /Fxx, liczby, operatory
        tokens = re.findall(rb'(<[0-9A-Fa-f]+>|\(.*?\)|/[A-Za-z0-9]+|\S+)', stream, re.DOTALL)
        i = 0
        while i < len(tokens):
            tok = tokens[i]

            # Zmiana fontu: /F1 12 Tf
            if tok.startswith(b'/F'):
                current_font = tok[1:].decode('latin-1', errors='ignore')
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
            if tok == b'Tj' and i > 0 and tokens[i-1].startswith(b'<'):
                hex_str = tokens[i-1].strip(b'<>').decode('ascii')
                text = self._decode_hex_string(hex_str, current_map)
                if text:
                    extracted_text.append(text)

            # Literal string + Tj
            if tok == b'Tj' and i > 0 and tokens[i-1].startswith(b'('):
                lit = tokens[i-1][1:-1].decode('latin-1', errors='ignore')
                extracted_text.append(lit)

            # Tablica TJ
            if tok == b'TJ' and i > 0 and tokens[i-1].startswith(b'['):
                array_content = tokens[i-1][1:-1]
                parts = re.findall(rb'<([0-9A-Fa-f]+)>|(-?\d+)', array_content)
                block = []
                for hex_str, spacing in parts:
                    if hex_str:
                        text = self._decode_hex_string(hex_str.decode('ascii'), current_map)
                        if text:
                            block.append(text)
                    elif spacing and int(spacing) < -100:
                        block.append(' ')
                if block:
                    extracted_text.append(''.join(block))

            i += 1

        return ' '.join(extracted_text)

    

    def _handle_object_streams(self):
        
        objstm_pattern = rb'(\d+)\s+\d+\s+obj[^>]*?/Type\s*/ObjStm.*?endobj'

        for match in re.finditer(objstm_pattern, self.pdf_bytes, re.DOTALL):
            stream_obj_num = int(match.group(1))
            obj_content = match.group(0)

            n_match = re.search(rb'/N\s+(\d+)', obj_content)
            first_match = re.search(rb'/First\s+(\d+)', obj_content)

            if not n_match or not first_match:
                continue

            n = int(n_match.group(1))
            first = int(first_match.group(1))

            stream_data = self._extract_stream_from_object(obj_content)
            if not stream_data:
                continue

            index_data = stream_data[:first]
            objects_data = stream_data[first:]

            try:
                index_str = index_data.decode('latin-1', errors='ignore')
            except:
                continue

            numbers = re.findall(r'\d+', index_str)

            for i in range(0, len(numbers), 2):
                if i + 1 < len(numbers):
                    obj_num = int(numbers[i])
                    offset = int(numbers[i+1])

                    if i + 3 < len(numbers):
                        next_offset = int(numbers[i+3])
                        obj_data = objects_data[offset:next_offset]
                    else:
                        obj_data = objects_data[offset:]

                    if obj_num not in self.xref_table:
                        self.xref_table[obj_num] = -stream_obj_num



    def _extract_binary_text(self, stream: bytes, output: List[str]):

        bt_pattern = rb'BT(.*?)ET'

        for match in re.finditer(bt_pattern, stream, re.DOTALL):
            text_block = match.group(1)

            if b'\xfe\xff' in text_block:
                utf16_pattern = rb'\xfe\xff((?:[\x00-\xff][\x00-\xff])+)'
                for utf16_match in re.finditer(utf16_pattern, text_block):
                    try:
                        text = utf16_match.group(1).decode('utf-16-be', errors='ignore')
                        text = text.replace('\00', '')
                        if text.strip():
                            output.append(text)
                    except:
                        print("extract binary text error")
                        pass


    def _decode_pdf_text(self, text_bytes: bytes) -> str:

        if text_bytes.startswith(b'\xfe\xff'):
            try:
                return text_bytes[2:].decode('utf-16-be', errors='ignore')
            except:
                pass
        
        if text_bytes.startswith(b'\xff\xfe'):
            try:
                return text_bytes[2:].decode('uft-16-le', errors='ignore')
            except:
                pass
        
        if len(text_bytes) % 2 == 0 and len(text_bytes) >= 2:
            if all(b == 0 for b in text_bytes[1::2]) or all(b == 0 for b in text_bytes[::2]):
                try:
                    return text_bytes.decode('utf-16-be', errors='ignore')
                except:
                    try:
                        return text_bytes.decode('utf-16-le', errors='ignore')
                    except:
                        pass
        
        try:
            return text_bytes.decode('utf-8')
        except:
            pass

        try:
            return text_bytes.decode('cp1252')
        except:
            pass

        return text_bytes.decode('latin-1', errors='ignore')