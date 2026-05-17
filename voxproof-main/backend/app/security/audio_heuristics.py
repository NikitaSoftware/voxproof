"""Audio-layer threat heuristics for VoxProof.

Detection techniques derived from 2024-2026 research:
- DolphinAttack (CCS 2017, dl.acm.org/doi/10.1145/3133956.3134052) — ultrasonic ≥20kHz commands
- NUIT (USENIX Security 2023) — near-ultrasound inaudible trojan via victim's own speaker
- AudioHijack (arXiv:2604.14604, IEEE S&P 2026) — adversarial LALM injection, ASR confidence collapse
- CommanderSong (arXiv:1801.08535) — adversarial audio embedded in carriers
- AdvPulse (CCS 2020) — sub-second universal perturbation
- Pause-pattern voice cloning (JMIR PMC11041410, 2024) — TTS clones have uniform inter-word gaps
- Cloned-voice formants (arXiv:2307.07683) — narrower F1-F3 bandwidth in synthetic speech
- Surfing/Acoustic-metamaterial attacks (arXiv:2501.15031, 2025) — directional inaudible

Two analysis modes:
- `AudioHeuristics.analyze(transcript, segments=None)` — transcript-only (always available)
- `SpectralHeuristics.analyze(pcm, sr)` — light spectral via numpy/scipy if PCM available
"""

from __future__ import annotations

import math
import re
import statistics
from dataclasses import dataclass
from typing import Optional

from app.schemas import Finding, Boundary, RiskType


@dataclass
class Segment:
    """One ASR segment with timing and confidence metadata."""
    text: str
    start: float = 0.0
    end: float = 0.0
    language: Optional[str] = None
    speaker: Optional[str] = None
    asr_confidence: Optional[float] = None  # whisper avg_logprob, typically -1.0..0.0


@dataclass
class AudioMeta:
    """Audio capture metadata (without raw PCM)."""
    sample_rate: int = 16000
    duration_sec: float = 0.0
    channels: int = 1


