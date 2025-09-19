from . import analyzer, stream_handler, text_extractor, xref_handler, font_mapper, utils


class PDFParser:
    
    def __init__(self, pdf_bytes: bytes, debug):
        self.pdf_bytes = pdf_bytes
        self.objects = {}
        self.xref_table = {}
        self.debug = debug


    def parse(self) -> str:

        try:
            analysis = analyzer.analyze_pdf(self.pdf_bytes)
            print(f"PDF Analysis: {analysis}")

            xref_handler.parse_xref_table(self.pdf_bytes, self.xref_table)

            if analysis['has_object_streams']:
                print("Processing object streams...")
                stream_handler._handle_object_streams(self.pdf_bytes, self.xref_table)

            font_mappings = {}
            if analysis['has_tounicode'] or analysis['has_hex_text']:
                print("Extracting font mapings...")
                font_mappings = font_mapper._extract_font_mappings(self.pdf_bytes, self.xref_table)
                print(f"Found {len(font_mappings)} font mappings")
            
            streams = stream_handler._extract_all_streams(self.xref_table, self.pdf_bytes, self.objects)
            print(f"Found {len(streams)} content streams")

            seen_texts = set()
            all_text = []
            for i, stream in enumerate(streams):
                if i == 6:  # Debug stream 6 which has text
                    stream_handler.debug_stream_content(stream)
                if font_mappings or analysis['has_hex_text']:
                    print(f"Stream {i}: Using advanced extraction (has mappings: {len(font_mappings)})")
                    text = text_extractor._extract_text_from_stream_advanced(stream, font_mappings)
                else:
                    print(f"Stream {i}: Using basic extraction")
                    text = text_extractor._extract_text_from_stream(stream)

                if text and text.strip():
                    if text not in seen_texts:
                        seen_texts.add(text)
                        print(f"Stream {i}: extracted {len(text)} chars")
                        print(f"  Preview: {repr(text[:50])}")
                        all_text.append(text)
                    else:
                        print(f"Stream {i}: extracted {len(text)} chars (duplicate, skipping)")

            result = ' '.join(all_text)
            result = text_extractor._clean_extracted_text(result)

            print(f"Total extracted: {len(result)} characters")

            utils.find_font_resources(self.pdf_bytes)

            if result:
                print(f"Final preview: {repr(result[:100])}")
            return result

        except Exception as e:
            print(f"Error during parsing: {e}")
            import traceback
            traceback.print_exc()
            return ""