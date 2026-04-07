"""Step 3c: Video Agent — multi-cut video generation synced to audio.

Architecture (WAT framework):
  This module is an AGENT that orchestrates three groups of TOOLS:

  ┌─────────────────────────────────────────────────────────────┐
  │  AUDIO TOOLS                                                 │
  │    build_ssml()          → SSML doc + segment metadata      │
  │    synthesize_audio()    → MP3 + per-segment timepoints      │
  ├─────────────────────────────────────────────────────────────┤
  │  CLIP TOOLS                                                  │
  │    pexels_search()       → MP4 URLs (with 3-tier fallback)   │
  │    download_clip()       → local MP4 path                   │
  │    veo_generate()        → AI-generated MP4 path            │
  │    create_card()         → branded PNG (intro / outro)      │
  ├─────────────────────────────────────────────────────────────┤
  │  EDIT TOOLS                                                  │
  │    extract_keyframes()   → list of PNG bytes (for VLM)      │
  │    vlm_score_clip()      → relevance score + reason         │
  │    best_clip_for_segment()→ pick/fallback per segment       │
  │    trim_to_duration()    → clip trimmed/looped to exact sec  │
  │    compose_timeline()    → final MP4 from ordered cuts      │
  └─────────────────────────────────────────────────────────────┘

Agent loop (video_agent):
  1. build_ssml + synthesize_audio → audio.mp3 + timepoints
  2. Convert timepoints → Timeline (list of AudioSegment windows)
  3. For each segment in parallel:
       a. Search Pexels with segment keywords (3-tier fallback)
       b. Score candidates with VLM
       c. Fall back to Veo if best score < 5
  4. Trim every clip to its exact audio window duration
  5. compose_timeline → final multi-cut MP4 synced to audio

Required env vars:
    GOOGLE_API_KEY            — Gemini API (Veo 3.1 + Gemini Flash VLM)
    PEXELS_API_KEY            — free at pexels.com/api
    GOOGLE_APPLICATION_CREDENTIALS  (or Cloud Run ADC) — for Cloud TTS

Usage:
    uv run python tools/generate_video.py \
        --input .tmp/newsletter_content.json \
        --topic "Telugu cinema" \
        --output .tmp/newsletter_video.mp4
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
from google import genai
from google.genai import types
from google.cloud import texttospeech

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ── constants ────────────────────────────────────────────────────────────────
TARGET_W, TARGET_H  = 1280, 720
TARGET_FPS          = 24
CARD_DURATION_S     = 3.0       # intro + outro card durations
WORD_BUDGET         = 290       # ~120s at 140 wpm

# brand palette (RGB)
BRAND_DARK   = (26, 34, 54)
BRAND_BLUE   = (47, 148, 251)
BRAND_DEEP   = (35, 103, 211)
BRAND_INDIGO = (75, 63, 224)

_FONT_BOLD    = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
_FONT_REGULAR = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"


# ── data classes ─────────────────────────────────────────────────────────────

@dataclass
class AudioSegment:
    """One named section of the voiceover audio with its time window."""
    name: str               # "intro", "section_0", "section_1", "closing"
    start_s: float          # start time in the audio (seconds)
    end_s: float            # end time in the audio (seconds)
    search_query: str       # Pexels search query for this segment
    veo_prompt: str         # Veo generation prompt as fallback
    use_card: bool = False  # True → use a static card instead of video clip

    @property
    def duration(self) -> float:
        return max(self.end_s - self.start_s, 0.5)


@dataclass
class ClipCandidate:
    """A video clip candidate with its VLM relevance score."""
    path: Path
    source: str     # "pexels" | "veo" | "card"
    score: int = 5  # VLM relevance score 1-10
    reason: str = ""


@dataclass
class Timeline:
    """Fully resolved edit plan: one ClipCandidate per AudioSegment."""
    audio_path: Path
    total_audio_duration: float
    cuts: list[tuple[AudioSegment, ClipCandidate]] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════
#  AUDIO TOOLS
# ═══════════════════════════════════════════════════════════════════════════════

def build_ssml(content: dict, topic: str) -> tuple[str, list[dict]]:
    """Build an SSML document with <mark> tags, returning (ssml_str, segment_meta).

    Each segment_meta entry:
        {"name": str, "search_query": str, "veo_prompt": str, "use_card": bool}

    SSML mark names map 1-to-1 with segment_meta names so timepoints can be
    matched back to segment metadata after synthesis.
    """
    date_str   = datetime.now().strftime("%Y-%m-%d")
    headline   = _xml(content.get("headline", topic))
    subtitle   = _xml(content.get("subtitle", ""))
    summary    = _xml(content.get("summary", ""))
    sections   = content.get("sections", [])
    topic_esc  = _xml(topic)

    segments_meta: list[dict] = []
    lines: list[str] = ["<speak>"]

    # ── Intro segment (use branded card) ────────────────────────────────────
    segments_meta.append({
        "name": "intro",
        "search_query": topic,
        "veo_prompt": f"Cinematic b-roll establishing shot related to {topic}.",
        "use_card": True,
    })
    lines.append(f'<mark name="intro"/>')
    lines.append(
        f'Welcome to your AI Newsletter. <break time="300ms"/>'
        f"Today&#x2019;s edition: "
        f'<emphasis level="strong">{headline}</emphasis>.'
    )
    if subtitle:
        lines.append(f'<break time="200ms"/>{subtitle}.')

    # ── Summary segment ──────────────────────────────────────────────────────
    if summary:
        segments_meta.append({
            "name": "summary",
            "search_query": f"{topic} overview",
            "veo_prompt": (
                f"Wide cinematic establishing shot for a news story about {topic}. "
                "Professional documentary style, natural light."
            ),
            "use_card": False,
        })
        lines.append('<break time="500ms"/>')
        lines.append(f'<mark name="summary"/>')
        lines.append(summary)

    # ── Per-section segments ─────────────────────────────────────────────────
    word_count = sum(len(l.split()) for l in lines)
    for i, section in enumerate(sections):
        body     = _xml(section.get("body", "").strip())
        heading  = _xml(section.get("heading", ""))
        key_stat = _xml(section.get("key_stat", "") or "")
        if not body:
            continue

        block_words = body.split()
        remaining   = WORD_BUDGET - word_count - 20
        if remaining <= 0:
            break
        if len(block_words) > remaining:
            body = " ".join(block_words[:remaining]) + "&#x2026;"

        seg_name = f"section_{i}"
        # Build a 2-5 word Pexels query from heading + first words of body
        pexels_q = _pexels_query_for_section(
            heading, section.get("body", ""), topic
        )
        veo_p = (
            f"Cinematic b-roll footage, no text, no on-screen speech. "
            f"Visual representation of: {heading or topic}. "
            f"{section.get('body', '')[:150]}. "
            "Professional news broadcast style."
        )
        segments_meta.append({
            "name": seg_name,
            "search_query": pexels_q,
            "veo_prompt": veo_p,
            "use_card": False,
        })

        lines.append(f'<break time="500ms"/>')
        lines.append(f'<mark name="{seg_name}"/>')
        if heading:
            lines.append(
                f'<emphasis level="moderate">{heading}.</emphasis><break time="200ms"/>'
            )
        lines.append(body)
        if key_stat:
            lines.append(
                f'<break time="300ms"/>'
                f'<prosody rate="slow">{key_stat}</prosody>'
                f'<break time="300ms"/>'
            )
        word_count += len(body.split())

    # ── Closing segment (use outro card) ────────────────────────────────────
    segments_meta.append({
        "name": "closing",
        "search_query": topic,
        "veo_prompt": "",
        "use_card": True,
    })
    lines.append(
        f'<break time="600ms"/>'
        f'<mark name="closing"/>'
        f"That&#x2019;s your {topic_esc} briefing for "
        f'<say-as interpret-as="date" format="yyyymmdd" detail="1">'
        f'{date_str}</say-as>. '
        f'<break time="200ms"/>Stay informed, and we&#x2019;ll see you next time.'
    )
    lines.append("</speak>")

    ssml = "\n".join(lines)
    return ssml, segments_meta


def synthesize_audio(ssml: str, output_path: Path) -> tuple[Path, list[dict]]:
    """Call Google Cloud TTS with time-pointing enabled.

    Returns:
        (mp3_path, timepoints)
        timepoints: [{"name": str, "time_s": float}, ...]
    """
    client  = texttospeech.TextToSpeechClient()
    request = texttospeech.SynthesizeSpeechRequest(
        input=texttospeech.SynthesisInput(ssml=ssml),
        voice=texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name="en-US-Neural2-D",
            ssml_gender=texttospeech.SsmlVoiceGender.MALE,
        ),
        audio_config=texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=0.95,
        ),
        enable_time_pointing=["SSML_MARK"],
    )
    response = client.synthesize_speech(request=request)
    output_path.write_bytes(response.audio_content)

    timepoints = [
        {"name": tp.mark_name, "time_s": tp.time_seconds}
        for tp in response.timepoints
    ]
    print(
        f"  [Audio] {len(response.audio_content):,} bytes, "
        f"{len(timepoints)} timepoints",
        file=sys.stderr,
    )
    return output_path, timepoints


def build_timeline_segments(
    segments_meta: list[dict],
    timepoints: list[dict],
    total_duration: float,
) -> list[AudioSegment]:
    """Merge segment metadata with TTS timepoints to produce AudioSegment windows.

    If a mark is missing from timepoints (TTS sometimes omits marks at t=0),
    the segment gets a 0.1s start time as fallback.
    """
    tp_map = {tp["name"]: tp["time_s"] for tp in timepoints}

    # Build ordered list of (name, start_time)
    ordered: list[tuple[str, float]] = []
    for meta in segments_meta:
        name = meta["name"]
        t    = tp_map.get(name, None)
        if t is None:
            # Try to estimate from position
            t = ordered[-1][1] + 2.0 if ordered else 0.0
            print(
                f"  [Timeline] Mark '{name}' missing from timepoints, "
                f"estimated at {t:.1f}s",
                file=sys.stderr,
            )
        ordered.append((name, t))

    # Build AudioSegment objects with start/end windows
    audio_segments: list[AudioSegment] = []
    meta_by_name   = {m["name"]: m for m in segments_meta}
    for i, (name, start_s) in enumerate(ordered):
        end_s = ordered[i + 1][1] if i + 1 < len(ordered) else total_duration
        meta  = meta_by_name[name]
        audio_segments.append(AudioSegment(
            name         = name,
            start_s      = start_s,
            end_s        = end_s,
            search_query = meta["search_query"],
            veo_prompt   = meta["veo_prompt"],
            use_card     = meta["use_card"],
        ))
        print(
            f"  [Timeline] {name:15s} {start_s:6.1f}s → {end_s:6.1f}s "
            f"({end_s - start_s:.1f}s)",
            file=sys.stderr,
        )

    return audio_segments


def get_audio_duration(audio_path: Path) -> float:
    """Return audio duration in seconds using ffprobe."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)],
            capture_output=True, text=True, timeout=10,
        )
        return float(result.stdout.strip())
    except Exception:
        return 120.0  # fallback