class AudioHeuristics:
    """Transcript-level audio-attack detection. CPU-only, no ML inference."""

    # --- Regex patterns ---
    MULTILINGUAL_PATTERN = re.compile(r'[а-яё].{0,30}[a-z]|[a-z].{0,30}[а-яё]', re.IGNORECASE)

    # Note: [whispered]/[background] markers are a SOFT prosody signal — not AudioHijack proper.
    # AudioHijack is adversarial LALM injection, detected via ASR confidence collapse (see #5 below).
    PROSODY_MARKER_PATTERN = re.compile(r'\[whispered\]|\[background\]|\(whisper\)|\(background\)', re.IGNORECASE)
    IMPERCEPTIBLE_PATTERN = re.compile(
        r'\[(imperceptible(?: audio)?|inaudible(?: audio)?|ultrasonic|hidden audio|adversarial audio|low volume|music bed)\]'
        r'|\((imperceptible(?: audio)?|inaudible(?: audio)?|ultrasonic|hidden audio|adversarial audio|low volume|music bed)\)'
        r'|not audible to (the )?user|embedded in (the )?(music|background audio)',
        re.IGNORECASE,
    )
    COVERT_COMMAND_PATTERN = re.compile(
        r'(do not tell|without telling|without notifying|silently|secretly).{0,80}'
        r'(approve|export|send|forward|ignore|override|verify|transfer)',
        re.IGNORECASE,
    )

    AUTHORITY_PATTERN = re.compile(
        r'(CFO|CEO|director|executive|president|head office|руководств|директор|исполнит)',
        re.IGNORECASE,
    )
    URGENCY_PATTERN = re.compile(
        r'(urgent|immediately|right now|done now|asap|срочно|немедленно|сейчас же)',
        re.IGNORECASE,
    )

    # --- Thresholds (calibrated against test scenarios) ---
    CODE_SWITCH_HIGH = 4.0       # switches/min — high anomaly
    CODE_SWITCH_LOW = 2.0        # switches/min — moderate anomaly
    SPEECH_RATE_ZSCORE_THRESH = 2.5
    PAUSE_STD_CLONE_THRESHOLD = 60.0   # ms — std below this is suspicious (TTS-uniform)
    PAUSE_MIN_SEGMENTS = 5
    ASR_CONFIDENCE_DROP = 0.4
    SPEAKER_OVERLAP_WINDOW = 5.0       # sec

    def analyze(
        self,
        transcript: str,
        segments: Optional[list[Segment]] = None,
        audio_meta: Optional[AudioMeta] = None,
    ) -> list[Finding]:
        """
        Detect audio-layer threats from transcript and optional segment metadata.

        - `transcript`: full text (always required).
        - `segments`: per-utterance metadata from ASR (Whisper/diarization) — enables advanced detection.
        - `audio_meta`: capture metadata (sample_rate matters for ultrasonic detection eligibility).
        """
        findings: list[Finding] = []

        # 1. Multilingual code-switching (transcript-only, always works)
        if self.MULTILINGUAL_PATTERN.search(transcript):
            findings.append(Finding(
                boundary=Boundary.AUDIO_LAYER,
                risk=RiskType.AUDIO_LAYER_ATTACK,
                severity=0.55,
                evidence="Mid-sentence language switch (RU↔EN) — guardrail-bypass pattern (Salesforce/Intercom 2026 field reports)",
            ))

        # 2. Prosody markers ([whispered], [background]) — soft signal, NOT AudioHijack
        if self.PROSODY_MARKER_PATTERN.search(transcript):
            findings.append(Finding(
                boundary=Boundary.AUDIO_LAYER,
                risk=RiskType.AUDIO_LAYER_ATTACK,
                severity=0.65,
                evidence="Prosody marker ([whispered]/[background]) in transcript — possible covert-channel embedding",
            ))

        if self.IMPERCEPTIBLE_PATTERN.search(transcript):
            findings.append(Finding(
                boundary=Boundary.AUDIO_LAYER,
                risk=RiskType.ADVERSARIAL_AUDIO,
                severity=0.82,
                evidence="Imperceptible/inaudible audio marker — auditory prompt injection risk (AudioHijack-style)",
            ))

        if self.COVERT_COMMAND_PATTERN.search(transcript):
            findings.append(Finding(
                boundary=Boundary.AUDIO_LAYER,
                risk=RiskType.AUDIO_LAYER_ATTACK,
                severity=0.74,
                evidence="Covert command asks the voice agent to act without user awareness",
            ))

        # 3. Combined authority + urgency = social engineering (boosted severity vs. either alone)
        has_auth = bool(self.AUTHORITY_PATTERN.search(transcript))
        has_urgency = bool(self.URGENCY_PATTERN.search(transcript))
        has_lang_switch = bool(self.MULTILINGUAL_PATTERN.search(transcript))
        if has_auth and has_urgency:
            base_sev = 0.65
            evidence_parts = ["authority claim", "urgency"]
            if has_lang_switch:
                base_sev = 0.85
                evidence_parts.append("language switch")
            findings.append(Finding(
                boundary=Boundary.USER_INPUT,
                risk=RiskType.SOCIAL_ENGINEERING,
                severity=base_sev,
                evidence=f"Social engineering combo: {' + '.join(evidence_parts)} (severity boosted from combined signals)",
            ))

        # Segment-based heuristics (require ASR segment metadata)
        if segments:
            findings.extend(self._analyze_segments(segments))

        return findings

    # --- Segment-level detectors ---

    def _analyze_segments(self, segments: list[Segment]) -> list[Finding]:
        out: list[Finding] = []

        # 4. Code-switch density (per minute of speech)
        cs_density, lang_switches = self._code_switch_density(segments)
        if cs_density >= self.CODE_SWITCH_HIGH:
            out.append(Finding(
                boundary=Boundary.AUDIO_LAYER,
                risk=RiskType.AUDIO_LAYER_ATTACK,
                severity=0.80,
                evidence=f"code_switch_density={cs_density:.1f}/min (≥{self.CODE_SWITCH_HIGH}) — adversarial language-guardrail bypass",
            ))
        elif cs_density >= self.CODE_SWITCH_LOW:
            out.append(Finding(
                boundary=Boundary.AUDIO_LAYER,
                risk=RiskType.AUDIO_LAYER_ATTACK,
                severity=0.55,
                evidence=f"code_switch_density={cs_density:.1f}/min — elevated for non-bilingual line",
            ))

        # 5. ASR confidence collapse — AudioHijack / adversarial perturbation signature
        # arXiv:2604.14604 IEEE S&P 2026: LALM injection causes ASR logit anomalies (AUC 0.71-0.85)
        max_drop = self._asr_confidence_collapse(segments)
        if max_drop >= self.ASR_CONFIDENCE_DROP:
            out.append(Finding(
                boundary=Boundary.AUDIO_LAYER,
                risk=RiskType.ADVERSARIAL_AUDIO,
                severity=0.75,
                evidence=f"asr_confidence_collapse drop={max_drop:.2f} between adjacent segments — AudioHijack adversarial-LALM signature (arXiv:2604.14604)",
            ))

        # 6. Pause uniformity — voice cloning detector
        # JMIR PMC11041410 (2024): TTS clones have inter-segment pauses with abnormally low std-dev
        pause_std, pause_count = self._pause_uniformity(segments)
        if pause_count >= self.PAUSE_MIN_SEGMENTS and pause_std is not None and pause_std < self.PAUSE_STD_CLONE_THRESHOLD:
            out.append(Finding(
                boundary=Boundary.AUDIO_LAYER,
                risk=RiskType.VOICE_CLONE,
                severity=0.60,
                evidence=f"pause_std={pause_std:.0f}ms over {pause_count} segments — TTS-uniform timing (JMIR 2024 deepfake signature)",
            ))

        # 7. Speaker overlap within 5s window — background-conversation embedding
        overlap_events = self._speaker_overlap(segments)
        if overlap_events:
            out.append(Finding(
                boundary=Boundary.AUDIO_LAYER,
                risk=RiskType.AUDIO_LAYER_ATTACK,
                severity=0.70,
                evidence=f"speaker_overlap_within_{self.SPEAKER_OVERLAP_WINDOW:.0f}s={overlap_events} — background-voice command embedding suspected",
            ))

        # 8. Speech rate z-score spikes
        rate_anomaly = self._speech_rate_anomaly(segments)
        if rate_anomaly is not None:
            z, wps = rate_anomaly
            out.append(Finding(
                boundary=Boundary.AUDIO_LAYER,
                risk=RiskType.AUDIO_LAYER_ATTACK,
                severity=0.55,
                evidence=f"speech_rate_z={z:.2f} (wps={wps:.1f}) — paralinguistic anomaly (AAAI 2025)",
            ))

        return out

    def _code_switch_density(self, segments: list[Segment]) -> tuple[float, int]:
        """Language flips per minute. Requires segment.language set."""
        langs = [s.language for s in segments if s.language]
        if len(langs) < 2:
            return 0.0, 0
        switches = sum(1 for a, b in zip(langs, langs[1:]) if a != b)
        duration = max(s.end for s in segments) - min(s.start for s in segments)
        minutes = max(duration / 60.0, 0.05)
        return switches / minutes, switches

    def _asr_confidence_collapse(self, segments: list[Segment]) -> float:
        """Max drop in asr_confidence between adjacent segments."""
        confs = [s.asr_confidence for s in segments if s.asr_confidence is not None]
        if len(confs) < 2:
            return 0.0
        max_drop = 0.0
        for a, b in zip(confs, confs[1:]):
            # whisper logprobs are negative — confidence "drops" when b is MORE negative than a
            drop = abs(b) - abs(a)
            if drop > max_drop:
                max_drop = drop
        return max_drop

    def _pause_uniformity(self, segments: list[Segment]) -> tuple[Optional[float], int]:
        """Std-dev of inter-segment pauses in ms. Low std = TTS-uniform = clone candidate."""
        pauses_ms = []
        for prev, cur in zip(segments, segments[1:]):
            gap = (cur.start - prev.end) * 1000.0
            if 50.0 <= gap <= 1500.0:  # only natural inter-word/segment pauses, not silence breaks
                pauses_ms.append(gap)
        if len(pauses_ms) < self.PAUSE_MIN_SEGMENTS:
            return None, len(pauses_ms)
        return statistics.stdev(pauses_ms), len(pauses_ms)

    def _speaker_overlap(self, segments: list[Segment]) -> int:
        """Count distinct-speaker overlaps within a SPEAKER_OVERLAP_WINDOW second window."""
        labeled = [s for s in segments if s.speaker]
        if len(labeled) < 2:
            return 0
        events = 0
        for i, a in enumerate(labeled):
            speakers_in_window = {a.speaker}
            for b in labeled[i + 1:]:
                if b.start - a.start > self.SPEAKER_OVERLAP_WINDOW:
                    break
                speakers_in_window.add(b.speaker)
            if len(speakers_in_window) >= 2:
                events += 1
        return events

    def _speech_rate_anomaly(self, segments: list[Segment]) -> Optional[tuple[float, float]]:
        """Z-score of segment words-per-second. Returns (z, wps) if |z|>=threshold."""
        rates = []
        for s in segments:
            dur = max(s.end - s.start, 0.1)
            wc = len(s.text.split())
            if wc >= 2 and dur >= 0.3:
                rates.append(wc / dur)
        if len(rates) < 3:
            return None
        mean = sum(rates) / len(rates)
        std = statistics.stdev(rates) if len(rates) > 1 else 0.0
        if std < 0.1:
            return None
        max_z = max((abs((r - mean) / std), r) for r in rates)
        if max_z[0] >= self.SPEECH_RATE_ZSCORE_THRESH:
            return max_z[0], max_z[1]
        return None


