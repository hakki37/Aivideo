from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path

from engine import WATERMARK_FILE, WATERMARK_OPACITY, WATERMARK_WIDTH, _ffmpeg, _normalize_clip, _concat_clips, _safe_query, FALLBACK_QUERIES

ENGINE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = ENGINE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:8b")
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
MUSIC_FILE = Path(os.getenv("AIVIDEO_MUSIC_FILE", str(ENGINE_DIR / "assets" / "music.mp3")))


def _http_json(url: str, *, method: str = "GET", headers: dict | None = None, data: bytes | None = None) -> dict:
    request = urllib.request.Request(url, method=method, headers=headers or {}, data=data)
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def _story_prompt(topic: str, minutes: int) -> str:
    words = 2100 if minutes == 15 else 2800
    return f'''Sen Türkçe dini hikâye senaristisin. Konu: {topic}. Hedef süre: {minutes} dakika. Yaklaşık {words} kelimelik, seslendirmeye uygun, akıcı ve merak uyandıran bir hikâye hazırla.

Yalnızca JSON döndür. Alanlar:
- title: kısa YouTube başlığı
- description: YouTube açıklaması
- tags: virgülle ayrılmış etiketler
- scenes: 8 ila 12 sahne. Her sahnede "narration" ve "visual_query" alanları olsun.

Kurallar:
1. Anlatım doğal Türkçe olsun; kısa cümleler, güçlü giriş, ortada merak, sonda anlamlı ders ve dua/temenni.
2. Peygamberler, sahabeler veya ayet/hadis kullanıyorsan yalnızca güvenilir ve genel kabul görmüş bilgileri kullan; kaynak uydurma, kesin olmayan rivayeti kesin gerçek gibi anlatma.
3. Çocuklara yönelikse korku ve şiddeti yumuşak anlat.
4. Her sahnenin narration metni yaklaşık eşit uzunlukta olsun.
5. visual_query İngilizce olsun ve yalnızca nötr sinematik görüntüler iste: nature, mountains, desert, sunrise, sky, rain, old village, book, lantern, silhouette gibi. Kilise, haç, katedral, İsa, Hristiyan sembolleri veya dini mekân içi görüntü isteme.
6. Metin içinde sahne başlığı, emoji veya konuşmacı etiketi kullanma; doğrudan seslendirilecek metin yaz.
7. Toplam metin hedefe yakın olsun; 15 dakika için yaklaşık 2100, 20 dakika için yaklaşık 2800 kelime hedefle.'''


def generate_story_script(topic: str, minutes: int) -> dict:
    if minutes not in {15, 20}:
        raise ValueError("Hikâye süresi 15 veya 20 dakika olmalı.")
    if not topic.strip():
        raise ValueError("Hikâye konusu boş bırakılamaz.")
    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "prompt": _story_prompt(topic.strip(), minutes),
        "stream": False,
        "format": "json",
        "options": {"temperature": 0.7, "num_ctx": 8192},
    }).encode("utf-8")
    result = _http_json(f"{OLLAMA_URL.rstrip('/')}/api/generate", method="POST", headers={"Content-Type": "application/json"}, data=payload)
    text = result.get("response", "{}").strip()
    try:
        story = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Qwen hikâye JSON üretemedi: {text[:500]}") from exc
    scenes = story.get("scenes")
    if not isinstance(scenes, list) or len(scenes) < 3:
        raise RuntimeError("Qwen geçerli hikâye sahneleri üretmedi.")
    clean_scenes = []
    for scene in scenes[:12]:
        narration = str(scene.get("narration", "")).strip()
        query = _safe_query(str(scene.get("visual_query", "peaceful nature")))
        if narration:
            clean_scenes.append({"narration": narration, "visual_query": query})
    if len(clean_scenes) < 3:
        raise RuntimeError("Hikâyede yeterli anlatım sahnesi yok.")
    story["scenes"] = clean_scenes
    story["title"] = str(story.get("title") or topic.strip())[:100]
    story["description"] = str(story.get("description") or "").strip()
    return story


def _pexels_video(query: str, destination: Path) -> Path:
    if not PEXELS_API_KEY:
        raise RuntimeError("PEXELS_API_KEY ayarlı değil.")
    safe = _safe_query(query)
    url = "https://api.pexels.com/videos/search?" + urllib.parse.urlencode({"query": safe, "size": "medium", "per_page": 20})
    data = _http_json(url, headers={"Authorization": PEXELS_API_KEY})
    videos = data.get("videos", [])
    if not videos:
        for fallback in FALLBACK_QUERIES:
            try:
                data = _http_json("https://api.pexels.com/videos/search?" + urllib.parse.urlencode({"query": fallback, "size": "medium", "per_page": 20}), headers={"Authorization": PEXELS_API_KEY})
                videos = data.get("videos", [])
                if videos:
                    break
            except Exception:
                continue
    candidates = []
    for video in videos:
        blob = json.dumps(video, ensure_ascii=False).lower()
        if any(x in blob for x in ("church", "cross", "cathedral", "christian", "crucifix", "jesus", "steeple", "altar")):
            continue
        for item in video.get("video_files", []):
            link = item.get("link")
            width = int(item.get("width") or 0)
            height = int(item.get("height") or 0)
            if link and width >= 540 and height >= 540:
                ratio_error = abs((height / max(width, 1)) - 16 / 9)
                candidates.append((ratio_error, -(width * height), link))
    if not candidates:
        raise RuntimeError(f"Hikâye için Pexels videosu bulunamadı: {safe}")
    candidates.sort(key=lambda x: (x[0], x[1]))
    request = urllib.request.Request(candidates[0][2], headers={"User-Agent": "Aivideo/Story"})
    with urllib.request.urlopen(request, timeout=120) as response, destination.open("wb") as output:
        shutil.copyfileobj(response, output)
    return destination


