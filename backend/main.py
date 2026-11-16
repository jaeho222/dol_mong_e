"""FastAPI 서버. 실행: uvicorn backend.main:app --reload

API
  GET  /api/health          모드(claude/mock), 더미 데이터 여부
  GET  /api/regions         지역 목록
  POST /api/estimate        폼 조건 → 지역 순위 (LLM 없이 바로 계산)
  POST /api/chat            자연어 → Agent 답변 + 지역 순위
그 외 경로는 frontend/ 정적 파일을 서빙한다.
"""
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend import config
from backend.agent import run_agent
from backend.tools.data_loader import data_is_dummy
from backend.tools.region import list_regions, rank_regions

app = FastAPI(title="제주 한달살이 코파일럿 (가칭)")


class EstimateRequest(BaseModel):
    conditions: dict
    top_k: int = 6


class ChatRequest(BaseModel):
    message: str
    history: list = []  # TODO[AGENT]: 멀티턴 대화 시 프론트에서 이전 메시지 전달


@app.get("/api/health")
def health():
    return {"ok": True, "agent_mode": config.resolved_agent_mode(), "dummy_data": data_is_dummy()}


@app.get("/api/regions")
def regions():
    return list_regions()


@app.post("/api/estimate")
def estimate(req: EstimateRequest):
    try:
        return rank_regions(req.conditions, top_k=req.top_k)
    except (KeyError, ValueError) as e:
        raise HTTPException(400, str(e))


@app.post("/api/chat")
def chat(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(400, "메시지가 비어 있어요")
    return run_agent(req.message, req.history)


app.mount("/", StaticFiles(directory=config.FRONTEND_DIR, html=True), name="frontend")
