# Architecture

## Goal
Build a free-first Android Islamic Shorts studio. The Android app is the control panel; heavy AI/rendering runs on the user's PC when available.

## Free-first providers

| Capability | Provider | Role |
|---|---|---|
| Script / quote | Ollama + Qwen | Local text generation |
| Image generation/editing | ComfyUI | Local workflows; modular model support |
| Video generation | ComfyUI workflows (Wan/LTX/Hunyuan where hardware permits) | Optional AI motion clips |
| Voice | Piper | Offline TTS |
| Subtitles | Whisper | Local transcription |
| Music | Local files / free licensed sources | Background audio |
| Stock media | Pexels / Pixabay / Wikimedia / Archive.org | Fallback visuals |
| Vision safety filter | CLIP / local vision model | Reject crosses/church imagery when requested |
| Render | FFmpeg | Final 9:16 MP4 |
| Optional advanced editing | Remotion | Timeline-style composition on server |
| Upscale | Real-ESRGAN / SwinIR | Optional enhancement |

## Android screens

1. Home / New Video
2. Presets: Hadis, Ayet, Dua, Islamic quote, Hayırlı Cumalar
3. Visual source: Stock / AI / Mixed
4. Voice: Off / Piper voice
5. Music and volume
6. Duration and 9:16 output
7. Generate / progress
8. Preview / save / share
9. History
10. Local server settings

## Server API (planned)

- `GET /health`
- `GET /providers`
- `POST /generate/script`
- `POST /generate/assets`
- `POST /render`
- `GET /jobs/{id}`
- `GET /jobs/{id}/result`

## Hardware strategy

The RX 5600 XT is treated as a constrained local GPU. The app must not require every AI model to be installed. Providers are modular, with graceful fallback to stock footage and CPU-compatible components.

## Security

- Never commit Pexels/Pixabay/API keys.
- Keep secrets in local environment/config files.
- Local server URL is configurable in Android settings.
