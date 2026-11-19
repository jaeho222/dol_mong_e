// 돌몽이 프론트엔드 (빌드 도구 없는 바닐라 JS)
// ① 검색바·돌몽이 타일 → /api/estimate   ② 추천 동네: 목록 + 지도   ③ 선택한 동네: 비용·돌몽이 한마디·생활 점수·세심 체크·지수
// ④ 돌몽이 AI Agent 상담 → /api/consult — 웹은 오른쪽 30% 고정(리포트 70%), 모바일은 플로팅 창.
//    버튼은 규칙, 자유 질문은 Claude Agent 가 도구를 골라 쓰고, 리포트 수정은 '제안 카드'로 묻고 사용자가 적용
const CFG = window.APP_CONFIG;
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];

// window.STATIC_DEMO 가 있으면(노션 임베드용 정적 데모) 서버 대신 미리 계산된 결과를 쓴다 — scripts/build_static_demo.py
const api = (path, body) => window.STATIC_DEMO ? Promise.resolve(window.STATIC_DEMO.handle(path, body)) :
  fetch(CFG.apiBase + path, body ? {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  } : undefined).then(async (r) => { if (!r.ok) throw new Error(await r.text()); return r.json(); });

const state = { people: 2, data: null, selected: null };
const DAYS_LABEL = { 14: "2주", 30: "한 달", 60: "두 달", 90: "석 달", 180: "반년", 365: "1년" };
const TOOL_LABEL = {
  list_regions: "동네 목록 확인",
  rank_regions: "조건에 맞춰 동네 순위 매기기",
  estimate_total_cost: "체류 비용 계산",
  get_region_detail: "동네 자세히 보기",
};
const SHOW = 7;  // 목록에 처음 보여줄 동네 수

// ① 검색바 ─────────────────────────────────────────
function init() {
  $("#support-link").href = CFG.support.url;
  heroPhoto();

  const sel = $("#f-month");
  const d = new Date(); d.setDate(1);
  for (let i = 1; i <= 12; i++) {
    const m = new Date(d.getFullYear(), d.getMonth() + i, 1);
    sel.add(new Option(`${m.getFullYear()}년 ${m.getMonth() + 1}월`, ym(m)));
  }

  $("#p-minus").onclick = () => setPeople(state.people - 1);
  $("#p-plus").onclick = () => setPeople(state.people + 1);
  setPeople(2);

  $("#f-opts").insertAdjacentHTML("beforeend", CFG.options.map((o) =>
    `<label class="chk"><input type="checkbox" data-k="${o.key}" />${escapeHtml(o.label)}</label>`).join(""));

  // 가장 중요한 것 3가지: 누른 순서 = 중요도 (3·2·1 가중치는 백엔드 region._weights)
  state.priorities = [];
  $("#f-prio").insertAdjacentHTML("beforeend", CFG.priorities.map((p) =>   
  `<button type="button" class="pchip" data-k="${escapeHtml(p.key)}">
    <img class="pchip-icon"
        src="assets/icons/${encodeURIComponent(p.icon)}"
        alt=""
        aria-hidden="true" />
    <span>${escapeHtml(p.label)}</span>
  </button>`).join(""));
  $$("#f-prio .pchip").forEach((b) => b.onclick = () => {
    const k = b.dataset.k, i = state.priorities.indexOf(k);
    if (i >= 0) state.priorities.splice(i, 1);
    else if (state.priorities.length < 3) state.priorities.push(k);
    drawPrio();
  });

  $("#plan").onsubmit = (e) => { e.preventDefault(); runEstimate(true); };
  // 조건을 바꾸면 바로 다시 계산해서 이전 결과와 비교 (0.5초 동안 더 안 바뀌면)
  const live = () => { clearTimeout(state.liveT); state.liveT = setTimeout(() => runEstimate(false, true), 500); };
  $("#plan").addEventListener("change", live);
  $("#plan").addEventListener("input", (e) => { if (e.target.id === "f-budget") live(); });
  ["#p-minus", "#p-plus"].forEach((id) => $(id).addEventListener("click", live));
  $("#f-prio").addEventListener("click", (e) => { if (e.target.closest(".pchip")) live(); });

  // 첫 방문 문답 다시 열기 (예전 '돌몽이랑 고르기' 타일)
  $("#redo-ob").onclick = () => window.startOnboarding?.();

  // 상담 (오른쪽 아래 플로팅 창)
  initConsult();
  // 근거 '?' 버튼 (renderDetail 이 다시 그려도 동작하도록 위임)
  $("#detail-in").addEventListener("click", (e) => {
    const q = e.target.closest("[data-ev]");
    if (q) { const box = $("#" + q.dataset.ev); box.hidden = !box.hidden; q.setAttribute("aria-expanded", String(!box.hidden)); return; }
    const tab = e.target.closest("[data-rh]");
    if (tab) { drawRehearsal(tab.dataset.rh); return; }
  });

  api("/api/health").then((h) => {
    state.agentMode = h.agent_mode;
    const m = $("#cs-mode");
    m.hidden = false;
    m.textContent = h.agent_mode === "claude" ? "AI Agent" : "기본 모드";
    m.classList.toggle("off", h.agent_mode !== "claude");
    m.title = h.agent_mode === "claude" ? "자유 질문은 AI Agent 가 도구를 골라 답해요" : "API 키가 없어 규칙 + 데이터로만 답해요";
    updateWhere();
    if (h.dummy_data) {
      $("#data-note").hidden = false;
      $("#data-note").textContent = "지금은 동네 지표가 더미 데이터예요. 제주데이터허브 실제 데이터로 바꾸는 중이에요.";
    }
  }).catch(() => {});

  // 글꼴이 늦게 오면 지도 이름표 폭을 다시 잰다
  document.fonts?.ready.then(() => state.data?.results.length && drawMap(state.data.results));
  // 돌몽이 말투 규칙(jeju_rules.json)을 받은 뒤 첫 계산 → 한마디가 처음부터 제주 어미로
  (window.jejuReady || Promise.resolve()).finally(() => runEstimate(false));
}

