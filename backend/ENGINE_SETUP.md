# Aivideo Local Engine

## Free/local engine stack

- **Brain:** Ollama + Qwen3 (`OLLAMA_MODEL`)
- **Visual fallback:** Pexels API (portrait stock footage)
- **Optional visual engines:** ComfyUI, Wan/LTX
- **Optional audio:** ACE-Step, Piper
- **Optional subtitles:** Whisper
- **Render:** FFmpeg
- **Publisher:** YouTube Data API

The engine is intentionally modular: missing optional AI models do not prevent the stock-footage pipeline from working.

## Windows

1. Install FFmpeg and make sure `ffmpeg` works in a terminal.
2. Make sure Ollama is running and `qwen3:8b` is available.
3. Put the Pexels key in a local `.env` file as `PEXELS_API_KEY=...`.
4. Put the Google OAuth desktop client JSON at `backend/client_secret.json` when YouTube upload is needed.
5. Run `start_windows.bat`.

Never commit `.env`, `client_secret.json`, or `token.json`.

## API

- `GET /health` — engine health
- `GET /engines` — active engine map
- `POST /generate` — generate a 9:16 1080x1920 short using Qwen3 + Pexels + FFmpeg
- `GET /video/latest` — latest rendered MP4
- `POST /youtube/auth` — start Google OAuth
- `GET /youtube/status` — YouTube connection status
- `POST /youtube/upload` — upload an MP4 with title/description/tags/privacy
