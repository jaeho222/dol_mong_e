"""규칙 기반 조건 파서 — API 키 없이도 데모가 돌아가게 하는 대체 경로.

Claude 모드에서는 Claude가 직접 조건을 뽑으므로 이 파일은 쓰이지 않는다.
TODO[AGENT]: 테스트 문장을 tests/test_parser.py 에 계속 추가하면서 규칙 보강
"""
import re
from datetime import date

from backend.schema import Conditions
from backend.tools.data_loader import find_region_ids

KOR_NUM = {"한": 1, "두": 2, "세": 3, "네": 4, "다섯": 5, "여섯": 6, "일곱": 7, "여덟": 8, "아홉": 9, "열": 10}


def _num(tok: str) -> int:
    return int(tok) if tok.isdigit() else KOR_NUM.get(tok, 1)


def _parse_days(t: str) -> int | None:
    if re.search(r"반\s*년", t):
        return 180
    if re.search(r"(1|일|한)\s*년", t):
        return 365
    m = re.search(r"(\d+|한|두|세|네|다섯|여섯)\s*(개월|달)", t)
    if m:
        return _num(m.group(1)) * 30
    m = re.search(r"(\d+|한|두|세|네)\s*주", t)
    if m:
        return _num(m.group(1)) * 7
    m = re.search(r"(\d+)\s*(박|일)(?!\s*월)", t)
    if m:
        return int(m.group(1))
    if "한달" in t:
        return 30
    return None


def _parse_start(t: str) -> str | None:
    today = date.today()
    m = re.search(r"(\d{1,2})\s*월", t)
    month = int(m.group(1)) if m and 1 <= int(m.group(1)) <= 12 else None
    if month is None:
        for kw, mo in (("여름", 7), ("겨울", 12), ("봄", 4), ("가을", 10)):
            if kw in t:
                month = mo
                break
    if month is None:
        return None
    year = today.year + 1 if ("내년" in t or month <= today.month) else today.year
    return date(year, month, 1).isoformat()


def _parse_people(t: str) -> int | None:
    m = re.search(r"(\d+)\s*(명|인)", t)
    if m:
        return int(m.group(1))
    for kw, n in (("혼자", 1), ("둘이", 2), ("부부", 2), ("커플", 2), ("셋이", 3), ("넷이", 4)):
        if kw in t:
            return n
    return None


def _parse_car(t: str) -> bool | None:
    if re.search(r"차\s*(없|x|X|안|빼)|뚜벅|버스로|대중교통", t):
        return False
    if re.search(r"렌트|렌터카|차\s*(있|가지고|끌고)|자차", t):
        return True
    return None


def _parse_budget(t: str, days: int) -> int | None:
    months = max(days / 30, 1)
    m = re.search(r"월\s*(\d+)\s*(만|백)?", t)
    if m:
        v = int(m.group(1)) * (100 if m.group(2) == "백" else 1)
        return round(v * months)
    m = re.search(r"(총|전체|예산)\s*(\d+)\s*(만|백)?", t)
    if m:
        return int(m.group(2)) * (100 if m.group(3) == "백" else 1)
    m = re.search(r"(\d+)\s*만\s*원?\s*(이내|이하|까지|안쪽)", t)
    if m:
        return int(m.group(1))
    return None


def parse_conditions(text: str) -> Conditions:
    t = text.strip()
    days = _parse_days(t) or 30
    c = Conditions(days=days)
    c.start_date = _parse_start(t)
    c.people = _parse_people(t) or (3 if re.search(r"아이|애들|가족", t) else 1)
    c.car = _parse_car(t)
    c.budget_total = _parse_budget(t, days)
    c.with_kids = bool(re.search(r"아이|애기|아기|초등|유아|키즈|자녀", t))
    c.remote_work = bool(re.search(r"원격|재택|워케이션|리모트|노트북|일하면서", t))
    c.with_pet = bool(re.search(r"강아지|반려|고양이|댕댕", t))
    c.prefer_quiet = bool(re.search(r"조용|한적|힐링|쉬고", t))
    c.regions = find_region_ids(t) if re.search(r"비교|중에|vs|랑|이랑", t) else []
    c.priorities = _parse_priorities(t)
    return c


_PRIORITY_WORDS = [
    ("비용", r"싸|저렴|가성비|돈|예산|아끼"), ("교통", r"버스|대중교통|교통"), ("생활편의", r"마트|편의점|편의시설|장보기"),
    ("의료", r"병원|소아과|응급"), ("조용함", r"조용|한적|북적|관광객 적"), ("자연", r"오름|자연|바다|해변|캠핑|숲"),
    ("날씨", r"날씨|따뜻|햇볕|빨래"), ("맛집", r"맛집|식당|노포|먹"), ("밤길안심", r"치안|안전|밤길|CCTV|씨씨티비"),
]


def _parse_priorities(t: str) -> list[str]:
    """문장에 처음 나온 순서대로 최대 3개."""
    hits = []
    for key, pat in _PRIORITY_WORDS:
        m = re.search(pat, t)
        if m:
            hits.append((m.start(), key))
    return [k for _, k in sorted(hits)][:3]
