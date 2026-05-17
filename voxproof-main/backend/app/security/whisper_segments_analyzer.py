"""Whisper JSON segment analyzer.

Converts a Whisper transcription response (segments with avg_logprob,
no_speech_prob, compression_ratio, language) into our `Segment` dataclass
and runs `AudioHeuristics._analyze_segments` for ASR-confidence-collapse,
code-switch density, pause uniformity, etc.

Reference: OpenAI Whisper docs (segment fields), HuggingFace `transformers`
`AutomaticSpeechRecognitionPipeline` output schema.
"""

from __future__ import annotations

from typing import Any

from app.schemas import Finding, Boundary, RiskType
from app.security.audio_heuristics import AudioHeuristics, Segment


class WhisperSegmentsAnalyzer:
    """Adapter that converts Whisper JSON to our Segment + runs heuristics."""

    def __init__(self, audio_heuristics: AudioHeuristics | None = None):
        self.audio = audio_heuristics or AudioHeuristics()

    def from_whisper_json(self, whisper_response: dict[str, Any]) -> list[Segment]:
        """Parse openai-whisper / faster-whisper / transformers Whisper output."""
        raw_segments = whisper_response.get("segments", [])
        segments: list[Segment] = []
        for s in raw_segments:
            segments.append(Segment(
                text=s.get("text", "").strip(),
                start=float(s.get("start", 0.0)),
                end=float(s.get("end", 0.0)),
                language=s.get("language") or whisper_response.get("language"),
                speaker=s.get("speaker"),
                asr_confidence=s.get("avg_logprob"),
            ))
        return segments

    def analyze_whisper_response(self, whisper_response: dict[str, Any]) -> list[Finding]:
        segments = self.from_whisper_json(whisper_response)
        if not segments:
            return []
        findings = self.audio._analyze_segments(segments)

        # Additional Whisper-specific signals
        for s in whisper_response.get("segments", []):
            comp_ratio = s.get("compression_ratio", 1.0)
            if comp_ratio and float(comp_ratio) > 2.4:
                findings.append(Finding(
                    boundary=Boundary.AUDIO_LAYER,
                    risk=RiskType.ADVERSARIAL_AUDIO,
                    severity=0.68,
                    evidence=f"Whisper compression_ratio={float(comp_ratio):.2f} (>2.4) — repetition/looping signature of adversarial or synthetic audio",
                ))
                break
            no_speech_prob = s.get("no_speech_prob", 0.0)
            if no_speech_prob and float(no_speech_prob) > 0.8 and len((s.get("text") or "").strip()) > 5:
                findings.append(Finding(
                    boundary=Boundary.AUDIO_LAYER,
                    risk=RiskType.ADVERSARIAL_AUDIO,
                    severity=0.72,
                    evidence=f"Whisper no_speech_prob={float(no_speech_prob):.2f} but produced text — universal-perturbation signature (Raina arXiv:2405.06134 'Muting Whisper')",
                ))
                break

        return findings
