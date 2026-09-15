from __future__ import annotations

import json
import os
import shutil
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

from dotenv import load_dotenv
from engine import WATERMARK_FILE, WATERMARK_OPACITY, WATERMARK_WIDTH, _ffmpeg, _run_ffmpeg, _safe_query, FALLBACK_QUERIES

ENGINE_DIR = Path(__file__).resolve().parent
load_dotenv(ENGINE_DIR / ".env")
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
Yalnızca JSON döndür. Alanlar: title, description, tags, scenes.
scenes 8 ila 12 adet olsun ve her sahnede narration ile visual_query bulunsun.
Kurallar: Doğal Türkçe; güçlü giriş, merak ve sonunda anlamlı ders. Peygamber, sahabe, ayet veya hadis kullanıyorsan kaynak uydurma ve kesin olmayan rivayeti kesin gerçek gibi anlatma. visual_query İngilizce, nötr sinematik stok görüntüleri için olsun: nature, mountains, desert, sunrise, sky, rain, old village, book, lantern, silhouette. Kilise, haç, katedral, İsa, Hristiyan sembolleri veya dini mekân içi görüntüler isteme. Sahne metinleri doğrudan seslendirilebilir olsun. Toplam anlatım yaklaşık {words} kelime olsun.'''


def generate_story_script(topic: str, minutes: int) -> dict:
    if minutes not in {15, 20}:
        raise ValueError("Hikâye süresi 15 veya 20 dakika olmalı.")
    if not topic.strip():
        raise ValueError("Hikâye konusu boş bırakılamaz.")
    payload = json.dumps({"model": OLLAMA_MODEL, "prompt": _story_prompt(topic.strip(), minutes), "stream": False, "format": "json", "options": {"temperature": 0.7, "num_ctx": 8192}}).encode("utf-8")
    result = _http_json(f"{OLLAMA_URL.rstrip('/')}/api/generate", method="POST", headers={"Content-Type": "application/json"}, data=payload)
    text = result.get("response", "{}").strip()
    try:
        story = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Qwen hikâye JSON üretemedi: {text[:500]}") from exc
    scenes = story.get("scenes")
    if not isinstance(scenes, list) or len(scenes) < 3:
        raise RuntimeError("Qwen geçerli hikâye sahneleri üretmedi.")
    clean = []
    for scene in scenes[:12]:
        narration = str(scene.get("narration", "")).strip()
        query = _safe_query(str(scene.get("visual_query", "peaceful nature")))
        if narration:
            clean.append({"narration": narration, "visual_query": query})
    if len(clean) < 3:
        raise RuntimeError("Hikâyede yeterli anlatım sahnesi yok.")
    story["scenes"] = clean
    story["title"] = str(story.get("title") or topic.strip())[:100]
    story["description"] = str(story.get("description") or "").strip()
    return story


def _pexels_video(query: str, destination: Path) -> Path:
    if not PEXELS_API_KEY:
        raise RuntimeError("PEXELS_API_KEY ayarlı değil.")
    safe = _safe_query(query)
    queries = [safe] + [q for q in FALLBACK_QUERIES if q.lower() != safe.lower()]
    errors = []
    for candidate_query in queries[:8]:
        try:
            url = "https://api.pexels.com/videos/search?" + urllib.parse.urlencode({"query": candidate_query, "size": "medium", "per_page": 20})
            data = _http_json(url, headers={"Authorization": PEXELS_API_KEY})
            candidates = []
            for video in data.get("videos", []):
                blob = json.dumps(video, ensure_ascii=False).lower()
                if any(x in blob for x in ("church", "cross", "cathedral", "christian", "crucifix", "jesus", "steeple", "altar")):
                    continue
                for item in video.get("video_files", []):
                    link = item.get("link")
                    w, h = int(item.get("width") or 0), int(item.get("height") or 0)
                    if link and w >= 540 and h >= 540:
                        ratio_error = abs((w / max(h, 1)) - 16 / 9)
                        candidates.append((ratio_error, -(w * h), link))
            if not candidates:
                errors.append(f"{candidate_query}: sonuç yok")
                continue
            candidates.sort(key=lambda x: (x[0], x[1]))
            request = urllib.request.Request(candidates[0][2], headers={"User-Agent": "Aivideo/Story"})
            with urllib.request.urlopen(request, timeout=120) as response, destination.open("wb") as output:
                shutil.copyfileobj(response, output)
            if destination.stat().st_size > 0:
                return destination
        except Exception as exc:
            errors.append(f"{candidate_query}: {exc}")
    raise RuntimeError("Hikâye için Pexels videosu bulunamadı. " + " | ".join(errors[:4]))


def _normalize_story_clip(source: Path, destination: Path, seconds: float) -> None:
    # Long-form YouTube story: true 16:9, 1920x1080. Loop short source clips to
    # guarantee that each scene actually occupies its allocated duration.
    vf = "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=30,eq=contrast=1.03:saturation=1.05:brightness=0.01,zoompan=z='min(zoom+0.00035,1.06)':d=1:s=1920x1080:fps=30"
    command = [_ffmpeg(), "-y", "-stream_loop", "-1", "-i", str(source), "-t", f"{seconds:.2f}", "-vf", vf, "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", str(destination)]
    _run_ffmpeg(command, timeout=max(180, int(seconds * 6) + 120), context=f"story sahne normalize ({seconds:.0f}sn)")


def _concat(clips: list[Path], output: Path) -> None:
    list_file = output.parent / "story_concat.txt"
    list_file.write_text("\n".join(f"file '{p.as_posix()}'" for p in clips), encoding="utf-8")
    _run_ffmpeg([_ffmpeg(), "-y", "-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", "-movflags", "+faststart", str(output)], timeout=300, context="story sahne birlestirme")


def _tts(text: str, destination: Path) -> bool:
    try:
        import pyttsx3
        engine = pyttsx3.init()
        for voice in engine.getProperty("voices") or []:
            info = f"{getattr(voice, 'id', '')} {getattr(voice, 'name', '')}".lower()
            if any(x in info for x in ("turkish", "türk", "tr-tr", "tr_tr", "turkiye", "turkey")):
                engine.setProperty("voice", voice.id)
                break
        engine.setProperty("rate", int(os.getenv("AIVIDEO_TTS_RATE", "145")))
        engine.setProperty("volume", 1.0)
        engine.save_to_file(text, str(destination))
        engine.runAndWait()
        return destination.exists() and destination.stat().st_size > 0
    except Exception as exc:
        print(f"TTS devre dışı bırakıldı: {exc}", flush=True)
        return False


def _render_story(source: Path, audio: Path | None, output: Path, duration: int, title: str, music_enabled: bool, watermark_enabled: bool) -> Path:
    font = "/Windows/Fonts/arial.ttf" if os.name == "nt" else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    safe_title = re.sub(r"[^\w\u0080-\uFFFF .,!?;:'’()\-]", "", title).replace("'", "\\'")[:90]
    vf = f"drawtext=fontfile='{font}':text='{safe_title}':fontcolor=white@0.82:fontsize=38:x=(w-text_w)/2:y=60:box=1:boxcolor=black@0.22:boxborderw=16"
    inputs = ["-i", str(source)]
    filters = [f"[0:v]{vf}[base]"]
    label = "base"
    index = 1
    if watermark_enabled and WATERMARK_FILE.exists():
        inputs += ["-loop", "1", "-i", str(WATERMARK_FILE)]
        filters += [f"[1:v]scale={max(80, min(500, WATERMARK_WIDTH))}:-1,format=rgba,colorchannelmixer=aa={max(0.0, min(1.0, WATERMARK_OPACITY)):.3f}[wm]", "[base][wm]overlay=x=W-w-55:y=H-h-55:format=auto[vout]"]
        label = "vout"
        index = 2
    else:
        filters[0] = f"[0:v]{vf}[vout]"
        label = "vout"
    audio_args = ["-an"]
    if audio is not None and audio.exists():
        inputs += ["-i", str(audio)]
        narration_index = index
        if music_enabled and MUSIC_FILE.exists():
            inputs += ["-stream_loop", "-1", "-i", str(MUSIC_FILE)]
            music_index = narration_index + 1
            filters.append(f"[{narration_index}:a]volume=1.0[narr];[{music_index}:a]volume=0.10[mus];[narr][mus]amix=inputs=2:duration=first:dropout_transition=2[aout]")
            audio_args = ["-map", "[aout]", "-c:a", "aac", "-b:a", "128k", "-t", str(duration)]
        else:
            audio_args = ["-map", f"{narration_index}:a:0", "-c:a", "aac", "-b:a", "128k", "-t", str(duration)]
    command = [_ffmpeg(), "-y", *inputs, "-t", str(duration), "-filter_complex", ";".join(filters), "-map", f"[{label}]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", *audio_args, "-movflags", "+faststart", str(output)]
    _run_ffmpeg(command, timeout=max(300, duration * 4), context="story final render")
    return output


def generate_story_video(topic: str, minutes: int = 15, music_enabled: bool = True, watermark_enabled: bool = True) -> dict:
    job_id = uuid.uuid4().hex[:12]
    job_dir = OUTPUT_DIR / "jobs" / f"story_{job_id}"
    job_dir.mkdir(parents=True, exist_ok=True)
    story = generate_story_script(topic, minutes)
    (job_dir / "story_script.json").write_text(json.dumps(story, ensure_ascii=False, indent=2), encoding="utf-8")
    scenes = story["scenes"]
    scene_seconds = (minutes * 60) / len(scenes)
    clips, used = [], []
    for i, scene in enumerate(scenes, 1):
        raw = job_dir / f"story_scene_{i}.mp4"
        normalized = job_dir / f"story_scene_{i}_1080p.mp4"
        _pexels_video(scene["visual_query"], raw)
        _normalize_story_clip(raw, normalized, scene_seconds)
        clips.append(normalized)
        used.append(scene["visual_query"])
    montage = job_dir / "story_montage.mp4"
    _concat(clips, montage)
    narration = job_dir / "story_narration.wav"
    tts_ok = _tts("\n\n".join(s["narration"] for s in scenes), narration)
    output = job_dir / "aivideo_story.mp4"
    _render_story(montage, narration if tts_ok else None, output, minutes * 60, story["title"], music_enabled, watermark_enabled)
    latest = OUTPUT_DIR / "aivideo_story.mp4"
    try:
        shutil.copyfile(output, latest)
    except OSError:
        pass
    return {"ok": True, "job_id": job_id, "video_path": str(output), "script": story, "scenes": used, "narration_enabled": tts_ok, "music_enabled": bool(music_enabled and MUSIC_FILE.exists()), "watermark_enabled": bool(watermark_enabled and WATERMARK_FILE.exists()), "engine": "qwen3+pexels+ffmpeg-story-16x9+local-tts"}
