"""앱 전역 설정. 환경변수(.env)에서 읽는다.

새 설정을 추가할 때는 여기 한 곳에만 추가하고 .env.example에도 같이 적어 주세요.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

# ── LLM ──────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-haiku-5-5")
# auto: 키가 있으면 claude, 없으면 mock / claude / mock 강제 가능
AGENT_MODE = os.getenv("AGENT_MODE", "auto").lower()
AGENT_MAX_TURNS = int(os.getenv("AGENT_MAX_TURNS", "6"))

# ── 데이터 ────────────────────────────────────────────
# 실제 데이터가 준비되면 data/processed/region_metrics.csv 를 만들고 이 경로를 바꾸면 끝.
REGION_METRICS_PATH = Path(
    os.getenv("REGION_METRICS_PATH", ROOT_DIR / "data" / "sample" / "region_metrics.csv")
)

FRONTEND_DIR = ROOT_DIR / "frontend"


def resolved_agent_mode() -> str:
    if AGENT_MODE in ("claude", "mock"):
        return AGENT_MODE
    return "claude" if ANTHROPIC_API_KEY else "mock"
