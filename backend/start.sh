#!/usr/bin/env bash
# ARC search engine backend (FastAPI). Requires MongoDB on localhost:27017
# (see docker-compose.yml at the repo root) and dependencies from requirements.txt
cd "$(dirname "$0")"
exec python main.py
