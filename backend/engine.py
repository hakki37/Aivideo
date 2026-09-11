from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = ENGINE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")


def _http_json(url: str, *, method: str = "GET", headers: dict | None = None, data: bytes | None = None) -> dict:
    request = urllib.request.Request(url, method=method, headers=headers or {}, data=data)
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def ollama_generate(topic: str, template: str, duration: int) -> dict:
    prompt = f"""Türkçe İslami Shorts editörüsün. Konu: {topic or 'günün anlamlı mesajı'}. Şablon: {template}. Süre: {duration} saniye.
Yalnızca JSON döndür. Alanlar: quote, title, description, tags, visual_query.
quote kısa, güçlü ve ekrana uygun olsun. Ayet/hadis ise kaynak uydurma; emin değilsen genel bir İslami öğüt yaz ve kaynak iddiası yapma.
visual_query İngilizce, doğal manzara/insan/huzur gibi nötr stok video araması için olsun; kilise, haç, dini sembol ve benzeri Hristiyan görselleri isteme."""
    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.65},
    }).encode("utf-8")
    result = _http_json(
        f"{OLLAMA_URL.rstrip('/')}/api/generate",
        method="POST",
        headers={"Content-Type": "application/json"},
        data=payload,
    )
    text = result.get("response", "{}").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"quote": text, "title": topic or "Günün Mesajı", "description": "", "tags": [], "visual_query": "peaceful nature"}


def pexels_video(query: str, destination: Path) -> Path:
    if not PEXELS_API_KEY:
        raise RuntimeError("PEXELS_API_KEY ayarlı değil.")
    url = "https://api.pexels.com/videos/search?" + urllib.parse.urlencode({"query": query, "orientation": "portrait", "size": "medium", "per_page": 10})
    data = _http_json(url, headers={"Authorization": PEXELS_API_KEY})
    candidates = []
    for video in data.get("videos", []):
        # Avoid obvious religious architecture/symbols in the search result metadata.
        name = json.dumps(video, ensure_ascii=False).lower()
        if any(word in name for word in ("church", "cross", "cathedral", "christian")):
            continue
        for item in video.get("video_files", []):
            width, height = item.get("width", 0), item.get("height", 0)
            if height >= width and item.get("link"):
                candidates.append((abs((height / max(width, 1)) - 16 / 9), item["link"]))
    if not candidates:
        raise RuntimeError("Uygun portre Pexels videosu bulunamadı.")
    candidates.sort(key=lambda x: x[0])
    request = urllib.request.Request(candidates[0][1], headers={"User-Agent": "Aivideo/0.1"})
    with urllib.request.urlopen(request, timeout=120) as response, destination.open("wb") as output:
        shutil.copyfileobj(response, output)
    return destination


def _ffmpeg() -> str:
    path = shutil.which("ffmpeg")
    if not path:
        raise RuntimeError("FFmpeg PATH üzerinde bulunamadı.")
    return path


def render_short(source: Path, output: Path, quote: str, duration: int) -> Path:
    # 1080x1920, clean dark gradient, centered quote and subtle zoom.
    safe = re.sub(r"[^\w\u0080-\uFFFF .,!?;:'’()-]", "", quote).strip()[:220]
    drawtext = (
        "drawtext=text='" + safe.replace("'", "\\'") + "'"
        ":fontcolor=white:fontsize=64:fontfile=/Windows/Fonts/arial.ttf"
        ":x=(w-text_w)/2:y=(h-text_h)/2:line_spacing=14:box=1:boxcolor=black@0.42:boxborderw=35"
    )
    vf = f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,zoompan=z='min(zoom+0.0007,1.08)':d=1:s=1080x1920:fps=30,{drawtext}"
    command = [_ffmpeg(), "-y", "-stream_loop", "-1", "-i", str(source), "-t", str(duration), "-vf", vf, "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", str(output)]
    subprocess.run(command, check=True, capture_output=True, text=True)
    return output


def generate_video(topic: str, template: str, duration: int) -> dict:
    script = ollama_generate(topic, template, duration)
    query = script.get("visual_query") or "peaceful nature sunrise"
    source = OUTPUT_DIR / "source.mp4"
    output = OUTPUT_DIR / "aivideo_short.mp4"
    pexels_video(query, source)
    render_short(source, output, script.get("quote", "Hayra vesile olan bir söz."), duration)
    return {"ok": True, "video_path": str(output), "script": script, "engine": "ollama+pexels+ffmpeg"}
