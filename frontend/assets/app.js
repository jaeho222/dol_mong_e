// 돌몽이 프론트엔드 (빌드 도구 없는 바닐라 JS)
// ① 조건 입력 → /api/estimate   ② 추천 동네: 지도 + 순위   ③ 동네 자세히: 비용·돌몽이 한마디·생활 점수·세심 체크·지수
// ④ 대화창 → /api/chat (Agent)
const CFG = window.APP_CONFIG;
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];

// window.STATIC_DEMO 가 있으면(노션 임베드용 정적 데모) 서버 대신 미리 계산된 결과를 쓴다 — scripts/build_static_demo.py
const api = (path, body) => window.STATIC_DEMO ? Promise.resolve(window.STATIC_DEMO.handle(path, body)) :
  fetch(CFG.apiBase + path, body ? {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  } : undefined).then(async (r) => { if (!r.ok) throw new Error(await r.text()); return r.json(); });

const state = { people: 2, opts: {}, data: null, selected: null, dummy: false };
const DAYS_LABEL = { 14: "2주", 30: "한 달", 60: "두 달", 90: "석 달", 180: "반년", 365: "1년" };
const TOOL_LABEL = {
  list_regions: "동네 목록 확인",
  rank_regions: "조건에 맞춰 동네 순위 매기기",
  estimate_total_cost: "체류 비용 계산",
  get_region_detail: "동네 자세히 보기",
};

// ① 조건 입력 ─────────────────────────────────────
function init() {
  $("#support-link").href = CFG.support.url;

  const sel = $("#f-month");
  const d = new Date(); d.setDate(1);
  for (let i = 1; i <= 12; i++) {
    const m = new Date(d.getFullYear(), d.getMonth() + i, 1);
    sel.add(new Option(`${m.getFullYear()}년 ${m.getMonth() + 1}월`, ym(m)));
  }

  $$(".seg").forEach((g) => $$("button", g).forEach((b) => {
    b.setAttribute("role", "radio");
    b.setAttribute("aria-checked", String(b.classList.contains("on")));
    b.onclick = () => $$("button", g).forEach((x) => { x.classList.toggle("on", x === b); x.setAttribute("aria-checked", String(x === b)); });
  }));

  const setPeople = (n) => {
    state.people = Math.min(6, Math.max(1, n));
    $("#f-people").textContent = `${state.people}명`;
    $("#p-minus").disabled = state.people === 1;
    $("#p-plus").disabled = state.people === 6;
  };
  $("#p-minus").onclick = () => setPeople(state.people - 1);
  $("#p-plus").onclick = () => setPeople(state.people + 1);
  setPeople(2);

  $("#f-opts").innerHTML = CFG.options.map((o) =>
    `<button type="button" class="chip" data-k="${o.key}" aria-pressed="false"><svg class="ico"><use href="#i-${o.icon}"/></svg>${escapeHtml(o.label)}</button>`).join("");
  $$("#f-opts .chip").forEach((c) => c.onclick = () => {
    const k = c.dataset.k;
    state.opts[k] = !state.opts[k];
    c.setAttribute("aria-pressed", String(state.opts[k]));
  });

  $("#plan").onsubmit = (e) => {
    e.preventDefault();
    runEstimate();
    $("#result").scrollIntoView({ behavior: "smooth" });
  };

  // 대화창
  $$("[data-open-chat]").forEach((b) => b.onclick = (e) => { e.preventDefault(); openChat(); });
  $("#chat-close").onclick = closeChat;
  $("#scrim").onclick = closeChat;
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeChat(); });
  $("#examples").innerHTML = CFG.examples.map((e) => `<button type="button">${escapeHtml(e)}</button>`).join("");
  $$("#examples button").forEach((b) => b.onclick = () => ask(b.textContent));
  $("#ask").onsubmit = (e) => { e.preventDefault(); ask($("#ask-text").value); };

  api("/api/health").then((h) => {
    $("#mode-label").textContent = h.agent_mode === "claude" ? "Claude로 답해요" : "데모 모드로 답해요";
    state.dummy = !!h.dummy_data;
    if (state.dummy) {
      const n = $("#data-note");
      n.hidden = false;
      n.textContent = "지금 보이는 동네 지표는 더미 데이터예요. 제주데이터허브 실제 데이터로 바꾸는 중이에요.";
    }
  }).catch(() => {});

  // 글꼴이 늦게 오면 지도 이름표 폭을 다시 잰다
  document.fonts?.ready.then(() => state.data?.results.length && drawMap(state.data.results));
  runEstimate();
}

