"""Build the final demo video from screenshots + Gemini TTS audio.

Each narration segment is held over a relevant screenshot for its full audio
duration — no loading spinners, no error states, no sync drift.

Output: docs/voxproof_demo.mp4 (overwrites the Playwright screencast version)

Run:
    python3 docs/generate_demo_video.py
Prereqs: ffmpeg, screenshots in docs/screenshots/, voiceover wavs in docs/voiceover/
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

ROOT = Path(__file__).parent
SHOTS = ROOT / "screenshots"
VOICE = ROOT / "voiceover"
TITLES = ROOT / "titles"
TITLES.mkdir(exist_ok=True)

if shutil.which("ffmpeg") is None:
    print("ERROR: ffmpeg not found in PATH", file=sys.stderr)
    sys.exit(1)


# ── Title card generator (PIL — generates branded overlay frames) ────────────
def make_title_card(text: str, subtitle: str, output: Path,
                    width: int = 1920, height: int = 1200,
                    bg=(9, 9, 11), fg=(255, 255, 255), accent=(16, 185, 129)):
    """Generate a dark title card with VoxProof branding."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("WARN: Pillow not installed — skipping title card", flush=True)
        return None

    img = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(img)

    # Try common system fonts (Helvetica Neue on macOS, fallback chain)
    def load_font(size, bold=True):
        candidates = [
            "/System/Library/Fonts/HelveticaNeue.ttc",
            "/System/Library/Fonts/Supplemental/Helvetica.ttc",
            "/Library/Fonts/Arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]
        for c in candidates:
            if Path(c).exists():
                try:
                    return ImageFont.truetype(c, size)
                except Exception:
                    continue
        return ImageFont.load_default()

    # Brand chip
    chip_x, chip_y = 90, 90
    draw.rounded_rectangle((chip_x, chip_y, chip_x + 60, chip_y + 60),
                           radius=14, fill=accent)
    f_chip = load_font(28)
    draw.text((chip_x + 12, chip_y + 14), "VP", fill=(255, 255, 255), font=f_chip)
    f_brand = load_font(28)
    draw.text((chip_x + 80, chip_y + 18), "VoxProof", fill=(255, 255, 255), font=f_brand)

    # Headline
    f_title = load_font(108)
    lines = []
    cur = ""
    for word in text.split():
        if len(cur + " " + word) > 28:
            lines.append(cur); cur = word
        else:
            cur = (cur + " " + word).strip()
    if cur: lines.append(cur)
    y = height // 2 - (len(lines) * 130) // 2
    for line in lines:
        draw.text((90, y), line, fill=fg, font=f_title)
        y += 130

    if subtitle:
        f_sub = load_font(36)
        draw.text((90, y + 30), subtitle, fill=(161, 161, 170), font=f_sub)

    # Track badges at bottom
    f_chip2 = load_font(22)
    draw.rounded_rectangle((90, height - 130, 470, height - 80),
                           radius=10, fill=accent)
    draw.text((110, height - 117), "TRACK 1 · LOBSTER TRAP", fill=(6, 78, 59), font=f_chip2)
    draw.rounded_rectangle((490, height - 130, 870, height - 80),
                           radius=10, fill=(245, 158, 11))
    draw.text((510, height - 117), "TRACK 2 · GEMINI 2.5", fill=(24, 24, 27), font=f_chip2)

    img.save(output, "PNG")
    return output


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as r:
        return r.getnframes() / float(r.getframerate())


# ── Storyboard: map each voiceover shot → background image ────────────────────
# (audio_filename, image_path_or_title, optional_title_text, optional_subtitle)
STORY = [
    ("01_open.wav",
     SHOTS / "02_attack_suite.png", None, None),                              # incidents hook → trust gauge visual
    ("02_identity.wav",
     SHOTS / "01_login.png", None, None),                                     # brand + features
    ("03_playground_intro.wav",
     SHOTS / "03_playground_gemini_judge.png", None, None),                   # preview judge
    ("03_playground_judge.wav",
     SHOTS / "03_playground_gemini_judge.png", None, None),                   # judge in action
    ("04_wire_attack.wav",
     SHOTS / "04_playground_wire_attack.png", None, None),                    # tool policy
    ("05_rag_intro.wav",
     "title", "EchoLeak · ForcedLeak",
     "CVE-2025-32711 · CVSS 9.3 · CVSS 9.4 · Indirect injection · Markdown egress"),
    ("05_rag_outcome.wav",
     SHOTS / "05_rag_demo.png", None, None),                                  # sanitization diff
    ("06_suite.wav",
     SHOTS / "02_attack_suite.png", None, None),                              # 12 scenarios result
    ("07_threat_model.wav",
     "title", "Honest threat model",
     "We catch what is real. We declare what is not. L1 acoustic — out of scope."),
    ("08_close.wav",
     SHOTS / "01_login.png", None, None),                                     # brand close
]


# ── Build clips ───────────────────────────────────────────────────────────────
def build_clips(workdir: Path) -> list[Path]:
    clips: list[Path] = []
    for i, (wav, img_spec, title, subtitle) in enumerate(STORY):
        wav_path = VOICE / wav
        if not wav_path.exists():
            print(f"  ! missing {wav_path}", flush=True)
            continue
        dur = wav_duration(wav_path)

        if isinstance(img_spec, Path):
            image_path = img_spec
        else:
            # Generate title card on the fly
            tc = TITLES / f"{i:02d}_title.png"
            make_title_card(title or "VoxProof", subtitle or "", tc)
            image_path = tc

        clip_path = workdir / f"clip_{i:02d}.mp4"
        # Loop the still image for `dur` seconds, scale to 1920x1200, encode silent
        subprocess.run([
            "ffmpeg", "-y", "-loglevel", "error",
            "-loop", "1", "-i", str(image_path),
            "-t", f"{dur:.3f}",
            "-vf", "scale=1920:1200:force_original_aspect_ratio=decrease,"
                   "pad=1920:1200:(ow-iw)/2:(oh-ih)/2:color=0xfafafa,format=yuv420p",
            "-c:v", "libx264", "-preset", "medium", "-crf", "20",
            "-r", "30", "-pix_fmt", "yuv420p",
            "-an",
            str(clip_path),
        ], check=True)
        clips.append(clip_path)
        print(f"  ✓ clip_{i:02d}.mp4 · {dur:.1f}s · {Path(image_path).name}", flush=True)
    return clips


def concat_clips(clips: list[Path], workdir: Path, out_video_only: Path):
    list_file = workdir / "concat.txt"
    list_file.write_text("\n".join(f"file '{c.resolve()}'" for c in clips))
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", str(list_file),
        "-c", "copy",
        str(out_video_only),
    ], check=True)


