# Offline Sound Recognition on macOS

This folder contains a Python script that performs speech recognition entirely offline using [Vosk](https://alphacephei.com/vosk/). The code is designed for macOS laptops (including Apple Silicon) and relies on lightweight "small" Vosk acoustic models that run on-device without an internet connection.

## Features

- ✅ Offline recognition using efficient Vosk small models (English and French examples included).
- 🎧 Live transcription from the MacBook microphone using CoreAudio through the `sounddevice` library.
- 🧩 Automatic download and extraction of the selected model on first run.
- 🛠️ Command line options for listing audio devices, limiting recording duration, and showing partial results.

## Requirements

1. Python 3.9 or newer (3.11 recommended on macOS).
2. Xcode Command Line Tools (for building native dependencies on the first installation):
   ```bash
   xcode-select --install
   ```
3. Create a virtual environment and install dependencies:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

The `requirements.txt` file is at the repository root and contains the following runtime dependencies:

- `sounddevice` – captures audio using the CoreAudio backend.
- `vosk` – lightweight offline speech recognition engine.
- `numpy` – required by both libraries.

## Downloading Models

On the first run the script automatically downloads the selected language model into `~/\.cache/vosk_models`. The included language codes and corresponding small models are:

| Language | Code | Model Size |
|----------|------|------------|
| English  | `en` | ~50 MB |
| French   | `fr` | ~55 MB |

To use a different model, download it from the [Vosk model list](https://alphacephei.com/vosk/models) and pass the directory via `--model-dir`.

## Usage

```bash
python sound_recognition/offline_sound_recognizer.py
```

Optional flags:

- `--language en` – Language code (defaults to English). Must be one of the supported codes in the script.
- `--model-dir /path/to/models` – Directory where models are stored (default: `~/\.cache/vosk_models`).
- `--show-partial` – Print partial results while speaking.
- `--duration 30` – Stop automatically after the given number of seconds.
- `--list-devices` – Show available audio devices and exit.

Example session:

```bash
python sound_recognition/offline_sound_recognizer.py --language en --show-partial
```

Press `Ctrl+C` to stop the recognizer at any time.

## Troubleshooting

- **No audio input detected**: Run with `--list-devices` to see if the microphone appears. If not, grant microphone permission to the terminal (System Settings → Privacy & Security → Microphone).
- **Crackling audio**: Reduce the `--block-size` (e.g., 4000) to lower latency on slower CPUs.
- **Model download blocked**: Manually download the ZIP file and place the extracted folder inside the directory given by `--model-dir`.

## Additional Notes

- The script uses `sd.RawInputStream` to avoid NumPy conversions for every chunk, which keeps CPU usage low.
- Models are cached on disk, so subsequent runs start immediately without extra downloads.
- Vosk can also load command grammars or speaker diarization models if you need more advanced features.
