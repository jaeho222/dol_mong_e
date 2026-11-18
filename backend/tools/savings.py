"""'예산을 줄이려면?' — 비용 계산식(cost.py)을 조건만 바꿔 다시 돌려서 아낄 수 있는 방법을 금액으로 보여준다.

지어낸 숫자는 없다. 모든 금액 = estimate_total_cost(바뀐 조건) − estimate_total_cost(지금 조건).
"""
from dataclasses import replace
from datetime import date

from backend.schema import Conditions
from backend.tools.cost import COST, estimate_total_cost
from backend.tools.data_loader import get_region, load_regions


def _shift_month(d: date, k: int) -> date:
    m = d.month - 1 + k
    return date(d.year + m // 12, m % 12 + 1, 1)


def suggest_savings(region_id: str, conditions: dict | Conditions, target: int | None = None) -> dict:
    cond = conditions if isinstance(conditions, Conditions) else Conditions.from_dict(conditions)
    base = estimate_total_cost(region_id, cond)
    region = get_region(region_id)
    total = base["total"]
    options = []

    def add(label, new_cond, how, caveat="", key=""):
        c2 = estimate_total_cost(region_id if not key.startswith("region:") else key[7:], new_cond)
        saved = total - c2["total"]
        if saved > 0:
            options.append({"label": label, "saved": saved, "new_total": c2["total"], "how": how, "caveat": caveat,
                            "key": key, "breakdown": c2["breakdown"]})

    # 1) 렌터카 대신 버스
    if cond.car is not False:
        bus = int(region.get("bus_stops") or 0)
        add("렌터카 대신 버스 타기", replace(cond, car=False),
            f"렌터카 월 단가(성수기 7·8월 100만, 평소 40~50만 원) 대신 버스 1인 월 {COST['bus_month_per_person']}만 원으로 계산",
            caveat=(f"이 동네 정류장은 {bus}곳이에요." + (" 정류장이 적어 차 없이 지내기 불편할 수 있어요." if bus < 250 else "")),
            key="car")

    # 2) 입도 시기 옮기기 (같은 기간, 앞으로 12개월 중 가장 싼 달)
    start = cond.resolved_start()
    best = None
    for k in range(1, 12):
        s = _shift_month(start, k)
        c2 = estimate_total_cost(region_id, replace(cond, start_date=s.isoformat()))
        if best is None or c2["total"] < best[1]:
            best = (s, c2["total"])
    if best and best[1] < total:
        add(f"{best[0].month}월에 들어오기", replace(cond, start_date=best[0].isoformat()),
            "숙소 성수기 배율(7·8월 1.3배, 3월 0.95배, 11월 0.9배)과 렌터카 월 단가가 달마다 달라요", key="month")

    # 3) 비슷한 권역의 더 싼 동네
    others = []
    for rid in load_regions().index:
        if rid == region_id:
            continue
        c2 = estimate_total_cost(rid, cond)
        others.append((rid, c2["total"]))
    others.sort(key=lambda x: x[1])
    df = load_regions()
    for rid, t in others[:2]:
        if t < total:
            o = df.loc[rid]
            add(f"{o['name']}에서 지내기", cond,
                f"숙소비 = 권역 기준가 × 임대지수. {o['name']} 임대지수 {o['rent_index']} (지금 동네 {region['rent_index']}, 국토부 전월세 실거래가)",
                caveat=f"정류장 {int(o['bus_stops'])}곳, 병·의원 {int(o['hospital_cnt'])}곳 (지금 동네 {int(region['bus_stops'])}곳·{int(region['hospital_cnt'])}곳)",
                key=f"region:{rid}")

    # 4) 90일 이상이면 연세가 이미 비교됨. 60~89일이면 90일로 늘렸을 때 한 달치 비용을 보여준다
    if 60 <= cond.days < 90:
        c90 = estimate_total_cost(region_id, replace(cond, days=90))
        per_now, per_90 = total / cond.days * 30, c90["total"] / 90 * 30
        if per_90 < per_now:
            options.append({"label": "90일로 늘리기(한 달 비용 기준)", "saved": round(per_now - per_90), "new_total": c90["total"],
                            "how": "90일 이상이면 연세와 장기 할인(0.88배)을 같이 비교해요", "caveat": "총액은 늘고 한 달 비용이 줄어요", "key": "days"})

    options.sort(key=lambda o: o["saved"], reverse=True)

    # 목표 금액을 주면: 한 가지로 안 되면 효과 큰 두 가지를 같이 적용해 다시 계산
    combo = None
    if target and options and options[0]["saved"] < target:
        a = next((o for o in options if o["key"] == "car"), None)
        b = next((o for o in options if o["key"] == "month"), None)
        if a and b:
            mcond = replace(cond, car=False, start_date=next(
                _shift_month(start, k) for k in range(1, 12) if _shift_month(start, k).month == int(b["label"].split("월")[0])).isoformat())
            c2 = estimate_total_cost(region_id, mcond)
            combo = {"label": f"{a['label']} + {b['label']}", "saved": total - c2["total"], "new_total": c2["total"]}

    return {
        "region_id": region_id, "region_name": region["name"], "total": total, "breakdown": base["breakdown"],
        "target": target, "options": options, "combo": combo,
        "fixed_note": f"식비(1인 월 {COST['food_month_first']}만 원)는 취사 위주 기준이라 계산식에서 더 줄일 항목이 없어요.",
        "unit": "만원",
    }


def budget_alternatives(conditions: dict | Conditions, limit: int = 3) -> dict:
    """예산을 넘어 추천에서 빠진 동네 중 점수 높은 곳: 무엇을 바꾸면 예산 안에 들어오는지 (계산식 재계산)."""
    from backend.tools.region import rank_regions

    cond = conditions if isinstance(conditions, Conditions) else Conditions.from_dict(conditions)
    if not cond.budget_total:
        return {"budget": None, "items": []}
    ranked = rank_regions(cond, top_k=14)
    over = sorted(ranked["over_budget"], key=lambda o: -o["score"])[:limit]
    items = []
    for o in over:
        s = suggest_savings(o["region_id"], cond, o["over"])
        fixes = [{"label": x["label"], "saved": x["saved"], "new_total": x["new_total"], "how": x["how"]}
                 for x in s["options"] if x["saved"] >= o["over"] and not x["key"].startswith("region:")]
        if not fixes and s["combo"] and s["combo"]["saved"] >= o["over"]:
            fixes = [{**s["combo"], "how": "두 가지를 같이 적용해 다시 계산"}]
        items.append({**o, "fixes": fixes[:2]})
    totals = sorted(o["total"] for o in ranked["over_budget"])
    return {
        "budget": cond.budget_total,
        "in_budget": len(ranked["results"]),
        "items": items,
        # 예산을 조금 늘리면 몇 곳이 더 들어오는지
        "raise": [{"plus": t - cond.budget_total, "count": i + 1} for i, t in enumerate(totals[:3])],
    }
