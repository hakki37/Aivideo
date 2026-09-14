from __future__ import annotations

import asyncio
import tempfile
import traceback
from pathlib import Path
from threading import Thread

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from engine import generate_video
from story_engine import generate_story_video
from youtube_uploader import authenticate, upload_video, youtube_status

app = FastAPI(title="Aivideo Local Engine", version="0.6.1")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])
oauth_running = False
oauth_error: str | None = None

def _oauth_worker() -> None:
    global oauth_running, oauth_error
    try:
        authenticate(); oauth_error = None
    except Exception as exc:  # noqa: BLE001
        oauth_error = str(exc)
    finally:
        oauth_running = False

@app.get("/health")
def health() -> dict:
    return {"ok": True, "service": "aivideo-local-engine", "version": "0.6.1"}

@app.get("/engines")
def engines() -> dict:
    return {"brain": {"provider": "Ollama", "model": "Qwen3", "local": True}, "visual": {"active": ["Pexels multi-scene"], "optional": ["ComfyUI", "Wan", "LTX-Video"], "safety_filter": "blocked visual metadata"}, "audio": {"active": ["local music file"], "optional": ["ACE-Step", "Piper", "Windows SAPI via pyttsx3"]}, "subtitles": {"active": "styled quote overlay", "optional": "Whisper"}, "render": ["FFmpeg Shorts 1080x1920", "FFmpeg Stories 1920x1080"], "publisher": "YouTube Data API", "watermark": {"active": "Mana", "default": True, "position": "bottom-right"}, "story": {"active": True, "durations_minutes": [15, 20], "format": "16:9", "narration": "local TTS when available"}, "fallbacks": True}

@app.get("/youtube/status")
def youtube_connection_status() -> dict:
    if oauth_running: return {"connected": False, "authorizing": True, "error": oauth_error}
    try: return {**youtube_status(), "authorizing": False, "error": oauth_error}
    except Exception as exc: return {"connected": False, "authorizing": False, "error": str(exc)}

@app.post("/youtube/auth")
def youtube_auth() -> dict:
    global oauth_running, oauth_error
    if oauth_running: return {"started": True, "authorizing": True}
    oauth_error = None; oauth_running = True
    Thread(target=_oauth_worker, daemon=True, name="youtube-oauth").start()
    return {"started": True, "authorizing": True, "message": "Google OAuth tarayıcıda açılacak."}

@app.post("/generate")
async def generate(topic: str = Form(""), template: str = Form("Hayırlı Cumalar"), duration: int = Form(30), music_enabled: bool = Form(True), watermark_enabled: bool = Form(True)) -> dict:
    if duration not in {15, 30, 60}: raise HTTPException(status_code=400, detail="Süre 15, 30 veya 60 saniye olmalı.")
    try: return await asyncio.to_thread(generate_video, topic, template, duration, music_enabled, watermark_enabled)
    except Exception as exc:
        print("\n===== AIVIDEO GENERATION ERROR =====", flush=True); traceback.print_exc(); print("===== END AIVIDEO GENERATION ERROR =====\n", flush=True)
        raise HTTPException(status_code=500, detail=f"Video üretimi başarısız: {exc}") from exc

@app.post("/generate-story")
async def generate_story(topic: str = Form(""), minutes: int = Form(15), music_enabled: bool = Form(True), watermark_enabled: bool = Form(True)) -> dict:
    if minutes not in {15, 20}: raise HTTPException(status_code=400, detail="Hikâye süresi 15 veya 20 dakika olmalı.")
    if not topic.strip(): raise HTTPException(status_code=400, detail="Hikâye konusu boş bırakılamaz.")
    try: return await asyncio.to_thread(generate_story_video, topic, minutes, music_enabled, watermark_enabled)
    except Exception as exc:
        print("\n===== AIVIDEO STORY ERROR =====", flush=True); traceback.print_exc(); print("===== END AIVIDEO STORY ERROR =====\n", flush=True)
        raise HTTPException(status_code=500, detail=f"Hikâye videosu üretilemedi: {exc}") from exc

