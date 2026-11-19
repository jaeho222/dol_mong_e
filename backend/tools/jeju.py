"""돌몽이 말투: 문장은 표준어 그대로, 문장 끝 어미만 '읽기 쉬운' 제주어로 일관되게 바꾼다.

표준어 해요체 끝을 아래처럼 하나의 규칙으로 바꾼다 (받침을 보고 판단 → 모든 문장이 같은 말투).
  받침 있는 말 + 어요/아요 → +수다      적어요→적수다, 많아요→많수다, 찾았어요→찾았수다, 있어요→있수다
  ~이에요 / ~예요            → ~이우다 / ~우다   곳이에요→곳이우다, 동네예요→동네우다
  ~해요                      → ~허우다          따뜻해요→따뜻허우다
  ~워요                      → ~웁수다          가까워요→가까웁수다
  돼요                       → 됨수다
  그 밖의 받침 없는 말 + 요   → 받침 ㅁ + 수다    달라요→달람수다, 매겨요→매겸수다
  ~ㄹ게요                    → ~쿠다            볼게요→보쿠다, 드릴게요→드리쿠다
  ~세요 (부탁)                → ~ㅂ서            보세요→봅서, 주세요→줍서, 하세요→헙서
  ~까요?                     → ~까마씸?         드릴까요?→드릴까마씸?
  ~네요                      → ~수다            좋겠네요→좋겠수다
  ~습니다 / ~ㅂ니다          → ~수다 / ~우다
  묻는 말(?)이면 ~다 → ~꽈     필요해요? → 필요허우꽈?
특별한 말(인사 등)은 frontend/assets/jeju_rules.json 의 words 에서 먼저 바꾼다.
같은 규칙을 화면(frontend/assets/jeju.js)도 쓴다 — 고칠 때 두 파일을 같이 고칠 것.
UI 문구(버튼·제목·표)는 바꾸지 않고 돌몽이가 하는 말에만 쓴다. 끄려면 DOLMONG_DIALECT=0.
"""
import json
import re
from functools import lru_cache

from backend import config

WORD = re.compile(r"([^\s<>]*?[가-힣])([^\s<>가-힣]*)(?=\s|$|<)")  # 어절 = 한글로 끝나는 몸통 + 뒤 문장부호
B, L, M = 17, 8, 16  # 받침 번호: ㅂ, ㄹ, ㅁ


@lru_cache
def _words():
    data = json.loads((config.FRONTEND_DIR / "assets" / "jeju_rules.json").read_text(encoding="utf-8"))
    return sorted(data["words"].items(), key=lambda x: -len(x[0]))


def _jong(ch: str) -> int:
    c = ord(ch) - 0xAC00
    return c % 28 if 0 <= c < 11172 else -1


def _set_jong(ch: str, j: int) -> str:
    c = ord(ch) - 0xAC00
    return chr(0xAC00 + c - c % 28 + j) if 0 <= c < 11172 else ch


def convert_word(w: str) -> str:
    """끝 어미 하나만 바꾼다. 해당 없으면 그대로."""
    for src, dst in _words():
        if w.endswith(src):
            return w[: -len(src)] + dst
    if w.endswith("습니다"):
        return w[:-3] + "수다"
    if w.endswith("습니까"):
        return w[:-3] + "수꽈"
    if len(w) >= 3 and w.endswith(("니다", "니까")) and _jong(w[-3]) == B:
        return w[:-3] + ("허" if w[-3] == "합" else _set_jong(w[-3], 0)) + ("우다" if w.endswith("니다") else "우꽈")
    if not w.endswith("요") or len(w) < 2:
        return w
    s, last = w[:-1], w[-2]
    if s.endswith("이에"):
        return s[:-2] + "이우다"
    if last == "예":
        return s[:-1] + "우다"
    if last == "세" and len(s) >= 2:
        p = s[-2]
        return s[:-2] + ("헙" if p == "하" else _set_jong(p, B) if _jong(p) == 0 else p + "읍") + "서"
    if last == "게" and len(s) >= 2 and _jong(s[-2]) == L:
        return s[:-2] + _set_jong(s[-2], 0) + "쿠다"
    if last == "까":
        return s + "마씸"
    if last == "네" and len(s) >= 2:  # 좋겠네요 → 좋겠수다
        return s[:-1] + "수다"
    if last == "해":
        return s[:-1] + "허우다"
    if last in ("돼", "되"):
        return s[:-1] + "됨수다"
    if last == "워" and len(s) >= 2:
        return s[:-1] + "웁수다"
    if last in ("어", "아") and len(s) >= 2 and _jong(s[-2]) > 0:
        return s[:-1] + "수다"
    if _jong(last) == 0:
        return s[:-1] + _set_jong(last, M) + "수다"
    return w


def jeju(text: str) -> str:
    """어절마다 끝 어미만 바꾼다. 링크 [이름](url) 과 주소는 건드리지 않는다."""
    if not config.DOLMONG_DIALECT or not text:
        return text

    def one(m):
        core, punct = m.group(1), m.group(2)
        if "](" in core or core.startswith("http"):
            return m.group(0)
        # 문장 끝에서만: 뒤에 문장부호가 있거나, 줄 끝이거나, 바로 괄호 설명이 이어질 때 ("주요 관광지"의 '주요'는 그대로)
        after = text[m.end():m.end() + 3]
        if not (re.search(r"[.?!~:…]", punct) or after == "" or after[0] in "\n<" or after.lstrip(" ").startswith("(")):
            return m.group(0)
        out = convert_word(core)
        if "?" in punct and out != core and out.endswith(("수다", "우다")):  # 묻는 말: 있수다? → 있수꽈?
            out = out[:-1] + "꽈"
        return out + punct

    return WORD.sub(one, text)
