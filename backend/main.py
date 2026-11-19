"""FastAPI 서버. 실행: uvicorn backend.main:app --reload

API
  GET  /api/health          모드(claude/mock), 더미 데이터 여부
  GET  /api/regions         지역 목록
  POST /api/estimate        폼 조건 → 지역 순위 (LLM 없이 바로 계산)
  POST /api/consult         돌몽이 상담 — 버튼은 규칙, 자유 질문은 Claude Agent (도구 호출 + 리포트 바꾸기)
  POST /api/chat            (예전) 자연어 → Agent 답변 + 지역 순위
그 외 경로는 frontend/ 정적 파일을 서빙한다.
"""
import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend import config
from backend.agent.consult import greeting, run_consult
from backend.agent.dolmong_agent import allow, clean_source, run_agent as run_dolmong
from backend.agent.icons import pick_icon, qr_icons, strip_emoji
from backend.agent import run_agent
from backend.tools.data_loader import data_is_dummy
from backend.tools.jeju import jeju
from backend.tools.rehearsal import rehearse
from backend.tools.savings import budget_alternatives
from backend.tools.region import list_regions, rank_regions

log = logging.getLogger("dolmong")
app = FastAPI(title="돌몽이 — 제주살이 동네 추천 AI Agent")


class EstimateRequest(BaseModel):
    conditions: dict
    top_k: int = 6


class ChatRequest(BaseModel):
    message: str
    history: list = []  # TODO[AGENT]: 멀티턴 대화 시 프론트에서 이전 메시지 전달


class ConsultRequest(BaseModel):
    region_id: str
    conditions: dict = {}
    message: str = ""
    intent: str | None = None  # 빠른 버튼 id (save, why, transit, compare, medical, contact)
    history: list = []


@app.post("/api/consult")
def consult(req: ConsultRequest, request: Request):
    """돌몽이 상담 (화면 어디서나 여는 플로팅 창).

    - message·intent 둘 다 없으면 인사 + 빠른 버튼
    - 빠른 버튼(intent) → 규칙 + 데이터로 바로 답 (빠르고 비용 0)
    - 자유 질문 → Claude Agent 가 도구를 골라 쓰고 필요하면 리포트 수정을 제안한다 (dolmong_agent)
    - 키가 없거나, 사용량 제한에 걸리거나, API 오류면 규칙 + 데이터로 답한다
    """
    try:
        if not req.message.strip() and not req.intent:
            out = greeting(req.region_id, req.conditions)
            out["answer"], out["quick_replies"] = strip_emoji(out["answer"]), qr_icons(out["quick_replies"])
            if config.resolved_agent_mode() == "claude":
                out["answer"] = out["answer"].split("\n")[0] + "\n" + jeju(
                    "저는 이 리포트와 연결된 AI Agent예요. 물어보시면 공공데이터를 찾고 다시 계산해서 답하고, "
                    "조건이 달라지면 리포트 수정을 제안해요.\n"
                    "예) \"차 없이 두 달이면 어디가 좋아?\" · \"애월이랑 한림 비교해줘\" · \"아이랑 갈 건데 소아과 가까운 데는?\"")
            return out | {"agent": config.resolved_agent_mode() == "claude"}
        if req.message.strip() and not req.intent and config.resolved_agent_mode() == "claude":
            who = request.headers.get("x-forwarded-for", request.client.host if request.client else "?").split(",")[0]
            if allow(who):
                try:
                    return run_dolmong(req.message, req.region_id, req.conditions, req.history)
                except Exception as e:  # API 오류·시간 초과 → 규칙 답으로
                    log.warning("agent 실패, 규칙으로 답함: %s", e)
                    fallback = "agent_error"
            else:
                fallback = "rate_limited"
        else:
            fallback = None
        out = run_consult(req.message, req.region_id, req.conditions, req.intent, req.history)
        out["sources"] = list(dict.fromkeys(clean_source(x) for x in out.get("sources", [])))
        out["answer"] = strip_emoji(out["answer"])
        out["icon"] = pick_icon(req.message, out["answer"], [out.get("intent")])
        out["quick_replies"] = qr_icons(out.get("quick_replies"))
        return out | ({"fallback": fallback} if fallback else {})
    except KeyError as e:
        raise HTTPException(400, str(e))


class RegionCondRequest(BaseModel):
    region_id: str = ""
    conditions: dict = {}


@app.post("/api/rehearsal")
def rehearsal(req: RegionCondRequest):
    """돌몽이의 한 달 살기 리허설: 평일·주말 하루 일과 (데이터 속 실제 장소로)."""
    try:
        return rehearse(req.region_id, req.conditions)
    except KeyError as e:
        raise HTTPException(400, str(e))


@app.post("/api/budget-alternatives")
def budget_alt(req: RegionCondRequest):
    """예산 때문에 빠진 동네를 예산 안으로 넣는 방법."""
    return budget_alternatives(req.conditions)


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
