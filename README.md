# Wardrobe-AI — Your Playful Personal Stylist

Welcome to Wardrobe-AI — half-closet alchemist, half-nerdy recommender. Toss in photos of your clothes, and it will help you craft outfits that actually make your morning decision shorter and your Instagram slightly more enviable. It's a work-in-progress lab for outfit magic: images go into storage, become searchable vectors, and are used to provide you style suggestions - create your daily outfits with the clothes you own!

**Wardrobe-AI now features a full-stack application with a FastAPI backend and Angular frontend UI** to manage your digital wardrobe.

## Features

- **Smart Clothing Recognition**: Automatically extracts detailed fashion metadata (color, pattern, material, season, style) from images using Google Gemini AI
- **Vector-based Recommendations**: Uses embeddings to find similar items and suggest complementary outfit pairings
- **Cloud Storage**: Integrates with AWS S3 for scalable image storage and retrieval
- **Modern Web Interface**: Angular-based UI for browsing, uploading, and managing your wardrobe
- **RESTful API**: FastAPI backend with comprehensive endpoints for all wardrobe operations

## Why this exists

- **Cut decision fatigue**: Get daily outfit suggestions from items you already own
- **Discover hidden matches**: The system surfaces pairings you wouldn't have noticed
- **Plug-and-play architecture**: Modular components so you can swap models, storage, or the UI as needed

## Project Structure

### Backend (Python/FastAPI)
- `app.py`: FastAPI server with REST API endpoints and CORS middleware
- `clothing_pipeline.py`: Image preprocessing and embedding extraction
- `gemini.py`: LLM helper functions for clothing identification and parsing
- `s3_utils.py`: AWS S3 integration for image storage and retrieval
- `vectordb.py`: Vector database for storing embeddings and semantic search
- `config.py`: Configuration for AI models and clothing metadata schemas

### Frontend (Angular)
- `web/src/app/app.component.ts`: Main application component
- `web/src/app/pages/wardrobe/`: Wardrobe management interface
- `web/src/app/pages/welcome/`: Welcome/onboarding page
- `web/src/app/components/navbar/`: Navigation component
- `web/src/app/services/wardrobe.service.ts`: API communication service

## Tech Stack

**Backend**:
- FastAPI (web framework)
- Google Generative AI (Gemini for clothing analysis)
- Sentence Transformers (embeddings)
- Qdrant/ChromaDB (vector databases)
- boto3 (AWS S3 integration)

**Frontend**:
- Angular (web framework)
- TypeScript

**Infrastructure**:
- AWS S3 (image storage)
