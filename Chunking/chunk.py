import json
import os

CHUNK_SIZE = 700
OVERLAP_SIZE = 100
MIN_CHUNK_SIZE = 300

def chunk_text(txt: str) -> list:
    if OVERLAP_SIZE >= CHUNK_SIZE:
        raise ValueError("OVERLAP_SIZE must be smaller than CHUNK_SIZE")
    
    paragraphs = txt.split("\n\n")
    chunks = []
    curr_para_list = []
    curr_len = 0
    for paragraph in paragraphs:
        curr_len = para_append_process(paragraph, curr_para_list, curr_len, chunks)
    
    if curr_para_list:
        chunks.append("\n\n".join(curr_para_list))

    return chunks

def para_append_process(paragraph: str,curr_para_list: list, curr_len: int, chunks: list, pending_overlap: str = "") -> int:

    # If this is the first real paragraph of a new chunk,
    # prepend overlap directly to it.
    if not curr_para_list and pending_overlap:
        effective_para = pending_overlap + paragraph
    else:
        effective_para = paragraph

    separator_len = 2 if curr_para_list else 0

    # Case 1:
    # paragraph fits inside current chunk
    if (curr_len + separator_len + len(effective_para) <= CHUNK_SIZE):
        curr_para_list.append(effective_para)

        curr_len += (separator_len + len(effective_para))

        return curr_len

    # Case 2:
    # current chunk already contains real paragraphs
    if curr_para_list:
        completed_chunk = "\n\n".join(curr_para_list)

        chunks.append(completed_chunk)

        curr_para_list.clear()
        curr_len = 0

        pending_overlap = ""

        # Only carry overlap when it can fit together
        # with the next paragraph.
        if (
            len(completed_chunk) > MIN_CHUNK_SIZE
            and OVERLAP_SIZE + len(paragraph) <= CHUNK_SIZE
        ):
            pending_overlap = completed_chunk[-OVERLAP_SIZE:]

        # Retry the same paragraph with a fresh chunk
        return para_append_process(paragraph, curr_para_list, curr_len, chunks, pending_overlap)

    index = 0
    stride = CHUNK_SIZE - OVERLAP_SIZE

    while index + CHUNK_SIZE <= len(paragraph):
        chunk = paragraph[index:index + CHUNK_SIZE]

        chunks.append(chunk)

        index += stride

    # Remaining portion can combine with following paragraphs
    if index < len(paragraph):
        remaining = paragraph[index:]

        curr_para_list.append(remaining)
        curr_len = len(remaining)

    return curr_len

def chunk_process():
    temp_file = "temp_chunk.jsonl"
    dest_file = "chunk.jsonl"
    
    try: 
        with open("../Extract/pages.jsonl", "r", encoding= "utf-8") as file:
            data = [json.loads(line) for line in file]
        
        with open(temp_file, "w", encoding= "utf-8") as chunk_json_file:
            chunk_id = 0
            for page in data:
                page_cleaned_text = page["page_cleaned_text"]
                page_chunks = chunk_text(page_cleaned_text)
                
                
                for text in page_chunks:
                    chunk_id += 1
                    json_data = {
                        "doc_id": page["doc_id"],
                        "pg_number": page["printed_page_number"],
                        "chunk_id" : chunk_id,
                        "char_count": len(text),
                        "txt": text,
                        "section_text": page["section_text"]
                    }
                    json.dump(json_data, chunk_json_file, ensure_ascii= False)
                    chunk_json_file.write("\n")
        
        os.replace(temp_file, dest_file)
    except Exception as ex:
        print(f"Excetion raised during Chunking: {ex}")
        raise
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

def main():
    chunk_process()
    
if __name__ == "__main__":
    main()
    