def mux_audio(video_only: Path, audio: Path, final: Path):
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(video_only), "-i", str(audio),
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        "-shortest",
        str(final),
    ], check=True)


if __name__ == "__main__":
    audio = ROOT / "voiceover.wav"
    if not audio.exists():
        print(f"ERROR: {audio} not found — run docs/generate_voiceover.py first", file=sys.stderr)
        sys.exit(1)

    with tempfile.TemporaryDirectory() as td:
        workdir = Path(td)
        print(f"\nbuilding {len(STORY)} clips in {workdir}\n", flush=True)
        clips = build_clips(workdir)
        if not clips:
            print("ERROR: no clips produced", file=sys.stderr)
            sys.exit(1)
        video_only = workdir / "video_only.mp4"
        concat_clips(clips, workdir, video_only)
        print("\nmuxing audio…", flush=True)
        final = ROOT / "voxproof_demo.mp4"
        mux_audio(video_only, audio, final)

    # Report
    size_mb = final.stat().st_size / 1024 / 1024
    import json
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "format=duration:stream=width,height", "-of", "json", str(final)],
        capture_output=True, text=True,
    )
    info = json.loads(probe.stdout)
    dur = float(info["format"]["duration"])
    w = info["streams"][0]["width"]; h = info["streams"][0]["height"]
    print(f"\n✓ {final}")
    print(f"  {dur:.1f}s · {w}x{h} · {size_mb:.1f}MB")
    print("\nLinkedIn-ready. Upload directly or run a final retime in iMovie.")
