"""Generate professional voiceover for VoxProof demo using Gemini 2.5 Flash TTS.

Strategically uses the same Gemini API key already in .env — adds another
Gemini integration point to the Track 2 hackathon narrative (TTS = on-brand).

Run:
    python3 docs/generate_voiceover.py
Output:
    docs/voiceover/01_open.wav      ← per-shot files
    docs/voiceover/02_identity.wav
    ...
    docs/voiceover.wav              ← concatenated full track aligned to video timing
    docs/voiceover.mp3              ← compressed version for LinkedIn

Optional merge with screencast (requires ffmpeg):
    ffmpeg -i docs/screenshots/voxproof_demo.webm -i docs/voiceover.wav \\
        -c:v copy -c:a aac -shortest docs/voxproof_demo.mp4
"""
from __future__ import annotations

import base64
import json
import os
import struct
import sys
import wave
from pathlib import Path
from typing import Optional

import httpx
from dotenv import load_dotenv

# ── Setup ─────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env")
API_KEY = os.environ.get("GEMINI_API_KEY", "")
if not API_KEY:
    print("ERROR: GEMINI_API_KEY not set in .env or environment", file=sys.stderr)
    sys.exit(1)

BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
TTS_MODEL = "gemini-2.5-flash-preview-tts"
VOICE = os.environ.get("VOXPROOF_VOICE", "Charon")     # deep professional male
SAMPLE_RATE = 24_000

OUT_DIR = Path(__file__).parent / "voiceover"
OUT_DIR.mkdir(exist_ok=True)


# ── Script (lifted from video_script.md, prosody-tuned) ──────────────────────
# Each shot: (filename, target_duration_sec, narration_text)
# "(pause)" markers map to wider gaps in Gemini's natural speech delivery.
SHOTS = [
    ("01_open", 10,
     "In February 2024, an Arup finance employee in Hong Kong wired "
     "twenty-five point six million dollars to attackers after a video call with a deepfake CFO. "
     "In 2025, Microsoft 365 Copilot lost CVSS nine point three to a zero-click RAG injection. "
     "Salesforce Agentforce — nine point four."),

    ("02_identity", 15,
     "Voice AI agents are taking over banking, support, and helpdesk. "
     "The attack surface is brand new — and there is no runtime security layer for it. "
     "VoxProof is that layer. Three tracks: audio, transcript, tool-call. "
     "Built on Lobster Trap MIT and Gemini 2.5."),

    ("03_playground_intro", 7,
     "Watch what happens when I send a Russian-language jailbreak to the voice agent."),

    ("03_playground_judge", 15,
     "Gemini 2.5 Flash, running as a runtime security judge, flags this as a direct jailbreak "
     "with ninety-eight percent confidence. The reasoning is generated live. "
     "Regex would miss this. Local DeBERTa is English-only. Gemini catches both the language and the intent."),

    ("04_wire_attack", 17,
     "Now the tool-call boundary. The caller asks the agent to approve a wire transfer. "
     "VoxProof's policy engine — backed by OWASP LLM06 — denies it with audit evidence: "
     "wire transfers must use the bank's authenticated channel. "
     "This is the Arup lesson, encoded as policy."),

    ("05_rag_intro", 12,
     "Most enterprise attacks come not through the user, but through the data the agent retrieves. "
     "EchoLeak — Microsoft 365 Copilot, June 2025, CVSS nine point three. "
     "ForcedLeak — Salesforce Agentforce, September 2025, CVSS nine point four. "
     "Both are zero-click."),

    ("05_rag_outcome", 17,
     "VoxProof strips three zero-width Unicode characters, removes the hidden HTML comment "
     "carrying the override instruction, and blocks the Markdown-image exfiltration URL "
     "on the agent's outbound channel. The agent never reads the leak. "
     "The user never even knows it was attempted. Full audit evidence is captured."),

    ("06_suite", 18,
     "Twelve adversarial scenarios, executed against a stock voice agent without guardrails. "
     "Trust score: twelve out of one hundred. Ten out of twelve scenarios fail. "
     "For each failure, Gemini 2.5 Pro generates auditable evidence — root cause plus remediation. "
     "This is the compliance artifact your security team needs."),

    ("07_threat_model", 20,
     "One thing we will not claim. DolphinAttack and NUIT — ultrasonic injection at twenty kilohertz — "
     "those are real research. They are also not real threats for a cloud telephony gateway. "
     "Telephony codecs eat ultrasound before our service ever sees it. "
     "Saying so explicitly is what separates an honest threat model from marketing. "
     "We catch what is real: voice cloning, vishing, prompt injection, tool boundary abuse, data egress."),

    ("08_close", 15,
     "VoxProof. The voice interface is the new SQL injection surface. We are the prepared statement. "
     "Built on Lobster Trap MIT and Gemini 2.5. "
     "Live demo. Code open-source. Twelve attack scenarios. Audit evidence built in."),
]

