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
ASSETS_DIR = ENGINE_DIR / "assets"
OUTPUT_DIR.mkdir(exist_ok=True)
ASSETS_DIR.mkdir(exist_ok=True)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
MUSIC_FILE = Path(os.getenv("AIVIDEO_MUSIC_FILE", str(ASSETS_DIR / "music.mp3")))
WATERMARK_FILE = Path(os.getenv("AIVIDEO_WATERMARK_FILE", str(ASSETS_DIR / "islamic_horizon_watermark.png")))
WATERMARK_OPACITY = float(os.getenv("AIVIDEO_WATERMARK_OPACITY", "0.65"))
WATERMARK_WIDTH = int(os.getenv("AIVIDEO_WATERMARK_WIDTH", "220"))

BLOCKED_VISUAL_WORDS = (
    "church", "cross", "cathedral", "christian", "chapel", "crucifix", "jesus",
    "bible church", "steeple", "altar", "mosque interior"
)
FALLBACK_QUERIES = [
    "peaceful sunrise mountains",
    "soft clouds golden light",
    "rain on window cinematic",
    "calm ocean sunset",
    "green forest sunlight",
]


def _http_json(url: str, *, method: str = "GET", headers: dict | None = None, data: bytes | None = None) -> dict:
    request = urllib.request.Request(url, method=method, headers=headers or {}, data=data)
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def ollama_generate(topic: str, template: str, duration: int) -> dict:
    prompt = f"""Türkçe İslami Shorts kreatif direktörüsün. Konu: {topic or 'günün anlamlı mesajı'}. Şablon: {template}. Süre: {duration} saniye.
Yalnızca JSON döndür. Alanlar: quote, title, description, tags, visual_queries.
visual_queries 3 ila 5 adet İngilizce kısa stok video araması olsun; doğal manzara, gökyüzü, yağmur, kitap, ışık, insan silüeti gibi sinematik ve nötr görüntüler seç. Kilise, haç, katedral, İsa veya Hristiyan sembolleri isteme.
quote kısa, güçlü ve ekrana uygun olsun. Ayet/hadis ise kaynak uydurma; emin değilsen kaynak iddiası yapma.
description YouTube için doğal Türkçe açıklama, tags virgülle ayrılmış etiket listesi olsun."""
    payload = json.dumps({"model": OLLAMA_MODEL, "prompt": prompt, "stream": False, "format": "json", "options": {"temperature": 0.65}}).encode("utf-8")
    result = _http_json(f"{OLLAMA_URL.rstrip('/')}/api/generate", method="POST", headers={"Content-Type": "application/json"}, data=payload)
    text = result.get("response", "{}").strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        data = {"quote": text, "title": topic or "Günün Mesajı", "description": "", "tags": [], "visual_queries": FALLBACK_QUERIES[:3]}
    queries = data.get("visual_queries")
    if isinstance(queries, str):
        queries = [queries]
    data["visual_queries"] = [q.strip() for q in (queries or []) if isinstance(q, str) and q.strip()][:5]
    if not data["visual_queries"]:
        data["visual_queries"] = FALLBACK_QUERIES[:3]
    return data