function drawPrio() {
  $$("#f-prio .pchip").forEach((b) => {
    const i = state.priorities.indexOf(b.dataset.k);
    b.classList.toggle("on", i >= 0);
    b.dataset.n = i >= 0 ? i + 1 : "";
  });
}

function heroPhoto() {
  const list = CFG.heroPhotos || [];
  if (!list.length) return;
  const p = list[Math.floor(Math.random() * list.length)];
  const file = encodeURIComponent(p.path.split("/").pop());
  const dir = p.path.split("/").slice(0, 2).join("/");
  $("#hero-photo").style.backgroundImage = `url("https://upload.wikimedia.org/wikipedia/commons/thumb/${dir}/${file}/1920px-${file}")`;
  $("#hero-credit").innerHTML = `${escapeHtml(p.place)} 사진: ${escapeHtml(p.artist)}, <a href="https://commons.wikimedia.org/wiki/File:${file}" target="_blank" rel="noopener">${escapeHtml(p.license)}</a>`;
}

function setPeople(n) {
  state.people = Math.min(6, Math.max(1, n));
  $("#f-people").textContent = `${state.people}명`;
  $("#p-minus").disabled = state.people === 1;
  $("#p-plus").disabled = state.people === 6;
}

function applyPreset(p) {
  if (p.month) {
    const now = new Date();
    const y = p.month <= now.getMonth() + 1 ? now.getFullYear() + 1 : now.getFullYear();
    $("#f-month").value = `${y}-${String(p.month).padStart(2, "0")}`;
  }
  if (p.days) $("#f-days").value = String(p.days);
  if (p.people) setPeople(p.people);
  if (p.car !== undefined) $("#f-car").value = String(p.car);
  if (p.budget !== undefined) $("#f-budget").value = p.budget ? String(p.budget) : "";
  $$("#f-opts input").forEach((c) => c.checked = !!p[c.dataset.k]);
  runEstimate(true);
}

function readConditions() {
  const budget = parseInt($("#f-budget").value, 10);
  return {
    start_date: `${$("#f-month").value}-01`,
    days: +$("#f-days").value,
    people: state.people,
    car: $("#f-car").value === "true",
    budget_total: budget > 0 ? budget : null,
    ...Object.fromEntries($$("#f-opts input").map((c) => [c.dataset.k, c.checked])),
    priorities: state.priorities || [],
  };
}

async function runEstimate(scroll, live) {
  // live: 조건만 바뀐 경우 — 목록을 지우지 않고 흐리게 둔 채 다시 계산, 바뀐 순위·금액을 표시
  const prev = live && state.data?.results?.length
    ? Object.fromEntries(state.data.results.map((r, i) => [r.region_id, { rank: i + 1, total: r.cost.total }])) : null;
  const prevCond = state.data?.conditions;
  if (live) $("#rank").classList.add("updating"); else $("#rank").innerHTML = `<li>${loaderHTML()}</li>`;
  if (scroll) $("#result").scrollIntoView({ behavior: "smooth" });
  try {
    const seq = (state.seq = (state.seq || 0) + 1);
    const req = api("/api/estimate", { conditions: readConditions(), top_k: 14 });
    const [data] = live ? [await req] : await Promise.all([req, wait(CFG.loader.minMs)]);
    if (seq !== state.seq) return;  // 더 최근 요청이 있으면 이 응답은 버린다
    $("#rank").classList.remove("updating");
    state.prev = prev;
    renderResults(data);
    renderLiveNote(prev, prevCond, data);
    renderBudgetAlt(data);
  } catch (e) {
    $("#rank").innerHTML = `<li class="empty">추천을 계산하지 못했어요. 서버가 켜져 있는지 확인해 주세요. (${escapeHtml(e.message)})</li>`;
  }
}

// ② 추천 동네 ─────────────────────────────────────
function renderResults(data) {
  state.data = data;
  const c = data.conditions || data.results[0]?.cost.conditions || {};
  $("#cond-summary").textContent = summary(c);

  if (!data.results.length) {
    const near = (data.over_budget || []).slice(0, 3).map((o) => `${o.name} ${won(o.total)}`).join(", ");
    $("#rank").innerHTML = `<li class="empty">예산 안에 드는 동네가 없어요. 예산을 늘리거나 기간을 줄여 보세요.${near ? `<br />가장 가까운 곳: ${escapeHtml(near)}` : ""}</li>`;
    drawMap([]);
    $("#detail-in").innerHTML = "";
    return;
  }
  const imgs = window.REGION_IMAGES || {};
  $("#rank").innerHTML = data.results.map((r, i) => {
    const img = imgs[r.region_id];
    const tags = [...r.badges.slice(0, 2).map((b) => `<span class="tag">${escapeHtml(b)}</span>`),
      ...r.warnings.slice(0, 1).map((w) => `<span class="tag warn">${escapeHtml(w)}</span>`)].join("");
    return `<li${i >= SHOW ? " hidden" : ""}><button type="button" class="row" data-id="${r.region_id}">
      <span class="thumb">${img ? `<img src="${img.src}" alt="" loading="lazy" onerror="this.remove()" />` : ""}<span class="rk">${i + 1}</span></span>
      <span><span class="row-name">${escapeHtml(r.name)}</span>
        <span class="row-meta">${escapeHtml(r.zone)}, ${escapeHtml(traitName(r))}</span>
        ${tags ? `<span class="row-tags">${tags}</span>` : ""}</span>
      <span class="row-price"><b>${won(r.cost.total)}</b><span>${period(r.cost.conditions.days)} 예상</span>${deltaHTML(r, i)}</span>
    </button></li>`;
  }).join("");
  if (data.results.length > SHOW) {
    $("#rank").insertAdjacentHTML("beforeend", `<li><button type="button" class="more">나머지 ${data.results.length - SHOW}곳 더 보기</button></li>`);
    $("#rank .more").onclick = (e) => { $$("#rank li[hidden]").forEach((li) => li.hidden = false); e.target.closest("li").remove(); };
  }
  $$("#rank .row").forEach((b) => b.onclick = () => select(b.dataset.id, true));
  const keep = data.results.find((r) => r.region_id === state.selected);
  select((keep || data.results[0]).region_id, false);
}

