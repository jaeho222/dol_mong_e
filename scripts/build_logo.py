"""ᄆᆞ슬 로고 SVG 생성기.

글자: 주아체(Jua, SIL Open Font License 1.1, 우아한형제들) 글리프를 패스로 변환 → 폰트 없이도 똑같이 보인다.
색: 'ᄆᆞ' 현무암 #2b2f31 · '슬' 이끼 #5e7d4a. 아래아(ㆍ)는 이끼 뭉치로, 현무암 글자 위에 이끼 장식.

사용: npm pack @fontsource/jua && tar xzf fontsource-jua-*.tgz  (폰트 준비)
      python scripts/build_logo.py <package/files 경로>
결과: frontend/assets/logo.svg (부제 포함), logo-mark.svg (부제 없음), index.html 헤더에 인라인
"""
import random
import sys
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]
FONT_DIR = Path(sys.argv[1] if len(sys.argv) > 1 else "package/files")
BASALT, MOSS = "#2b2f31", "#5e7d4a"
MOSS_TONES = ["#3f5a30", "#4b6a3a", "#5e7d4a", "#6f8f5c", "#8aa876", "#a9c08f"]


def load_glyphs(chars: str) -> dict:
    out = {}
    for f in sorted(FONT_DIR.glob("jua-*-400-normal.woff")):
        font = TTFont(f)
        cmap, gs = font.getBestCmap(), font.getGlyphSet()
        for ch in chars:
            if ch not in out and ord(ch) in cmap:
                g = gs[cmap[ord(ch)]]
                pen = SVGPathPen(gs)
                g.draw(pen)
                out[ch] = (pen.getCommands(), g.width)
    missing = set(chars) - set(out) - {" "}
    if missing:
        raise SystemExit(f"글리프 없음: {missing}")
    return out


def glyph(g, ch, x, y, s, fill):
    return f'<path transform="translate({x:.1f} {y:.1f}) scale({s} {-s})" d="{g[ch][0]}" fill="{fill}"/>'


def moss(cx, cy, w, h, n, seed):
    """가장자리에 붙어 자란 이끼: 어두운 바닥 → 밝은 윗부분 순으로 작은 원을 겹친다."""
    rnd = random.Random(seed)
    dots = []
    for i in range(n):
        t = rnd.random()
        x = cx + (t - 0.5) * w
        lift = 1 - abs(t - 0.5) * 2              # 가운데가 봉긋
        y = cy - rnd.random() * h * lift
        r = rnd.uniform(0.18, 0.34) * h * (0.6 + 0.4 * lift)
        tone = min(len(MOSS_TONES) - 1, int((cy - y) / h * len(MOSS_TONES) + rnd.random() * 2))
        dots.append((y, f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{MOSS_TONES[tone]}"/>'))
    return "".join(d for _, d in sorted(dots, key=lambda d: -d[0]))


def jamo(g, ch, tx, ty, sx, sy, fill):
    return f'<path transform="translate({tx:.1f} {ty:.1f}) scale({sx:.3f} {-sy:.3f})" d="{g[ch][0]}" fill="{fill}"/>'


def arae_a(cx, cy, r):
    """옛한글 아래아(ㆍ) — 이끼 뭉치처럼 명도가 다른 원을 겹쳐 그린다."""
    return (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{MOSS}"/>'
            f'<circle cx="{cx - r*0.28:.1f}" cy="{cy - r*0.3:.1f}" r="{r*0.42:.1f}" fill="#7f9d68"/>'
            f'<circle cx="{cx - r*0.38:.1f}" cy="{cy - r*0.42:.1f}" r="{r*0.18:.1f}" fill="#a9c08f"/>'
            f'<circle cx="{cx + r*0.42:.1f}" cy="{cy + r*0.36:.1f}" r="{r*0.2:.1f}" fill="#4b6a3a"/>')


def build(with_sub: bool, ink: str = BASALT) -> str:
    """ᄆᆞ슬: 'ᄆᆞ'(ㅁ + 아래아 점)은 현무암색, '슬'은 이끼색. 주아체엔 아래아가 없어 ㅁ 자모 + 직접 그린 점으로 조합."""
    g = load_glyphs("ㅁ슬고를한달숨모")
    base = 920
    # ㅁ 자모(글리프 범위 x 109~735, y 139~598)를 ᄆᆞ 의 윗부분(가로 40~780, 세로 120~590)에 맞춰 늘린다
    sx, sy = 740 / 626, 470 / 459
    parts = [
        jamo(g, "ㅁ", 40 - 109.25 * sx, 120 + 598 * sy, sx, sy, ink),
        arae_a(410, 755, 98),
        glyph(g, "슬", 830, base, 1, MOSS),
        moss(150, 136, 200, 80, 22, 1),     # ㅁ 왼쪽 위 모서리에 앉은 이끼
    ]
    height = 990
    if with_sub:
        s, gap = 0.17, 0.17 * 260
        text = "숨 고를 한 달"
        width = sum(g[c][1] * s if c != " " else gap for c in text)
        x, y = 1620 - width, 1150
        for ch in text:
            if ch == " ":
                x += gap
                continue
            parts.append(glyph(g, ch, x, y, s, ink))
            x += g[ch][1] * s
        height = 1175
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1650 {height}" role="img" aria-label="ᄆᆞ슬">{"".join(parts)}</svg>'


if __name__ == "__main__":
    out = ROOT / "frontend" / "assets"
    (out / "logo.svg").write_text(build(True), encoding="utf-8")
    (out / "logo-mark.svg").write_text(build(False), encoding="utf-8")
    # 헤더용: '숨'을 currentColor 로 → 다크 모드에서 글자색을 따라간다. index.html 의 LOGO 마커 사이에 인라인
    html = ROOT / "frontend" / "index.html"
    src = html.read_text(encoding="utf-8")
    a, b = "<!--LOGO-->", "<!--/LOGO-->"
    if a in src:
        src = src[: src.index(a) + len(a)] + build(False, "currentColor") + src[src.index(b):]
        html.write_text(src, encoding="utf-8")
    print("frontend/assets/logo.svg, logo-mark.svg, index.html 헤더 로고")
