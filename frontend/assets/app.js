// 돌몽이 프론트엔드 (빌드 도구 없는 바닐라 JS)
// ① 검색바·돌몽이 타일 → /api/estimate   ② 추천 동네: 목록 + 지도   ③ 선택한 동네: 비용·돌몽이 한마디·생활 점수·세심 체크·지수
// ④ 돌몽이 상담 → /api/chat (Agent)
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

  $("#plan").onsubmit = (e) => { e.preventDefault(); runEstimate(true); };

  $("#quick").innerHTML = CFG.quick.map((q, i) => `
    <button type="button" class="qt" data-i="${i}">
      <span class="qt-img"><img src="${CFG.pose[q.pose]}" alt="" /></span>
      <b>${escapeHtml(q.title)}</b><span>${escapeHtml(q.sub)}</span>
    </button>`).join("");
  $$("#quick .qt").forEach((b) => b.onclick = () => {
    const q = CFG.quick[b.dataset.i];
    if (q.chat) openChat(); else if (q.onboarding) window.startOnboarding?.(); else applyPreset(q.preset);
  });

  // 상담
  $$("[data-open-chat]").forEach((b) => b.onclick = (e) => { e.preventDefault(); openChat(); });
  $("#chat-close").onclick = closeChat;
  $("#scrim").onclick = closeChat;
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeChat(); });
  $("#examples").innerHTML = CFG.examples.map((e) => `<button type="button">${escapeHtml(e)}</button>`).join("");
  $$("#examples button").forEach((b) => b.onclick = () => ask(b.textContent));
  $("#ask").onsubmit = (e) => { e.preventDefault(); ask($("#ask-text").value); };

  api("/api/health").then((h) => {
    $("#mode-label").textContent = h.agent_mode === "claude" ? "Claude가 답해요" : "데모 모드";
    if (h.dummy_data) {
      $("#data-note").hidden = false;
      $("#data-note").textContent = "지금은 동네 지표가 더미 데이터예요. 제주데이터허브 실제 데이터로 바꾸는 중이에요.";
    }
  }).catch(() => {});

  // 글꼴이 늦게 오면 지도 이름표 폭을 다시 잰다
  document.fonts?.ready.then(() => state.data?.results.length && drawMap(state.data.results));
  runEstimate(false);
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
  };
}

