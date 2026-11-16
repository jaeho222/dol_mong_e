"""Vercel 진입점 — Vercel은 루트의 index.py 에서 FastAPI `app` 을 자동 인식한다.
로컬 실행은 그대로 `uvicorn backend.main:app --reload`.
"""
from backend.main import app  # noqa: F401