// 조건 변경 전후 비교 ─────────────────────────────
function deltaHTML(r, i) {
  const p = state.prev?.[r.region_id];
  if (!state.prev) return "";
  if (!p) return `<em class="dl new">새로 들어옴</em>`;
  const dr = p.rank - (i + 1), dc = r.cost.total - p.total;
  const parts = [];
  if (dr) parts.push(`<em class="dl ${dr > 0 ? "up" : "down"}">${dr > 0 ? "▲" : "▼"}${Math.abs(dr)}</em>`);
  if (dc) parts.push(`<em class="dl ${dc < 0 ? "up" : "down"}">${dc > 0 ? "+" : ""}${dc.toLocaleString()}만</em>`);
  return parts.join("");
}

const COND_LABEL = { start_date: "시작 달", days: "기간", people: "인원", car: "렌터카", budget_total: "예산",
  with_kids: "아이", remote_work: "원격근무", with_pet: "반려동물", prefer_quiet: "조용한 곳", priorities: "중요한 것" };

function renderLiveNote(prev, prevCond, data) {
  const box = $("#live-note");
  if (!prev || !prevCond) { box.hidden = true; return; }
  const c = data.conditions;
  const changed = Object.keys(COND_LABEL).filter((k) => JSON.stringify(prevCond[k] ?? null) !== JSON.stringify(c[k] ?? null)).map((k) => COND_LABEL[k]);
  if (!changed.length) { box.hidden = true; return; }
  const now = data.results;
  if (!now.length) {
    box.innerHTML = `<span class="live-dot"></span><b>${changed.join("·")}</b>을(를) 바꿨더니 조건에 맞는 동네가 없어요. 아래 대안을 확인해 보세요.`;
    box.hidden = false; return;
  }
  const prevTop = Object.entries(prev).sort((a, b) => a[1].rank - b[1].rank)[0]?.[0];
  const top = now[0];
  const moved = now.map((r, i) => ({ r, d: prev[r.region_id] ? prev[r.region_id].rank - (i + 1) : null }))
    .filter((x) => x.d).sort((a, b) => Math.abs(b.d) - Math.abs(a.d))[0];
  const avg = (xs) => xs.length ? Math.round(xs.reduce((a, b) => a + b, 0) / xs.length) : 0;
  const before = avg(Object.values(prev).map((p) => p.total)), after = avg(now.map((r) => r.cost.total));
  const lines = [`<b>${changed.join("·")}</b>을(를) 바꿨더니`];
  lines.push(top && top.region_id !== prevTop ? `1위가 <b>${escapeHtml(top.name)}</b>(으)로 바뀌었어요` : `1위는 그대로 ${escapeHtml(top.name)}`);
  if (moved) lines.push(`${escapeHtml(moved.r.name)} ${moved.d > 0 ? "▲" : "▼"}${Math.abs(moved.d)}`);
  if (after !== before) lines.push(`평균 비용 ${after > before ? "+" : ""}${(after - before).toLocaleString()}만 원`);
  box.innerHTML = `<span class="live-dot"></span>${lines.join(" · ")}`;
  box.hidden = false;
}

// 예산 초과 대안 ─────────────────────────────────
async function renderBudgetAlt(data) {
  const box = $("#budget-alt");
  const b = data.conditions?.budget_total;
  if (!b || !data.over_budget?.length) { box.hidden = true; box.innerHTML = ""; return; }
  try {
    const res = await api("/api/budget-alternatives", { conditions: data.conditions });
    if (!res.items?.length) { box.hidden = true; return; }
    box.innerHTML = `<img class="ba-pose" src="${CFG.pose.calc}" alt="" width="64" height="64" /><h3>예산 ${won(b)}을 넘어서 빠진 동네 ${data.over_budget.length}곳</h3>
      <p class="ba-sub">점수가 높은데 예산 때문에 빠진 곳이에요. 비용 계산식을 조건만 바꿔 다시 돌려 봤어요.</p>
      <ul>${res.items.map((it) => `<li><div class="ba-head"><b>${escapeHtml(it.name)}</b> <span>${it.score}점 · ${won(it.total)} (예산 +${it.over.toLocaleString()}만)</span></div>
        ${it.fixes.length ? `<ul class="ba-fix">${it.fixes.map((f) => `<li>${escapeHtml(f.label)} → <b>${won(f.new_total)}</b> <small>${escapeHtml(f.how)}</small></li>`).join("")}</ul>`
          : `<p class="ba-none">조건을 한두 개 바꿔서는 예산 안에 들어오지 않아요.</p>`}</li>`).join("")}</ul>
      ${res.raise?.length ? `<p class="ba-raise">예산을 <b>${res.raise[0].plus.toLocaleString()}만 원</b>만 늘리면 ${escapeHtml(res.items.find((i) => i.over === res.raise[0].plus)?.name || data.over_budget[0].name)}도 들어와요.</p>` : ""}`;
    box.hidden = false;
  } catch { box.hidden = true; }
}

function select(id, scroll) {
  state.selected = id;
  $$("#rank .row").forEach((b) => b.setAttribute("aria-current", String(b.dataset.id === id)));
  drawMap(state.data.results);
  renderDetail(state.data.results.find((r) => r.region_id === id));
  if (scroll) $("#detail").scrollIntoView({ behavior: "smooth" });
}