# ═══════════════════════════════════════════════════════════════════════════════
#  CLIP TOOLS
# ═══════════════════════════════════════════════════════════════════════════════

def pexels_search(query: str, n: int = 4) -> list[str]:
    """Search Pexels Videos API; return up to n direct MP4 URLs."""
    api_key = os.getenv("PEXELS_API_KEY", "")
    if not api_key:
        return []
    try:
        resp = requests.get(
            "https://api.pexels.com/videos/search",
            headers={"Authorization": api_key},
            params={"query": query, "per_page": n + 2, "size": "medium"},
            timeout=15,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"  [Pexels] '{query}': {exc}", file=sys.stderr)
        return []
    urls = []
    for video in resp.json().get("videos", []):
        url = _best_pexels_file(video.get("video_files", []))
        if url:
            urls.append(url)
            if len(urls) >= n:
                break
    return urls


def pexels_search_with_fallback(segment: AudioSegment, topic: str) -> list[str]:
    """Three-tier Pexels search for a segment:
    1. Segment-specific query
    2. Individual words from the query
    3. Generic visual keywords for the topic genre
    """
    seen: set[str] = set()
    urls: list[str] = []

    def _add(new_urls: list[str]):
        for u in new_urls:
            if u not in seen:
                seen.add(u)
                urls.append(u)

    # Tier 1 — specific query
    _add(pexels_search(segment.search_query, n=3))

    # Tier 2 — individual keywords
    if len(urls) < 2:
        for kw in segment.search_query.split()[:3]:
            if len(urls) >= 3:
                break
            _add(pexels_search(kw, n=2))

    # Tier 3 — topic-level genre fallback
    if len(urls) < 1:
        print(
            f"  [Pexels] No results for '{segment.search_query}', "
            f"using genre fallback for '{topic}'",
            file=sys.stderr,
        )
        for kw in _genre_fallback_keywords(topic):
            if len(urls) >= 2:
                break
            _add(pexels_search(kw, n=2))

    return urls