async function runEstimate(scroll) {
  $("#rank").innerHTML = `<li class="loading-row"><img src="${CFG.pose.search}" alt="" />동네를 비교하고 있어요</li>`;
  if (scroll) $("#result").scrollIntoView({ behavior: "smooth" });
  try {
    renderResults(await api("/api/estimate", { conditions: readConditions(), top_k: 14 }));
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
      <span class="row-price"><b>${won(r.cost.total)}</b><span>${period(r.cost.conditions.days)} 예상</span></span>
    </button></li>`;
  }).join("");
  if (data.results.length > SHOW) {
    $("#rank").insertAdjacentHTML("beforeend", `<li><button type="button" class="more">나머지 ${data.results.length - SHOW}곳 더 보기</button></li>`);
    $("#rank .more").onclick = (e) => { $$("#rank li[hidden]").forEach((li) => li.hidden = false); e.target.closest("li").remove(); };
  }
  $$("#rank .row").forEach((b) => b.onclick = () => select(b.dataset.id, true));
  select(data.results[0].region_id, false);
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
        <circle cx="${x}" cy="${y}" r="${on ? 16 : 12}" fill="${on ? "var(--ink)" : n <= 3 ? "var(--brand)" : "#6d7277"}"/>
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
          ${items.map(([k, v]) => `<tr><th>${escapeHtml(k)}</th><td><div class="bar"><i style="width:${(v / max) * 100}%"></i></div></td><td class="v">${won(v)}</td></tr>`).join("")}
        </tbody></table>
        ${c.alternatives?.length ? `<p class="alt">${escapeHtml(c.alternatives[0].tier)}로 구하면 숙소비가 ${won(c.alternatives[0].lodging)}이에요.</p>` : ""}
        <div class="say"><img src="${say.pose}" alt="" /><div><b class="who">돌몽이 한마디</b><p>${say.text}</p></div></div>
      </div>
    </div>
    <div class="d-cols">
      <div>
        <h3>살기엔 어떤지</h3>
        <ul class="kv">${Object.entries(r.living_scores || {}).map(([k, v]) => `
          <li><span>${escapeHtml(k)}</span><span class="s" aria-hidden="true">${[1, 2, 3, 4, 5].map((i) => `<i class="${i <= five(v) ? "on" : ""}"></i>`).join("")}</span><span class="n">${five(v)}/5</span></li>`).join("")}
        </ul>
        <p class="note">추천 동네끼리 비교한 점수예요.</p>
      </div>
      <div>
        <h3>세심 체크</h3>
        <ul class="checks">${checks.length ? checks.map(([cl, m, t]) => `<li class="${cl}"><span class="m">${m}</span>${escapeHtml(t)}</li>`).join("") : `<li>따로 챙길 점이 없어요.</li>`}</ul>
        ${seasons.length ? `<h3 class="sub-h">머무는 동안 제주는</h3>
        <ul class="checks">${seasons.map((e) => `<li class="${e.warn ? "warn" : "good"}"><span class="m">${e.warn ? "!" : "·"}</span>${escapeHtml(e.text)}</li>`).join("")}</ul>` : ""}
      </div>
      <div>
        <h3>동네 지수</h3>
        <ul class="idx">${CFG.indices.map((ix) => {
          const v = r.indices?.[ix.key];
          return `<li title="${escapeHtml(ix.hint)}">${escapeHtml(ix.name)}${v ? `<b>${escapeHtml(v.value)}</b>` : `<span>준비 중</span>`}</li>`;
        }).join("")}</ul>
      </div>
    </div>`;
}

// 돌몽이 한마디: 결과 값으로만 만든다 (지어내지 않음)
function dolmongSays(r) {
  const list = state.data.results;
  const c = r.cost, budget = c.conditions.budget_total;
  const out = [];
  if (budget) {
    const d = budget - c.total;
    out.push(d >= 0 ? `예산 안에 들어와요. <b>${d.toLocaleString()}만 원</b>이 남아요.` : `예산을 <b>${(-d).toLocaleString()}만 원</b> 넘어요.`);
  }
  const cheap = list.reduce((a, b) => (b.cost.total < a.cost.total ? b : a));
  if (cheap.region_id === r.region_id) out.push("추천 동네 중에 돈이 제일 덜 들어요.");
  else out.push(`${escapeHtml(cheap.name)}로 가면 <b>${(c.total - cheap.cost.total).toLocaleString()}만 원</b> 아낄 수 있어요.`);
  const [bk, bv] = Object.entries(c.breakdown).sort((a, b) => b[1] - a[1])[0];
  out.push(`비용은 ${escapeHtml(bk)}가 ${won(bv)}으로 제일 커요.`);
  const best = Object.entries(r.living_scores || {}).sort((a, b) => b[1] - a[1])[0];
  if (best && best[1] >= 0.7) out.push(`${escapeHtml(best[0])} 점수가 특히 높아요.`);
  return { text: out.join(" "), pose: budget && c.total > budget ? CFG.pose.calc : CFG.pose.done };
}

// ④ 상담 ─────────────────────────────────────────
function openChat() { document.body.classList.add("chat-open"); $("#chat").setAttribute("aria-hidden", "false"); setTimeout(() => $("#ask-text").focus(), 150); }
function closeChat() { document.body.classList.remove("chat-open"); $("#chat").setAttribute("aria-hidden", "true"); }

async function ask(text) {
  text = (text || "").trim();
  if (!text) return;
  openChat();
  $("#ask-text").value = "";
  addMsg("user").textContent = text;
  const loading = addMsg("bot loading");
  loading.innerHTML = `<img src="${CFG.pose.calc}" alt="" />동네마다 계산하고 있어요`;
  try {
    const res = await api("/api/chat", { message: text });
    loading.remove();
    const el = addMsg("bot");
    el.innerHTML = mdLite(res.answer);
    if (res.trace?.length) {
      el.insertAdjacentHTML("beforeend", `<div class="trace">돌몽이가 한 일<ol>${res.trace.map((t) => `<li>${escapeHtml(TOOL_LABEL[t.tool] || t.tool)}</li>`).join("")}</ol></div>`);
    }
    if (res.ranked?.results) {
      el.insertAdjacentHTML("beforeend", `<button type="button" class="see">추천 동네 목록에서 보기</button>`);
      $(".see", el).onclick = () => { renderResults(res.ranked); closeChat(); $("#result").scrollIntoView({ behavior: "smooth" }); };
    }
  } catch (e) {
    loading.classList.remove("loading");
    loading.textContent = `답을 만들지 못했어요. 잠시 뒤 다시 물어봐 주세요. (${e.message})`;
  }
}

function addMsg(cls) {
  const el = document.createElement("div");
  el.className = "msg " + cls;
  $("#msgs").appendChild(el);
  requestAnimationFrame(() => { $("#msgs").scrollTop = $("#msgs").scrollHeight; });
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
