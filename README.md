# Traffic Law QA System 🚗

A chatbot system that answers questions about traffic laws using RAG (Retrieval-Augmented Generation) with AI.

## 📋 Requirements

- Python 3.9+
- Node.js 18+ & pnpm
- Qdrant Vector Database
- OpenAI API key

## 🚀 Quick Start Guide

### 1. Prepare Data

```bash
# Navigate to law-crawler directory
cd law-crawler

# Install dependencies
pip install pypdf pandas

# Crawl data from PDF (place PDF files in data/ folder)
python crawl_pdf.py

# Output: output/traffic_laws.json
```

### 2. Setup Vector Database (Qdrant)

**Option A: Using Docker**
```bash
docker run -p 6335:6335 qdrant/qdrant
```

**Option B: Standalone**
- Download from: https://qdrant.tech/

### 3. Create .env File

Create `.env` file in the root directory:
```env
OPENAI_API_KEY=your_openai_api_key
PORT=5000
QDRANT_URL=http://localhost:6335
QDRANT_API_KEY=
OPENAI_MODEL=gpt-4-mini
RERANKER_MODEL=gpt-4-mini
```

### 4. Setup Backend

```bash
# Install dependencies
pip install -r requirements.txt

# Run script to create vector embeddings
cd vectorDB
python main.py  # Load traffic_laws.json data into Qdrant

cd ../backend

# Start API server
python app.py
# Server running on: http://localhost:5000
```

### 5. Setup Frontend

```bash
cd frontend

# Install dependencies
pnpm install

# Run development server
pnpm dev
# Frontend running on: http://localhost:3000
```

### 6. Usage

- Open browser: http://localhost:3000
- Enter questions about traffic laws
- Chatbot will answer based on legal data

## 📁 Project Structure

```
traffic-law-qa-system/
├── backend/              # FastAPI server
│   ├── app.py           # Main application
│   └── src/
│       ├── routers/     # Chat & health endpoints
│       ├── services/    # RAG, LLM, Vector DB services
│       └── schemas/     # Data models
├── frontend/            # Next.js UI
│   └── src/
│       ├── app/         # Pages
│       └── components/  # UI components
├── law-crawler/         # PDF data extraction
│   └── output/          # traffic_laws.json
├── vectorDB/            # Embedding generation
│   └── main.py
└── requirements.txt     # Python dependencies
```

## 🔑 API Endpoints

- `GET /health` - Server health check
- `POST /api/agent/chat` - Send question to chatbot

## 📝 Important Notes

- Ensure Qdrant is running before starting the backend
- Valid OPENAI_API_KEY is required
- Data is embedded using: `jinaai/jina-embeddings-v3`

## 🔧 Troubleshooting

**Qdrant Connection Error:**
```bash
# Check if Qdrant is running on port 6335
curl http://localhost:6335/health
```

**API Key Error:**
- Verify OPENAI_API_KEY in .env file

**Frontend Cannot Connect to Backend:**
- Check CORS configuration in backend/app.py
