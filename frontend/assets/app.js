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
  $("#logo-main").textContent = CFG.name.main;
  $("#logo-accent").textContent = CFG.name.accent;

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
      ${bannerDeco(b.tone)}
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

// 배너 장식: 오름 실루엣과 해 — 색만 바꿔 반복하는 단순한 도형
function bannerDeco(tone) {
  return `<svg class="deco" viewBox="0 0 400 300" preserveAspectRatio="xMaxYMin slice" aria-hidden="true">
    <path d="M150 150 Q260 30 370 150Z" fill="#fff" opacity=".10"/>
    <path d="M250 160 Q330 80 430 160Z" fill="#fff" opacity=".08"/>
    <circle cx="340" cy="62" r="22" fill="${tone === "basalt" ? "#f29b4b" : "#fff"}" opacity="${tone === "basalt" ? ".95" : ".22"}"/>
  </svg>`;
}

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
