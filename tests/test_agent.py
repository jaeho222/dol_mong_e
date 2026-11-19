"""돌몽이 상담 Agent 테스트 — API 키 없이 가짜 Claude 로 도구 루프를 확인한다. 실행: python -m pytest -q"""
from types import SimpleNamespace as NS

from fastapi.testclient import TestClient

from backend import config
from backend.agent import dolmong_agent as ag
from backend.main import app
from backend.schema import Conditions

COND = {"start_date": "2027-01-01", "days": 30, "people": 2, "car": True}


def _ctx():
    return {"sources": [], "next": None, "report_update": None}


def test_every_tool_runs():
    c = Conditions.from_dict(COND)
    for topic in ag.TOPICS:
        out = ag.run_tool("ask_data", {"topic": topic, "region_id": "aewol", "question": "궁금해요"}, c, _ctx())
        assert out["facts"], topic
    assert ag.run_tool("rank_regions", {"changes": {"car": False}}, c, _ctx())["conditions"]["car"] is False
    cmp = ag.run_tool("compare_regions", {"region_ids": ["aewol", "한림"]}, c, _ctx())
    assert [r["region_id"] for r in cmp["regions"]] == ["aewol", "hallim"]
    assert ag.run_tool("estimate_cost", {"region_id": "aewol", "changes": {"days": 60}}, c, _ctx())["total"] > 0
    assert ag.run_tool("get_region_detail", {"region_id": "애월"}, c, _ctx())["name"]
    assert ag.run_tool("rehearse", {"region_id": "aewol"}, c, _ctx())["weekday"]


def test_proposal_records_only_changes():
    ctx = _ctx()
    ag.run_tool("propose_report_change", {"changes": {"car": False, "days": 30}, "select_region_id": "hallim"},
                Conditions.from_dict(COND), ctx)
    assert ctx["report_update"]["conditions"] == {"car": False}
    assert ctx["report_update"]["select_region_id"] == "hallim"


def test_report_context_names_regions():
    txt = ag.report_context("aewol", Conditions.from_dict(COND))
    assert "aewol" in txt and "추천 순위" in txt


class FakeClaude:
    """정해 둔 순서대로 응답한다: ① 도구 두 개 호출 → ② 리포트 바꾸기 → ③ 답."""

    def __init__(self, script):
        self.script, self.calls = list(script), []
        self.messages = self

    def create(self, **kw):
        self.calls.append(kw | {"messages": list(kw["messages"])})  # 호출 시점 복사본
        return self.script.pop(0)


def _tool(id_, name, inp):
    return NS(type="tool_use", id=id_, name=name, input=inp)


def _text(t):
    return NS(type="text", text=t)


def test_agent_loop_multi_step_and_report_update():
    fake = FakeClaude([
        NS(stop_reason="tool_use", content=[_tool("1", "estimate_cost", {"region_id": "aewol", "changes": {"car": False}}),
                                            _tool("2", "ask_data", {"topic": "transit", "region_id": "aewol", "question": "차 없이"})]),
        NS(stop_reason="tool_use", content=[_tool("3", "propose_report_change", {"changes": {"car": False}, "reason": "렌터카 → 버스·도보"})]),
        NS(stop_reason="end_turn", content=[_text("버스로 지내면 더 싸요.")]),
    ])
    out = ag.run_agent("차 없이 지내면 어때? 리포트도 바꿔줘", "aewol", COND, client=fake)
    assert out["mode"] == "agent"
    assert [t["tool"] for t in out["trace"]] == ["estimate_cost", "ask_data", "propose_report_change"]
    assert out["report_update"]["conditions"] == {"car": False}
    assert out["sources"]
    # 두 번째 호출에는 도구 결과 두 개가 같이 들어간다
    assert len(fake.calls[1]["messages"][-1]["content"]) == 2


def test_agent_tool_error_goes_back_to_claude():
    fake = FakeClaude([
        NS(stop_reason="tool_use", content=[_tool("1", "get_region_detail", {"region_id": "없는동네"})]),
        NS(stop_reason="end_turn", content=[_text("다시 볼게요.")]),
    ])
    out = ag.run_agent("없는동네 알려줘", "aewol", COND, client=fake)
    assert out["trace"][0]["error"] is True
    assert fake.calls[1]["messages"][-1]["content"][0]["is_error"] is True


def test_history_is_cleaned():
    h = [{"role": "assistant", "content": "안녕"}, {"role": "user", "content": "a"},
         {"role": "assistant", "content": "b"}, {"role": "user", "content": "c"}]
    assert [m["role"] for m in ag._history(h)] == ["user", "assistant"]


