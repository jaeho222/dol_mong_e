"""제주 밭담(현무암 돌담) 띠 그림을 만든다 → frontend/assets/batdam.svg
가로로 이어 붙여도 이음새가 안 보이게 양 끝 돌을 맞춘다. 사용: python scripts/build_batdam.py
"""
import math
import random
from pathlib import Path

random.seed(7)
W, H = 640, 120
STONE = ["#3b3e42", "#44484d", "#34373b", "#4c5055", "#2f3235"]
out = []


def stone(cx, cy, rx, ry):
    n = random.choice([5, 6, 6, 7])
    rot = random.uniform(0, 2 * math.pi)
    pts = []
    for k in range(n):
        a = rot + 2 * math.pi * k / n + random.uniform(-0.35, 0.35)
        r = random.uniform(0.78, 1.18)
        pts.append((cx + math.cos(a) * rx * r, cy + math.sin(a) * ry * r))
    d = "M" + " ".join(f"{(pts[k][0] + pts[(k + 1) % n][0]) / 2:.1f},{(pts[k][1] + pts[(k + 1) % n][1]) / 2:.1f}" for k in range(0))
    # 부드러운 닫힌 곡선 (중점 사이를 꼭짓점으로 Q)
    mids = [((pts[k][0] + pts[(k + 1) % n][0]) / 2, (pts[k][1] + pts[(k + 1) % n][1]) / 2) for k in range(n)]
    # 모서리만 살짝 둥근 각진 돌: 꼭짓점 앞뒤 18% 지점을 잇고 꼭짓점에서 Q
    def lerp(p, q, t): return (p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t)
    seg = []
    for k in range(n):
        prv, cur, nxt = pts[k - 1], pts[k], pts[(k + 1) % n]
        seg.append((lerp(cur, prv, .18), cur, lerp(cur, nxt, .18)))
    d = f"M{seg[0][2][0]:.1f},{seg[0][2][1]:.1f} " + " ".join(f"L{a[0]:.1f},{a[1]:.1f} Q{c[0]:.1f},{c[1]:.1f} {b[0]:.1f},{b[1]:.1f}" for a, c, b in seg[1:] + seg[:1]) + "Z"
    col = random.choice(STONE)
    g = [f'<path d="{d}" fill="{col}"/>']
    # 윗면 빛
    g.append(f'<path d="{d}" fill="none" stroke="#ffffff" stroke-opacity=".07" stroke-width="2" transform="translate(0 -1)"/>')
    # 구멍
    for _ in range(int(rx * ry / 90)):
        a = random.uniform(0, 2 * math.pi); r = random.uniform(0, 0.75)
        x, y = cx + math.cos(a) * rx * r, cy + math.sin(a) * ry * r
        g.append(f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="{random.uniform(1, 2.6):.1f}" ry="{random.uniform(.8, 1.8):.1f}" fill="#222427" opacity=".75"/>')
    # 이끼
    if random.random() < 0.18:  # 이끼: 아래쪽 틈에 작게 여러 점
        a = random.uniform(0.6, 2.5)
        for _ in range(random.randint(4, 8)):
            x = cx + math.cos(a) * rx * 0.8 + random.uniform(-7, 7)
            y = cy + math.sin(a) * ry * 0.8 + random.uniform(-3, 3)
            g.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{random.uniform(1.4, 3.2):.1f}" fill="{random.choice(["#5f7f45", "#6f8f52", "#4e6b3a"])}"/>')
    return "".join(g)


def row(y, h, start, gap=0):
    x = start
    while x < W:
        w = random.uniform(30, 84)
        cx = x + w / 2
        if cx - w / 2 < W:
            s = stone(cx, y + random.uniform(-5, 5), w / 2 + 3, h / 2 + random.uniform(-4, 5))
            out.append(s)
            if cx + w / 2 > W:  # 오른쪽 끝을 넘어가면 왼쪽에도 같은 돌
                out.append(f'<g transform="translate({-W} 0)">{s}</g>')
        x += w - random.uniform(0, 6) + (gap if random.random() < 0.25 else 0)


row(98, 40, -10)
row(64, 36, 18)
row(36, 30, -4, gap=26)  # 윗줄은 듬성듬성
svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">{"".join(out)}</svg>'
p = Path(__file__).resolve().parents[1] / "frontend" / "assets" / "batdam.svg"
p.write_text(svg, encoding="utf-8")
print(p.name, len(svg) // 1024, "KB")
