# Fit Check AI

Fit Check AI turns your physical closet into a searchable, intelligent wardrobe. Snap a photo of any clothing item and Gemini automatically tags it with category, color, material, occasion, and more. From there, search what you own in plain English, or chat with an AI agent that knows your wardrobe and current trends to help you put together outfits — no more staring at a full closet with nothing to wear.

## Features

- **AI Clothing Recognition** — Gemini extracts rich metadata from photos: category, color, pattern, material, season, occasion, fit, and style vibe
- **Semantic Search** — Natural language queries run through a 3-step pipeline: filter extraction → vector search → AI re-ranking
- **Conversational Agent** — LangGraph ReAct agent that can search your wardrobe and look up fashion trends to answer style questions
- **Outfit Builder** — Drag-and-drop canvas to compose outfits, get AI feedback, and save them to your collection
- **Cloud Storage** — Images stored in AWS S3; embeddings in Qdrant

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, FastAPI |
| AI / LLM | Google Gemini (`gemini-2.0-flash`) |
| Embeddings | Sentence Transformers (`all-MiniLM-L6-v2`) |
| Vector DB | Qdrant Cloud |
| Agent Framework | LangChain + LangGraph |
| Image Storage | AWS S3 |
| Frontend | Angular 17 (standalone components) |

## Project Structure

```
Wardrobe-AI/
├── server/
│   ├── app.py                  # FastAPI app & all REST endpoints
│   ├── clothing_pipeline.py    # Upload pipeline: MIME check → Gemini → S3 → Qdrant
│   ├── gemini.py               # Gemini API client wrapper
│   ├── vectordb.py             # Qdrant operations (add, search, update, delete)
│   ├── s3_utils.py             # S3 upload/download helpers
│   ├── config.py               # Prompts, model names, schemas, enums
│   ├── requirements.txt
│   └── agent/
│       ├── agent.py            # LangGraph ReAct agent + response post-processor
│       └── tools.py            # Wardrobe search tool, DuckDuckGo trend research tool
└── web/
    └── src/app/
        ├── pages/
        │   ├── wardrobe/       # Browse, upload, search, edit clothing items
        │   ├── chat/           # Conversational agent UI
        │   ├── outfit-dump/    # Outfit builder canvas
        │   └── welcome/        # Landing page
        └── services/
            ├── wardrobe.service.ts
            └── chat.service.ts
```

## API Overview

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/wardrobe/items` | List all wardrobe items |
| `POST` | `/wardrobe/upload` | Upload a clothing image |
| `GET` | `/wardrobe/search?query=` | Semantic search |
| `PATCH` | `/wardrobe/item/{id}` | Update an item field |
| `DELETE` | `/wardrobe/item/{id}` | Delete an item |
| `POST` | `/wardrobe/outfit-feedback` | Get AI feedback on an outfit |
| `POST` | `/wardrobe/outfit-save` | Save an outfit |
| `GET` | `/wardrobe/outfits` | List saved outfits |
| `DELETE` | `/wardrobe/outfit-delete/{id}` | Delete a saved outfit |
| `POST` | `/wardrobe/agent` | Chat with the wardrobe agent |