function readConditions() {
  const budget = parseInt($("#f-budget").value, 10);
  return {
    start_date: `${$("#f-month").value}-01`,
    days: +$("#f-days .on").dataset.v,
    people: state.people,
    car: $("#f-car .on").dataset.v === "true",
    budget_total: budget > 0 ? budget : null,
    ...Object.fromEntries(CFG.options.map((o) => [o.key, !!state.opts[o.key]])),
  };
}

async function runEstimate() {
  $("#rank").innerHTML = `<li class="waiting"><img src="${CFG.pose.search}" alt="" />동네를 살펴보고 있어요</li>`;
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
    $("#rank").innerHTML = `<li class="empty">예산 안에 드는 동네가 없어요. 예산을 늘리거나 기간을 줄여 보세요.${near ? `<br/>가장 가까운 곳: ${escapeHtml(near)}` : ""}</li>`;
    drawMap([]);
    $("#detail").innerHTML = "";
    return;
  }
  $("#rank").innerHTML = data.results.map((r, i) => `
    <li><button type="button" data-id="${r.region_id}">
      <span class="no">${i + 1}</span>
      <span><span class="nm">${escapeHtml(r.name)}</span><br /><span class="zn">${escapeHtml(r.zone)} · 맞춤 ${r.score}점</span></span>
      <span class="cost"><b>${won(r.cost.total)}</b><span>${DAYS_LABEL[r.cost.conditions.days] || r.cost.conditions.days + "일"} 예상</span></span>
    </button></li>`).join("");
  const SHOW = 6;
  if (data.results.length > SHOW) {
    $$("#rank li").slice(SHOW).forEach((li) => li.hidden = true);
    $("#rank").insertAdjacentHTML("beforeend", `<li><button type="button" class="more">나머지 ${data.results.length - SHOW}곳도 보기</button></li>`);
    $("#rank .more").onclick = (e) => { $$("#rank li[hidden]").forEach((li) => li.hidden = false); e.target.parentElement.remove(); };
  }
  $$("#rank button[data-id]").forEach((b) => b.onclick = () => select(b.dataset.id, true));
  select(data.results[0].region_id, false);
}

function select(id, scroll) {
  state.selected = id;
  $$("#rank button[data-id]").forEach((b) => b.setAttribute("aria-current", String(b.dataset.id === id)));
  drawMap(state.data.results);
  renderDetail(state.data.results.find((r) => r.region_id === id));
  if (scroll) $("#detail").scrollIntoView({ behavior: "smooth" });
}

// 제주 해안선 (경도, 위도) — 대략적인 모양. 위치는 실제 좌표로 찍는다.
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
  const p = pts.map(px), n = p.length;
  let d = `M${p[0][0].toFixed(1)} ${p[0][1].toFixed(1)}`;
  for (let i = 0; i < n; i++) {
    const p0 = p[(i - 1 + n) % n], p1 = p[i], p2 = p[(i + 1) % n], p3 = p[(i + 2) % n];
    const c1 = [p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6];
    const c2 = [p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6];
    d += ` C${c1.map((v) => v.toFixed(1))} ${c2.map((v) => v.toFixed(1))} ${p2.map((v) => v.toFixed(1))}`;
  }
  return d + "Z";
}

