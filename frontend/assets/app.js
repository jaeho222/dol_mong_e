// 프론트엔드 로직 (빌드 도구 없는 바닐라 JS)
// ① 초기화(배너·탭·조건)  ② 조건 바 → /api/estimate (바꿀 때마다 자동 재계산)
// ③ Agent 시트 → /api/chat  ④ 카드 렌더링
// TODO[FRONT]: 지도 탭(카카오/Leaflet), 카드 클릭 시 상세 시트, 기간별 비용 비교 차트

const CFG = window.APP_CONFIG;
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];

// window.STATIC_DEMO 가 있으면(노션 임베드용 정적 데모) 서버 대신 미리 계산된 결과를 쓴다 — scripts/build_static_demo.py
const api = (path, body) => window.STATIC_DEMO ? Promise.resolve(window.STATIC_DEMO.handle(path, body)) :
  fetch(CFG.apiBase + path, body ? {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  } : undefined).then(async (r) => { if (!r.ok) throw new Error(await r.text()); return r.json(); });

const state = { zone: "", last: null, toggles: { with_kids: false, remote_work: false, prefer_quiet: false } };

// ① 초기화 ─────────────────────────────────────────
function init() {
  const tb = CFG.topBanner;
  $("#top-banner").href = tb.url;
  $("#nav-support").href = tb.url;
  $("#tb-tag").textContent = tb.tag;
  $("#tb-text").textContent = tb.text;
  $("#tb-sub").textContent = tb.sub;

  renderBanners();

  const saved = safeGet("theme");
  if (saved) document.documentElement.dataset.theme = saved;
  $("#theme-toggle").onclick = () => {
    const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    safeSet("theme", next);
  };

  const d = new Date(); d.setMonth(d.getMonth() + 1, 1);  // 기본: 다음 달
  $("#c-month").value = ym(d);

  $$("#conditions select, #conditions input").forEach((el) => el.addEventListener("change", runEstimate));
  $$(".toggle").forEach((el) => {
    el.setAttribute("aria-pressed", "false");
    el.onclick = () => {
      const k = el.dataset.toggle;
      state.toggles[k] = !state.toggles[k];
      el.setAttribute("aria-pressed", String(state.toggles[k]));
      runEstimate();
    };
  });
  $$(".tab").forEach((t) => t.onclick = () => {
    $$(".tab").forEach((x) => x.classList.toggle("active", x === t));
    state.zone = t.dataset.zone;
    if (state.last) renderResults(state.last, $("#results-title").textContent);
  });

  // Agent 시트
  $$("[data-open-agent]").forEach((b) => b.onclick = (e) => { e.preventDefault(); openSheet(); });
  $("#sheet-close").onclick = closeSheet;
  $("#sheet-backdrop").onclick = closeSheet;
  $("#examples").innerHTML = CFG.examples.map((e) => `<button type="button">${escapeHtml(e)}</button>`).join("");
  $$("#examples button").forEach((b) => b.onclick = () => ask(b.textContent));
  $("#ask").onsubmit = (e) => { e.preventDefault(); ask($("#ask-text").value); };

  api("/api/health").then((h) => {
    $("#mode-label").textContent = h.agent_mode === "claude" ? "Claude" : "데모 모드";
    if (h.dummy_data) $("#data-note").textContent = "지금은 더미 데이터예요";
  }).catch(() => {});

  runEstimate();
}

function renderBanners() {
  const el = $("#carousel");
  el.innerHTML = CFG.banners.map((b, i) => `
    <button class="banner tone-${b.tone}" data-i="${i}">
      ${ART[b.art] || ""}
      <span class="eyebrow">${escapeHtml(b.eyebrow)}</span>
      <h2>${escapeHtml(b.title)}</h2>
      <p>${escapeHtml(b.sub)}</p>
    </button>`).join("");
  $("#dots").innerHTML = CFG.banners.map((_, i) => `<i class="${i ? "" : "on"}"></i>`).join("");
  $$(".banner", el).forEach((b) => b.onclick = () => bannerAction(CFG.banners[b.dataset.i].action));
  el.addEventListener("scroll", () => {
    const w = el.firstElementChild.getBoundingClientRect().width + 16;
    const idx = Math.round(el.scrollLeft / w);
    $$("#dots i").forEach((d, i) => d.classList.toggle("on", i === idx));
  }, { passive: true });
}