// 제주 해안선 (경도, 위도) — 대략적인 모양. 핀은 실제 좌표로 찍는다.
const COAST = [
  [126.163, 33.300], [126.185, 33.352], [126.232, 33.400], [126.290, 33.437], [126.335, 33.462], [126.400, 33.477],
  [126.468, 33.500], [126.522, 33.518], [126.600, 33.527], [126.668, 33.544], [126.750, 33.556], [126.828, 33.546],
  [126.885, 33.523], [126.935, 33.478], [126.938, 33.440], [126.885, 33.385], [126.848, 33.328], [126.780, 33.300],
  [126.700, 33.274], [126.622, 33.246], [126.560, 33.238], [126.480, 33.236], [126.410, 33.238], [126.335, 33.222],
  [126.280, 33.200], [126.250, 33.210], [126.208, 33.240], [126.172, 33.268],
];
const UDO = [[126.940, 33.512], [126.962, 33.520], [126.968, 33.505], [126.950, 33.494], [126.936, 33.500]];
const K = 860, LON0 = 126.13, LAT0 = 33.585, COS = 0.836;
const px = ([lon, lat]) => [(lon - LON0) * COS * K, (LAT0 - lat) * K];
function smooth(pts) {
  const p = pts.map(px), n = p.length, f = (v) => v.map((x) => x.toFixed(1)).join(" ");
  let d = `M${f(p[0])}`;
  for (let i = 0; i < n; i++) {
    const p0 = p[(i - 1 + n) % n], p1 = p[i], p2 = p[(i + 1) % n], p3 = p[(i + 2) % n];
    d += ` C${f([p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6])} ${f([p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6])} ${f(p2)}`;
  }
  return d + "Z";
}

function drawMap(results) {
  const W = (126.99 - LON0) * COS * K, H = (LAT0 - 33.17) * K;
  const [hx, hy] = px([126.533, 33.362]);
  const rank = Object.fromEntries(results.map((r, i) => [r.region_id, i + 1]));
  const pins = results.filter((r) => r.lat).map((r) => ({ r, n: rank[r.region_id], xy: px([+r.lon, +r.lat]) }))
    .sort((a, b) => (a.r.region_id === state.selected) - (b.r.region_id === state.selected) || b.n - a.n);
  const map = $("#map");
  map.setAttribute("viewBox", `0 0 ${W.toFixed(0)} ${H.toFixed(0)}`);
  map.innerHTML = `
    <path class="island" d="${smooth(COAST)}"/><path class="island" d="${smooth(UDO)}"/>
    <ellipse class="contour" cx="${hx}" cy="${hy}" rx="118" ry="60"/><ellipse class="contour" cx="${hx}" cy="${hy}" rx="70" ry="36"/>
    <ellipse class="peak" cx="${hx}" cy="${hy}" rx="28" ry="15"/>
    <text class="map-lbl" x="${hx}" y="${hy - 22}" text-anchor="middle">한라산</text>
    ${pins.map(({ r, n, xy: [x, y] }) => {
      const on = r.region_id === state.selected;
      return `<g class="pin" tabindex="0" role="button" data-id="${r.region_id}" aria-label="${n}위 ${escapeHtml(r.name)}">
        ${on ? `<g class="label" data-cx="${x}"><rect y="${y - 58}" height="30" rx="6"/><text y="${y - 38}">${escapeHtml(r.name)}</text></g>` : ""}
        <circle cx="${x}" cy="${y}" r="${on ? 16 : 12}" fill="${on ? "var(--cta)" : n === 1 ? "var(--gyul)" : n <= 3 ? "var(--brand)" : "#8a8f95"}"/>
        <text class="n" x="${x}" y="${y}">${n}</text>
      </g>`;
    }).join("")}`;
  $$(".label", map).forEach((g) => {  // 이름표 폭을 실제 글자 폭에 맞춘다
    const t = $("text", g), rc = $("rect", g), w = t.getBBox().width + 24;
    const x = Math.min(Math.max(+g.dataset.cx - w / 2, 4), W - w - 4);
    rc.setAttribute("x", x); rc.setAttribute("width", w); t.setAttribute("x", x + 12);
  });
  $$(".pin", map).forEach((g) => {
    g.onclick = () => select(g.dataset.id, false);
    g.onkeydown = (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); select(g.dataset.id, false); } };
  });
}

