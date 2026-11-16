"""서버 없이 열리는 단일 HTML 데모를 만든다 (노션 임베드·발표 백업용).

사용: python scripts/build_static_demo.py  →  dist/demo.html
- 예시 질문(config.js 의 examples)과 폼 기본 조건의 결과를 지금 데이터로 미리 계산해 HTML 안에 넣는다.
- 그 외 입력은 계산하지 않고 가장 가까운 예시 결과를 보여준다. 실제 동작은 서버(로컬/Vercel) 버전에서.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.agent.mock_agent import run_mock_agent  # noqa: E402
from backend.tools.data_loader import data_is_dummy  # noqa: E402
from backend.tools.region import list_regions, rank_regions  # noqa: E402

FE = ROOT / "frontend"
html = (FE / "index.html").read_text(encoding="utf-8")
css = (FE / "assets" / "style.css").read_text(encoding="utf-8")
cfg = (FE / "assets" / "config.js").read_text(encoding="utf-8")
app = (FE / "assets" / "app.js").read_text(encoding="utf-8")

examples = re.findall(r'^\s*"([^"]+)",\s*$', cfg.split("examples:")[1], re.M)
chats = {q: run_mock_agent(q) for q in examples}
for v in chats.values():
    v["answer"] = v["answer"].replace("_(키 없이 도는 데모 모드 답변이에요)_", "_(노션 미리보기 — 예시 질문의 미리 계산된 결과예요)_")
estimate = rank_regions({"days": 30, "people": 2, "car": True}, top_k=6)


def slim(ranked: dict) -> dict:
    """임베드 용량을 줄이기 위해 화면에 안 쓰는 필드를 뺀다."""
    if not ranked:
        return ranked
    keep_cost = ("tier", "total", "range", "per_month", "breakdown", "alternatives")
    out = {"results": [], "over_budget": ranked["over_budget"]}
    for r in ranked["results"]:
        c = {k: r["cost"][k] for k in keep_cost}
        c["conditions"] = {"days": r["cost"]["conditions"]["days"]}
        out["results"].append({k: r[k] for k in ("name", "zone", "score", "badges", "warnings")} | {"cost": c})
    return out


for v in chats.values():
    v["ranked"] = slim(v["ranked"])
    v["trace"] = [{"tool": t["tool"]} for t in v["trace"]]
estimate = slim(estimate)

static = f"""<script>
window.STATIC_DEMO = (() => {{
  const D = {json.dumps({"chats": chats, "estimate": estimate, "regions": [{"name": r["name"]} for r in list_regions()],
                          "health": {"ok": True, "agent_mode": "mock", "dummy_data": data_is_dummy()}},
                         ensure_ascii=False, default=str)};
  const keys = Object.keys(D.chats);
  return {{ handle(path, body) {{
    if (path === "/api/health") return D.health;
    if (path === "/api/regions") return D.regions;
    if (path === "/api/estimate") return D.estimate;
    if (path === "/api/chat") return D.chats[body.message] || D.chats[keys[0]];
  }} }};
}})();
</script>"""

out = html.replace('<link rel="stylesheet" href="assets/style.css" />', f"<style>{css}</style>")
out = out.replace('<script src="assets/config.js"></script>', f"<script>{cfg}</script>{static}")
out = out.replace('<script src="assets/app.js"></script>', f"<script>{app}</script>")
out = out.replace("<body>", '<body><div class="notice" style="border-radius:0;margin:0;text-align:center">📌 노션 미리보기용 정적 데모 — 예시 질문만 동작해요. 실제 계산은 서버 버전에서.</div>', 1)

dist = ROOT / "dist"
dist.mkdir(exist_ok=True)
(dist / "demo.html").write_text(out, encoding="utf-8")
print(f"dist/demo.html ({len(out.encode()) // 1024} KB)")