// 배너 일러스트 — 제주 상징을 단순한 도형으로 직접 그림 (오른쪽 위에 배치)
const ART = {
  // 귤 두 알과 잎
  gyul: `<svg class="deco" viewBox="0 0 400 300" preserveAspectRatio="xMaxYMin meet" aria-hidden="true">
    <g transform="translate(266 104)">
      <circle r="52" fill="#f6a65e"/><circle r="52" fill="url(#gyulShade)"/>
      <g fill="#e07b24" opacity=".55"><circle cx="-18" cy="-6" r="2.4"/><circle cx="6" cy="14" r="2.2"/><circle cx="20" cy="-18" r="2"/><circle cx="-6" cy="28" r="2"/><circle cx="26" cy="12" r="2.2"/><circle cx="-28" cy="18" r="1.8"/></g>
      <path d="M0 -50 q4 -10 2 -18" stroke="#3f5a30" stroke-width="5" stroke-linecap="round" fill="none"/>
      <path d="M2 -64 C 24 -86, 58 -78, 64 -60 C 40 -50, 16 -52, 2 -64 Z" fill="#5e7d4a"/>
      <path d="M8 -62 C 26 -68, 44 -66, 58 -60" stroke="#3f5a30" stroke-width="2" fill="none" opacity=".6"/>
    </g>
    <g transform="translate(192 166)"><circle r="30" fill="#f8b673"/><circle cx="-8" cy="-4" r="1.8" fill="#e07b24" opacity=".5"/><circle cx="9" cy="8" r="1.6" fill="#e07b24" opacity=".5"/><path d="M0 -29 q2 -6 1 -10" stroke="#3f5a30" stroke-width="4" stroke-linecap="round"/></g>
    <defs><radialGradient id="gyulShade" cx=".35" cy=".3" r=".8"><stop offset="0" stop-color="#fff" stop-opacity=".35"/><stop offset=".6" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#c85f15" stop-opacity=".35"/></radialGradient></defs>
  </svg>`,

  // 돌하르방: 벙거지 모자, 툭 튀어나온 눈, 큰 코, 배 위에 얹은 두 손
  hareubang: `<svg class="deco" viewBox="0 0 400 300" preserveAspectRatio="xMaxYMin meet" aria-hidden="true">
    <g transform="translate(300 22)" fill="#2b2f31">
      <path d="M-46 40 C -46 6, 46 6, 46 40 Z"/>
      <rect x="-54" y="36" width="108" height="12" rx="6"/>
      <path d="M-42 48 C -50 110, -46 170, -40 200 L 40 200 C 46 170, 50 110, 42 48 Z"/>
      <g fill="#4a5052"><circle cx="-18" cy="70" r="11"/><circle cx="18" cy="70" r="11"/></g>
      <g fill="#7c8384"><circle cx="-16" cy="68" r="4"/><circle cx="20" cy="68" r="4"/></g>
      <rect x="-9" y="74" width="18" height="34" rx="9" fill="#4a5052"/>
      <path d="M-14 120 q14 6 28 0" stroke="#4a5052" stroke-width="4" stroke-linecap="round" fill="none"/>
      <rect x="-40" y="140" width="46" height="14" rx="7" fill="#4a5052"/>
      <rect x="-4" y="158" width="44" height="14" rx="7" fill="#4a5052"/>
      <g fill="#3a3f40" opacity=".9"><circle cx="-30" cy="96" r="2"/><circle cx="30" cy="104" r="2.2"/><circle cx="-26" cy="186" r="2"/><circle cx="24" cy="184" r="1.8"/><circle cx="-8" cy="30" r="1.8"/><circle cx="18" cy="24" r="1.6"/></g>
    </g>
  </svg>`,

  // 한라산 능선 + 흰 눈 + 감귤빛 해
  hallasan: `<svg class="deco" viewBox="0 0 400 300" preserveAspectRatio="xMaxYMin meet" aria-hidden="true">
    <circle cx="328" cy="56" r="26" fill="#f29b4b"/>
    <path d="M120 170 C 190 120, 230 82, 262 78 C 286 76, 300 86, 330 108 C 360 130, 390 150, 420 170 Z" fill="#3c4244"/>
    <path d="M232 96 C 246 84, 256 78, 264 78 C 280 77, 292 84, 306 96 C 296 100, 290 94, 282 100 C 272 92, 262 102, 252 96 C 244 102, 238 98, 232 96 Z" fill="#ecebe4"/>
    <path d="M150 170 Q 190 150 230 160 Q 270 148 310 162 Q 350 150 420 168 L 420 176 L 150 176 Z" fill="#4a5052"/>
  </svg>`,

  // 현무암 돌담과 초가
  dotdam: `<svg class="deco" viewBox="0 0 400 300" preserveAspectRatio="xMaxYMin meet" aria-hidden="true">
    <g transform="translate(210 46)">
      <path d="M20 58 C 40 20, 120 14, 150 58 Z" fill="#c9b78f"/>
      <path d="M30 46 Q 85 36 140 46 M44 34 Q 85 26 126 34" stroke="#a8946b" stroke-width="2.5" fill="none"/>
      <rect x="34" y="56" width="104" height="44" fill="#ece3cf"/>
      <rect x="74" y="70" width="22" height="30" fill="#7a6a4f"/>
    </g>
    <g fill="#2b2f31">
      <ellipse cx="200" cy="164" rx="22" ry="15"/><ellipse cx="242" cy="160" rx="20" ry="17"/><ellipse cx="284" cy="165" rx="24" ry="14"/>
      <ellipse cx="326" cy="161" rx="19" ry="16"/><ellipse cx="366" cy="164" rx="23" ry="15"/><ellipse cx="404" cy="161" rx="18" ry="15"/>
      <ellipse cx="220" cy="136" rx="20" ry="14"/><ellipse cx="262" cy="134" rx="22" ry="15"/><ellipse cx="305" cy="137" rx="19" ry="13"/>
      <ellipse cx="346" cy="134" rx="22" ry="15"/><ellipse cx="388" cy="136" rx="20" ry="14"/>
    </g>
    <g fill="#5f6567"><circle cx="196" cy="160" r="2.4"/><circle cx="248" cy="156" r="2"/><circle cx="290" cy="162" r="2.2"/><circle cx="330" cy="158" r="2"/><circle cx="226" cy="132" r="2"/><circle cx="268" cy="130" r="2.2"/><circle cx="350" cy="131" r="2"/><circle cx="370" cy="162" r="2.2"/></g>
  </svg>`,
};

