# Wardrobe-AI — Your Playful Personal Stylist

Welcome to Wardrobe-AI — half-closet alchemist, half-nerdy recommender. Toss in photos of your clothes, and it will help you craft outfits that actually make your morning decision shorter and your Instagram slightly more enviable. It's a work-in-progress lab for outfit magic: images go into storage, become searchable vectors, and are used to provide you style suggestions - create your daily outfits with the clothes you own!

## Why this exists

- Cut decision fatigue: get daily outfit suggestions from items you already own.
- Discover hidden matches: the system surfaces pairings you wouldn't have noticed.
- Plug-and-play: modular pieces so you can swap models, storage, or the UI.

## Purpose of key files
- `gemini.py`: LLM helper functions (prompts, calls, parsing).
- `s3_utils.py`: S3 helpers — upload/download, presigned URLs, and stream uploads.
- `clothing_pipeline.py`: Image preprocessing and embedding extraction.
- `vectordb.py`: Store and query embeddings; nearest-neighbor search for recommendations.