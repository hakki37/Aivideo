# Local AI Server

This directory will contain the local FastAPI service used by the Android app.

Planned modules:

- `ollama_client.py` — Qwen/local LLM
- `comfyui_client.py` — image/video workflows
- `media_search.py` — Pexels/Pixabay/free media
- `vision_filter.py` — unwanted imagery filter
- `tts.py` — Piper
- `subtitles.py` — Whisper
- `renderer.py` — FFmpeg/Remotion
- `jobs.py` — generation queue and progress

The first milestone is a working health/providers API, followed by script generation and rendering.