TARGET_TOTAL_SEC = sum(d for _, d, _ in SHOTS)
print(f"Target total duration: {TARGET_TOTAL_SEC}s · voice='{VOICE}' · model='{TTS_MODEL}'", flush=True)


# ── TTS call ─────────────────────────────────────────────────────────────────
def gemini_tts(text: str, voice: str = VOICE) -> bytes:
    """Return raw 16-bit signed-PCM mono @ 24kHz for the narration."""
    r = httpx.post(
        f"{BASE_URL}/models/{TTS_MODEL}:generateContent",
        params={"key": API_KEY},
        json={
            "contents": [{"parts": [{"text": text}]}],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}
                },
            },
        },
        timeout=120,
    )
    r.raise_for_status()
    data = r.json()
    try:
        inline = data["candidates"][0]["content"]["parts"][0]["inlineData"]
        return base64.b64decode(inline["data"])
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"unexpected TTS response: {json.dumps(data)[:400]}") from e


def pcm_to_wav(pcm_bytes: bytes, path: Path, sample_rate: int = SAMPLE_RATE):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)        # 16-bit
        w.setframerate(sample_rate)
        w.writeframes(pcm_bytes)


def wav_duration_sec(path: Path) -> float:
    with wave.open(str(path), "rb") as r:
        return r.getnframes() / float(r.getframerate())


def silence_pcm(seconds: float, sample_rate: int = SAMPLE_RATE) -> bytes:
    samples = int(seconds * sample_rate)
    return b"\x00\x00" * samples


# ── Pipeline ─────────────────────────────────────────────────────────────────
def synthesize_all() -> list[tuple[str, int, bytes]]:
    out: list[tuple[str, int, bytes]] = []
    for fname, target_dur, text in SHOTS:
        path = OUT_DIR / f"{fname}.wav"
        print(f"  → synthesizing {fname} (target {target_dur}s)…", flush=True)
        pcm = gemini_tts(text)
        pcm_to_wav(pcm, path)
        actual = wav_duration_sec(path)
        print(f"    saved {path.name} · {actual:.1f}s actual · target {target_dur}s", flush=True)
        out.append((fname, target_dur, pcm))
    return out


def concatenate(shots: list[tuple[str, int, bytes]], out_wav: Path):
    """Concat per-shot PCM with silence padding to hit each shot's target duration."""
    combined = bytearray()
    for fname, target_dur, pcm in shots:
        combined.extend(pcm)
        actual_sec = len(pcm) / 2 / SAMPLE_RATE
        gap = max(0.5, target_dur - actual_sec)   # at least 0.5s breath between shots
        combined.extend(silence_pcm(gap))
    pcm_to_wav(bytes(combined), out_wav)
    print(f"\ncombined → {out_wav} · {wav_duration_sec(out_wav):.1f}s total", flush=True)


def try_convert_mp3(wav_path: Path) -> Optional[Path]:
    """Try ffmpeg → mp3. Skip silently if ffmpeg is unavailable."""
    import shutil, subprocess
    if not shutil.which("ffmpeg"):
        print("(ffmpeg not found — skipping mp3 conversion)", flush=True)
        return None
    mp3_path = wav_path.with_suffix(".mp3")
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(wav_path), "-codec:a", "libmp3lame",
         "-qscale:a", "2", str(mp3_path)],
        capture_output=True, check=True,
    )
    print(f"mp3 → {mp3_path}", flush=True)
    return mp3_path


if __name__ == "__main__":
    shots = synthesize_all()
    full = Path(__file__).parent / "voiceover.wav"
    concatenate(shots, full)
    try_convert_mp3(full)
    print("\nDone.")
    print(f"  Per-shot WAVs: {OUT_DIR}")
    print(f"  Full track: {full}")
    print("\nMerge with screencast (needs ffmpeg):")
    print(f"  ffmpeg -i docs/screenshots/voxproof_demo.webm -i {full.name} \\")
    print( "    -c:v copy -c:a aac -shortest docs/voxproof_demo.mp4")
