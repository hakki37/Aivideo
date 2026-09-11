# Aivideo

Free/open-source Islamic short video studio.

## Build

GitHub Actions builds a debug APK automatically on every push to `main`.

## Architecture

- Android: Jetpack Compose controller/editor
- Local AI server: Ollama + ComfyUI + Piper + Whisper + FFmpeg
- Media: Pexels/Pixabay and generated visuals
- Optional vision filtering for unwanted religious imagery
- No API keys committed to the repository

See `docs/ARCHITECTURE.md` for the planned stack and setup.
