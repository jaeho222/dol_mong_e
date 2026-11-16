// 프론트엔드 로직 (빌드 도구 없는 바닐라 JS)
// 구성: ① 초기화  ② 폼 → /api/estimate  ③ 대화 → /api/chat  ④ 결과 카드 렌더링
// TODO[FRONT]: 지도(카카오/Leaflet) 위에 결과 표시, 카드 클릭 시 상세 모달, 기간별 비용 비교 차트

const CFG = window.APP_CONFIG;
const $ = (s) => document.querySelector(s);
const api = (path, body) =>
  fetch(CFG.apiBase + path, body ? {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  } : undefined).then(async (r) => { if (!r.ok) throw new Error(await r.text()); return r.json(); });

// ① 초기화 ─────────────────────────────────────────
function init() {
  $("#logo-main").textContent = CFG.name.main;
  $("#logo-accent").textContent = CFG.name.accent;
  $("#tagline").textContent = CFG.tagline;
  $("#hero-chip").textContent = CFG.heroChip;

  const saved = safeGet("theme");
  if (saved) document.documentElement.dataset.theme = saved;
  $("#theme-toggle").onclick = () => {
    const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    safeSet("theme", next);
  };

  const d = new Date(); d.setMonth(d.getMonth() + 1, 1);   // 기본값: 다음 달 1일 (로컬 시간 기준)
  $("#start").value = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-01`;

  document.querySelectorAll(".chip[data-group]").forEach((el) => el.onclick = () => {
    document.querySelectorAll(`.chip[data-group="${el.dataset.group}"]`).forEach((c) => c.setAttribute("aria-pressed", "false"));
    el.setAttribute("aria-pressed", "true");
  });
  document.querySelectorAll(".chip[data-toggle]").forEach((el) => el.onclick = () =>
    el.setAttribute("aria-pressed", el.getAttribute("aria-pressed") === "true" ? "false" : "true"));

  $("#examples").innerHTML = CFG.examples.map((e) => `<button class="chip">${e}</button>`).join("");
  $("#examples").querySelectorAll(".chip").forEach((b) => b.onclick = () => { $("#chat-text").value = b.textContent; sendChat(); });

  $("#estimate-btn").onclick = runEstimate;
  $("#chat-send").onclick = sendChat;
  $("#chat-text").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); sendChat(); }
  });

  api("/api/regions").then((r) => $("#region-count").textContent = r.length).catch(() => {});
  api("/api/health").then((h) => {
    $("#mode-label").textContent = h.agent_mode === "claude" ? "Claude Agent" : "데모 모드 (API 키 없음)";
    if (h.dummy_data) $("#notice").innerHTML = `<div class="notice">⚠️ 지금은 <b>더미 데이터</b>로 동작 중이에요. 숫자는 화면 확인용이에요.</div>`;
  }).catch(() => {});
}

// ② 폼 경로 ────────────────────────────────────────
function readForm() {
  const pressed = (sel) => document.querySelector(sel)?.getAttribute("aria-pressed") === "true";
  const budget = parseInt($("#budget").value, 10);
  return {
    start_date: $("#start").value || null,
    days: parseInt($("#days").value, 10),
    people: parseInt($("#people").value, 10),
    car: document.querySelector('.chip[data-group="car"][aria-pressed="true"]').dataset.value === "true",
    budget_total: Number.isFinite(budget) && budget > 0 ? budget : null,
    with_kids: pressed('[data-toggle="with_kids"]'),
    remote_work: pressed('[data-toggle="remote_work"]'),
    prefer_quiet: pressed('[data-toggle="prefer_quiet"]'),
  };
}

async function runEstimate() {
  const btn = $("#estimate-btn");
  btn.disabled = true; btn.textContent = "계산 중…";
  try {
    renderResults(await api("/api/estimate", { conditions: readForm(), top_k: 6 }));
    $("#results").scrollIntoView({ behavior: "smooth" });
  } catch (e) {
    $("#result-grid").innerHTML = `<div class="empty card">계산에 실패했어요: ${escapeHtml(e.message)}</div>`;
  } finally {
    btn.disabled = false; btn.textContent = "🔍 동네 비교하기";
  }
}

// ③ 대화 경로 ──────────────────────────────────────
async function sendChat() {
  const text = $("#chat-text").value.trim();
  if (!text) return;
  $("#chat-text").value = "";
  addMsg("user", text);
  const loading = addMsg("bot loading", "동네별 비용을 계산하고 있어요…");
  try {
    const res = await api("/api/chat", { message: text });
    loading.remove();
    const el = addMsg("bot", "");
    el.innerHTML = mdLite(res.answer);
    if (res.trace?.length) el.insertAdjacentHTML("beforeend",
      `<div class="trace">🔧 사용한 도구: ${res.trace.map((t) => t.tool).join(" → ")}</div>`);
    if (res.ranked) renderResults(res.ranked);
  } catch (e) {
    loading.textContent = "오류가 났어요: " + e.message;
  }
}

function addMsg(cls, text) {
  const el = document.createElement("div");
  el.className = "msg " + cls;
  el.textContent = text;
  $("#msgs").appendChild(el);
  $("#msgs").scrollTop = $("#msgs").scrollHeight;
  return el;
}

// ④ 결과 렌더링 ────────────────────────────────────
function renderResults(data) {
  const grid = $("#result-grid");
  if (!data.results.length) {
    const near = data.over_budget.slice(0, 3).map((o) => `${o.name} ${won(o.total)}`).join(", ");
    grid.innerHTML = `<div class="empty card">예산 안에 맞는 동네가 없어요.${near ? "<br/>가장 가까운 곳: " + near : ""}</div>`;
    return;
  }
  grid.innerHTML = data.results.map((r, i) => regionCard(r, i)).join("");
}

function regionCard(r, i) {
  const c = r.cost;
  const items = Object.entries(c.breakdown);
  const sum = items.reduce((a, [, v]) => a + v, 0) || 1;
  return `
  <article class="card region-card">
    <div class="rank">추천 ${i + 1}위 · 적합도 ${r.score}</div>
    <h4>${r.name}</h4><div class="zone">${r.zone}</div>
    <div class="price"><b>${won(c.range[0])}~${won(c.range[1])}</b> <small>총 ${c.conditions.days}일 · 월 ${won(c.per_month)}</small></div>
    <div class="bar">${items.map(([, v]) => `<i style="width:${(v / sum) * 100}%"></i>`).join("")}</div>
    <div class="legend">${items.map(([k, v]) => `<span>${k} ${won(v)}</span>`).join("")}</div>
    <div class="tier">숙소 형태: ${c.tier}${c.alternatives.length ? ` (비교: ${c.alternatives[0].tier} ${won(c.alternatives[0].lodging)})` : ""}</div>
    <div class="badges">
      ${r.badges.map((b) => `<span class="badge">${b}</span>`).join("")}
      ${r.warnings.map((w) => `<span class="badge warn">${w}</span>`).join("")}
    </div>
  </article>`;
}

// ── 유틸 ──
const won = (v) => `${Number(v).toLocaleString()}만`;
function escapeHtml(s) { return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }
function mdLite(s) { // **굵게**, _기울임_ 정도만 지원
  return escapeHtml(s).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/(^|\s)_(.+?)_(\s|$)/g, "$1<i>$2</i>$3");
}
function safeGet(k) { try { return localStorage.getItem(k); } catch { return null; } }
function safeSet(k, v) { try { localStorage.setItem(k, v); } catch {} }

init();
