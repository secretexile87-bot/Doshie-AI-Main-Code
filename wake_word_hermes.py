#!/usr/bin/env python3
"""Hermes Offline Wake Word Listener for Doshie.

Runs quietly in the background using openwakeword.
When wake word is detected, activates the live conversational assistant.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import numpy as np
import pyaudio
import openwakeword
from openwakeword.model import Model

FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 1280  # 80ms chunks for openwakeword


def play_chime():
    """Play a short chime beep when wake word is triggered."""
    os.system("paplay /usr/share/sounds/freedesktop/stereo/message.oga 2>/dev/null || (speaker-test -t sine -f 880 -l 1 >/dev/null 2>&1 &)")


def run_wake_listener(model_names: list[str] | None = None, threshold: float = 0.5):
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)

    # Initialize openWakeWord
    print("🧠 Loading local wake word detection models...")
    owwModel = Model(inference_framework="onnx")
    active_models = model_names or list(owwModel.models.keys())
    print(f"✅ Wake models active: {', '.join(active_models)}")
    print("=" * 60)
    print("🎙️  Hermes Wake Word Listener is Active (Standing by)")
    print("👉  Say 'Hey Jarvis' or 'Alexa' to wake up Hermes. Press Ctrl+C to exit.")
    print("=" * 60)

    try:
        while True:
            audio_data = np.frombuffer(stream.read(CHUNK, exception_on_overflow=False), dtype=np.int16)
            prediction = owwModel.predict(audio_data)

            for mdl, score in owwModel.prediction_buffer.items():
                if len(score) > 0 and score[-1] >= threshold:
                    print(f"\n✨ Wake word detected ({mdl}: {score[-1]:.2f})! Activating Hermes...")
                    play_chime()
                    
                    # Pause mic stream while active session runs
                    stream.stop_stream()
                    python_bin = sys.executable
                    script_path = os.path.expanduser("~/live_voice_hermes.py")
                    subprocess.run([python_bin, script_path])
                    
                    print("\n🎙️  Returning to wake word standby mode...")
                    owwModel.reset()
                    stream.start_stream()

    except KeyboardInterrupt:
        print("\nStopping wake word listener...")
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()


def main():
    parser = argparse.ArgumentParser(description="Hermes Offline Wake Word Listener")
    parser.add_argument("--threshold", type=float, default=0.5, help="Detection threshold (0.1 to 0.9)")
    args = parser.parse_args()
    run_wake_listener(threshold=args.threshold)


if __name__ == "__main__":
    main()
