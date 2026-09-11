from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from threading import Thread

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from youtube_uploader import authenticate, upload_video, youtube_status

app = FastAPI(title="Aivideo Local Engine", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth_running = False

oauth_error: str | None = None


def _oauth_worker() -> None:
    global oauth_running, oauth_error
    try:
        authenticate()
        oauth_error = None
    except Exception as exc:  # noqa: BLE001 - surface setup errors through status endpoint
        oauth_error = str(exc)
    finally:
        oauth_running = False


@app.get("/health")
def health() -> dict:
    return {"ok": True, "service": "aivideo-local-engine"}


@app.get("/youtube/status")
def youtube_connection_status() -> dict:
    if oauth_running:
        return {"connected": False, "authorizing": True, "error": oauth_error}
    try:
        return {**youtube_status(), "authorizing": False, "error": oauth_error}
    except Exception as exc:  # noqa: BLE001
        return {"connected": False, "authorizing": False, "error": str(exc)}


@app.post("/youtube/auth")
def youtube_auth() -> dict:
    global oauth_running, oauth_error
    if oauth_running:
        return {"started": True, "authorizing": True}

    oauth_error = None
    oauth_running = True
    Thread(target=_oauth_worker, daemon=True, name="youtube-oauth").start()
    return {
        "started": True,
        "authorizing": True,
        "message": "Google OAuth tarayıcıda açılacak. İzin verdikten sonra /youtube/status ile bağlantıyı kontrol et.",
    }


@app.post("/youtube/upload")
async def youtube_upload(
    video: UploadFile = File(...),
    title: str = Form("Aivideo"),
    description: str = Form(""),
    tags: str = Form(""),
    privacy_status: str = Form("private"),
) -> dict:
    try:
        status = youtube_status()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if not status.get("connected"):
        raise HTTPException(status_code=401, detail="YouTube hesabı bağlı değil. Önce /youtube/auth çalıştır.")

    if not (video.filename or "").lower().endswith(".mp4"):
        raise HTTPException(status_code=400, detail="Sadece MP4 video yüklenebilir.")

    tags_list = [item.strip() for item in tags.split(",") if item.strip()]
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(prefix="aivideo_", suffix=".mp4", delete=False) as tmp:
            temp_path = Path(tmp.name)
            while chunk := await video.read(1024 * 1024):
                tmp.write(chunk)

        # Google upload is blocking; run it off the FastAPI event loop.
        result = await asyncio.to_thread(
            upload_video,
            temp_path,
            title,
            description,
            tags_list,
            privacy_status,
        )
        return {"ok": True, **result}
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        await video.close()
        if temp_path:
            temp_path.unlink(missing_ok=True)