// ③ 선택한 동네 ───────────────────────────────────
function renderDetail(r) {
  if (!r) return;
  const c = r.cost, cond = c.conditions;
  const items = Object.entries(c.breakdown);
  const max = Math.max(...items.map(([, v]) => v), 1);
  const budget = cond.budget_total, diff = budget ? budget - c.total : null;
  const img = (window.REGION_IMAGES || {})[r.region_id];
  const say = dolmongSays(r);
  const seasons = cond.start_date ? seasonEvents(+cond.start_date.slice(5, 7), cond.days) : [];
  const checks = [...r.warnings.map((w) => ["warn", "!", w]), ...r.badges.map((b) => ["good", "✓", b])];
  // 백엔드가 임계값을 넘긴 지수만 보낸다 → config 순서대로 그것만 그린다
  const ev = r.evidence || { living: {}, cost: {} };
  let evN = 0;
  const q = (box) => { const id = `ev-${++evN}`; return [`<button type="button" class="evq" data-ev="${id}" aria-expanded="false" aria-label="산정 근거 보기">?</button>`,
    box ? `<div class="ev-box" id="${id}" hidden>${box}</div>` : ""]; };
  const evHTML = (e) => e ? `<p>${escapeHtml(e.how)}</p><p class="src">데이터: ${escapeHtml(e.data)}</p>` : "";
  const shownIdx = CFG.indices.filter((ix) => r.indices?.[ix.key]).map((ix) => [ix, r.indices[ix.key]]);

  $("#detail-in").innerHTML = `
    <div class="d-top">
      <figure class="d-photo">
        ${img ? `<img src="${img.src}" alt="${escapeHtml(img.place)}" onerror="this.style.visibility='hidden'" />
          <figcaption>${escapeHtml(img.place)} 사진: ${escapeHtml(img.artist || "작자 미상")}, <a href="${img.page}" target="_blank" rel="noopener">${escapeHtml(img.license)}</a></figcaption>` : `<img alt="" />`}
      </figure>
      <div>
        <p class="d-zone">${escapeHtml(r.zone)} / ${escapeHtml(traitName(r))}</p>
        <h2 class="d-name">${escapeHtml(r.name)}</h2>
        <p class="d-score">조건에 맞는 정도 <b>${r.score}점</b> / 100점</p>
        <div class="d-price">
          <p class="lbl">${period(cond.days)}, ${cond.people}명, ${c.tier} 기준 예상 비용</p>
          <p><span class="amt">${c.total.toLocaleString()}<small>만 원</small></span>${diff === null ? "" : diff >= 0
            ? `<span class="budget ok">예산보다 ${diff.toLocaleString()}만 원 적어요</span>`
            : `<span class="budget over">예산보다 ${(-diff).toLocaleString()}만 원 많아요</span>`}</p>
          <p class="range">실제로는 ${won(c.range[0])}~${won(c.range[1])} 사이${cond.days > 31 ? `, 한 달에 ${won(c.per_month)} 꼴` : ""}</p>
        </div>
        <table class="bd"><tbody>
          ${items.map(([k, v]) => { const [btn, box] = q(evHTML(ev.cost[k]));
            return `<tr><th>${escapeHtml(k)} ${btn}</th><td><div class="bar"><i style="width:${(v / max) * 100}%"></i></div></td><td class="v">${won(v)}</td></tr>${box ? `<tr class="ev-row"><td colspan="3">${box}</td></tr>` : ""}`; }).join("")}
        </tbody></table>
        ${c.alternatives?.length ? `<p class="alt">${escapeHtml(c.alternatives[0].tier)}로 구하면 숙소비가 ${won(c.alternatives[0].lodging)}이에요.</p>` : ""}
        <div class="say"><img src="${say.pose}" alt="" /><div><b class="who">돌몽이 한마디</b>${say.lines.map((t) => `<p>${t}</p>`).join("")}</div></div>
      </div>
    </div>
    <div class="d-cols">
      <div>
        <h3>이 동네, 살아보면?</h3>
        <ul class="kv">${Object.entries(r.living_scores || {}).map(([k, v]) => `
          ${(() => { const [btn, box] = q(evHTML(ev.living[k]));
            return `<li><span>${escapeHtml(lab(k))} ${btn}</span><span class="s" aria-hidden="true">${[1, 2, 3, 4, 5].map((i) => `<i class="${i <= five(v) ? "on" : ""}"></i>`).join("")}</span><span class="n">${five(v)}/5</span>${ev.living[k]?.reason ? `<small class="why">${escapeHtml(ev.living[k].reason)}</small>` : ""}${box}</li>`; })()}`).join("")}
        </ul>
        <p class="note">제주 14개 동네끼리 순위로 비교한 점수예요.</p>
      </div>
      <div>
        <h3>유의 사항</h3>
        <ul class="checks">${checks.length ? checks.map(([cl, m, t]) => `<li class="${cl}"><span class="m">${m}</span>${escapeHtml(t)}</li>`).join("") : `<li>따로 챙길 점이 없어요.</li>`}</ul>
        ${seasons.length ? `<h3 class="sub-h">머무는 동안 제주는</h3>
        <ul class="checks">${seasons.map((e) => `<li class="${e.warn ? "warn" : "good"}"><span class="m">${e.warn ? "!" : "·"}</span>${escapeHtml(e.text)}</li>`).join("")}</ul>` : ""}
      </div>
      ${shownIdx.length ? `<div>
        <h3>돌몽's Tip</h3>
        <ul class="idx">${shownIdx.map(([ix, v]) =>
          { const [btn, box] = q(v.source ? `<p class="src">데이터: ${escapeHtml(v.source)}</p>` : "");
            return `<li class="${escapeHtml(v.tone || "")}">${escapeHtml(ix.name)} ${btn}<b>${escapeHtml(v.value)}</b>${v.text ? `<small>${escapeHtml(v.text)}</small>` : ""}${box}</li>`; }).join("")}</ul>
      </div>` : ""}
    </div>
    <section class="rehearsal" id="rehearsal" aria-label="돌몽이의 한 달 살기 리허설">
      <div class="rh-head"><img src="${CFG.pose.search}" alt="" width="56" height="56" />
        <div><h3>돌몽이랑 하루 살아보기</h3><p>${escapeHtml(r.name)}에 살면 하루가 이렇게 흘러가요. 장소는 전부 공공데이터에 있는 실제 이름이에요.</p></div>
        <div class="rh-tabs" role="tablist"><button type="button" role="tab" aria-selected="true" data-rh="weekday">평일</button><button type="button" role="tab" aria-selected="false" data-rh="weekend">주말</button></div></div>
      <ol class="rh-list" id="rh-list"><li>${loaderHTML("small")}</li></ol>
      <p class="rh-notes" id="rh-notes"></p>
    </section>`;
  consultSetRegion(r);
  startRehearsal(r);
}

// ⑤ 한 달 살기 리허설 ─────────────────────────────
async function startRehearsal(r) {
  const id = r.region_id;
  try {
    const res = await api("/api/rehearsal", { region_id: id, conditions: { ...r.cost.conditions, priorities: state.priorities || [] } });
    if (state.selected !== id) return;
    state.rehearsal = res;
    drawRehearsal("weekday");
  } catch { $("#rh-list").innerHTML = `<li class="empty">리허설을 불러오지 못했어요.</li>`; }
}

function drawRehearsal(which) {
  const res = state.rehearsal; if (!res) return;
  $$("[data-rh]").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.rh === which)));
  $("#rh-list").innerHTML = res[which].map((x) => `<li><time>${x.time}</time><div><b>${escapeHtml(x.title)}</b>
    ${x.url ? `<a class="rh-place" href="${escapeHtml(x.url)}" target="_blank" rel="noopener" title="구글 지도에서 보기">${escapeHtml(x.place)} ↗</a>` : `<span class="rh-place">${escapeHtml(x.place)}</span>`}<small>${escapeHtml(x.why)}</small></div></li>`).join("");
  $("#rh-notes").textContent = [...res.notes, `${res.month}월 기준`].join(" · ");
}

