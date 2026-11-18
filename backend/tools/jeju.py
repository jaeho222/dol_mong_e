"""돌몽이 말투: 문장은 표준어 그대로 두고 끝 어미만 제주어로 바꾼다 (규칙: frontend/assets/jeju_rules.json).

예) "38만 원 늘어요" → "38만 원 늘어마씸", "지금 동네는 1위예요" → "지금 동네는 1위우다", "확인하세요" → "확인헙서"
UI 문구(버튼·제목·표)는 바꾸지 않고 돌몽이가 하는 말(상담 답변, 한마디, 온보딩 대사)에만 쓴다.
"""
import json
import re
from functools import lru_cache

from backend import config

END = r"(?=[\s.,:;!?~…)\]\"'”]|$)"  # 어미 뒤: 공백·문장부호·줄 끝


@lru_cache
def _rules():
    data = json.loads((config.FRONTEND_DIR / "assets" / "jeju_rules.json").read_text(encoding="utf-8"))
    return [(re.compile(src + END), dst.replace("$1", r"\1")) for src, dst in data["rules"]]


def _word(m_text: str) -> str:
    for pat, dst in _rules():
        new, n = pat.subn(dst, m_text, count=1)
        if n:
            return new
    return m_text


def jeju(text: str) -> str:
    """어미로 끝나는 어절마다 규칙 하나씩 적용. 링크 [이름](url) 과 **굵게** 표시는 건드리지 않는다."""
    if not config.DOLMONG_DIALECT:
        return text
    # 어절 단위(공백 기준)로 끝 어미만 본다 → 단어 가운데의 '요'·'예요'는 안 바뀐다
    return re.sub(r"[^\s]+", lambda m: m.group(0) if m.group(0).startswith(("http", "[", "(")) and "](" in m.group(0) else _word(m.group(0)), text)