def download_clip(url: str, dest: Path) -> Optional[Path]:
    """Download a single MP4 clip. Returns dest or None on failure."""
    try:
        resp = requests.get(url, stream=True, timeout=60)
        resp.raise_for_status()
        with dest.open("wb") as fh:
            for chunk in resp.iter_content(chunk_size=256 * 1024):
                fh.write(chunk)
        size_mb = dest.stat().st_size / (1024 * 1024)
        print(f"  [Clip] Downloaded {dest.name} ({size_mb:.1f} MB)", file=sys.stderr)
        return dest
    except Exception as exc:
        print(f"  [Clip] SKIP {dest.name}: {exc}", file=sys.stderr)
        return None


def veo_generate(prompt: str, dest: Path) -> Optional[Path]:
    """Generate a single AI video clip via Veo 3.1. Returns dest or None."""
    api_key = os.getenv("GOOGLE_API_KEY", "")
    if not api_key:
        return None
    try:
        client    = genai.Client(api_key=api_key)
        operation = client.models.generate_videos(
            model="veo-3.1-generate-preview",
            prompt=prompt,
            config=types.GenerateVideosConfig(aspect_ratio="16:9", duration_seconds=6),
        )
        deadline = time.time() + 90
        while not operation.done and time.time() < deadline:
            time.sleep(5)
            operation = client.operations.get(operation)
        if operation.done and operation.response:
            video = operation.response.generated_videos[0].video
            dest.write_bytes(client.files.download(file=video))
            size_mb = dest.stat().st_size / (1024 * 1024)
            print(f"  [Veo] {dest.name} ({size_mb:.1f} MB)", file=sys.stderr)
            return dest
        print(f"  [Veo] Timed out for: {prompt[:60]}...", file=sys.stderr)
    except Exception as exc:
        print(f"  [Veo] Error: {exc}", file=sys.stderr)
    return None


