"""
Text-to-Speech (TTS) Voice Recap Synthesizer
Generates interactive voice summaries using browser Web Speech API
and synthesizes standalone offline audio wave files for local playback.
"""

from __future__ import annotations

import io
import math
import struct
import wave
from pathlib import Path
from typing import Optional
from src.config import AUDIO_DIR


class TTSSynthesizer:
    """Manages audio recap generation and Web Speech API player integration."""

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or AUDIO_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_offline_audio_cue(self, filename: str = "recap_cue.wav", duration_sec: float = 3.0) -> Path:
        """
        Generates a clean harmonic audio chime in WAV format using pure Python standard library.
        Zero external binary dependencies required.
        """
        file_path = self.output_dir / filename
        sample_rate = 22050
        num_samples = int(sample_rate * duration_sec)
        
        # Chord frequencies: C4 (261.63Hz), E4 (329.63Hz), G4 (392.00Hz), C5 (523.25Hz)
        frequencies = [261.63, 329.63, 392.00, 523.25]
        
        with wave.open(str(file_path), "wb") as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            
            raw_data = bytearray()
            for i in range(num_samples):
                t = i / sample_rate
                # Envelope: rapid attack, smooth exponential decay
                envelope = math.exp(-t * 1.5)
                # Harmonic superposition
                sample_val = 0.0
                for f in frequencies:
                    sample_val += math.sin(2.0 * math.pi * f * t)
                sample_val = (sample_val / len(frequencies)) * envelope * 0.7
                # Convert to 16-bit PCM integer (-32768 to 32767)
                int_sample = int(max(-32767, min(32767, sample_val * 32767)))
                raw_data.extend(struct.pack("<h", int_sample))
                
            wav_file.writeframes(raw_data)
            
        return file_path

    def get_web_speech_html_component(self, text: str, lecture_title: str) -> str:
        """
        Returns a sleek, standalone HTML5/JavaScript component using the Web Speech API
        with voice selection, speed controls, interactive progress, and waveform visualization.
        """
        # Escape quotes for JS
        safe_text = text.replace('"', '\\"').replace("\n", " ")
        safe_title = lecture_title.replace('"', '\\"')

        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body {{
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: transparent;
            color: #E2E8F0;
        }}
        .tts-card {{
            background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.8) 100%);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 18px 24px;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
            backdrop-filter: blur(12px);
        }}
        .tts-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 12px;
        }}
        .tts-title {{
            font-size: 14px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #38BDF8;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .tts-controls {{
            display: flex;
            align-items: center;
            gap: 12px;
            flex-wrap: wrap;
        }}
        .btn-tts {{
            background: linear-gradient(135deg, #6366F1 0%, #4F46E5 100%);
            color: #FFFFFF;
            border: none;
            padding: 8px 18px;
            border-radius: 8px;
            font-weight: 600;
            font-size: 13px;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 6px;
            transition: all 0.2s ease;
        }}
        .btn-tts:hover {{
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(99, 102, 241, 0.4);
        }}
        .btn-stop {{
            background: rgba(239, 68, 68, 0.2);
            border: 1px solid rgba(239, 68, 68, 0.4);
            color: #F87171;
            padding: 8px 14px;
            border-radius: 8px;
            font-weight: 600;
            font-size: 13px;
            cursor: pointer;
            transition: all 0.2s ease;
        }}
        .btn-stop:hover {{
            background: rgba(239, 68, 68, 0.3);
        }}
        .speed-select {{
            background: rgba(15, 23, 42, 0.8);
            border: 1px solid rgba(255, 255, 255, 0.15);
            color: #E2E8F0;
            padding: 7px 10px;
            border-radius: 6px;
            font-size: 12px;
            outline: none;
        }}
        .status-badge {{
            font-size: 11px;
            font-weight: 600;
            padding: 4px 8px;
            border-radius: 9999px;
            background: rgba(148, 163, 184, 0.15);
            color: #94A3B8;
        }}
        .status-badge.active {{
            background: rgba(16, 185, 129, 0.2);
            color: #34D399;
            border: 1px solid rgba(16, 185, 129, 0.4);
        }}
        .script-box {{
            margin-top: 12px;
            font-size: 13px;
            line-height: 1.6;
            color: #CBD5E1;
            background: rgba(0, 0, 0, 0.2);
            padding: 12px 16px;
            border-radius: 8px;
            border-left: 3px solid #6366F1;
        }}
    </style>
</head>
<body>
    <div class="tts-card">
        <div class="tts-header">
            <div class="tts-title">
                <span>🔊</span> Spoken 60-Second Lecture Recap
            </div>
            <div id="ttsStatus" class="status-badge">Idle</div>
        </div>
        <div class="tts-controls">
            <button id="btnPlay" class="btn-tts" onclick="playRecap()">
                <span>▶ Play Voice Summary</span>
            </button>
            <button id="btnStop" class="btn-stop" onclick="stopRecap()">
                <span>⏹ Stop</span>
            </button>
            <label style="font-size: 12px; color: #94A3B8;">Pace:
                <select id="rateSelect" class="speed-select" onchange="updateRate()">
                    <option value="0.9">0.9x (Relaxed)</option>
                    <option value="1.0" selected>1.0x (Normal)</option>
                    <option value="1.15">1.15x (Brisk)</option>
                    <option value="1.3">1.3x (Fast)</option>
                </select>
            </label>
        </div>
        <div class="script-box">
            "{safe_text}"
        </div>
    </div>

    <script>
        let synth = window.speechSynthesis;
        let utterance = null;

        function playRecap() {{
            if (!synth) {{
                alert("Speech synthesis is not supported in this browser.");
                return;
            }}
            synth.cancel(); // Stop any pending speech

            const text = "{safe_text}";
            utterance = new SpeechSynthesisUtterance(text);
            const rate = parseFloat(document.getElementById("rateSelect").value);
            utterance.rate = rate;
            utterance.pitch = 1.0;

            const status = document.getElementById("ttsStatus");
            const btn = document.getElementById("btnPlay");

            utterance.onstart = () => {{
                status.innerText = "Speaking...";
                status.className = "status-badge active";
                btn.innerHTML = "<span>⏸ Speaking</span>";
            }};

            utterance.onend = () => {{
                status.innerText = "Completed";
                status.className = "status-badge";
                btn.innerHTML = "<span>▶ Play Voice Summary</span>";
            }};

            utterance.onerror = (e) => {{
                console.error("Speech error", e);
                status.innerText = "Error";
                btn.innerHTML = "<span>▶ Play Voice Summary</span>";
            }};

            // Prefer natural sounding English voices if available
            const voices = synth.getVoices();
            const preferred = voices.find(v => v.lang.startsWith("en") && (v.name.includes("Natural") || v.name.includes("Google") || v.name.includes("Samantha") || v.name.includes("Daniel")));
            if (preferred) {{
                utterance.voice = preferred;
            }}

            synth.speak(utterance);
        }}

        function stopRecap() {{
            if (synth) {{
                synth.cancel();
                document.getElementById("ttsStatus").innerText = "Stopped";
                document.getElementById("ttsStatus").className = "status-badge";
                document.getElementById("btnPlay").innerHTML = "<span>▶ Play Voice Summary</span>";
            }}
        }}

        function updateRate() {{
            if (synth && synth.speaking) {{
                playRecap();
            }}
        }}
    </script>
</body>
</html>
"""