// 받침에 따라 로/으로 (ㄹ 받침은 '로')
function ro(word) {
  const c = word.charCodeAt(word.length - 1) - 0xac00;
  if (c < 0 || c > 11171) return "로";
  const jong = c % 28;
  return jong === 0 || jong === 8 ? "로" : "으로";
}

// 돌몽이 한마디: 결과 값으로만 만든다 (지어내지 않음)
function dolmongSays(r) {
  // 3줄: ① 순위 ② 가장 좋은 점 ③ 가장 아쉬운 점. 전부 결과 값(순위, 생활 점수, 한 줄 근거)에서만 만든다.
  const list = state.data.results;
  const c = r.cost, budget = c.conditions.budget_total;
  const ev = r.evidence?.living || {};
  const why = (k) => (ev[k]?.reason ? ` ${escapeHtml(ev[k].reason)}.` : "");
  const rank = list.findIndex((x) => x.region_id === r.region_id) + 1;
  const ls = Object.entries(r.living_scores || {}).sort((a, b) => b[1] - a[1]);
  const lines = [`${escapeHtml(r.name)}${josa(r.name, "은", "는")} 조건에 맞는 동네 ${list.length}곳 중 <b>${rank}위</b>예요.`];
  if (ls.length) {
    const [bk] = ls[0], [wk] = ls.at(-1);
    lines.push(`가장 좋은 점은 ${escapeHtml(lab(bk))}${josa(lab(bk), "이에요", "예요")}.${why(bk)}`);
    lines.push(`가장 아쉬운 점은 ${escapeHtml(lab(wk))}${josa(lab(wk), "이에요", "예요")}.${why(wk)}`);
  }
  return { lines: lines.map((t) => (window.jeju || String)(t)), pose: budget && c.total > budget ? CFG.pose.calc : CFG.pose.done };
}

// 생활 점수 항목의 화면 이름 (백엔드 region.FACTOR_LABELS → /api/estimate 응답 labels)
const lab = (k) => state.data?.labels?.[k] || k;

// 받침에 따라 조사 (은/는, 이/가)
function josa(word, withJong, without) {
  const c = String(word).charCodeAt(String(word).length - 1) - 0xac00;
  return c >= 0 && c <= 11171 && c % 28 ? withJong : without;
}

// ④ 돌몽이 AI Agent 상담 ─────────────────────────
// 웹(1200px 이상): 화면 오른쪽 30%에 고정, 리포트와 나란히. 닫으면 버튼으로 접힌다.
// 모바일: 오른쪽 아래 버튼으로 여는 전체 화면 창.
// 지금 보는 동네·조건을 매번 같이 보내므로(실시간 연결) 사용자가 폼을 바꾸면 Agent 기준도 바로 바뀐다.
// Agent 는 리포트를 직접 바꾸지 않고 '수정 제안 카드'를 띄운다 → 사용자가 [적용하기]를 눌러야 바뀐다.
const consult = { region: null, cond: null, history: [], greeted: false, busy: false, quiet: false };
const DOCK = matchMedia("(min-width: 1200px)");

function initConsult() {
  $("#cs-fab").onclick = () => toggleConsult(true, true);
  $("#cs-close").onclick = () => toggleConsult(false);
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !$("#cs-panel").hidden && !DOCK.matches) toggleConsult(false); });
  $("#cs-panel").addEventListener("click", (e) => {
    const chip = e.target.closest("[data-qr]");
    if (chip) { consultAsk("", chip.dataset.qr, chip.textContent); return; }
    const act = e.target.closest("[data-pr]");
    if (act) decideProposal(act.closest(".cs-propose"), act.dataset.pr === "ok");
  });
  $("#cs-form").onsubmit = (e) => { e.preventDefault(); const t = $("#cs-text").value.trim(); if (t) consultAsk(t); };
  if (DOCK.matches) toggleConsult(true, false);  // 웹은 처음부터 열어 둔다
  DOCK.addEventListener("change", () => {
    if (!DOCK.matches && !$("#cs-panel").hidden) toggleConsult(false);
    else if (DOCK.matches) toggleConsult(true, false);
  });
}

function toggleConsult(open, focus) {
  $("#cs-panel").hidden = !open;
  $("#cs-fab").setAttribute("aria-expanded", String(open));
  document.body.classList.toggle("cs-docked", open && DOCK.matches);
  document.fonts?.ready.then(() => state.data?.results.length && drawMap(state.data.results));  // 본문 폭이 바뀌면 지도 이름표 다시
  if (open) {
    if (!consult.greeted && consult.region) greetConsult();
    if (focus) setTimeout(() => $("#cs-text").focus(), 50);
    scrollMsgs();
  } else $("#cs-fab").focus();
}

function updateWhere() {
  const el = $("#cs-where"), r = consult.region;
  if (!r) return;
  const agent = state.agentMode === "claude";
  el.textContent = agent ? `리포트와 연결됨 · ${r.name}` : `${r.name} 리포트 기준 · 공공데이터로만 답해요`;
  el.classList.toggle("cs-sub-agent", agent);
}

function consultBody(extra) {
  const r = consult.region;
  return { region_id: r.region_id, conditions: { ...r.cost.conditions, priorities: state.priorities || [] }, history: consult.history.slice(-8), ...extra };
}

// 리포트가 다시 그려질 때마다 호출: 다른 동네를 열거나 조건을 바꾸면 상담 기준도 같이 바뀐다 (대화는 이어진다)
function consultSetRegion(r) {
  const before = consult.region?.region_id;
  const cond = JSON.stringify({ ...r.cost.conditions, priorities: state.priorities || [] });
  const condChanged = consult.cond && consult.cond !== cond;
  consult.region = r; consult.cond = cond;
  updateWhere();
  if (consult.greeted && !consult.quiet) {
    if (condChanged) csNote(`조건이 바뀌었어요 (${summary(r.cost.conditions)}). 새 리포트 기준으로 답할게요`);
    else if (before && before !== r.region_id) csNote(`이제 ${r.name} 리포트 기준으로 답해요`);
  }
  if (!$("#cs-panel").hidden && !consult.greeted) greetConsult();
}

