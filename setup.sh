#!/usr/bin/env bash
set -e
cd backend
python -m venv .venv
.venv/bin/pip install -q -r requirements.txt
[ -f .env ] || cp .env.example .env
cd ../frontend
npm install --silent
echo "Setup done. Next: add your API key to backend/.env"
