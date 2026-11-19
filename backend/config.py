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
AGENT_MAX_TURNS = int(os.getenv("AGENT_MAX_TURNS", "5"))      # 도구 호출 루프 최대 횟수
AGENT_MAX_TOKENS = int(os.getenv("AGENT_MAX_TOKENS", "900"))   # 답 한 번의 최대 길이
AGENT_TIMEOUT = float(os.getenv("AGENT_TIMEOUT", "25"))        # API 한 번 기다리는 초
AGENT_RATE_PER_MIN = int(os.getenv("AGENT_RATE_PER_MIN", "8")) # 한 사용자(IP)가 1분에 보낼 수 있는 자유 질문 수

# ── 데이터 ────────────────────────────────────────────
# 실데이터(data/processed, Supabase에서 export)가 있으면 그걸, 없으면 더미(sample)를 쓴다.
_PROCESSED = ROOT_DIR / "data" / "processed" / "region_metrics.csv"
_SAMPLE = ROOT_DIR / "data" / "sample" / "region_metrics.csv"
REGION_METRICS_PATH = Path(
    os.getenv("REGION_METRICS_PATH") or (_PROCESSED if _PROCESSED.exists() else _SAMPLE)
)

FRONTEND_DIR = ROOT_DIR / "frontend"


def resolved_agent_mode() -> str:
    if AGENT_MODE in ("claude", "mock"):
        return AGENT_MODE
    return "claude" if ANTHROPIC_API_KEY else "mock"

# 돌몽이 말투: 끝 어미만 제주어로 (backend/tools/jeju.py). 끄려면 DOLMONG_DIALECT=0
DOLMONG_DIALECT = os.getenv("DOLMONG_DIALECT", "1") != "0"
