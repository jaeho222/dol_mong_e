"""ᄆᆞ슬 로고 SVG 생성기.

글꼴: 제주한라산체(제주특별자치도 제주전용서체 — 웹·임베딩 포함 자유 이용, 유료 양도·판매만 금지).
      글리프를 SVG 패스로 바꿔 넣으므로 방문자 PC에 폰트가 없어도 똑같이 보인다.
아래아: 이 글꼴은 'ᄆᆞ' 같은 옛한글 조합을 지원하지 않아서, 같은 글꼴의 'ㅁ'(U+3141)과 'ㆍ'(U+318D)를
        직접 위아래로 배치해 'ᄆᆞ'를 만든다.
색: 'ᄆᆞ' 현무암 #2b2f31(헤더에선 currentColor), '슬' 이끼 #5e7d4a, 아래아 점·이끼 장식은 이끼 톤.

폰트 준비: npm pack @noonnu/jeju-hallasan && tar xzf noonnu-jeju-hallasan-*.tgz
사용:      python scripts/build_logo.py package/fonts/jeju-hallasan-400.ttf
결과:      frontend/assets/logo.svg(부제 포함) · logo-mark.svg(부제 없음) · index.html 헤더 인라인
"""
import random
import sys
from pathlib import Path

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]
FONT = Path(sys.argv[1] if len(sys.argv) > 1 else "package/fonts/jeju-hallasan-400.ttf")
BASALT, MOSS = "#2b2f31", "#5e7d4a"
MOSS_TONES = ["#3f5a30", "#4b6a3a", "#5e7d4a", "#6f8f5c", "#8aa876", "#a9c08f"]

font = TTFont(FONT)
GS, CMAP = font.getGlyphSet(), font.getBestCmap()


def g(ch):
    """글자 → (패스, 가로폭, (xmin, ymin, xmax, ymax))"""
    gl = GS[CMAP[ord(ch)]]
    pen, bp = SVGPathPen(GS), BoundsPen(GS)
    gl.draw(pen)
    gl.draw(bp)
    return pen.getCommands(), gl.width, bp.bounds


def top_part(ch, cut_ratio=0.4):
    """'므'처럼 위아래로 쌓인 글자에서 윗부분 자모(ㅁ)의 윤곽선만 남긴다 → (패스, 범위)."""
    rec = RecordingPen()
    GS[CMAP[ord(ch)]].draw(rec)
    contours, cur = [], []
    for op, args in rec.value:
        cur.append((op, args))
        if op in ("closePath", "endPath"):
            contours.append(cur)
            cur = []
    ys = [pt[1] for c in contours for _, a in c for pt in a]
    cut = min(ys) + (max(ys) - min(ys)) * cut_ratio
    def center_y(c):
        cy = [pt[1] for _, a in c for pt in a]
        return (min(cy) + max(cy)) / 2
    keep = [c for c in contours if center_y(c) > cut]   # 아래 자모(ㅡ)의 윤곽선은 버린다
    pen, bp = SVGPathPen(GS), BoundsPen(GS)
    for c in keep:
        for op, args in c:
            getattr(pen, op)(*args)
            getattr(bp, op)(*args)
    return pen.getCommands(), bp.bounds


def place_d(d, bounds, box, fill):
    xmin, ymin, xmax, ymax = bounds
    x0, y0, x1, y1 = box
    s = min((x1 - x0) / (xmax - xmin), (y1 - y0) / (ymax - ymin))
    w, h = (xmax - xmin) * s, (ymax - ymin) * s
    tx = x0 + ((x1 - x0) - w) / 2 - xmin * s
    ty = y0 + ((y1 - y0) - h) / 2 + ymax * s
    return f'<path transform="translate({tx:.1f} {ty:.1f}) scale({s:.4f} {-s:.4f})" d="{d}" fill="{fill}"/>'


def place(ch, box, fill):
    """글리프를 box(x0, y0, x1, y1; SVG 좌표, 위→아래)에 비율 유지해 맞춘다."""
    d, _, (xmin, ymin, xmax, ymax) = g(ch)
    x0, y0, x1, y1 = box
    s = min((x1 - x0) / (xmax - xmin), (y1 - y0) / (ymax - ymin))
    w, h = (xmax - xmin) * s, (ymax - ymin) * s
    tx = x0 + ((x1 - x0) - w) / 2 - xmin * s
    ty = y0 + ((y1 - y0) - h) / 2 + ymax * s
    return f'<path transform="translate({tx:.1f} {ty:.1f}) scale({s:.4f} {-s:.4f})" d="{d}" fill="{fill}"/>'


def text_run(text, x_right, baseline, size, fill):
    upm = font["head"].unitsPerEm
    s = size / upm
    widths = [g(c)[1] * s if c != " " else size * 0.28 for c in text]
    x = x_right - sum(widths)
    out = []
    for c, w in zip(text, widths):
        if c != " ":
            out.append(f'<path transform="translate({x:.1f} {baseline:.1f}) scale({s:.4f} {-s:.4f})" d="{g(c)[0]}" fill="{fill}"/>')
        x += w
    return "".join(out)


def moss(cx, cy, w, h, n, seed):
    """가장자리에 붙어 자란 이끼: 작은 원을 어두운 바닥 → 밝은 윗부분 순으로 겹친다."""
    rnd = random.Random(seed)
    dots = []
    for _ in range(n):
        t = rnd.random()
        lift = 1 - abs(t - 0.5) * 2
        x, y = cx + (t - 0.5) * w, cy - rnd.random() * h * lift
        r = rnd.uniform(0.18, 0.34) * h * (0.6 + 0.4 * lift)
        tone = min(len(MOSS_TONES) - 1, int((cy - y) / h * len(MOSS_TONES) + rnd.random() * 2))
        dots.append((y, f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="{MOSS_TONES[tone]}"/>'))
    return "".join(d for _, d in sorted(dots, key=lambda d: -d[0]))


def build(with_sub: bool, ink: str = BASALT) -> str:
    parts = [
        place_d(*top_part("므"), (40, 120, 760, 600), ink),   # ᄆᆞ 의 ㅁ ('므'의 윗부분만)
        place("ㆍ", (340, 690, 480, 830), MOSS),              # ᄆᆞ 의 아래아 — 이끼색 점
        place("슬", (800, 60, 1620, 940), MOSS),
        moss(150, 130, 210, 78, 22, 1),               # ㅁ 왼쪽 위 모서리에 앉은 이끼
    ]
    height = 960
    if with_sub:
        parts.append(text_run("모슬, 내 마음속 고향", 1620, 1110, 130, ink))
        height = 1150
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1660 {height}" role="img" aria-label="ᄆᆞ슬">'
            f'{"".join(parts)}</svg>')


if __name__ == "__main__":
    out = ROOT / "frontend" / "assets"
    (out / "logo.svg").write_text(build(True), encoding="utf-8")
    (out / "logo-mark.svg").write_text(build(False), encoding="utf-8")
    html = ROOT / "frontend" / "index.html"
    src = html.read_text(encoding="utf-8")
    a, b = "<!--LOGO-->", "<!--/LOGO-->"
    if a in src:   # 헤더: 'ᄆᆞ' 를 currentColor 로 → 다크 모드에서 글자색을 따라간다
        src = src[: src.index(a) + len(a)] + build(False, "currentColor") + src[src.index(b):]
        html.write_text(src, encoding="utf-8")
    print("frontend/assets/logo.svg, logo-mark.svg, index.html 헤더 로고")
