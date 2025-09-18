"""Offline sound recognition script for macOS using Vosk."""
from __future__ import annotations

import argparse
import json
import os
import queue
import sys
import threading
import time
from pathlib import Path
from typing import Iterable

try:
    import sounddevice as sd
except Exception as exc:  # pragma: no cover - import error feedback
    raise SystemExit(
        "sounddevice is required. Install dependencies from requirements.txt."
    ) from exc

try:
    import vosk
except Exception as exc:  # pragma: no cover - import error feedback
    raise SystemExit("vosk is required. Install dependencies from requirements.txt.") from exc

MODEL_URLS = {
    "en": "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip",
    "fr": "https://alphacephei.com/vosk/models/vosk-model-small-fr-0.22.zip",
}


def _download_model(url: str, destination: Path) -> None:
    """Download and extract a Vosk model if it is not already present."""
    import zipfile
    from urllib.request import urlretrieve

    destination.mkdir(parents=True, exist_ok=True)
    archive_path = destination / "model.zip"
    print(f"Downloading model from {url} ...")
    urlretrieve(url, archive_path)
    print("Extracting model...")
    with zipfile.ZipFile(archive_path, "r") as archive:
        archive.extractall(destination)
    archive_path.unlink(missing_ok=True)


def ensure_model(model_dir: Path, language: str) -> Path:
    """Ensure a language model is available and return its path."""
    if model_dir.exists():
        # If the directory already contains a model, return the first folder.
        for child in model_dir.iterdir():
            if child.is_dir():
                return child
    url = MODEL_URLS.get(language)
    if not url:
        supported = ", ".join(sorted(MODEL_URLS))
        raise ValueError(f"Unsupported language '{language}'. Supported: {supported}")

    _download_model(url, model_dir)
    for child in model_dir.iterdir():
        if child.is_dir():
            return child
    raise FileNotFoundError("Model extraction failed; no directory found after download.")


def recognize_stream(
    recognizer: "vosk.KaldiRecognizer",
    audio_stream: Iterable[bytes],
    *,
    show_partial: bool = False,
) -> Iterable[str]:
    """Yield recognition results for a stream of audio chunks."""
    for chunk in audio_stream:
        if recognizer.AcceptWaveform(chunk):
            result = json.loads(recognizer.Result())
            text = result.get("text", "").strip()
            if text:
                yield text
        elif show_partial:
            result = json.loads(recognizer.PartialResult())
            partial = result.get("partial", "").strip()
            if partial:
                yield partial
    final_result = json.loads(recognizer.FinalResult())
    final_text = final_result.get("text", "").strip()
    if final_text:
        yield final_text


def microphone_stream(sample_rate: int, block_size: int, channels: int = 1) -> Iterable[bytes]:
    """Create a generator that yields audio chunks recorded from the microphone."""
    audio_queue: "queue.Queue[bytes]" = queue.Queue()
    stream_closed = threading.Event()

    def _callback(indata, frames, time_info, status):  # pragma: no cover - interacts with hardware
        if status:
            print(status, file=sys.stderr)
        audio_queue.put(bytes(indata))

    def _producer():  # pragma: no cover - interacts with hardware
        with sd.RawInputStream(
            samplerate=sample_rate,
            blocksize=block_size,
            device=None,
            dtype="int16",
            channels=channels,
            callback=_callback,
        ):
            stream_closed.wait()

    thread = threading.Thread(target=_producer, daemon=True)
    thread.start()

    try:
        while True:
            chunk = audio_queue.get()
            yield chunk
    except KeyboardInterrupt:
        print("Stopping recognition...")
    finally:
        stream_closed.set()
        thread.join(timeout=1)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Offline speech recognition using Vosk.")
    parser.add_argument(
        "--language",
        default="en",
        help="Language model to use (default: en). Supported: %(choices)s" if MODEL_URLS else "en",
        choices=sorted(MODEL_URLS),
    )
    parser.add_argument(
        "--model-dir",
        type=Path,
        default=Path.home() / ".cache" / "vosk_models",
        help="Directory where Vosk models are stored.",
    )
    parser.add_argument(
        "--sample-rate",
        type=int,
        default=16_000,
        help="Sampling rate for recording.",
    )
    parser.add_argument(
        "--block-size",
        type=int,
        default=8_000,
        help="Buffer size for capturing audio frames.",
    )
    parser.add_argument(
        "--show-partial",
        action="store_true",
        help="Display partial recognition results while speaking.",
    )
    parser.add_argument(
        "--list-devices",
        action="store_true",
        help="List available audio devices and exit.",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=None,
        help="Optional duration in seconds to record before stopping automatically.",
    )
    return parser.parse_args(argv)


def list_audio_devices() -> None:
    """List available audio devices."""
    try:
        devices = sd.query_devices()
    except Exception as exc:  # pragma: no cover - depends on hardware
        raise SystemExit(f"Could not query audio devices: {exc}")
    for idx, device in enumerate(devices):  # pragma: no cover - depends on hardware
        print(f"#{idx}: {device['name']} - {device['max_input_channels']} input channels")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.list_devices:
        list_audio_devices()
        return 0

    try:
        model_path = ensure_model(args.model_dir, args.language)
    except Exception as exc:
        print(f"Failed to prepare model: {exc}", file=sys.stderr)
        return 1

    print(f"Using model at {model_path}")
    model = vosk.Model(str(model_path))
    recognizer = vosk.KaldiRecognizer(model, args.sample_rate)

    audio_iter = microphone_stream(args.sample_rate, args.block_size)

    deadline = time.time() + args.duration if args.duration else None
    try:
        for text in recognize_stream(recognizer, audio_iter, show_partial=args.show_partial):
            print(text)
            if deadline and time.time() >= deadline:
                break
    except KeyboardInterrupt:
        print("Interrupted by user.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
