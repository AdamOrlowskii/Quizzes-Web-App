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


    def parse(self) -> str:

        self._parse_xref_table()

        streams = self._extract_all_streams()

        all_text = []

        for stream in streams:
            text = self._extract_text_from_stream(stream)
            if text:
                all_text.append(text)

        return '\n'.join(all_text)
    

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