import json
import os
import shutil
import sys
from pathlib import Path

# Allow direct execution to find config.py in the project root.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from google import genai
from google.genai import types
from config import GEMINI_API_KEY, PROJECT_ROOT, CHUNKS_PATH, EMBEDDINGS_PATH


BATCH_SIZE = 50
client = genai.Client(api_key=GEMINI_API_KEY)

def create_embedding(contents):        
    
    result = client.models.embed_content(
            model="gemini-embedding-2",
            contents= contents
    )

    return result.embeddings

def process_embedding(file_path=None, *, output_path=None):
    file_path = Path(file_path) if file_path is not None else CHUNKS_PATH
    output_path = Path(output_path) if output_path is not None else EMBEDDINGS_PATH
    if not file_path.is_absolute():
        file_path = PROJECT_ROOT / file_path
    if not output_path.is_absolute():
        output_path = PROJECT_ROOT / output_path
    with open(file_path, "r", encoding= "utf-8") as file:
        data = [json.loads(line) for line in file]
    
    if not data:
        raise ValueError("No chunk data present")
    contents = []
    for i, chunk_rec in enumerate(data):
        content = types.Content(
            parts=[
                types.Part.from_text(text=f"section text:{chunk_rec['section_text'] or 'None'} | content: {chunk_rec['txt']}")
            ]
        )
        contents.append(content)
                
        if i != 0 and len(contents) % BATCH_SIZE == 0:
            embedding_result = create_embedding(contents)
            store_embeddings(embedding_result, i-BATCH_SIZE+1, data, output_path=output_path)
            contents.clear()
    
    if contents:
        embedding_result = create_embedding(contents)

        store_embeddings(embedding_result, i-len(contents), data, output_path=output_path)

def store_embeddings(embedding_result, start_index, data, *, output_path=None):
    dest_file = Path(output_path) if output_path is not None else EMBEDDINGS_PATH
    if not dest_file.is_absolute():
        dest_file = PROJECT_ROOT / dest_file
    dest_file.parent.mkdir(parents=True, exist_ok=True)
    temp_file = dest_file.parent / "temp.jsonl"
    with open(temp_file, "w", encoding="utf-8") as embedding_file:
        for embedding_vec in embedding_result:
            chunk_rec = data[start_index]
            record = {
                "id" : chunk_rec["chunk_id"],
                "page_number": chunk_rec["pg_number"],
                "section_text": chunk_rec["section_text"],
                "text": chunk_rec["txt"],
                "embedding": embedding_vec.values
            }
            embedding_file.write(json.dumps(record) + "\n")
            start_index += 1
    
    append_temp_to_main(temp_file, dest_file)
            
def append_temp_to_main(temp_file, dest_file):
    with open(dest_file, "a", encoding="utf-8") as main_file:
        with open(temp_file, "r", encoding="utf-8") as temp:
            shutil.copyfileobj(temp, main_file)

    os.remove(temp_file)

if __name__ == "__main__":
    process_embedding()    
