import sys
from pathlib import Path

# Support running this script directly as well as importing it from the API.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import PROJECT_ROOT, EXTRACT_DIR, CLEAN_DIR, EXTRACTED_DATA_PATH, PATTERNS_PATH

from datetime import datetime, timezone
import os
import re
import unicodedata
import pymupdf
import json
import hashlib

def extract_data(start_printed_page_num:int, end_printed_page_num:int, page_offset:int = -1, file_path = PROJECT_ROOT / "AnnualReports/Mastercard/Report.pdf", *, output_dir=EXTRACT_DIR):
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    start_page_index = start_printed_page_num + page_offset
    end_page_index = end_printed_page_num + page_offset
    print(file_path)
    
    if not check_file_exists(file_path):
        raise FileNotFoundError(f"file doesn't exist at the given path {file_path}")
        
    with pymupdf.open(file_path) as pdf_text:
        
        temp_file = Path(output_dir) / "temp_extracted_data.jsonl"
        dest_file = Path(output_dir) / "extracted_data.jsonl"
        
        if not validate_page_number_range(start_page_index, end_page_index, 0, len(pdf_text)-1):
            print("Enter valid page number range")
            raise ValueError("Enter valid page number range")

        try:
            
            with open(temp_file, "w", encoding= "utf-8") as file:
            
                for pagenum in range (start_page_index, end_page_index+1):
                    
                    page = pdf_text[pagenum]
                    
                    blocks = []
                    for block in page.get_text("blocks"):
                        x0, y0, x1, y1, text, block_number, block_type = block
                        
                        current_block = {
                            "x0" : x0,
                            "y0" : y0,
                            "x1" : x1,
                            "y1" : y1,
                            "text" : text,
                            "block_number" : block_number,
                            "block_type" : block_type
                        }
                        
                        blocks.append(current_block)
                    
                    is_text = True
                    page_raw_text = page.get_text()
                    if not page_raw_text or page_raw_text.isspace():
                        is_text = False               
                    
                    section_text = section_harvesting(blocks, page_height= page.rect.height)
                    data = {
                        "doc_id": Path(file_path).name,
                        "char_count": len(page_raw_text),
                        "printed_page_number" : pagenum-page_offset,
                        "page_width" : page.rect.width,
                        "page_height": page.rect.height,
                        "section_text": section_text,
                        "is_text": is_text,
                        "flags": [],
                        "page_raw_text": page_raw_text,
                        "blocks": blocks
                    }

                    json.dump(data, file, ensure_ascii= False)
                    file.write("\n")
                    
            os.replace(temp_file, dest_file)
            add_metadata(file_path, end_page_index-start_page_index+1, len(pdf_text), Path(file_path).name, page_offset, start_printed_page_num, end_printed_page_num, output_dir=output_dir)
            
        except Exception as ex:
            print(f"exception raised during extraction: {ex}")
            raise
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)
            

def add_metadata(file_path: str, no_of_pages_extracted: int, no_of_pages: int,  doc_name: str, page_offset: int, start_printed_page_num:int, end_printed_page_num:int, *, output_dir=EXTRACT_DIR):
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    h = hashlib.sha256(Path(file_path).read_bytes()).hexdigest()
    
    temp_file = Path(output_dir) / "temp_metadata.json"
    dest_file = Path(output_dir) / "metadata.json"
    try:
        data = {
            "document_name": doc_name,
            "page_offset": page_offset,
            "numbering_convention": "printed",
            "printed_page_range":[start_printed_page_num, end_printed_page_num],
            "doc_identification_id": h,
            "file_path": file_path,
            "number_of_pages": no_of_pages,
            "number_of_pages_extracted": no_of_pages_extracted,
            "date_created": datetime.now(timezone.utc).isoformat(),
            "pymupdf_version": pymupdf.__version__
        }
        
        with open(temp_file, "w", encoding= "utf-8") as file:
            json.dump(data, file, ensure_ascii= False)
        
        os.replace(temp_file, dest_file)
        
    except Exception as e:
        print(f"An exception was raised during addition of meta data: {e}")
        raise
        
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

