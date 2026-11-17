// 첫 방문 문답: 돌몽이가 한 문항씩 묻고, 마지막에 '궁합 1위 동네'를 보여준 뒤 본 화면에 조건을 채운다.
// - 처음 온 사람에게 한 번만 뜬다 (localStorage). 주소 뒤에 ?start=1 이면 다시 뜬다.
// - 질문·답·돌몽이 대사는 config.js 의 onboarding 에서 고친다.
// - app.js 의 api, renderResults, setPeople, traitName, seasonEvents 를 쓴다 (app.js 다음에 불러올 것).
(() => {
  const CFG = window.APP_CONFIG;
  const STEPS = CFG.onboarding;
  const KEY = "dolmong.onboarded";
  const QUESTIONS = STEPS.filter((s) => s.type !== "intro" && s.type !== "ready").length;
  let i = 0, picks = {}, root = null;

  const store = { get: () => { try { return localStorage.getItem(KEY); } catch { return "1"; } },
                  set: () => { try { localStorage.setItem(KEY, "1"); } catch {} } };


  function open() {
    i = 0; picks = {};
    root?.remove();
    root = document.createElement("div");
    root.className = "ob";
    root.setAttribute("role", "dialog");
    root.setAttribute("aria-modal", "true");
    root.setAttribute("aria-label", "돌몽이와 동네 고르기");
    root.innerHTML = `
      <div class="ob-top">
        <button type="button" class="ob-back" aria-label="이전 질문">‹</button>
        <div class="ob-bar" aria-hidden="true"><i></i></div>
        <button type="button" class="ob-skip">건너뛰기</button>
      </div>
      <div class="ob-main"></div>
      <div class="ob-foot"><button type="button" class="ob-next"></button></div>`;
    document.body.appendChild(root);
    document.body.classList.add("ob-open");
    root.querySelector(".ob-back").onclick = () => go(i - 1);
    root.querySelector(".ob-skip").onclick = () => close();
    root.addEventListener("keydown", onKey);
    render();
  }

  function close() {
    store.set();
    document.body.classList.remove("ob-open");
    root?.remove(); root = null;
  }

  function go(n) { if (n < 0) return; i = n; render(); }

  // 고른 답들을 조건 하나로 합친다
  function conditions() {
    const next = new Date(); next.setMonth(next.getMonth() + 1, 1);
    const c = { month: ym(next), days: 30, people: 2, car: true, budget: null,
                with_kids: false, with_pet: false, remote_work: false, prefer_quiet: false };
    STEPS.forEach((s, k) => {
      const p = picks[k];
      if (p === undefined) return;
      if (s.type === "month") c.month = p;
      else Object.assign(c, s.options[p].set);
    });
    return c;
  }

  function render() {
    const s = STEPS[i];
    const main = root.querySelector(".ob-main");
    const next = root.querySelector(".ob-next");
    const answered = STEPS.slice(0, i).filter((x) => x.type !== "intro").length;
    root.querySelector(".ob-bar i").style.width = `${Math.min(100, (answered / QUESTIONS) * 100)}%`;
    root.querySelector(".ob-back").style.visibility = i > 0 ? "visible" : "hidden";
    root.querySelector(".ob-top").hidden = false;
    root.querySelector(".ob-foot").hidden = false;
    next.onclick = () => go(i + 1);

    if (s.type === "intro" || s.type === "ready") {
      main.innerHTML = `
        <div class="ob-hero">
          ${pose(s.pose, "big")}
          <h2>${esc(s.say)}</h2>
          ${s.sub ? `<p>${esc(s.sub)}</p>` : ""}
          ${s.type === "ready" ? `<ul class="ob-sum">${summaryChips().map((t) => `<li>${esc(t)}</li>`).join("")}</ul>` : ""}
        </div>`;
      next.textContent = s.cta;
      next.disabled = false;
      if (s.type === "ready") next.onclick = find;
      return;
    }

    const opts = s.type === "month" ? monthOptions() : s.options;
    main.innerHTML = `
      <div class="ob-q">
        ${pose(s.pose)}
        <div class="ob-bubble"><p class="ob-say">${esc(s.say)}</p>${s.sub ? `<p class="ob-sub">${esc(s.sub)}</p>` : ""}</div>
      </div>
      <div class="ob-opts ${s.type === "month" ? "grid" : ""}" role="radiogroup" aria-label="${esc(s.say)}">
        ${opts.map((o, k) => `
          <button type="button" class="ob-opt" role="radio" aria-checked="false" data-k="${k}">
            ${s.type === "month" ? "" : `<span class="key">${k + 1}</span>`}
            <span class="txt"><b>${esc(o.label)}</b>${o.sub ? `<span>${esc(o.sub)}</span>` : ""}</span>
          </button>`).join("")}
      </div>`;
    next.textContent = "계속";
    next.disabled = picks[i] === undefined;

    main.querySelectorAll(".ob-opt").forEach((b) => b.onclick = () => choose(+b.dataset.k, opts));
    if (picks[i] !== undefined) {
      const k = s.type === "month" ? opts.findIndex((o) => o.value === picks[i]) : picks[i];
      if (k >= 0) mark(k, opts, false);
    }
  }

  function choose(k, opts) {
    const s = STEPS[i];
    picks[i] = s.type === "month" ? opts[k].value : k;
    mark(k, opts, true);
    root.querySelector(".ob-next").disabled = false;
  }

  function mark(k, opts, speak) {
    const s = STEPS[i];
    root.querySelectorAll(".ob-opt").forEach((b) => {
      const on = +b.dataset.k === k;
      b.classList.toggle("on", on);
      b.setAttribute("aria-checked", String(on));
    });
    if (!speak) return;
    const o = opts[k];
    let react = o.react || s.react;
    if (s.type === "month") {
      const ev = seasonEvents(+o.value.slice(5, 7), 30).filter((e) => !e.warn)[0];
      react = ev ? `${+o.value.slice(5, 7)}월이면 ${ev.text}이에요!` : "좋아요, 그때 맞춰 볼게요.";
    }
    if (react) {
      root.querySelector(".ob-say").textContent = react;
      const sub = root.querySelector(".ob-sub");
      if (sub) sub.remove();
      bump();
    }
  }

  function monthOptions() {
    const d = new Date(); d.setDate(1);
    return Array.from({ length: 12 }, (_, n) => {
      const m = new Date(d.getFullYear(), d.getMonth() + n + 1, 1);
      return { label: `${m.getMonth() + 1}월`, sub: `${m.getFullYear()}년`, value: ym(m) };
    });
  }

  function summaryChips() {
    const c = conditions();
    const out = [`${+c.month.slice(5, 7)}월 출발`, DAYS_LABEL[c.days] || `${c.days}일`, `${c.people}명`, c.car ? "렌터카" : "버스·도보"];
    out.push(c.budget ? `예산 ${c.budget.toLocaleString()}만 원` : "예산 상관없음");
    if (c.with_kids) out.push("아이와 함께");
    if (c.with_pet) out.push("반려동물");
    if (c.prefer_quiet) out.push("조용한 곳");
    if (c.remote_work) out.push("원격근무");
    return out;
  }

  // 로딩 연출 → 결과 공개
  async function find() {
    const c = conditions();
    root.querySelector(".ob-top").hidden = true;
    root.querySelector(".ob-foot").hidden = true;
    const main = root.querySelector(".ob-main");
    const req = {
      start_date: `${c.month}-01`, days: c.days, people: c.people, car: c.car, budget_total: c.budget,
      with_kids: c.with_kids, with_pet: c.with_pet, remote_work: c.remote_work, prefer_quiet: c.prefer_quiet,
    };
    const job = api("/api/estimate", { conditions: req, top_k: 14 });
    for (const step of CFG.onboardingLoading) {
      main.innerHTML = `<div class="ob-hero ob-wait">${pose(step.pose, "big")}<h2>${esc(step.say)}</h2><div class="dots"><i></i><i></i><i></i></div></div>`;
      await sleep(900);
    }
    let data;
    try { data = await job; } catch (e) {
      main.innerHTML = `<div class="ob-hero">${pose("calc", "big")}<h2>계산하지 못했어요</h2><p>서버가 켜져 있는지 확인해 주세요. 본 화면에서 조건을 직접 넣어도 돼요.</p></div>`;
      root.querySelector(".ob-foot").hidden = false;
      const nb = root.querySelector(".ob-next");
      nb.textContent = "본 화면으로"; nb.disabled = false; nb.onclick = close;
      return;
    }
    reveal(c, data);
  }

  function reveal(c, data) {
    const main = root.querySelector(".ob-main");
    const top = data.results[0];
    if (!top) {
      const near = (data.over_budget || [])[0];
      main.innerHTML = `<div class="ob-hero">${pose("calc", "big")}<h2>예산 안에 드는 동네가 없어요</h2>
        <p>${near ? `제일 가까운 곳은 ${esc(near.name)}, ${near.total.toLocaleString()}만 원이에요. ` : ""}예산을 조금 늘려 볼까요?</p></div>`;
      root.querySelector(".ob-foot").hidden = false;
      const nb = root.querySelector(".ob-next");
      nb.textContent = "예산 다시 고르기"; nb.disabled = false;
      nb.onclick = () => { root.querySelector(".ob-top").hidden = false; go(STEPS.findIndex((s) => s.options?.some((o) => "budget" in o.set))); };
      return;
    }
    const img = (window.REGION_IMAGES || {})[top.region_id];
    const budgetLine = c.budget ? (c.budget >= top.cost.total ? `예산보다 ${(c.budget - top.cost.total).toLocaleString()}만 원 적어요` : `예산보다 ${(top.cost.total - c.budget).toLocaleString()}만 원 많아요`) : "";
    const events = seasonEvents(+c.month.slice(5, 7), c.days);
    main.innerHTML = `
      <div class="ob-reveal">
        <div class="ob-q">
          ${pose("signature")}
          <div class="ob-bubble"><p class="ob-say">찾았어요! 우리랑 제일 잘 맞는 동네는 <b>${esc(top.name)}</b>예요. 귤 하나 드릴게요!</p></div>
        </div>
        <article class="ob-card">
          <div class="ob-photo">${img ? `<img src="${img.src}" alt="${esc(img.place)}" onerror="this.remove()" />` : ""}<span>궁합 1위</span></div>
          <div class="ob-card-body">
            <p class="ob-trait">${esc(traitName(top))}</p>
            <h3>${esc(top.name)} <small>${esc(top.zone)}</small></h3>
            <p class="ob-cost"><b>${top.cost.total.toLocaleString()}만 원</b> ${esc(DAYS_LABEL[c.days] || c.days + "일")} 예상${budgetLine ? `<span>${budgetLine}</span>` : ""}</p>
            ${events.length ? `<p class="ob-ev-h">머무는 동안 제주는</p><ul class="ob-ev">${events.map((e) => `<li class="${e.warn ? "warn" : ""}">${esc(e.text)}</li>`).join("")}</ul>` : ""}
          </div>
        </article>
        ${data.results.length > 1 ? `<ol class="ob-more">${data.results.slice(1, 3).map((r, k) => `<li><i>${k + 2}</i><b>${esc(r.name)}</b><span>${esc(traitName(r))}</span><em>${r.cost.total.toLocaleString()}만 원</em></li>`).join("")}</ol>` : ""}
      </div>`;
    root.querySelector(".ob-foot").hidden = false;
    const nb = root.querySelector(".ob-next");
    nb.textContent = "전체 동네 비교하기"; nb.disabled = false;
    nb.onclick = () => { applyToPage(c, data); close(); };
  }

  // 본 화면 검색바에 같은 조건을 채우고 결과를 그대로 보여준다
  function applyToPage(c, data) {
    const set = (sel, v) => { const el = document.querySelector(sel); if (el) el.value = v; };
    set("#f-month", c.month);
    set("#f-days", String(c.days));
    set("#f-car", String(c.car));
    set("#f-budget", c.budget ? String(c.budget) : "");
    setPeople(c.people);
    document.querySelectorAll("#f-opts input").forEach((x) => x.checked = !!c[x.dataset.k]);
    renderResults(data);
    document.getElementById("result").scrollIntoView();
  }

  function onKey(e) {
    if (e.key === "Escape") { close(); return; }
    const n = parseInt(e.key, 10);
    const btns = root.querySelectorAll(".ob-opt");
    if (n >= 1 && n <= btns.length && STEPS[i].type !== "month") btns[n - 1].click();
    if (e.key === "Enter" && e.target.tagName !== "BUTTON") root.querySelector(".ob-next:not([disabled])")?.click();
  }

  function pose(name, size = "") {
    const img = `<img class="ob-pose ${size}" src="${CFG.pose[name]}" alt="" />`;
    return size === "big" ? `<div class="ob-stage">${img}<div class="ob-wall"></div></div>` : img;  // 큰 돌몽이는 밭담 위에 세운다
  }
  function bump() { const p = root.querySelector(".ob-pose"); p.classList.remove("bump"); void p.offsetWidth; p.classList.add("bump"); }
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const esc = (s) => String(s).replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch]));

  window.startOnboarding = open;
  if (!store.get() || /[?&]start=1/.test(location.search)) open();
})();