async function greetConsult() {
  consult.greeted = true;
  try { csBot(await api("/api/consult", consultBody({}))); } catch (e) { csAdd("bot").textContent = "상담을 불러오지 못했어요."; }
}

async function consultAsk(text, intent, label) {
  if (!consult.region || consult.busy) return;
  consult.busy = true;
  $("#cs-text").value = "";
  csAdd("user").textContent = text || label;
  $$("#cs-msgs .qr").forEach((x) => x.remove());   // 지난 빠른 버튼은 치운다
  const loading = csAdd("bot loading"); loading.innerHTML = loaderHTML("small");
  try {
    const res = await api("/api/consult", consultBody({ message: text || "", intent: intent || null }));
    loading.remove(); csBot(res);
    consult.history.push({ role: "user", content: text || label }, { role: "assistant", content: res.answer });
  } catch (e) {
    loading.classList.remove("loading");
    loading.textContent = `답을 만들지 못했어요. 제주120만덕콜센터(국번 없이 120)로 물어봐 주세요. (${e.message})`;
  } finally { consult.busy = false; }
}

function csBot(res) {
  const el = csAdd("bot");
  el.innerHTML = res.answer.split("\n").map((l) => `<p class="${/^\s+└/.test(l) ? "sub" : ""}">${linkify(mdLite(l.trim()))}</p>`).join("");
  // 주제가 충분히 겹칠 때만 서버가 icon 을 준다 → 말풍선 왼쪽 위에 돌몽이 아이콘
  if (res.icon) { el.classList.add("has-ico"); el.insertAdjacentHTML("afterbegin", `<img class="cs-ico" src="assets/icons/${encodeURIComponent(res.icon)}.webp" alt="" />`); }
  if (res.sources?.length) el.insertAdjacentHTML("beforeend", `<p class="cs-src">참고 데이터: ${res.sources.map(escapeHtml).join(" · ")}</p>`);
  if (res.trace?.length) {
    const who = res.mode === "agent" ? "돌몽이(AI Agent)가 확인한 것" : "돌몽이가 확인한 것";
    el.insertAdjacentHTML("beforeend", `<details class="cs-trace"><summary>${who} ${res.trace.length}단계</summary><ol>${res.trace.map((t) =>
      `<li class="${t.error ? "err" : ""}">${escapeHtml(t.label || TOOL_LABEL[t.tool] || t.tool)}${t.error ? " (다시 시도)" : ""}</li>`).join("")}</ol></details>`);
  }
  if (res.fallback === "rate_limited") csNote("질문이 많아서 잠깐 기본 모드로 답했어요");
  if (res.report_update) renderProposal(res.report_update);
  if (res.quick_replies?.length) {
    $("#cs-msgs").insertAdjacentHTML("beforeend", `<div class="qr">${res.quick_replies.map((q) => `<button type="button" data-qr="${q.id}">${q.icon ? `<img src="assets/icons/${encodeURIComponent(q.icon)}.webp" alt="" />` : ""}${escapeHtml(q.label)}</button>`).join("")}</div>`);
  }
  scrollMsgs();
}

// ── 리포트 수정 제안 카드 ──
// 값 보기 좋게: car true → 렌터카, days 60 → 두 달 ...
function condText(k, v) {
  if (k === "car") return v ? "렌터카" : "버스·도보";
  if (k === "days") return period(v);
  if (k === "people") return `${v}명`;
  if (k === "budget_total") return v ? `${won(v)} 이하` : "상관없음";
  if (k === "start_date") return v ? `${v.slice(0, 4)}년 ${+v.slice(5, 7)}월 출발` : "-";
  if (k === "priorities") return v?.length ? v.map(lab).join(" > ") : "없음";
  if (typeof v === "boolean") return v ? "예" : "아니요";
  return String(v ?? "-");
}

function renderProposal(u) {
  const now = consult.region.cost.conditions;
  const rows = Object.entries(u.conditions || {}).map(([k, v]) =>
    `<li><b>${escapeHtml(COND_LABEL[k] || k)}</b><span><s>${escapeHtml(condText(k, k === "priorities" ? state.priorities : now[k]))}</s> → <strong>${escapeHtml(condText(k, v))}</strong></span></li>`);
  if (u.select_region_id) {
    const nm = state.data?.results.find((r) => r.region_id === u.select_region_id)?.name || u.select_region_id;
    rows.push(`<li><b>열어 볼 동네</b><span><strong>${escapeHtml(nm)}</strong></span></li>`);
  }
  const card = document.createElement("div");
  card.className = "cs-propose";
  card._u = u;
  card.innerHTML = `<h4>리포트 수정 제안</h4>${u.reason ? `<p class="why">${escapeHtml(u.reason)}</p>` : ""}
    <ul>${rows.join("")}</ul>
    <div class="acts"><button type="button" class="ok" data-pr="ok">적용하기</button><button type="button" class="no" data-pr="no">그대로 둘게요</button></div>`;
  $("#cs-msgs").appendChild(card);
}

function decideProposal(card, ok) {
  if (!card || card.classList.contains("done")) return;
  card.classList.add("done", ok ? "applied" : "dismissed");
  card.insertAdjacentHTML("beforeend", `<p class="pr-done">${ok ? "리포트에 적용했어요" : "그대로 둘게요"}</p>`);
  consult.history.push({ role: "user", content: ok ? `(리포트 수정 제안을 적용함: ${card._u.reason || ""})` : "(리포트 수정 제안은 적용하지 않음)" });
  if (ok) applyReportUpdate(card._u);
}

