import sys
from pathlib import Path

# Support running this script directly as well as importing it from the API.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import EXTRACTED_DATA_PATH, PATTERNS_PATH

from datetime import datetime, timezone
import json
import re

def repeated_text_analysis(file_path=EXTRACTED_DATA_PATH):
    with open(file_path, "r", encoding= "utf-8") as file:
        data = [json.loads(line) for line in file]
    
    mapper = {}
    for page in data:
        page_num = page["printed_page_number"]
        blocks = page["blocks"]
        for block in blocks:
            text = " ".join(block["text"].split())
            text = re.sub(r'\d+', '<N>', text)
            
            
            key = (
                text,
                block["x0"],
                block["y0"],
                block["x1"],
                block["y1"]
            )
            
            if key in mapper:
                mapper[key].add(page_num)

            else:
                mapper[key] = {page_num}

    for (text, x0, y0, x1, y1), pages in mapper.items():        
        if len(pages) >30:
            print(text, x0, y0, x1, y1, len(pages))

def header_footer_separation(top_fraction: float = 0.05, bottom_fraction: float = 0.05, *, file_path=EXTRACTED_DATA_PATH, output_path=PATTERNS_PATH):
    with open(file_path, "r", encoding= "utf-8") as file:
        data = [json.loads(line) for line in file]
        
    pattern_mapper = {}
    
    count = 0
    
    pages_without_any_chrome = []
    for page in data:
        
        top_cutoff = page["page_height"] * top_fraction
        bottom_cutoff = page["page_height"] * (1 - bottom_fraction)                
        hea_foo_flag = False
        for block in page["blocks"]:
            
            text = " ".join(block["text"].split())
            text = re.sub(r'\d+', '<N>', text)
            if (block["y1"] <= top_cutoff):
                
                key = (
                    "header",
                    text
                )
                hea_foo_flag = True
                if key in pattern_mapper:
                    pattern_mapper[key] +=1
                else:
                    pattern_mapper[key] = 1
                
                count+=1
                                
            if block["y0"] >= bottom_cutoff:
                # print(f'page number= {page["printed_page_number"]}')
                hea_foo_flag = True
                key = (
                    "footer",
                    text
                )
                count+=1
            
                if key in pattern_mapper:
                    pattern_mapper[key] +=1
                else:
                    pattern_mapper[key] = 1
        if not hea_foo_flag:
            pages_without_any_chrome.append(page["printed_page_number"])
        
    json_data = {
        "top_fraction": top_fraction,
        "bottom_fraction": bottom_fraction,
        "detected_at": datetime.now(timezone.utc).isoformat(),
        "sample_header_patterns": [],
        "sample_footer_patterns": [],
        "pages_without_any_chrome":pages_without_any_chrome
    }
        
    for key_m, value_m in pattern_mapper.items():
        if key_m[0] == "header":
            json_data["sample_header_patterns"].append({"text": key_m[1], "total_count": value_m})
        else:
            json_data["sample_footer_patterns"].append({"text": key_m[1], "total_count": value_m})
        
        
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding= "utf-8") as cp_file:
        json.dump(json_data, cp_file, ensure_ascii= False)
            
    print(count)

def main():
    header_footer_separation()
    
if __name__ == "__main__":
    main()