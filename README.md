# AI-Powered Sites-Documentation ChatBot

A Chrome extension that lets you ask questions about any documentation website in natural language. It crawls the site, indexes it with embeddings, and uses AI to answer your questions with source citations.

## What It Does

1. **Crawl** — Automatically visit and scrape documentation pages using headless Playwright
2. **Embed & Index** — Split text into chunks, embed them using Google Gemini, store in ChromaDB
3. **Query** — Ask natural-language questions; retrieves relevant chunks and generates answers with sources

## Tech Stack

- **Backend:** FastAPI (Python), Playwright, BeautifulSoup, ChromaDB, Google Gemini API
- **Frontend:** Chrome Extension (Manifest V3), vanilla JS/HTML/CSS
- **Storage:** ChromaDB (persistent vector database)

---

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js (optional, for extension dev tools)
- Chrome browser
- Google Gemini API key

### Setup

#### 1. Backend Setup

```bash
cd docs-chat/backend

# Install dependencies
pip install fastapi uvicorn playwright beautifulsoup4 chromadb google-genai python-dotenv

# Download Playwright browsers
playwright install chromium

# Create .env file with your API key
echo GEMINI_API_KEY=your_api_key_here > .env

# Start the server
uvicorn main:app --reload --port 8000
```

Server runs on `http://localhost:8000`

#### 2. Load Extension in Chrome

1. Open Chrome and go to `chrome://extensions/`
2. Enable **Developer mode** (top-right toggle)
3. Click **Load unpacked**
4. Select the `docs-chat/extension/` folder
5. The extension icon should appear in your toolbar

#### 3. Use It

1. Navigate to any documentation site (e.g., `https://dummyjson.com/docs`)
2. Click the extension icon (or open the side panel via VS Code)
3. Click **"Index this site"** — takes 1–2 minutes to crawl and embed
4. Ask a question: *"How do I get all products?"*
5. Get an answer with source links

---

## How It Works (Flow)

### 1. Indexing Flow

```
User clicks "Index this site"
    ↓
Extension calls POST /crawl with current URL
    ↓
Backend crawler starts:
  - Visits pages recursively (Playwright)
  - Extracts text with BeautifulSoup
  - Skips nav/footer/script tags
  - Filters out login, blog, pricing pages
    ↓
Returns list of pages: [{url, title, content}, ...]
    ↓
Backend chunks each page (300-word chunks, 30-word overlap)
    ↓
For each chunk:
  - Embed text using Gemini embedding API
  - Store in ChromaDB with metadata (url, title)
    ↓
Extension shows "✅ Indexed 26 pages"
```

### 2. Query Flow

```
User types question + clicks Send
    ↓
Extension calls POST /query with question
    ↓
Backend retrieves:
  - Embed question using Gemini
  - Find top-5 similar chunks from ChromaDB
    ↓
Generate answer:
  - Build prompt with chunks + question
  - Call Gemini to generate response
    ↓
Return answer + source URLs to extension
    ↓
Extension displays answer with clickable sources
```

### 3. Session Flow

```
User closes extension popup
    ↓
unload event fires
    ↓
Extension calls POST /clear
    ↓
Backend deletes ChromaDB collection
    ↓
Next session starts fresh (must re-index)
```
![screenshot of demo](<docs-chat/demoimages/Screenshot 2026-04-25 133504.png>)

![screenshot of demo](<docs-chat/demoimages/Screenshot 2026-04-25 133504.png>)

video: https://drive.google.com/file/d/1-iu47nPgzx6xntlYvxPztBytT6MR_F77/view?usp=sharing

---

## File Structure

```
docs-chat/
├── backend/
│   ├── main.py           # FastAPI server (crawl, query, clear endpoints)
│   ├── crawler.py        # Playwright crawler + link extraction
│   ├── vectorstore.py    # Embedding, chunking, ChromaDB storage
│   ├── chroma_db/        # Persistent vector database
│   └── requirements.txt   # Python dependencies
│
├── extension/
│   ├── manifest.json     # Permissions, background script, side panel
│   ├── popup.html        # Chat UI (side panel)
│   ├── popup.js          # Event handlers, API calls
│   ├── background.js     # Service worker (minimal)
│   └── content.js        # Content script (minimal)
```

---

## API Endpoints

### `POST /crawl`
Index a documentation site.

```bash
curl -X POST http://localhost:8000/crawl \
  -H "Content-Type: application/json" \
  -d '{"url": "https://dummyjson.com/docs"}'

# Response: {"status": "done", "pages_indexed": 26}
```

### `POST /query`
Ask a question about indexed docs.

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "How do I get all products?"}'

# Response:
# {
#   "answer": "The fetch endpoint...",
#   "sources": [
#     {"url": "https://dummyjson.com/docs/products", "title": "Products"}
#   ]
# }
```

### `POST /clear`
Delete all indexed data.

```bash
curl -X POST http://localhost:8000/clear
# Response: {"status": "cleared"}
```

### `GET /is-indexed`
Check if a hostname is already indexed.

```bash
curl "http://localhost:8000/is-indexed?hostname=dummyjson.com"
# Response: {"indexed": true}
```

---

## Customization

### Increase Chunks per Page

If the assistant misses code examples, edit `vectorstore.py` line 45:

```python
# Change from:
for i, chunk in enumerate(chunks[:3]):

# To:
for i, chunk in enumerate(chunks):  # index all chunks (no limit)
```

### Adjust Chunk Size

In `vectorstore.py`, modify the chunking parameters:

```python
chunks = chunk_text(page["content"], chunk_size=500, overlap=50)
# Larger chunks = fewer but more context; smaller = more but less context each
```

### Skip Different URL Patterns

In `crawler.py`, edit `SKIP_PATTERNS`:

```python
SKIP_PATTERNS = [
    "/blog/", "/changelog/", "/pricing",
    # Add more patterns to skip
]
```

---

## Known Limitations

- **Session memory:** ChromaDB clears when popup closes (designed for privacy, not persistence)
- **API costs:** Gemini embedding & generation APIs have usage limits on free tier
- **Crawl time:** Large documentation sites (100+ pages) take 3–5 minutes
- **No authentication:** Backend has no API key validation (self-hosted only)
- **Windows async workaround:** Uses ProactorEventLoop on Windows due to asyncio limitations

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| "Cannot find chromium" | Run `playwright install chromium` |
| "GEMINI_API_KEY not set" | Create `.env` file with `GEMINI_API_KEY=your_key` |
| "Backend not responding" | Check server is running: `http://localhost:8000/docs` |
| "Assistant says 'not found'" | Try increasing chunks per page (see Customization) |
| "Port 8000 already in use" | Use different port: `uvicorn main:app --port 8001` |

---

## Next Steps

- [ ] Add persistent storage option (toggle to keep DB between sessions)
- [ ] Support multiple concurrent users with per-user vector stores
- [ ] Add authentication layer for production
- [ ] Deploy to cloud (Render, Cloud Run, Fly.io)
- [ ] Build admin dashboard to manage indexed sites
- [ ] Add support for authenticating crawls (login to restricted docs)
