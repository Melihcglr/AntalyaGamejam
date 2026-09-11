#!/usr/bin/env bash
# Jarvis Asistan geliştirme ortamı kurulumu (idempotent).
set -euo pipefail

# Sistem bağımlılıkları: venv, Python başlıkları (PyAudio derleme),
# tkinter (pyautogui/mouseinfo import'u), portaudio (PyAudio), espeak (pyttsx3), libgl (opencv).
sudo apt-get update -qq
sudo apt-get install -y -qq \
  python3-venv python3-dev python3-tk build-essential \
  portaudio19-dev libespeak1 espeak libgl1

cd "$(dirname "$0")/../asistan"

if [ ! -x ".venv/bin/python" ]; then
  python3 -m venv .venv
fi
.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

# İlk çalıştırmada örnek yapılandırmadan config.json üret.
if [ ! -f config.json ]; then
  cp config.example.json config.json
fi

echo "Jarvis kurulum tamam."