function drawMap(results) {
  const W = (126.99 - LON0) * COS * K, H = (LAT0 - 33.17) * K;
  const [hx, hy] = px([126.533, 33.362]);
  const rank = Object.fromEntries(results.map((r, i) => [r.region_id, i + 1]));
  const pins = results.filter((r) => r.lat).map((r) => ({ r, n: rank[r.region_id], xy: px([+r.lon, +r.lat]) }))
    .sort((a, b) => (a.r.region_id === state.selected) - (b.r.region_id === state.selected) || b.n - a.n);
  $("#map").setAttribute("viewBox", `0 0 ${W.toFixed(0)} ${H.toFixed(0)}`);
  $("#map").innerHTML = `
    <path class="island" d="${smooth(COAST)}"/>
    <path class="island" d="${smooth(UDO)}"/>
    <ellipse class="ring" cx="${hx}" cy="${hy}" rx="120" ry="62"/>
    <ellipse class="ring" cx="${hx}" cy="${hy}" rx="72" ry="38"/>
    <ellipse class="halla" cx="${hx}" cy="${hy}" rx="30" ry="16"/>
    <text class="map-label" x="${hx}" y="${hy - 24}" text-anchor="middle">한라산</text>
    ${pins.map(({ r, n, xy: [x, y] }) => {
      const on = r.region_id === state.selected;
      const fill = n <= 3 ? "var(--gyul)" : "var(--basalt)";
      const label = `${r.name} ${r.score}점`;
      const tw = label.length * 13 + 22;
      const tx = Math.min(Math.max(x - tw / 2, 4), W - tw - 4);
      return `<g class="pin" tabindex="0" role="button" data-id="${r.region_id}" aria-label="${n}위 ${escapeHtml(r.name)}">
        ${on ? `<g class="tag"><rect data-cx="${x}" x="${tx}" y="${y - 62}" width="${tw}" height="32" rx="16"/>
          <text x="${tx + 14}" y="${y - 45}">${escapeHtml(r.name)} <tspan class="sc">${r.score}점</tspan></text></g>` : ""}
        <circle cx="${x}" cy="${y}" r="${on ? 17 : 13}" fill="${on ? "var(--moss)" : fill}"/>
        <text x="${x}" y="${y}" style="font-size:${on ? 16 : 13}px">${n}</text>
      </g>`;
    }).join("")}`;
  $$("#map .tag").forEach((t) => {  // 이름표 폭을 실제 글자 폭에 맞춘다
    const tx = $("text", t), rect = $("rect", t);
    const w = tx.getBBox().width + 28;
    const cx = +rect.getAttribute("data-cx");
    const x = Math.min(Math.max(cx - w / 2, 4), W - w - 4);
    rect.setAttribute("x", x); rect.setAttribute("width", w); tx.setAttribute("x", x + 14);
  });
  $$("#map .pin").forEach((g) => {
    g.onclick = () => select(g.dataset.id, false);
    g.onkeydown = (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); select(g.dataset.id, false); } };
  });
}