def create_card(text: str, output_path: Path, card_type: str = "intro") -> Path:
    """Render a branded 1280×720 PNG card (intro or outro)."""
    W, H = TARGET_W, TARGET_H
    img  = Image.new("RGB", (W, H), color=BRAND_DARK)
    draw = ImageDraw.Draw(img)

    # Top accent bar
    draw.rectangle([(0, 0), (W, 8)], fill=BRAND_BLUE)

    try:
        f_big  = ImageFont.truetype(_FONT_BOLD, 52)
        f_sm   = ImageFont.truetype(_FONT_BOLD, 26)
        f_date = ImageFont.truetype(_FONT_REGULAR, 22)
    except (IOError, OSError):
        f_big = f_sm = f_date = ImageFont.load_default()

    label = "AI NEWSLETTER" if card_type == "intro" else "STAY INFORMED"
    bbox  = draw.textbbox((0, 0), label, font=f_sm)
    draw.text(((W - (bbox[2] - bbox[0])) // 2, 150), label, font=f_sm, fill=BRAND_BLUE)
    draw.rectangle([(W // 2 - 60, 193), (W // 2 + 60, 196)], fill=BRAND_INDIGO)

    for idx, line in enumerate(_wrap(text, 38)):
        bbox = draw.textbbox((0, 0), line, font=f_big)
        lw   = bbox[2] - bbox[0]
        y    = H // 2 - (len(_wrap(text, 38)) * 70 // 2) + 20 + idx * 70
        draw.text(((W - lw) // 2, y), line, font=f_big, fill=(255, 255, 255))

    date_str = datetime.now().strftime("%B %d, %Y")
    bbox = draw.textbbox((0, 0), date_str, font=f_date)
    draw.text((W - (bbox[2] - bbox[0]) - 40, H - 56), date_str,
              font=f_date, fill=(170, 170, 170))

    img.save(str(output_path), format="PNG")
    return output_path


# ═══════════════════════════════════════════════════════════════════════════════
#  EDIT TOOLS
# ═══════════════════════════════════════════════════════════════════════════════

def extract_keyframes(clip_path: Path, n: int = 3) -> list[bytes]:
    """Extract n evenly-spaced frames from a video as PNG bytes (via ffmpeg)."""
    frames = []
    try:
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(clip_path)],
            capture_output=True, text=True, timeout=10,
        )
        duration = float(probe.stdout.strip() or "6")
        step     = max(duration / (n + 1), 0.3)
        for i in range(1, n + 1):
            r = subprocess.run(
                ["ffmpeg", "-ss", str(step * i), "-i", str(clip_path),
                 "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"],
                capture_output=True, timeout=15,
            )
            if r.returncode == 0 and r.stdout:
                frames.append(r.stdout)
    except Exception as exc:
        print(f"  [Frames] {clip_path.name}: {exc}", file=sys.stderr)
    return frames


def vlm_score_clip(
    clip_path: Path,
    search_query: str,
    segment_name: str,
) -> ClipCandidate:
    """Ask Gemini 2.5 Flash to score a clip's visual relevance (1-10)."""
    api_key = os.getenv("GOOGLE_API_KEY", "")
    if not api_key:
        return ClipCandidate(path=clip_path, source="pexels", score=6,
                             reason="VLM skipped (no API key)")

    frames = extract_keyframes(clip_path, n=3)
    if not frames:
        return ClipCandidate(path=clip_path, source="pexels", score=5,
                             reason="No frames extracted")

    client = genai.Client(api_key=api_key)
    prompt = (
        f"You are a video editor. These 3 frames are from a stock footage clip.\n"
        f"The clip will be used for the '{segment_name}' segment of a news video about: "
        f"'{search_query}'.\n\n"
        "Score its visual relevance 1-10 (10 = perfect match, 1 = irrelevant).\n"
        "Return JSON only: {\"score\": 7, \"reason\": \"one sentence\"}"
    )
    parts: list = [prompt]
    for fb in frames:
        parts.append(types.Part.from_bytes(data=fb, mime_type="image/png"))

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=parts,
        )
        text = response.text.strip()
        text = re.sub(r"^```[a-z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
        data = json.loads(text)
        return ClipCandidate(
            path=clip_path, source="pexels",
            score=int(data.get("score", 5)),
            reason=data.get("reason", ""),
        )
    except Exception as exc:
        print(f"  [VLM] Score failed for {clip_path.name}: {exc}", file=sys.stderr)
        return ClipCandidate(path=clip_path, source="pexels", score=5,
                             reason=f"VLM error: {exc}")


def best_clip_for_segment(
    segment: AudioSegment,
    topic: str,
    tmp_dir: Path,
    seg_index: int,
) -> ClipCandidate:
    """Acquire and select the best clip for one audio segment.

    Decision tree:
    1. Search Pexels (3-tier fallback) → download candidates → VLM-score each
    2. If best Pexels score >= 6 → use it
    3. Otherwise try Veo 3.1 → VLM-score the Veo clip
    4. Return whichever scored higher (Pexels wins ties)
    5. If both fail, fall back to the top Pexels candidate regardless of score
    """
    print(f"  [Edit] Segment '{segment.name}': query='{segment.search_query}'",
          file=sys.stderr)

    # Pexels candidates
    pexels_urls = pexels_search_with_fallback(segment, topic)
    pexels_candidates: list[ClipCandidate] = []
    for idx, url in enumerate(pexels_urls[:3]):
        dest = tmp_dir / f"pexels_{seg_index}_{idx}.mp4"
        path = download_clip(url, dest)
        if path:
            cand = vlm_score_clip(path, segment.search_query, segment.name)
            cand.source = "pexels"
            pexels_candidates.append(cand)
            print(
                f"    Pexels candidate {idx}: score={cand.score} ({cand.reason[:60]})",
                file=sys.stderr,
            )

    best_pexels = max(pexels_candidates, key=lambda c: c.score) if pexels_candidates else None

    # If Pexels looks good, use it straight away (skip Veo to save time)
    if best_pexels and best_pexels.score >= 6:
        print(f"  [Edit] '{segment.name}' → Pexels (score {best_pexels.score})",
              file=sys.stderr)
        return best_pexels

    # Try Veo as alternative
    veo_candidate: Optional[ClipCandidate] = None
    if segment.veo_prompt and os.getenv("GOOGLE_API_KEY"):
        veo_dest = tmp_dir / f"veo_{seg_index}.mp4"
        veo_path = veo_generate(segment.veo_prompt, veo_dest)
        if veo_path:
            veo_cand = vlm_score_clip(veo_path, segment.search_query, segment.name)
            veo_cand.source = "veo"
            veo_candidate = veo_cand
            print(
                f"  [Edit] '{segment.name}' Veo score={veo_cand.score} "
                f"({veo_cand.reason[:60]})",
                file=sys.stderr,
            )

    # Pick winner
    all_candidates = ([best_pexels] if best_pexels else [])
    if veo_candidate:
        all_candidates.append(veo_candidate)

    if all_candidates:
        winner = max(all_candidates, key=lambda c: c.score)
        print(f"  [Edit] '{segment.name}' → {winner.source} (score {winner.score})",
              file=sys.stderr)
        return winner

    raise RuntimeError(
        f"Could not acquire any clip for segment '{segment.name}'. "
        "Check PEXELS_API_KEY and GOOGLE_API_KEY."
    )


def trim_to_duration(clip_path: Path, duration: float, dest: Path) -> Path:
    """Trim or loop a video clip to exactly `duration` seconds using ffmpeg.

    If the clip is shorter than duration, it is looped seamlessly.
    Output is always scaled to 1280×720, audio stripped.
    """
    vf = f"scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=decrease," \
         f"pad={TARGET_W}:{TARGET_H}:(ow-iw)/2:(oh-ih)/2,setsar=1"

    # Check source clip duration
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(clip_path)],
        capture_output=True, text=True, timeout=10,
    )
    try:
        src_dur = float(probe.stdout.strip())
    except ValueError:
        src_dur = duration

    if src_dur >= duration:
        # Simple trim
        cmd = [
            "ffmpeg", "-y",
            "-i", str(clip_path),
            "-t", str(duration),
            "-vf", vf,
            "-an",                  # strip audio
            "-r", str(TARGET_FPS),
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
            str(dest),
        ]
    else:
        # Loop: repeat enough times then trim
        loops = int(duration / src_dur) + 2
        cmd = [
            "ffmpeg", "-y",
            "-stream_loop", str(loops),
            "-i", str(clip_path),
            "-t", str(duration),
            "-vf", vf,
            "-an",
            "-r", str(TARGET_FPS),
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
            str(dest),
        ]

    result = subprocess.run(cmd, capture_output=True, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg trim failed for {clip_path.name}:\n"
            f"{result.stderr.decode(errors='replace')[-500:]}"
        )
    return dest


def compose_timeline(timeline: Timeline, output_path: Path) -> Path:
    """Assemble the final multi-cut MP4 from the resolved timeline.

    Each cut is a pre-trimmed, 720p silent clip (produced by trim_to_duration).
    We concatenate them with ffmpeg concat demuxer, then mux in the TTS audio
    delayed by CARD_DURATION_S (so the branded intro card plays silently first).
    """
    tmp_dir    = output_path.parent
    concat_txt = tmp_dir / "concat_list.txt"
    lines      = []

    for i, (seg, cand) in enumerate(timeline.cuts):
        dest = tmp_dir / f"cut_{i:03d}_{seg.name}.mp4"
        if cand.source == "card":
            # Static image → silent video via ffmpeg
            _card_to_video(cand.path, dest, seg.duration)
        else:
            trim_to_duration(cand.path, seg.duration, dest)
        # escape backslashes for ffmpeg on Windows
        safe_path = str(dest).replace("\\", "/")
        lines.append(f"file '{safe_path}'")

    concat_txt.write_text("\n".join(lines), encoding="utf-8")

    # Concatenate all clips into silent_video.mp4
    silent_out = tmp_dir / "silent_video.mp4"
    result = subprocess.run(
        ["ffmpeg", "-y",
         "-f", "concat", "-safe", "0", "-i", str(concat_txt),
         "-c", "copy",
         str(silent_out)],
        capture_output=True, timeout=180,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg concat failed:\n"
            f"{result.stderr.decode(errors='replace')[-500:]}"
        )

    # Mux in TTS audio (starts at CARD_DURATION_S)
    # Total video = CARD_DURATION_S (intro card) + total_audio_duration
    # Audio starts at CARD_DURATION_S, so we pad with silence at the start.
    result2 = subprocess.run(
        ["ffmpeg", "-y",
         "-i", str(silent_out),
         "-itsoffset", str(CARD_DURATION_S),
         "-i", str(timeline.audio_path),
         "-map", "0:v:0",
         "-map", "1:a:0",
         "-c:v", "copy",
         "-c:a", "aac",
         "-shortest",
         str(output_path)],
        capture_output=True, timeout=120,
    )
    if result2.returncode != 0:
        raise RuntimeError(
            f"ffmpeg mux failed:\n"
            f"{result2.stderr.decode(errors='replace')[-500:]}"
        )

    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"  [Compose] Done: {output_path.name} ({size_mb:.1f} MB)", file=sys.stderr)
    return output_path


def _card_to_video(png_path: Path, dest: Path, duration: float) -> Path:
    """Render a static PNG as a silent MP4 for the given duration."""
    result = subprocess.run(
        ["ffmpeg", "-y",
         "-loop", "1", "-i", str(png_path),
         "-t", str(duration),
         "-vf", f"scale={TARGET_W}:{TARGET_H},setsar=1",
         "-r", str(TARGET_FPS),
         "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
         "-an",
         str(dest)],
        capture_output=True, timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Card-to-video failed:\n"
            f"{result.stderr.decode(errors='replace')[-300:]}"
        )
    return dest


# ═══════════════════════════════════════════════════════════════════════════════
#  VIDEO AGENT
# ═══════════════════════════════════════════════════════════════════════════════

def video_agent(content: dict, topic: str, output_path: Path) -> Path:
    """Orchestrate all tools to produce a multi-cut video synced to audio.

    Agent decision loop:
    1. AUDIO TOOLS  → build SSML + synthesize → timepoints
    2. AUDIO TOOLS  → build timeline segments from timepoints
    3. CLIP TOOLS   → create intro/outro cards
    4. For each non-card segment (in parallel):
           CLIP TOOLS  → Pexels search with fallback
           EDIT TOOLS  → VLM score each candidate
           CLIP TOOLS  → Veo fallback if Pexels score < 6
    5. EDIT TOOLS   → trim every clip to its exact window duration
    6. EDIT TOOLS   → compose_timeline → final multi-cut MP4
    """
    tmp_dir  = output_path.parent
    headline = content.get("headline", topic)

    print("\n  ╔══ Video Agent ════════════════════════════════╗", file=sys.stderr)

    # ── AUDIO TOOLS ─────────────────────────────────────────────────────────
    print("  ║  [1/4] Audio tools: SSML → TTS → timepoints", file=sys.stderr)
    ssml, segments_meta = build_ssml(content, topic)
    audio_path          = tmp_dir / "voiceover.mp3"
    audio_path, tps     = synthesize_audio(ssml, audio_path)
    total_dur           = get_audio_duration(audio_path)
    print(f"  ║         Total audio: {total_dur:.1f}s, marks: {len(tps)}",
          file=sys.stderr)

    audio_segments = build_timeline_segments(segments_meta, tps, total_dur)

    # ── CLIP TOOLS: cards ────────────────────────────────────────────────────
    print("  ║  [2/4] Clip tools: creating intro/outro cards", file=sys.stderr)
    intro_card_path = tmp_dir / "card_intro.png"
    outro_card_path = tmp_dir / "card_outro.png"
    create_card(headline, intro_card_path, card_type="intro")
    create_card("Stay Informed", outro_card_path, card_type="outro")

    # ── CLIP + EDIT TOOLS: acquire best clip per segment (parallel) ──────────
    print("  ║  [3/4] Clip + edit tools: acquiring clips per segment",
          file=sys.stderr)

    resolved: dict[str, ClipCandidate] = {}

    def _acquire_segment(seg: AudioSegment, idx: int):
        if seg.use_card:
            card_path = intro_card_path if seg.name == "intro" else outro_card_path
            return seg.name, ClipCandidate(path=card_path, source="card", score=10)
        try:
            cand = best_clip_for_segment(seg, topic, tmp_dir, idx)
            return seg.name, cand
        except Exception as exc:
            print(f"  ║  [Agent] Segment '{seg.name}' failed: {exc}", file=sys.stderr)
            # Return intro card as last resort so pipeline doesn't die
            return seg.name, ClipCandidate(path=intro_card_path, source="card",
                                           score=1, reason="fallback")

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {
            pool.submit(_acquire_segment, seg, i): seg
            for i, seg in enumerate(audio_segments)
        }
        for fut in as_completed(futures):
            seg_name, cand = fut.result()
            resolved[seg_name] = cand

    # ── EDIT TOOLS: build & compose timeline ─────────────────────────────────
    print("  ║  [4/4] Edit tools: multi-cut compose", file=sys.stderr)

    # Intro card segment gets CARD_DURATION_S prepended (silent branded opening)
    # Its AudioSegment window covers the "intro" voiceover (may be a few seconds),
    # but we always guarantee at least CARD_DURATION_S of intro card.
    intro_seg = next((s for s in audio_segments if s.name == "intro"), None)
    if intro_seg:
        intro_seg.end_s = max(intro_seg.end_s, CARD_DURATION_S)

    timeline = Timeline(
        audio_path           = audio_path,
        total_audio_duration = total_dur,
        cuts = [
            (seg, resolved[seg.name])
            for seg in audio_segments
            if seg.name in resolved
        ],
    )

    result = compose_timeline(timeline, output_path)

    total_dur_out = total_dur + CARD_DURATION_S
    print(
        f"  ║  Done. {len(timeline.cuts)} cuts, "
        f"~{total_dur_out:.0f}s total",
        file=sys.stderr,
    )
    print("  ╚═══════════════════════════════════════════════╝", file=sys.stderr)
    return result


# ═══════════════════════════════════════════════════════════════════════════════
#  Public entry point (called from main.py)
# ═══════════════════════════════════════════════════════════════════════════════

def generate_video(content: dict, topic: str, output_path: Path) -> Path:
    """Public API — wraps video_agent for use by the newsletter pipeline."""
    return video_agent(content, topic, output_path)


# ═══════════════════════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _xml(text: str) -> str:
    """Escape XML special chars and strip markdown/URLs for safe SSML embedding."""
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"\*+", "", text)
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = text.replace('"', "&quot;")
    return re.sub(r"\s+", " ", text).strip()


def _wrap(text: str, max_chars: int) -> list[str]:
    words = text.split()
    lines, cur = [], ""
    for w in words:
        t = f"{cur} {w}".strip()
        if len(t) <= max_chars:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _best_pexels_file(video_files: list[dict]) -> Optional[str]:
    mp4 = [f for f in video_files if f.get("file_type") == "video/mp4"]
    if not mp4:
        return None
    hd = [f for f in mp4 if f.get("width") == 1280 and f.get("height") == 720]
    if hd:
        return hd[0]["link"]
    ok = sorted([f for f in mp4 if (f.get("width") or 0) <= 1920],
                key=lambda f: f.get("width") or 0, reverse=True)
    return ok[0]["link"] if ok else mp4[0].get("link")


def _pexels_query_for_section(heading: str, body: str, topic: str) -> str:
    """Build a 2-4 word Pexels search query from section content."""
    stop = {"the","a","an","in","of","and","or","for","to","is","are","was",
            "were","on","at","by","with","from","that","this","its","their",
            "have","has","been","will","new","your","our"}
    text  = re.sub(r"[^a-z0-9\s]", " ", f"{heading} {body[:100]}".lower())
    words = [w for w in text.split() if w not in stop and len(w) > 3]
    seen, unique = set(), []
    for w in words:
        if w not in seen:
            seen.add(w)
            unique.append(w)
    kws = unique[:3]
    return " ".join(kws) if kws else topic


def _genre_fallback_keywords(topic: str) -> list[str]:
    """Return reliable Pexels search terms for a given topic genre."""
    mapping = {
        "cinema": ["film", "movie", "entertainment"],
        "technology": ["technology", "computer", "innovation"],
        "ai": ["technology", "future", "innovation"],
        "business": ["business", "office", "finance"],
        "sports": ["sports", "athletics", "competition"],
        "health": ["healthcare", "wellness", "medicine"],
        "politics": ["government", "city", "people"],
        "finance": ["finance", "money", "economy"],
    }
    tl = topic.lower()
    for key, kws in mapping.items():
        if key in tl:
            return kws
    return ["city", "people", "nature"]


# ═══════════════════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Video Agent — Step 3c")
    parser.add_argument("--input",  type=Path,
                        default=PROJECT_ROOT / ".tmp" / "newsletter_content.json")
    parser.add_argument("--output", type=Path,
                        default=PROJECT_ROOT / ".tmp" / "newsletter_video.mp4")
    parser.add_argument("--topic",  default="news")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"ERROR: {args.input} not found", file=sys.stderr)
        sys.exit(1)

    content = json.loads(args.input.read_text(encoding="utf-8"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result = generate_video(content, args.topic, args.output)
    print(str(result))


if __name__ == "__main__":
    main()