function bannerAction(a) {
  if (a.type === "link") window.open(a.url, "_blank", "noopener");
  else if (a.type === "ask") { openSheet(); ask(a.text); }
  else if (a.type === "preset") {
    const c = a.conditions;
    if (c.days) $("#c-days").value = String(c.days);
    if (c.start_month) {
      const now = new Date();
      const y = c.start_month <= now.getMonth() + 1 ? now.getFullYear() + 1 : now.getFullYear();
      $("#c-month").value = `${y}-${String(c.start_month).padStart(2, "0")}`;
    }
    runEstimate();
    $("#conditions").scrollIntoView({ behavior: "smooth", block: "start" });
  }
}

// ② 조건 바 → 계산 ──────────────────────────────────
function readConditions() {
  const budget = parseInt($("#c-budget").value, 10);
  const m = $("#c-month").value;
  return {
    start_date: m ? `${m}-01` : null,
    days: +$("#c-days").value,
    people: +$("#c-people").value,
    car: $("#c-car").value === "true",
    budget_total: budget > 0 ? budget : null,
    ...state.toggles,
  };
}

async function runEstimate() {
  try {
    renderResults(await api("/api/estimate", { conditions: readConditions(), top_k: 14 }));
  } catch (e) {
    $("#grid").innerHTML = `<p class="empty">계산하지 못했어요. ${escapeHtml(e.message)}</p>`;
  }
}

// ③ Agent ─────────────────────────────────────────
function openSheet() { document.body.classList.add("sheet-open"); $("#sheet").setAttribute("aria-hidden", "false"); setTimeout(() => $("#ask-text").focus(), 200); }
function closeSheet() { document.body.classList.remove("sheet-open"); $("#sheet").setAttribute("aria-hidden", "true"); }