// ③ 동네 자세히 ───────────────────────────────────
function renderDetail(r) {
  if (!r) return;
  const c = r.cost, cond = c.conditions;
  const items = Object.entries(c.breakdown);
  const max = Math.max(...items.map(([, v]) => v), 1);
  const budget = cond.budget_total;
  const diff = budget ? budget - c.total : null;
  const img = (window.REGION_IMAGES || {})[r.region_id];
  const say = dolmongSays(r);

  $("#detail").innerHTML = `
    <div class="d-head">
      <div><h2>${escapeHtml(r.name)}</h2><span class="zone">${escapeHtml(r.zone)}</span></div>
      <div class="score"><b>${r.score}</b><span>조건에 맞는 정도 (100점 만점)</span></div>
    </div>
    <div class="d-grid">
      <div class="panel">
        <h3>예상 생활비</h3>
        <div class="cost-top">
          <span class="cost-total num">${c.total.toLocaleString()}<small>만 원</small></span>
          ${diff === null ? "" : diff >= 0
            ? `<span class="budget-chip ok">예산보다 ${diff.toLocaleString()}만 원 덜 들어요</span>`
            : `<span class="budget-chip over">예산보다 ${(-diff).toLocaleString()}만 원 더 들어요</span>`}
        </div>
        <p class="cost-sub">${DAYS_LABEL[cond.days] || cond.days + "일"} 동안 ${cond.people}명 기준, ${c.tier}에 묵을 때. 실제로는 ${won(c.range[0])}~${won(c.range[1])} 사이일 거예요.${cond.days > 31 ? ` 한 달에 ${won(c.per_month)} 꼴이에요.` : ""}</p>
        <div class="bd">
          ${items.map(([k, v]) => `<div class="bd-row"><span class="k">${escapeHtml(k)}</span><span class="bd-bar"><i style="width:${(v / max) * 100}%"></i></span><span class="v">${won(v)}</span></div>`).join("")}
        </div>
        ${c.alternatives?.length ? `<p class="cost-sub" style="margin:16px 0 0">${escapeHtml(c.alternatives[0].tier)}로 구하면 숙소비가 ${won(c.alternatives[0].lodging)}이에요.</p>` : ""}
        ${img ? `<figure class="photo"><img src="${img.src}" alt="${escapeHtml(img.place)}" loading="lazy" onerror="this.parentElement.remove()" />
          <figcaption>${escapeHtml(img.place)}, 사진 ${escapeHtml(img.artist || "작자 미상")} (<a href="${img.page}" target="_blank" rel="noopener">${escapeHtml(img.license)}</a>)</figcaption></figure>` : ""}
      </div>
      <div>
        <div class="say">
          <img src="${say.pose}" alt="" />
          <p class="bubble">${say.text}</p>
        </div>
        <div class="panel">
          <h3>살기엔 어떤지</h3>
          <div class="living">
            ${Object.entries(r.living_scores || {}).map(([k, v]) => `
              <div class="living-row"><span>${escapeHtml(k)}</span>
                <span class="stones" role="img" aria-label="${escapeHtml(k)} 5점 중 ${stones(v)}점">${[1, 2, 3, 4, 5].map((i) => `<i class="${i <= stones(v) ? "on" : ""}"></i>`).join("")}</span></div>`).join("")}
          </div>
          <p class="living-note">돌 다섯 개 중 몇 개인지로 보여줘요. 추천 동네끼리 비교한 값이에요.</p>
          ${(r.badges.length || r.warnings.length) ? `
          <h3 style="margin-top:22px">세심 체크</h3>
          <div class="flags">
            ${r.warnings.map((w) => `<div class="flag warn"><svg class="ico"><use href="#i-alert"/></svg>${escapeHtml(w)}</div>`).join("")}
            ${r.badges.map((b) => `<div class="flag good"><svg class="ico"><use href="#i-check"/></svg>${escapeHtml(b)}</div>`).join("")}
          </div>` : ""}
        </div>
      </div>
    </div>
    <div class="panel indices">
      <h3>동네 지수</h3>
      <div class="idx-grid">
        ${CFG.indices.map((ix) => {
          const v = r.indices?.[ix.key];
          return v ? `<div class="idx"><h4>${escapeHtml(ix.name)}</h4><div class="val num">${escapeHtml(v.value)}</div><p>${escapeHtml(v.text || ix.hint)}</p></div>`
            : `<div class="idx pending"><h4>${escapeHtml(ix.name)}</h4><p>${escapeHtml(ix.hint)}</p><div class="val">데이터 연결 전</div></div>`;
        }).join("")}
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
    out.push(d >= 0 ? `예산 안에 들어와요. <b>${d.toLocaleString()}만 원</b> 남아요!` : `예산을 <b>${(-d).toLocaleString()}만 원</b> 넘어요.`);
  }
  const cheap = list.reduce((a, b) => (b.cost.total < a.cost.total ? b : a));
  if (cheap.region_id === r.region_id) out.push("추천 동네 중에 제일 덜 들어요.");
  else out.push(`<b>${escapeHtml(cheap.name)}</b>로 가면 <b>${(c.total - cheap.cost.total).toLocaleString()}만 원</b> 아낄 수 있어요.`);
  const [bk, bv] = Object.entries(c.breakdown).sort((a, b) => b[1] - a[1])[0];
  out.push(`돈은 ${escapeHtml(bk)}에 제일 많이 들어요(${won(bv)}).`);
  const best = Object.entries(r.living_scores || {}).sort((a, b) => b[1] - a[1])[0];
  if (best && best[1] >= 0.7) out.push(`${escapeHtml(best[0])} 점수가 특히 높아요.`);
  return { text: out.join(" "), pose: budget && c.total > budget ? CFG.pose.calc : CFG.pose.done };
}

// ④ 대화창 ─────────────────────────────────────────
function openChat() { document.body.classList.add("chat-open"); $("#chat").setAttribute("aria-hidden", "false"); setTimeout(() => $("#ask-text").focus(), 200); }
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
      el.insertAdjacentHTML("beforeend", `<button type="button" class="see">추천 동네 지도에서 보기</button>`);
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

// ── 유틸 ──
function summary(c) {
  const parts = [];
  if (c.start_date) parts.push(`${+c.start_date.slice(5, 7)}월부터`);
  parts.push(DAYS_LABEL[c.days] || `${c.days}일`, `${c.people}명`, c.car ? "렌터카" : "버스");
  if (c.budget_total) parts.push(`예산 ${c.budget_total.toLocaleString()}만 원`);
  const extra = CFG.options.filter((o) => c[o.key]).map((o) => o.label);
  return parts.join(", ") + (extra.length ? `, ${extra.join("·")}` : "") + " 기준";
}
const stones = (v) => Math.max(1, Math.round(v * 5));
const won = (v) => `${Number(v).toLocaleString()}만 원`;
const ym = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
function escapeHtml(s) { return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }
function mdLite(s) { return escapeHtml(s).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/(^|\s)_(.+?)_(\s|$)/g, "$1<i>$2</i>$3"); }

init();
