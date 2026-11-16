"""키 없이 돌아가는 데모용 Agent.

Claude Agent와 '같은 도구'를 '같은 순서'로 호출하고 템플릿으로 답한다.
→ 프론트·도구 개발을 LLM 키 없이 진행할 수 있다.
"""
from backend.agent.mock_parser import parse_conditions
from backend.tools.registry import TOOLS_BY_NAME


def _fmt_range(c: dict) -> str:
    lo, hi = c["range"]
    return f"{lo:,}~{hi:,}만원"


def run_mock_agent(message: str, history: list | None = None) -> dict:
    cond = parse_conditions(message)
    trace = [{"tool": "rank_regions", "input": {"conditions": cond.to_dict()}}]
    ranked = TOOLS_BY_NAME["rank_regions"].run({"conditions": cond.to_dict(), "top_k": 5})

    c = ranked["conditions"]
    car_txt = {True: "렌터카", False: "차 없이", None: "차량 미정(렌터카 기준)"}[cond.car]
    lines = [f"**{c['start_date'][:7]}부터 {c['days']}일, {c['people']}명, {car_txt}** 조건으로 계산했어요."]
    if c.get("budget_total"):
        lines.append(f"예산 {c['budget_total']:,}만원 안에서 골랐어요.")
    lines.append("")

    if not ranked["results"]:
        near = ranked["over_budget"][:2]
        lines.append("예산 안에 들어오는 동네가 없어요.")
        if near:
            lines.append("가장 가까운 곳은 " + ", ".join(f"**{n['name']}**(약 {n['total']:,}만원)" for n in near)
                         + "이에요. 예산을 조금 늘리거나 기간을 줄여볼까요?")
    for i, r in enumerate(ranked["results"][:3], 1):
        cost = r["cost"]
        top_item = max(cost["breakdown"], key=cost["breakdown"].get)
        line = f"{i}. **{r['name']}** — 총 {_fmt_range(cost)} (가장 큰 항목: {top_item})"
        if r["badges"]:
            line += " · " + ", ".join(r["badges"][:2])
        if r["warnings"]:
            line += " · 주의: " + r["warnings"][0]
        lines.append(line)

    first = ranked["results"][0]["cost"] if ranked["results"] else None
    if first and first["alternatives"]:
        lines.append(f"\n{c['days']}일이면 **{first['tier']}**가 더 유리해요.")
    if cond.car is None:
        lines.append("\n차를 빌릴 계획인가요? 차 없이 지내면 순위가 꽤 달라져요.")
    lines.append("\n_(키 없이 도는 데모 모드 답변이에요)_")

    return {"answer": "\n".join(lines), "ranked": ranked, "trace": trace, "mode": "mock"}
