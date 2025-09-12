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
        font_objects = []
        font_pattern = rb'(\d+)\s+\d+\s+obj[^>]*?/Type\s*/Font.*?endobj'
        for match in re.finditer(font_pattern, self.pdf_bytes, re.DOTALL):
            obj_num = int(match.group(1))
            obj_content = match.group(0)
            font_objects.append((obj_num, obj_content))
        
        # Also find font references like /F1, /F2 in the PDF
        font_refs = {}
        ref_pattern = rb'/F(\d+)\s+(\d+)\s+\d+\s+R'
        for match in re.finditer(ref_pattern, self.pdf_bytes):
            font_id = f"F{match.group(1).decode()}"
            obj_ref = int(match.group(2))
            font_refs[font_id] = obj_ref
        
        for obj_num, font_obj in font_objects:
            name_match = re.search(rb'/BaseFont\s*/([^\s/>]+)', font_obj)
            if not name_match:
                continue
            font_name = name_match.group(1).decode('latin-1', errors='ignore')
            if '+' in font_name:
                base_font_name = font_name.split('+')[1]
            else:
                base_font_name = font_name
            
            tounicode_match = re.search(rb'/ToUnicode\s+(\d+)\s+\d+\s+R', font_obj)
            if tounicode_match:
                tounicode_obj_num = int(tounicode_match.group(1))
                cmap = self._extract_tounicode_cmap(tounicode_obj_num)
                if cmap:
                    font_mappings[font_name] = cmap
                    font_mappings[base_font_name] = cmap
                    
                    # Map F1, F2, etc. to this CMap
                    for font_id, ref_obj in font_refs.items():
                        if ref_obj == obj_num:
                            font_mappings[font_id] = cmap
        
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
            for i, (k, v) in enumerate(list(char_map.items())[:5]):
                print(f" {k} -> U+{ord(v):04X} ('{v}')")

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
        
        font_pattern = rb'/([^\s/]+)\s+[\d.]+\s+Tf'
        font_match = re.search(font_pattern, stream)
        if font_match:
            current_font = font_match.group(1).decode('latin-1', errors='ignore')
        
        char_map = {}
        if current_font and font_mappings:
            if current_font in font_mappings:
                char_map = font_mappings[current_font]
            else:
                for font_name, mapping in font_mappings.items():
                    if current_font in font_name or font_name in current_font:
                        char_map = mapping
                        break
        
        # Fallback if no font match
        if not char_map and font_mappings:
            char_map = list(font_mappings.values())[0]
        
        # Process TJ arrays - IMPROVED VERSION
        array_pattern = rb'\[(.*?)\]\s*TJ'
        for match in re.finditer(array_pattern, stream, re.DOTALL):
            array_content = match.group(1)
            
            # Process the entire array as one text block
            array_text = []
            
            # Split array content into tokens (hex strings and numbers)
            tokens = re.findall(rb'<([0-9A-Fa-f]+)>|(-?\d+(?:\.\d+)?)', array_content)
            
            for token in tokens:
                if token[0]:  # It's a hex string
                    hex_str = token[0].decode('ascii')
                    text = self._decode_hex_string(hex_str, char_map)
                    if text:
                        array_text.append(text)
                elif token[1]:  # It's a number (spacing adjustment)
                    # In PDF, negative values usually mean tighter spacing
                    # Values less than -100 typically indicate word spacing
                    spacing_value = float(token[1])
                    if spacing_value < -100:  # Threshold for word spacing
                        array_text.append(' ')
            
            # Join this array's text without spaces between hex strings
            if array_text:
                combined_text = ''.join(array_text)
                if combined_text.strip():
                    extracted_text.append(combined_text)
        
        # Process hex + Tj patterns (single strings)
        hex_pattern = rb'<([0-9A-Fa-f]+)>\s*T[jJ]'
        for match in re.finditer(hex_pattern, stream):
            hex_str = match.group(1).decode('ascii')
            text = self._decode_hex_string(hex_str, char_map)
            if text and text.strip():
                extracted_text.append(text)
        
        # Process literal strings
        literal_pattern = rb'\(([^)]*)\)\s*T[jJ]'
        for match in re.finditer(literal_pattern, stream):
            text_bytes = match.group(1)
            text = text_bytes.decode('utf-8', errors='ignore')
            text = text.replace('\\(', '(').replace('\\)', ')').replace('\\\\', '\\')
            if text.strip():
                extracted_text.append(text)
        
        # Join with spaces between different text operations
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