def _safe_query(query: str) -> str:
    cleaned = query.strip()
    for word in BLOCKED_VISUAL_WORDS:
        cleaned = re.sub(rf"\b{re.escape(word)}\b", "", cleaned, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", cleaned).strip() or "peaceful nature"


def _pexels_candidates(query: str) -> list[tuple[float, int, str]]:
    if not PEXELS_API_KEY:
        raise RuntimeError("PEXELS_API_KEY ayarlı değil.")
    safe_query = _safe_query(query)
    # Do not force Pexels to return portrait-only clips. Many good stock clips are
    # landscape/square and FFmpeg safely center-crops them to 1080x1920 later.
    url = "https://api.pexels.com/videos/search?" + urllib.parse.urlencode({"query": safe_query, "size": "medium", "per_page": 30})
    data = _http_json(url, headers={"Authorization": PEXELS_API_KEY})
    candidates: list[tuple[float, int, str]] = []
    for video in data.get("videos", []):
        blob = json.dumps(video, ensure_ascii=False).lower()
        if any(word in blob for word in BLOCKED_VISUAL_WORDS):
            continue
        for item in video.get("video_files", []):
            width, height = item.get("width", 0), item.get("height", 0)
            link = item.get("link")
            if width >= 540 and height >= 540 and link:
                ratio_error = abs((height / max(width, 1)) - 16 / 9)
                quality = width * height
                # Prefer vertical clips, but accept high-quality landscape/square
                # footage because the renderer can crop it into Shorts format.
                vertical_bonus = 0 if height >= width else 0.08
                score = ratio_error + vertical_bonus
                candidates.append((score, -quality, link))
    return candidates


def pexels_video(query: str, destination: Path) -> Path:
    queries = [query] + [q for q in FALLBACK_QUERIES if q.lower() != query.lower()]
    all_candidates: list[tuple[float, int, str]] = []
    for candidate_query in queries[:5]:
        try:
            all_candidates.extend(_pexels_candidates(candidate_query))
        except Exception:
            continue
        if all_candidates:
            break
    if not all_candidates:
        raise RuntimeError(f"Uygun Pexels videosu bulunamadı: {_safe_query(query)}")
    all_candidates.sort(key=lambda x: (x[0], x[1]))
    request = urllib.request.Request(all_candidates[0][2], headers={"User-Agent": "Aivideo/0.5"})
    with urllib.request.urlopen(request, timeout=120) as response, destination.open("wb") as output:
        shutil.copyfileobj(response, output)
    return destination


def _ffmpeg() -> str:
    path = shutil.which("ffmpeg")
    if not path:
        raise RuntimeError("FFmpeg PATH üzerinde bulunamadı.")
    return path


def _normalize_clip(source: Path, destination: Path, seconds: float) -> None:
    vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30,eq=contrast=1.03:saturation=1.05:brightness=0.01,zoompan=z='min(zoom+0.0006,1.07)':d=1:s=1080x1920:fps=30"
    command = [_ffmpeg(), "-y", "-i", str(source), "-t", f"{seconds:.2f}", "-vf", vf, "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p", str(destination)]
    subprocess.run(command, check=True, capture_output=True, text=True)


def _concat_clips(clips: list[Path], output: Path) -> None:
    list_file = OUTPUT_DIR / "concat.txt"
    list_file.write_text("\n".join(f"file '{p.as_posix()}'" for p in clips), encoding="utf-8")
    command = [_ffmpeg(), "-y", "-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", "-movflags", "+faststart", str(output)]
    subprocess.run(command, check=True, capture_output=True, text=True)


def _wrap_quote(text: str, max_chars: int = 30) -> str:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and len(candidate) > max_chars:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return "\n".join(lines[:6])


def render_short(source: Path, output: Path, quote: str, duration: int, template: str, music_enabled: bool, watermark_enabled: bool = True) -> Path:
    safe = re.sub(r"[^\w\u0080-\uFFFF .,!?;:'’()\-]", "", quote).strip()[:220]
    safe = _wrap_quote(safe)
    escaped = safe.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
    template_text = template.upper().replace("'", "")[:24]
    footer_text = "🌙 HAYIRLI CUMALAR 🤲" if template == "Hayırlı Cumalar" else "AIVIDEO • İSLAMİ SHORTS"
    font = "/Windows/Fonts/arial.ttf" if os.name == "nt" else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    draw = f"drawtext=fontfile='{font}':text='{escaped}':fontcolor=white:fontsize=66:x=(w-text_w)/2:y=(h-text_h)/2:line_spacing=16:box=1:boxcolor=black@0.38:boxborderw=42:alpha='if(lt(t,0.7),t/0.7,if(gt(t,{duration}-0.7),({duration}-t)/0.7,1))'"
    header = f"drawtext=fontfile='{font}':text='{template_text}':fontcolor=white@0.72:fontsize=30:x=(w-text_w)/2:y=90"
    footer = f"drawtext=fontfile='{font}':text='{footer_text}':fontcolor=white:fontsize=34:x=(w-text_w)/2:y=h-150:box=1:boxcolor=black@0.30:boxborderw=18"
    base_vf = f"{draw},{header},{footer}"

    inputs = ["-i", str(source)]
    use_watermark = watermark_enabled and WATERMARK_FILE.exists()
    if use_watermark:
        inputs += ["-loop", "1", "-i", str(WATERMARK_FILE)]
        opacity = max(0.0, min(1.0, WATERMARK_OPACITY))
        width = max(80, min(500, WATERMARK_WIDTH))
        video_filter = f"[0:v]{base_vf}[base];[1:v]scale={width}:-1,format=rgba,colorchannelmixer=aa={opacity:.3f}[wm];[base][wm]overlay=x=W-w-55:y=H-h-205:format=auto[vout]"
        watermark_input_index = 1
    else:
        video_filter = f"[0:v]{base_vf}[vout]"
        watermark_input_index = -1

    if music_enabled and MUSIC_FILE.exists():
        music_index = watermark_input_index + 1 if use_watermark else 1
        inputs += ["-stream_loop", "-1", "-i", str(MUSIC_FILE)]
        audio_args = ["-map", f"{music_index}:a:0", "-c:a", "aac", "-b:a", "128k", "-af", "volume=0.20", "-shortest"]
    else:
        audio_args = ["-an"]

    command = [
        _ffmpeg(), "-y", *inputs, "-t", str(duration),
        "-filter_complex", video_filter, "-map", "[vout]",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p",
        *audio_args, "-movflags", "+faststart", str(output),
    ]
    subprocess.run(command, check=True, capture_output=True, text=True)
    return output


def generate_video(topic: str, template: str, duration: int, music_enabled: bool = True, watermark_enabled: bool = True) -> dict:
    script = ollama_generate(topic, template, duration)
    queries = script["visual_queries"]
    scene_count = min(len(queries), max(3, duration // 10))
    selected_queries = queries[:scene_count]
    scene_seconds = duration / scene_count
    normalized_clips: list[Path] = []
    used_queries: list[str] = []
    for index, query in enumerate(selected_queries, start=1):
        raw = OUTPUT_DIR / f"scene_{index}.mp4"
        normalized = OUTPUT_DIR / f"scene_{index}_1080.mp4"
        pexels_video(query, raw)
        _normalize_clip(raw, normalized, scene_seconds)
        normalized_clips.append(normalized)
        used_queries.append(_safe_query(query))
    montage = OUTPUT_DIR / "montage.mp4"
    _concat_clips(normalized_clips, montage)
    output = OUTPUT_DIR / "aivideo_short.mp4"
    render_short(montage, output, script.get("quote", "Hayra vesile olan bir söz."), duration, template, music_enabled, watermark_enabled)
    return {
        "ok": True,
        "video_path": str(output),
        "script": script,
        "scenes": used_queries,
        "music_enabled": bool(music_enabled and MUSIC_FILE.exists()),
        "watermark_enabled": bool(watermark_enabled and WATERMARK_FILE.exists()),
        "engine": "ollama+pexels+ffmpeg-multiscene-watermark",
    }
