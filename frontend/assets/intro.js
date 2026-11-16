// 사이트 인트로 (약 3초): 제주 시골 풍경 사진 위에 ᄆᆞ슬 로고
// 사진: 우도의 밭담(현무암 돌담으로 나눈 밭)과 마을 — 제주영상문화산업진흥원, 공공누리 제1유형
//       (출처만 밝히면 상업적 이용·변경까지 자유) · 위키미디어 공용에서 불러옴
//       https://commons.wikimedia.org/wiki/File:Udo,_Jeju_Province,_South_Korea_04.jpg
// - 세션당 한 번만 재생 · OS '동작 줄이기' 설정이면 생략 · 아무 곳이나 누르거나 '건너뛰기'로 닫힘
// - 다시 보기: 주소 뒤에 ?intro=1 · 사진을 바꾸려면 아래 PHOTO 만 고치면 된다
(() => {
  const PHOTO = {
    src: "https://upload.wikimedia.org/wikipedia/commons/thumb/5/51/Udo%2C_Jeju_Province%2C_South_Korea_04.jpg/1920px-Udo%2C_Jeju_Province%2C_South_Korea_04.jpg",
    credit: "사진 · 우도 밭담 · 제주영상문화산업진흥원 · 공공누리 제1유형",
    page: "https://commons.wikimedia.org/wiki/File:Udo,_Jeju_Province,_South_Korea_04.jpg",
  };
  const seen = (() => { try { return sessionStorage.getItem("introSeen"); } catch { return null; } })();
  const reduce = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
  const forced = /[?&]intro=1/.test(location.search);
  if ((seen || reduce) && !forced) return;

  const root = document.createElement("div");
  root.id = "intro";
  root.innerHTML = `
    <img class="intro-photo" src="${PHOTO.src}" alt="" decoding="async">
    <div class="intro-shade"></div>
    <div class="intro-logo"><img src="assets/logo.svg" alt="ᄆᆞ슬"></div>
    <a class="intro-credit" href="${PHOTO.page}" target="_blank" rel="noopener">${PHOTO.credit}</a>
    <button class="intro-skip" type="button">건너뛰기</button>`;
  document.body.prepend(root);
  document.documentElement.classList.add("intro-on");

  let closed = false;
  const close = () => {
    if (closed) return;
    closed = true;
    try { sessionStorage.setItem("introSeen", "1"); } catch {}
    root.classList.add("out");
    document.documentElement.classList.remove("intro-on");
    setTimeout(() => root.remove(), 500);
  };
  root.addEventListener("click", (e) => { if (!e.target.closest(".intro-credit")) close(); });

  // 사진이 뜬 순간부터 3초 (사진이 늦거나 실패해도 1.2초 뒤엔 시작)
  const img = root.querySelector(".intro-photo");
  let started = false;
  const start = () => { if (started) return; started = true; root.classList.add("play"); setTimeout(close, 2600); };
  img.addEventListener("load", start);
  img.addEventListener("error", () => { img.remove(); start(); });
  if (img.complete && img.naturalWidth) start();
  setTimeout(start, 1200);
})();
