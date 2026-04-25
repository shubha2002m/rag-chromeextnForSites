import sys
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor
from crawler import crawl_in_thread
from vectorstore import index_pages, retrieve

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

app = FastAPI()
executor = ThreadPoolExecutor(max_workers=2)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class CrawlRequest(BaseModel):
    url: str

class QueryRequest(BaseModel):
    question: str

@app.post("/crawl")
async def crawl(req: CrawlRequest):
    import asyncio
    loop = asyncio.get_event_loop()
    # Run crawler in a thread with its own event loop (Windows fix)
    pages = await loop.run_in_executor(
        executor,
        crawl_in_thread,
        req.url,
        30
    )
    index_pages(pages)
    return {"status": "done", "pages_indexed": len(pages)}

@app.post("/clear")
async def clear():
    """Delete all indexed data from Chroma."""
    try:
        client.delete_collection("docs")
        return {"status": "cleared"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

@app.get("/is-indexed")
async def is_indexed(hostname: str):
    """Check if a hostname has already been indexed in Chroma."""
    try:
        collection = client.get_or_create_collection("docs")
        results = collection.get(where={"url": {"$contains": hostname}}, limit=1)
        return {"indexed": len(results["ids"]) > 0}
    except Exception:
        return {"indexed": False}

@app.post("/query")
async def query(req: QueryRequest):
    chunks = retrieve(req.question, top_k=5)

    context = "\n\n---\n\n".join([
        f"Source: {c['url']}\n{c['content']}" for c in chunks
    ])

    prompt = f"""You are a helpful assistant that ONLY answers using the documentation provided below.
If the answer is not in the docs, say "I couldn't find that in the docs."

Documentation:
{context}

Question: {req.question}

Answer:"""

    response = client.models.generate_content(
        model="gemini-flash-latest",
        contents=prompt,
    )

    sources = list({c["url"]: c["title"] for c in chunks}.items())

    return {
        "answer": response.text,
        "sources": [{"url": url, "title": title} for url, title in sources]
    }