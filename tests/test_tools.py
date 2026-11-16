"""실행: python -m pytest -q"""
from backend.agent.mock_parser import parse_conditions
from backend.tools.cost import estimate_total_cost
from backend.tools.region import rank_regions
from backend.tools.registry import TOOLS


def test_estimate_has_breakdown_and_range():
    r = estimate_total_cost("aewol", {"days": 30, "people": 2, "car": True})
    assert r["total"] == sum(r["breakdown"].values())
    assert r["range"][0] < r["total"] < r["range"][1]


def test_long_stay_compares_yearly_rent():
    r = estimate_total_cost("jeju_old", {"days": 365})
    assert r["tier"] == "연세"
    assert r["alternatives"]


def test_no_car_uses_bus():
    r = estimate_total_cost("jeju_new", {"days": 30, "car": False})
    assert "버스" in r["breakdown"]


def test_budget_filter():
    r = rank_regions({"days": 30, "budget_total": 1})
    assert r["results"] == [] and r["over_budget"]


def test_region_subset():
    r = rank_regions({"days": 30, "regions": ["aewol", "seongsan"]})
    assert {x["region_id"] for x in r["results"]} == {"aewol", "seongsan"}


def test_tools_schema_valid():
    for t in TOOLS:
        assert t.to_anthropic()["input_schema"]["type"] == "object"


def test_parser_examples():
    c = parse_conditions("1월부터 3개월, 둘이서, 차 없이, 원격근무, 월 200 이내")
    assert (c.days, c.people, c.car, c.remote_work, c.budget_total) == (90, 2, False, True, 600)
    assert c.resolved_start().month == 1

    c = parse_conditions("여름에 아이랑 2주 렌터카")
    assert (c.days, c.car, c.with_kids) == (14, True, True)

    c = parse_conditions("내년 3월부터 1년 살아보고 싶어")
    assert c.days == 365
