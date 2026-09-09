$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".venv\Scripts\python.exe")) {
  Write-Host "[Jarvis] Sanal ortam olusturuluyor..."
  python -m venv .venv
  & .\.venv\Scripts\Activate.ps1
  pip install -r requirements.txt
} else {
  & .\.venv\Scripts\Activate.ps1
}

if (-not (Test-Path "config.json")) {
  Copy-Item "config.example.json" "config.json"
  Write-Host "config.json olusturuldu."
}

Write-Host "Kontrol paneli: http://127.0.0.1:8787"
python main.py @args