def _tts(text: str, destination: Path) -> bool:
    try:
        import pyttsx3
    except ImportError:
        return False
    engine = pyttsx3.init()
    voices = engine.getProperty("voices") or []
    selected = None
    for voice in voices:
        info = f"{getattr(voice, 'id', '')} {getattr(voice, 'name', '')}".lower()
        if any(x in info for x in ("turkish", "türk", "tr-tr", "tr_tr", "turkiye", "turkey")):
            selected = voice
            break
    if selected is not None:
        engine.setProperty("voice", selected.id)
    engine.setProperty("rate", int(os.getenv("AIVIDEO_TTS_RATE", "145")))
    engine.setProperty("volume", 1.0)
    engine.save_to_file(text, str(destination))
    engine.runAndWait()
    return destination.exists() and destination.stat().st_size > 0


def _render_story(source: Path, audio: Path | None, output: Path, duration: int, title: str, music_enabled: bool, watermark_enabled: bool) -> Path:
    font = "/Windows/Fonts/arial.ttf" if os.name == "nt" else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    safe_title = re.sub(r"[^\w\u0080-\uFFFF .,!?;:'’()\-]", "", title).replace("'", "\\'")[:90]
    vf = f"drawtext=fontfile='{font}':text='{safe_title}':fontcolor=white@0.82:fontsize=34:x=(w-text_w)/2:y=90:box=1:boxcolor=black@0.22:boxborderw=16"
    inputs = ["-i", str(source)]
    filters = [f"[0:v]{vf}[base]"]
    video_label = "base"
    index = 1
    if watermark_enabled and WATERMARK_FILE.exists():
        inputs += ["-loop", "1", "-i", str(WATERMARK_FILE)]
        opacity = max(0.0, min(1.0, WATERMARK_OPACITY))
        width = max(80, min(500, WATERMARK_WIDTH))
        filters.append(f"[1:v]scale={width}:-1,format=rgba,colorchannelmixer=aa={opacity:.3f}[wm]")
        filters.append("[base][wm]overlay=x=W-w-55:y=H-h-205:format=auto[vout]")
        video_label = "vout"
        index = 2
    else:
        filters[0] = f"[0:v]{vf}[vout]"
        video_label = "vout"
    audio_args = ["-an"]
    if audio is not None and audio.exists():
        inputs += ["-i", str(audio)]
        narration_index = index
        if music_enabled and MUSIC_FILE.exists():
            inputs += ["-stream_loop", "-1", "-i", str(MUSIC_FILE)]
            music_index = narration_index + 1
            audio_args = ["-map", f"{narration_index}:a:0", "-c:a", "aac", "-b:a", "128k", "-af", "volume=1.0", "-t", str(duration)]
            # Mix music only when it exists; narration remains dominant.
            filters.append(f"[{narration_index}:a]volume=1.0[narr];[{music_index}:a]volume=0.10[mus];[narr][mus]amix=inputs=2:duration=first:dropout_transition=2[aout]")
            audio_args = ["-map", "[aout]", "-c:a", "aac", "-b:a", "128k", "-t", str(duration)]
        else:
            audio_args = ["-map", f"{narration_index}:a:0", "-c:a", "aac", "-b:a", "128k", "-t", str(duration)]
    command = [_ffmpeg(), "-y", *inputs, "-t", str(duration), "-filter_complex", ";".join(filters), "-map", f"[{video_label}]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", *audio_args, "-movflags", "+faststart", str(output)]
    subprocess.run(command, check=True, capture_output=True, text=True)
    return output


def generate_story_video(topic: str, minutes: int = 15, music_enabled: bool = True, watermark_enabled: bool = True) -> dict:
    story = generate_story_script(topic, minutes)
    script_path = OUTPUT_DIR / "story_script.json"
    script_path.write_text(json.dumps(story, ensure_ascii=False, indent=2), encoding="utf-8")
    scenes = story["scenes"]
    scene_seconds = (minutes * 60) / len(scenes)
    clips = []
    used = []
    for i, scene in enumerate(scenes, 1):
        raw = OUTPUT_DIR / f"story_scene_{i}.mp4"
        normalized = OUTPUT_DIR / f"story_scene_{i}_1080.mp4"
        _pexels_video(scene["visual_query"], raw)
        _normalize_clip(raw, normalized, scene_seconds)
        clips.append(normalized)
        used.append(scene["visual_query"])
    montage = OUTPUT_DIR / "story_montage.mp4"
    _concat_clips(clips, montage)
    narration_text = "\n\n".join(scene["narration"] for scene in scenes)
    narration = OUTPUT_DIR / "story_narration.wav"
    tts_ok = _tts(narration_text, narration)
    output = OUTPUT_DIR / "aivideo_story.mp4"
    _render_story(montage, narration if tts_ok else None, output, minutes * 60, story["title"], music_enabled, watermark_enabled)
    return {"ok": True, "video_path": str(output), "script": story, "scenes": used, "narration_enabled": tts_ok, "music_enabled": bool(music_enabled and MUSIC_FILE.exists()), "watermark_enabled": bool(watermark_enabled and WATERMARK_FILE.exists()), "engine": "qwen3+pexels+ffmpeg-story+local-tts"}
