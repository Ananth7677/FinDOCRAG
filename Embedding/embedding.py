import json
import os
import shutil
import sys
from pathlib import Path
import time
from google.genai.errors import ClientError
from sqlalchemy import exc

# Allow direct execution to find config.py in the project root.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    
from DBO.Services.embedding_db_services import insert_embedding, get_lastest_embedding_record
from DTO.embedding_dto import EmbeddingDTO

from google import genai
from google.genai import types
from config import GEMINI_API_KEY, PROJECT_ROOT, CHUNKS_PATH, EMBEDDINGS_PATH


BATCH_SIZE = 50
client = genai.Client(api_key=GEMINI_API_KEY)

def create_embedding(contents):
    while True:
        try:
            result = client.models.embed_content(
                model="gemini-embedding-2",
                contents=contents,
                config={"output_dimensionality": 768},
            )

            return result.embeddings

        except ClientError as e:
            if e.code == 429:
                print(e.message)
                print("Rate limit hit. Waiting 60 seconds...")
                time.sleep(60)
            else:
                raise
            
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
    # embed_start_index = check_embedded_file(output_path)
    
    latest_embed_rec = get_lastest_embedding_record(data[0].get("doc_id"))
    if latest_embed_rec:
        embed_start_index = latest_embed_rec.chunk_metadata["chunk_id"]
    else:
        embed_start_index = 0
        
    for i in range (embed_start_index, len(data)):
        chunk_rec = data[i]
        content = types.Content(
            parts=[
                types.Part.from_text(text=f"section text:{chunk_rec['section_text'] or 'None'} | content: {chunk_rec['txt']}")
            ]
        )
        contents.append(content)
                
        if i != 0 and len(contents) % BATCH_SIZE == 0:
            embedding_result = create_embedding(contents)
            list_of_databaseids = store_embeddings_to_db(embedding_result, i-BATCH_SIZE+1, data)
            print(list_of_databaseids)
            contents.clear()
    
    if contents:
        embedding_result = create_embedding(contents)

        list_of_databaseids = store_embeddings_to_db(embedding_result, i+1-len(contents), data)
        print(list_of_databaseids)

def check_embedded_file(embedding_result_file_path: str)->int:
    with open(embedding_result_file_path, "r", encoding="utf-8") as file:
        data = [json.loads(line) for line in file]
    
    if data:
        return data[len(data)-1]["id"]
    return 0
    
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
                "doc_id": chunk_rec["doc_id"],
                "page_number": chunk_rec["pg_number"],
                "section_text": chunk_rec["section_text"],
                "text": chunk_rec["txt"],
                "embedding": embedding_vec.values
            }
            embedding_file.write(json.dumps(record) + "\n")
            start_index += 1
    
    append_temp_to_main(temp_file, dest_file)

def store_embeddings_to_db(embedding_result, start_index, chunk_records):
    try:
        database_ids = []
        for embedding_vec in embedding_result:
            chunk_rec = chunk_records[start_index]
            record = {
                "id": chunk_rec["chunk_id"],
                "doc_id": chunk_rec.get("doc_id"),
                "page_number": chunk_rec["pg_number"],
                "section_text": chunk_rec.get("section_text"),
                "text": chunk_rec["txt"],
                "embedding": embedding_vec.values,
            }
            
            dto = EmbeddingDTO.model_validate(record)
            database_ids.append(insert_embedding(dto))
            start_index += 1
        return database_ids
    except exc.SQLAlchemyError:
        raise
    
def append_temp_to_main(temp_file, dest_file):
    with open(dest_file, "a", encoding="utf-8") as main_file:
        with open(temp_file, "r", encoding="utf-8") as temp:
            shutil.copyfileobj(temp, main_file)

    os.remove(temp_file)
    
def move_data_from_json_to_database(embedding_res_path: str):
    db_ids = []
    try:
        with open(embedding_res_path, "r", encoding="utf-8") as file:
            for line in file:
                if not line.strip():
                    continue
                
                dto = EmbeddingDTO.model_validate_json(line)
                db_ids.append(insert_embedding(dto))
            
        return db_ids
    except Exception as ex:
        raise
        
if __name__ == "__main__":
    move_data_from_json_to_database("./results/embedding/embeddings.jsonl")