async function ask(text) {
  text = (text || "").trim();
  if (!text) return;
  $("#ask-text").value = "";
  addMsg("user", text);
  const loading = addMsg("bot loading", "계산하고 있어요…");
  try {
    const res = await api("/api/chat", { message: text });
    loading.remove();
    const el = addMsg("bot", "");
    el.innerHTML = mdLite(res.answer);
    if (res.trace?.length) el.insertAdjacentHTML("beforeend", `<div class="trace">사용한 도구 · ${res.trace.map((t) => t.tool).join(" → ")}</div>`);
    if (res.ranked) renderResults(res.ranked, "물어본 조건으로 본 동네");
  } catch (e) {
    loading.textContent = "답을 만들지 못했어요. " + e.message;
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

// ④ 카드 렌더링 ────────────────────────────────────
function renderResults(data, title = "이번 조건으로 본 동네") {
  state.last = data;
  $("#results-title").textContent = title;
  const list = data.results
    .map((r, i) => ({ ...r, rank: i + 1 }))
    .filter((r) => !state.zone || r.zone === state.zone);
  if (!list.length) {
    const near = (data.over_budget || []).slice(0, 3).map((o) => `${o.name} ${won(o.total)}원`).join(", ");
    $("#grid").innerHTML = `<p class="empty">${data.results.length ? "이 권역엔 조건에 맞는 동네가 없어요." : "예산 안에 드는 동네가 없어요."}${near ? `<br/>가장 가까운 곳 · ${near}` : ""}</p>`;
    return;
  }
  $("#grid").innerHTML = list.map(placeCard).join("");
}

function placeCard(r) {
  const c = r.cost;
  const items = Object.entries(c.breakdown);
  const sum = items.reduce((a, [, v]) => a + v, 0) || 1;
  const coord = r.lat ? `${(+r.lat).toFixed(2)}°N ${(+r.lon).toFixed(2)}°E` : r.zone;
  const short = r.name.replace(/(읍|면)$/, "");
  const img = (window.REGION_IMAGES || {})[r.region_id];
  return `
  <article class="place">
    <div class="thumb zone-${r.zone}${img ? " has-photo" : ""}">
      ${img ? `<img class="photo" src="${img.src}" alt="${escapeHtml(img.place)}" loading="lazy" onerror="this.remove()">` : ""}
      ${r.rank <= 3 ? `<span class="ribbon">${r.rank}</span>` : ""}
      <span class="coord">${coord}</span>
      <span class="big">${escapeHtml(short)}</span>
      <span class="price"><b>${won(c.range[0])}~${won(c.range[1])}</b>원</span>
    </div>
    <div class="place-body">
      <div class="place-title"><h4>${escapeHtml(r.name)}</h4><span class="zone">${r.zone}</span></div>
      <div class="place-line">${c.conditions.days}일 · 월 ${won(c.per_month)}원 · ${items.map(([k, v]) => `${k} ${v}`).join(" · ")} (만원)</div>
      <div class="bar">${items.map(([, v]) => `<i style="width:${(v / sum) * 100}%"></i>`).join("")}</div>
      <div class="tags">
        ${r.badges.map((b) => `<span class="good">${b}</span>`).join("")}
        ${r.warnings.map((w) => `<span class="warn">${w}</span>`).join("")}
      </div>
      <div class="tier">${c.tier} 기준${c.alternatives.length ? ` · ${c.alternatives[0].tier}이면 숙소 ${won(c.alternatives[0].lodging)}원` : ""}</div>
      ${img ? `<a class="credit" href="${img.page}" target="_blank" rel="noopener">사진 · ${escapeHtml(img.place)} · ${escapeHtml(img.artist)} · ${img.license}</a>` : ""}
    </div>
  </article>`;
}

// ── 유틸 ──
const won = (v) => `${Number(v).toLocaleString()}만`;
const ym = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
function escapeHtml(s) { return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }
function mdLite(s) { return escapeHtml(s).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/(^|\s)_(.+?)_(\s|$)/g, "$1<i>$2</i>$3"); }
function safeGet(k) { try { return localStorage.getItem(k); } catch { return null; } }
function safeSet(k, v) { try { localStorage.setItem(k, v); } catch {} }

init();