class SpectralHeuristics:
    """Light spectral analysis when raw PCM is available.

    Uses numpy + scipy.signal (no torch, no GPU). Returns Findings for:
    - DolphinAttack/NUIT: ultrasonic band energy ratio
    - CommanderSong/AdvPulse: sub-band kurtosis and transient pulse detection
    - Cloned voice: breath-frame count, formant bandwidth narrowness
    """

    ULTRASONIC_LOW_HZ = 16000
    ULTRASONIC_HIGH_HZ = 24000
    TELEPHONY_LOW_HZ = 300
    TELEPHONY_HIGH_HZ = 3400
    ULTRASONIC_RATIO_THRESHOLD = 0.01   # E[16-24k] / E[0.3-3.4k]
    SUBBAND_KURTOSIS_THRESHOLD = 8.0
    BREATH_MIN_PER_10S = 1              # zero breaths in continuous speech = suspicious

    def analyze(self, pcm, sample_rate: int) -> list[Finding]:
        """Run spectral checks. Returns empty list if numpy/scipy unavailable or PCM too short."""
        try:
            import numpy as np
            from scipy import signal as sps
        except ImportError:
            return []

        if pcm is None or len(pcm) < sample_rate // 2:  # need at least 0.5s
            return []

        findings: list[Finding] = []
        pcm_arr = np.asarray(pcm, dtype=np.float32)
        if pcm_arr.ndim > 1:
            pcm_arr = pcm_arr.mean(axis=-1)

        # 1. Ultrasonic energy ratio (DolphinAttack/NUIT) — only meaningful if sr ≥ 32 kHz
        if sample_rate >= 32000:
            f, psd = sps.welch(pcm_arr, sample_rate, nperseg=min(8192, len(pcm_arr)))
            tele_mask = (f >= self.TELEPHONY_LOW_HZ) & (f <= self.TELEPHONY_HIGH_HZ)
            ultra_mask = (f >= self.ULTRASONIC_LOW_HZ) & (f <= min(self.ULTRASONIC_HIGH_HZ, sample_rate / 2))
            tele_energy = float(psd[tele_mask].sum()) + 1e-12
            ultra_energy = float(psd[ultra_mask].sum())
            ratio = ultra_energy / tele_energy
            if ratio > self.ULTRASONIC_RATIO_THRESHOLD:
                findings.append(Finding(
                    boundary=Boundary.AUDIO_LAYER,
                    risk=RiskType.SPECTRAL_ANOMALY,
                    severity=0.92,
                    evidence=f"ultrasonic_ratio={ratio:.3f} ({self.ULTRASONIC_LOW_HZ}-{self.ULTRASONIC_HIGH_HZ}Hz vs telephony) — DolphinAttack/NUIT candidate (CCS 2017 / USENIX 2023)",
                ))

        # 2. Sub-band kurtosis (CommanderSong/AdvPulse adversarial residue in 1-4 kHz)
        try:
            from scipy.stats import kurtosis as scipy_kurtosis
            f, psd = sps.welch(pcm_arr, sample_rate, nperseg=min(4096, len(pcm_arr)))
            band_mask = (f >= 1000) & (f <= 4000)
            band_kurt = float(scipy_kurtosis(psd[band_mask]))
            if band_kurt > self.SUBBAND_KURTOSIS_THRESHOLD:
                findings.append(Finding(
                    boundary=Boundary.AUDIO_LAYER,
                    risk=RiskType.ADVERSARIAL_AUDIO,
                    severity=0.65,
                    evidence=f"subband_kurtosis(1-4kHz)={band_kurt:.1f} — CommanderSong/AdvPulse adversarial residue (arXiv:1801.08535)",
                ))
        except ImportError:
            pass

        # 3. Breath-frame count (cloned voice — JMIR 2024)
        frame_size = sample_rate // 50   # 20ms frames
        if frame_size > 0:
            energies_db = []
            for i in range(0, len(pcm_arr) - frame_size, frame_size):
                rms = float(np.sqrt(np.mean(pcm_arr[i:i + frame_size] ** 2)) + 1e-12)
                energies_db.append(20.0 * math.log10(rms))
            # Breaths: -45dB < energy < -30dB
            breath_frames = sum(1 for e in energies_db if -45.0 < e < -30.0)
            speech_frames = sum(1 for e in energies_db if e >= -30.0)
            duration_s = len(pcm_arr) / sample_rate
            # Only flag if continuous speech is long enough
            if speech_frames > 100 and duration_s >= 10 and breath_frames < self.BREATH_MIN_PER_10S * (duration_s / 10):
                findings.append(Finding(
                    boundary=Boundary.AUDIO_LAYER,
                    risk=RiskType.VOICE_CLONE,
                    severity=0.60,
                    evidence=f"breath_frames={breath_frames} over {duration_s:.0f}s ({speech_frames} speech frames) — synthetic-voice signature (JMIR PMC11041410)",
                ))

        return findings