def validate_page_number_range(given_start_page_index: int, given_end_page_index:int, doc_start_page_index: int, doc_end_page_index:int)->bool:
    if given_start_page_index > given_end_page_index or given_start_page_index < doc_start_page_index or given_end_page_index > doc_end_page_index:
        return False
    return True

def section_harvesting(blocks: list, page_height: float, top_fraction: float = 0.05) -> str:
    top_cutoff = page_height * top_fraction
    text = ""
    for block in blocks:
        if block["y1"] <= top_cutoff:
            text = " ".join(block["text"].split())
            break
    if text:
        return text
    return None

def clean_raw_text(file_path=EXTRACTED_DATA_PATH, *, patterns_path=PATTERNS_PATH, output_dir=CLEAN_DIR):
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    with open(file_path, "r", encoding= "utf-8") as file:
        data = [json.loads(line) for line in file]
    
    with open(patterns_path, "r", encoding= "utf-8") as ch_file:
        chrome_data = json.load(ch_file)
    
    remove_texts = set()
    for footer in chrome_data["sample_footer_patterns"]:
        foo_txt = footer["text"]
        if not foo_txt:
            continue
        
        remove_texts.add(build_pattern(foo_txt))
    
    for header in chrome_data["sample_header_patterns"]:
        hea_txt = header["text"]
        if not hea_txt:
            continue
        
        remove_texts.add(build_pattern(hea_txt))
    
    combined_pattern = "|".join(remove_texts)
    
    temp_file_path = Path(output_dir) / "temp_data.jsonl"
    dest_file_path = Path(output_dir) / "pages.jsonl"
    with open(temp_file_path, "w", encoding="utf-8") as temp_file:
        for page in data:
            cleaned_blocks = []
            
            for block in page["blocks"]:
                if block["block_type"] != 0:
                    continue
                
                block_text = block["text"]
                
                if not block_text or block_text.isspace():
                    continue
                
                block_text = normalize_unicode(block_text)
                block_text = normalize_block_whitespace(block_text)
                
                if combined_pattern:
                    block_text = re.sub(combined_pattern, "", block_text)
                
                block_text = normalize_block_whitespace(block_text)
                
                if block_text:
                    cleaned_blocks.append(block_text)
                    
            cleaned_text = "\n\n".join(cleaned_blocks)
                    
            json_data = {
                "doc_id": page["doc_id"],
                "char_count": len(page["page_raw_text"]),
                "printed_page_number" : page["printed_page_number"],
                "page_width" : page["page_width"],
                "page_height": page["page_height"],
                "section_text": page["section_text"],
                "is_text": page["is_text"],
                "flags": [],
                "page_cleaned_text": cleaned_text,
                "blocks": page["blocks"]
            }
            json.dump(json_data, temp_file, ensure_ascii= False)
            temp_file.write("\n")
    
    os.replace(temp_file_path, dest_file_path)

def normalize_block_whitespace(text):
    return " ".join(text.split())
    
def normalize_unicode(text):
    # Converts ligatures like ﬁ -> fi, ﬂ -> fl
    text = unicodedata.normalize("NFKC", text)

    # Normalize quotes and dashes
    replacements = {
        "\u2018": "'",   # ‘
        "\u2019": "'",   # ’
        "\u201c": '"',   # “
        "\u201d": '"',   # ”
        "\u2013": "-",   # –
        "\u2014": "-",   # —
        "\u2212": "-",   # −
        "\u00a0": " ",   # non-breaking space
    }

    return text.translate(str.maketrans(replacements))

def build_pattern(text):
    tokens = text.split()

    escaped_tokens = [
        re.escape(token)
        for token in tokens
    ]

    pattern = r"\s+".join(escaped_tokens)

    pattern = pattern.replace(r"<N>", r"\d+")

    return pattern

def check_file_exists(file_path:str)->bool:
    return Path(file_path).is_file()
    
def main():
    # extract_data(1, 132)
    clean_raw_text()
    
if __name__ == "__main__":
    main()