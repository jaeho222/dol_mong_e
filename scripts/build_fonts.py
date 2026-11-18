"""제주한라산체(제주특별자치도, SIL OFL 1.1)을 웹용 woff2 로 줄여서 frontend/assets/fonts/ 에 만든다.

사용: python scripts/build_fonts.py  (원본 ttf 는 google/fonts 저장소 ofl/jejuhallasan)
- 제주한라산: 화면 문구에 실제로 쓰인 글자만 → 돌몽이 대사·로고 (문구를 바꾸면 이 스크립트를 다시 돌릴 것)
- OFL 의 예약 글꼴 이름 조건 때문에 줄인 글꼴은 이름을 Dolmong* 으로 바꿔 둔다. 라이선스: fonts/OFL-*.txt
"""
import re
import sys
import urllib.request
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "frontend" / "assets" / "fonts"
CACHE = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/fonts")
SRC = "https://raw.githubusercontent.com/google/fonts/main/ofl/{}/{}.ttf"

ascii_chars = "".join(chr(c) for c in range(0x20, 0x7F)) + "·…‘’“”~→←!?%₩"
used = set()
for p in ["frontend/index.html", "frontend/assets/config.js", "frontend/assets/app.js", "frontend/assets/onboarding.js", "frontend/assets/jeju_rules.json",
          "backend/tools/evidence.py", "backend/tools/indices.py", "data/processed/festival.csv",
          "data/sample/region_metrics.csv", "data/processed/region_metrics.csv"]:
    used |= set(re.findall(r"[가-힣ㄱ-ㅎ]", (ROOT / p).read_text(encoding="utf-8")))


# 자주 쓰는 한글 2,350자(KS X 1001 완성형)를 통째로 넣는다 → 데이터에서 오는 동네·가게 이름, 새 문구도 안 깨짐
ks = set()
for hi in range(0xB0, 0xC9):
    for lo in range(0xA1, 0xFF):
        try:
            ks.add(bytes([hi, lo]).decode("euc-kr"))
        except UnicodeDecodeError:
            pass
used |= {c for c in ks if "가" <= c <= "힣"}


def build(folder, name, family, text):
    src = CACHE / f"{name}.ttf"
    if not src.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(SRC.format(folder, name), src)
    opts = subset.Options()
    opts.flavor = "woff2"
    opts.layout_features = ["*"]
    font = TTFont(src)
    sub = subset.Subsetter(opts)
    sub.populate(text=text)
    sub.subset(font)
    for rec in font["name"].names:  # 예약 이름 대신 새 이름
        if rec.nameID in (1, 3, 4, 6, 16):
            rec.string = family if rec.nameID != 6 else family.replace(" ", "")
    out = OUT / f"{family.lower().replace(' ', '-')}.woff2"
    font.flavor = "woff2"
    font.save(out)
    print(out.name, out.stat().st_size // 1024, "KB")


OUT.mkdir(parents=True, exist_ok=True)
build("jejuhallasan", "JejuHallasan-Regular", "Dolmong Hallasan", ascii_chars + "".join(used))
