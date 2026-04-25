import chromadb
from google import genai
from google.genai import types
import os
import time
from dotenv import load_dotenv

load_dotenv()
client_genai = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

client = chromadb.PersistentClient(path="./chroma_db")

def get_collection(name: str = "docs"):
    return client.get_or_create_collection(name=name)

def embed_text(text: str, retries: int = 3) -> list[float]:
    """Embed a document chunk with retry on rate limit."""
    for attempt in range(retries):
        try:
            response = client_genai.models.embed_content(
                model="gemini-embedding-001",
                contents=text,
                config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")
            )
            return response.embeddings[0].values
        except Exception as e:
            if attempt < retries - 1:
                wait = 5 * (attempt + 1)  # wait 5s, then 10s
                print(f"Embedding failed, retrying in {wait}s... ({e})")
                time.sleep(wait)
            else:
                raise

def chunk_text(text: str, chunk_size: int = 300, overlap: int = 30) -> list[str]:
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        if chunk:
            chunks.append(chunk)
    return chunks

def index_pages(pages: list[dict]):
    """Chunk, embed, and store pages in Chroma."""
    collection = get_collection()
    total = 0
    for page in pages:
        chunks = chunk_text(page["content"])
        print(f"Total chunks for {page['url']}: {len(chunks)}")
        for i, chunk in enumerate(chunks[:3]):
            embedding = embed_text(chunk)
            doc_id = f"{page['url']}_{i}"
            collection.upsert(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[chunk],
                metadatas=[{"url": page["url"], "title": page["title"]}]
            )
            total += 1
            time.sleep(1.5)  # increased from 0.5 to 1.5 for free tier safety
            print(f"Indexed chunk {total}: {page['url']} [{i}]")
    print("Indexing complete.")

def retrieve(query: str, top_k: int = 7) -> list[dict]:
    collection = get_collection()
    query_embedding = client_genai.models.embed_content(
        model="gemini-embedding-001",
        contents=query,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY")
    ).embeddings[0].values

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas"]
    )

    output = []
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        output.append({"content": doc, "url": meta["url"], "title": meta["title"]})
    return output