def test_consult_without_key_uses_rules(monkeypatch):
    monkeypatch.setattr(config, "AGENT_MODE", "mock")
    r = TestClient(app).post("/api/consult", json={"region_id": "aewol", "conditions": COND, "message": "근처 병원 있어?"})
    body = r.json()
    assert r.status_code == 200 and body["mode"] == "rule" and not body.get("trace")


def test_activity_without_data_does_not_error():
    out = ag.run_tool("ask_data", {"topic": "activity", "region_id": "aewol", "question": "서핑"},
                      Conditions.from_dict(COND), _ctx())
    assert "모르는" in "".join(out["facts"]) and "120" in "".join(out["facts"])


def test_no_proposal_when_nothing_changes():
    ctx = _ctx()
    out = ag.run_tool("propose_report_change", {"changes": {"days": 30}}, Conditions.from_dict(COND), ctx)
    assert out["ok"] is False and ctx["report_update"] is None


def test_nudge_when_asks_without_proposal():
    fake = FakeClaude([
        NS(stop_reason="end_turn", content=[_text("차 없이 지내면 서귀포가 좋아요. 리포트를 수정해 드릴까요?")]),
        NS(stop_reason="tool_use", content=[_tool("1", "propose_report_change", {"changes": {"car": False}})]),
        NS(stop_reason="end_turn", content=[_text("차 없이 지내면 서귀포가 좋아요. 리포트를 수정해 드릴까요?")]),
    ])
    out = ag.run_agent("차 없이 갈 거야", "aewol", COND, client=fake)
    assert out["report_update"]["conditions"] == {"car": False}
    assert len(fake.calls) == 3


def test_dialect_is_consistent_and_sentence_final_only():
    from backend.tools.jeju import jeju
    assert jeju("주요 관광지예요. 많아요\n좋겠네요! 필요해요?") == "주요 관광지우다. 많수다\n좋겠수다! 필요허우꽈?"
    assert jeju("19만 원 저렴해요(301만 원 vs 320만 원). 제주시(원도심) 주요(대표) 곳") == "19만 원 저렴허우다(301만 원 vs 320만 원). 제주시(원도심) 주요(대표) 곳"


def test_internal_names_never_shown():
    assert ag.clean_answer("`transit`(버스·도보) 정보도 볼까요? 애월읍(aewol)이 좋아요") == "버스·도보 정보도 볼까요? 애월읍이 좋아요"
    assert ag.clean_source("비용 계산식·추천 점수 (docs/COST_MODEL.md, docs/DATA.md)") == "비용 계산식·추천 점수"


def test_icons_and_emoji():
    from backend.agent.icons import pick_icon, strip_emoji
    assert strip_emoji("🍜 식당\n- [서양국수](u) ★4.8 → 좋아요 ☎️ 120") == "식당\n- [서양국수](u) ★4.8 → 좋아요 120"
    assert pick_icon("근처 병원 있어?", "병원 24곳", ["medical"]) == "medical"
    assert pick_icon("애월이랑 한림 비교해줘", "한림이 점수가 높아요", []) is None
    assert pick_icon("아이랑 소아과", "", ["medical", "kids"]) is None  # 두 주제가 비슷하면 안 붙인다


def test_truncated_answer_is_rewritten():
    """길이 제한(max_tokens)으로 끊긴 답은 내보내지 않고 다시 정리하게 한다."""
    fake = FakeClaude([
        NS(stop_reason="tool_use", content=[_tool("1", "compare_regions", {"region_ids": ["seogwipo_dong", "aewol"]})]),
        NS(stop_reason="max_tokens", content=[_text("서귀포 동지역을 더 추천해요. 남원읍은 조용해요. 대신"),
                                             _tool("2", "rehearse", {"region_id": "seogwipo_dong"})]),
        NS(stop_reason="end_turn", content=[_text("서귀포 동지역을 더 추천해요. 남원읍은 조용하지만 버스가 적어요.")]),
    ])
    out = ag.run_agent("남원읍이랑 비교해줘", "seogwipo_dong", COND, client=fake)
    assert "대신" not in out["answer"]
    assert "버스가 적" in out["answer"]
    assert [t["tool"] for t in out["trace"]] == ["compare_regions"]


def test_empty_answer_after_tools_is_rewritten():
    """도구만 부르고 답을 비워 두면, 도구 없이 답을 다시 쓰게 한다."""
    fake = FakeClaude([
        NS(stop_reason="tool_use", content=[_tool("1", "compare_regions", {"region_ids": ["seogwipo_dong", "aewol"]})]),
        NS(stop_reason="end_turn", content=[]),
        NS(stop_reason="end_turn", content=[_text("차 없이 지내면 서귀포 동지역이 나아요.")]),
    ])
    out = ag.run_agent("애월읍이랑 비교해줘", "seogwipo_dong", COND, client=fake)
    assert "서귀포 동지역" in out["answer"]
    assert fake.calls[-1]["tool_choice"] == {"type": "none"}