// 적용: 조건 입력 폼에 그대로 넣고 다시 계산 (사용자가 폼에서 다시 바꿀 수 있다)
function applyReportUpdate(u) {
  const c = u.conditions || {};
  if (c.start_date) {
    const v = c.start_date.slice(0, 7), sel = $("#f-month");
    if (![...sel.options].some((o) => o.value === v)) sel.add(new Option(`${v.slice(0, 4)}년 ${+v.slice(5)}월`, v));
    sel.value = v;
  }
  if (c.days) {
    const sel = $("#f-days");
    if (![...sel.options].some((o) => +o.value === c.days)) sel.add(new Option(period(c.days), String(c.days)));
    sel.value = String(c.days);
  }
  if (c.people) setPeople(c.people);
  if ("car" in c) $("#f-car").value = String(!!c.car);
  if ("budget_total" in c) {
    const sel = $("#f-budget"), v = c.budget_total ? String(c.budget_total) : "";
    if (v && ![...sel.options].some((o) => o.value === v)) sel.add(new Option(`${(+v).toLocaleString()}만 원 이하`, v));
    sel.value = v;
  }
  $$("#f-opts input").forEach((x) => { if (x.dataset.k in c) x.checked = !!c[x.dataset.k]; });
  if (c.priorities) { state.priorities = c.priorities.slice(0, 3); drawPrio(); }
  if (u.select_region_id) state.selected = u.select_region_id;
  consult.quiet = true;  // 이번 다시 그리기는 '조건이 바뀌었어요' 안내를 띄우지 않는다
  runEstimate(false, true).finally(() => {
    consult.quiet = false;
    const box = $("#result");
    box.scrollIntoView({ behavior: "smooth", block: "start" });
    box.classList.remove("flash"); void box.offsetWidth; box.classList.add("flash");
  });
}

function csNote(text, cls = "") {
  const el = csAdd("note " + cls);
  el.textContent = text;
}

function scrollMsgs() { const box = $("#cs-msgs"); requestAnimationFrame(() => { box.scrollTop = box.scrollHeight; }); }

// [이름](https://...) → 새 탭 링크 (상담 답변의 구글 지도 링크)
function linkify(html) {
  return html.replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, (m, t, u) => `<a href="${u}" target="_blank" rel="noopener">${t} ↗</a>`);
}

function csAdd(cls) {
  const el = document.createElement("div");
  el.className = "msg " + cls;
  $("#cs-msgs").appendChild(el);
  scrollMsgs();
  return el;
}

// 동네 성격: 생활 점수 상위 2개(0.6 이상)로 이름을 짓는다. 값에서만 만든다.
function traitName(r) {
  const top = Object.entries(r.living_scores || {}).filter(([k, v]) => v >= 0.6 && CFG.traits[k])
    .sort((x, y) => y[1] - x[1]).slice(0, 2).map(([k]) => CFG.traits[k]);
  if (!top.length) return "무난한 동네";
  return top.length === 1 ? `${top[0][0]} 동네` : `${top[0][1]} ${top[1][0]} 동네`;
}

// 머무는 기간(시작 달부터 days 일)에 걸리는 계절 이벤트
function seasonEvents(startMonth, days) {
  const n = Math.min(12, Math.max(1, Math.ceil(days / 30)));
  const months = new Set(Array.from({ length: n }, (_, k) => ((startMonth - 1 + k) % 12) + 1));
  const list = (CFG.seasons || []).filter((e) => e.months.some((m) => months.has(m)));
  return days >= 365 ? list.filter((e) => !e.warn).slice(0, 6) : list;
}

// 로딩: 돌몽이 세 장면(뛰기 → 넘어지기 → 줍기)을 돌린다. 화면에 있는 .loader 를 한 타이머로 같이 넘긴다.
const userName = () => { try { return (localStorage.getItem("dolmong.name") || "").trim(); } catch { return ""; } };
function loaderText(f) {
  const n = userName();
  const t = n ? f.text.replace("{name}", n) : (f.nameless || f.text.replace("{name}님에게 ", ""));
  return (window.jeju || String)(t);
}
function loaderHTML(size = "") {
  const f = CFG.loader.frames[0];
  return `<div class="loader ${size}" role="status" aria-live="polite" data-f="0">
    <div class="loader-stage">${CFG.loader.frames.map((x, k) => `<img src="${x.img}" alt="" class="${k ? "" : "on"}" />`).join("")}</div>
    <p>${escapeHtml(loaderText(f))}</p></div>`;
}
setInterval(() => {
  $$(".loader").forEach((el) => {
    const k = (+el.dataset.f + 1) % CFG.loader.frames.length;
    el.dataset.f = k;
    $$(".loader-stage img", el).forEach((im, j) => im.classList.toggle("on", j === k));
    $("p", el).textContent = loaderText(CFG.loader.frames[k]);
  });
}, CFG.loader.frameMs);
// 화면 넓이의 약 1/24 (1/16~1/32 사이)를 차지하도록 크기를 정한다
function sizeLoader() {
  const px = Math.round(Math.min(280, Math.max(110, Math.sqrt((innerWidth * innerHeight) / 24))));
  document.documentElement.style.setProperty("--loader", `${px}px`);
}
sizeLoader();
addEventListener("resize", sizeLoader);
const wait = (ms) => new Promise((r) => setTimeout(r, ms));

// ── 유틸 ──
function summary(c) {
  const parts = [];
  if (c.start_date) parts.push(`${+c.start_date.slice(5, 7)}월 출발`);
  parts.push(period(c.days), `${c.people}명`, c.car ? "렌터카" : "버스·도보");
  if (c.budget_total) parts.push(`예산 ${c.budget_total.toLocaleString()}만 원`);
  parts.push(...CFG.options.filter((o) => c[o.key]).map((o) => o.label));
  return parts.join(", ");
}
const period = (d) => DAYS_LABEL[d] || `${d}일`;
const five = (v) => Math.max(1, Math.round(v * 5));
const won = (v) => `${Number(v).toLocaleString()}만 원`;
const ym = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
function escapeHtml(s) { return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }
function mdLite(s) { return escapeHtml(s).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/(^|\s)_(.+?)_(\s|$)/g, "$1<i>$2</i>$3"); }

init();