@app.post("/generate-and-upload")
async def generate_and_upload(topic: str = Form(""), template: str = Form("Hayırlı Cumalar"), duration: int = Form(30), music_enabled: bool = Form(True), watermark_enabled: bool = Form(True), youtube_enabled: bool = Form(True), title: str = Form(""), description: str = Form(""), tags: str = Form("islam, hadis, ayet, dua, islami söz, shorts"), privacy_status: str = Form("private")) -> dict:
    if duration not in {15, 30, 60}: raise HTTPException(status_code=400, detail="Süre 15, 30 veya 60 saniye olmalı.")
    try:
        result = await asyncio.to_thread(generate_video, topic, template, duration, music_enabled, watermark_enabled)
        if not youtube_enabled: return result
        status = await asyncio.to_thread(youtube_status)
        if not status.get("connected"): return {**result, "youtube": {"uploaded": False, "reason": "YouTube hesabı bağlı değil."}}
        script = result.get("script", {}); final_title = (title.strip() or script.get("title") or "Aivideo")[:100]; final_description = description.strip() or script.get("description", "")
        generated_tags = script.get("tags", []); generated_tags = [x.strip() for x in generated_tags.split(",") if x.strip()] if isinstance(generated_tags, str) else generated_tags
        final_tags = [x.strip() for x in tags.split(",") if x.strip()] or generated_tags
        uploaded = await asyncio.to_thread(upload_video, result["video_path"], final_title, final_description, final_tags, privacy_status)
        return {**result, "youtube": {"uploaded": True, **uploaded}}
    except Exception as exc:
        print("\n===== AIVIDEO GENERATE+UPLOAD ERROR =====", flush=True); traceback.print_exc(); print("===== END AIVIDEO GENERATE+UPLOAD ERROR =====\n", flush=True)
        raise HTTPException(status_code=500, detail=f"Video üretimi/yükleme başarısız: {exc}") from exc

@app.get("/video/latest")
def latest_video() -> FileResponse:
    path = Path(__file__).resolve().parent / "output" / "aivideo_short.mp4"
    if not path.exists(): raise HTTPException(status_code=404, detail="Henüz video üretilmedi.")
    return FileResponse(path, media_type="video/mp4", filename="aivideo_short.mp4")

@app.get("/video/story")
def latest_story_video() -> FileResponse:
    path = Path(__file__).resolve().parent / "output" / "aivideo_story.mp4"
    if not path.exists(): raise HTTPException(status_code=404, detail="Henüz hikâye videosu üretilmedi.")
    return FileResponse(path, media_type="video/mp4", filename="aivideo_story.mp4")

@app.post("/youtube/upload")
async def youtube_upload(video: UploadFile = File(...), title: str = Form("Aivideo"), description: str = Form(""), tags: str = Form(""), privacy_status: str = Form("private")) -> dict:
    try: status = youtube_status()
    except Exception as exc: raise HTTPException(status_code=500, detail=str(exc)) from exc
    if not status.get("connected"): raise HTTPException(status_code=401, detail="YouTube hesabı bağlı değil. Önce /youtube/auth çalıştır.")
    if not (video.filename or "").lower().endswith(".mp4"): raise HTTPException(status_code=400, detail="Sadece MP4 video yüklenebilir.")
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(prefix="aivideo_", suffix=".mp4", delete=False) as tmp:
            temp_path = Path(tmp.name)
            while chunk := await video.read(1024 * 1024): tmp.write(chunk)
        result = await asyncio.to_thread(upload_video, temp_path, title, description, [x.strip() for x in tags.split(",") if x.strip()], privacy_status)
        return {"ok": True, **result}
    except HTTPException: raise
    except Exception as exc: raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        await video.close()
        if temp_path: temp_path.unlink(missing_ok=True)
