#!/bin/sh
# Ensure runtime packages are installed (handles cached images missing these deps)
pip install --quiet pdf2image pytesseract openai 2>/dev/null

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
