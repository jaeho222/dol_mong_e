"""상담창 돌몽이 아이콘: 답의 주제가 '충분히' 겹칠 때만 아이콘 하나를 붙이고, 아니면 아무것도 안 붙인다.

아이콘 파일: frontend/assets/icons/<key>.webp
이모지는 상담창에서 쓰지 않는다 (strip_emoji 로 답·버튼에서 지운다).

점수 (아이콘마다)
  +2  그 주제의 데이터를 실제로 찾아 답했을 때 (규칙 답의 질문 분류, Agent 의 ask_data topic)
  +1.5 사용자 질문에 그 주제 낱말이 있을 때 (두 번 이상이면 +2)
  +0.5 답에 그 주제 낱말이 있을 때 (최대 1)
  → 1등 점수가 THRESHOLD 이상이고 2등보다 MARGIN 이상 앞설 때만 아이콘을 붙인다 (애매하면 안 붙인다).
"""
import re

THRESHOLD, MARGIN = 2.0, 1.0

# 데이터 주제(규칙 질문 분류 · ask_data topic) → 아이콘
TOPIC_ICON = {
    "save": "cost", "car_cost": "cost", "priority_cost": "cost", "why": "checklist", "cons": "caution",
    "transit": "transit", "amenity": "convenience", "medical": "medical", "lodging": "lodging", "food": "food",
    "hotplace": "tour", "beginner": "tour", "kids": "kids", "activity": "nature", "season": "season",
    "safety": "safety",
}
# 아이콘 → 주제 낱말
WORDS = {
    "cost": r"예산|비용|돈|얼마|싸|저렴|비싸|아끼|절약|만\s*원",
    "transit": r"버스|교통|정류장|차\s*없|뚜벅|렌터카|대중교통",
    "convenience": r"편의|마트|편의점|빨래방|세탁|헬스|약국|장보",
    "medical": r"병원|소아과|의원|응급|약국|아프|진료|보건소",
    "quiet": r"조용|한적|쉬고|잠|소음",
    "nature": r"오름|바다|해변|자연|산책|숲|캠핑|낚시|요트|카약|활동",
    "weather": r"날씨|비\s*오|바람|습도|기온|따뜻|추워|빨래\s*마르",
    "food": r"맛집|식당|카페|밥|음식|노포|먹",
    "safety": r"치안|안전|밤길|cctv|CCTV|위험",
    "kids": r"아이|아기|애기|어린이|키즈|자녀|가족",
    "pet": r"반려|강아지|고양이|댕댕|애견|펫",
    "remote": r"원격|재택|노트북|와이파이|워케이션|공유\s*오피스|일해",
    "lodging": r"숙소|숙박|민박|펜션|호텔|연세|집\s*구",
    "season": r"언제|몇\s*월|시기|계절|겨울|여름|봄|가을|귤",
    "caution": r"단점|주의|조심|불편|아쉬",
    "checklist": r"근거|왜|점수|어떻게\s*계산|이유",
    "festival": r"축제|행사|공연",
    "tour": r"관광|명소|가볼|핫플|구경|볼거리|처음",
}
_WORDS = {k: re.compile(v) for k, v in WORDS.items()}


def pick_icon(question: str, answer: str, topics: list[str]) -> str | None:
    score = {k: 0.0 for k in WORDS}
    for t in topics:
        if t in TOPIC_ICON:
            score[TOPIC_ICON[t]] += 2
    for k, pat in _WORDS.items():
        n = len(pat.findall(question or ""))
        score[k] += (1.5 + 0.5 * (n > 1) if n else 0) + min(1.0, 0.5 * len(pat.findall(answer or "")))
    ranked = sorted(score.items(), key=lambda x: -x[1])
    (top, s1), (_, s2) = ranked[0], ranked[1]
    return top if s1 >= THRESHOLD and s1 - s2 >= MARGIN else None


EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿⬀-⯿←-⇿⌀-⏿️‍]")
KEEP = set("→←↗★")  # 화살표·별점은 글 속 기호로 쓰니 남긴다


def strip_emoji(text: str) -> str:
    """이모지와 그 뒤 공백 한 칸만 지운다 (목록 '- ' 같은 다른 공백은 그대로)."""
    if not text:
        return text
    return re.sub(rf"(?:{EMOJI.pattern})+ ?", lambda m: m.group(0) if m.group(0).strip() in KEEP else "", text)


def qr_icons(quick_replies: list[dict]) -> list[dict]:
    """빠른 버튼: 이모지 빼고, 주제가 정해진 버튼에만 아이콘."""
    return [{**q, "label": strip_emoji(q["label"]).strip(), "icon": TOPIC_ICON.get(q["id"])} for q in quick_replies or []]
