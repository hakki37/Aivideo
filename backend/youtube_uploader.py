from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
BASE_DIR = Path(__file__).resolve().parent
CLIENT_SECRET_FILE = Path(os.getenv("YOUTUBE_CLIENT_SECRET", BASE_DIR / "client_secret.json"))
TOKEN_FILE = Path(os.getenv("YOUTUBE_TOKEN_FILE", BASE_DIR / "token.json"))


def _load_credentials() -> Credentials | None:
    if not TOKEN_FILE.exists():
        return None
    creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    return creds if creds and creds.valid else None


def authenticate() -> None:
    """Run the one-time Google OAuth consent flow on the PC running this backend."""
    if not CLIENT_SECRET_FILE.exists():
        raise FileNotFoundError(
            f"YouTube client secret bulunamadı: {CLIENT_SECRET_FILE}. "
            "Google Cloud'dan OAuth Desktop client JSON dosyasını bu isimle backend klasörüne koy."
        )

    creds = _load_credentials()
    if creds:
        return

    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET_FILE), SCOPES)
    creds = flow.run_local_server(port=0, open_browser=True, access_type="offline", prompt="consent")
    TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")


def youtube_status() -> dict:
    creds = _load_credentials()
    if not creds:
        return {"connected": False}

    youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)
    response = youtube.channels().list(part="snippet", mine=True).execute()
    items = response.get("items", [])
    if not items:
        return {"connected": False}

    snippet = items[0].get("snippet", {})
    return {
        "connected": True,
        "channel_id": items[0].get("id"),
        "channel_title": snippet.get("title", ""),
    }


def upload_video(
    file_path: str | Path,
    title: str,
    description: str,
    tags: Iterable[str] | None = None,
    privacy_status: str = "private",
    category_id: str = "22",
) -> dict:
    creds = _load_credentials()
    if not creds:
        raise RuntimeError("YouTube hesabı bağlı değil. Önce /youtube/auth çağrısını çalıştır.")

    privacy = privacy_status.lower().strip()
    if privacy not in {"private", "unlisted", "public"}:
        privacy = "private"

    clean_tags = [tag.strip() for tag in (tags or []) if tag.strip()]
    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": clean_tags[:500],
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }

    youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)
    media = MediaFileUpload(str(file_path), mimetype="video/mp4", resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    response = None
    while response is None:
        _, response = request.next_chunk()

    video_id = response["id"]
    return {
        "video_id": video_id,
        "url": f"https://www.youtube.com/watch?v={video_id}",
        "privacy_status": privacy,
        "title": body["snippet"]["title"],
    }
