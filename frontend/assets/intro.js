// 사이트 인트로 (약 3초): 제주 풍경 실사 사진 16장 중 하나를 무작위로 띄우고 가운데 ᄆᆞ슬 로고
// 사진: 모두 위키미디어 공용의 자유 이용 사진 — CC0 / 퍼블릭 도메인 / 공공누리 제1유형(출처 표기 조건)
//       출처는 인트로 왼쪽 아래에 표시하고 원본 페이지로 링크
// - 고르는 법: Math.random() 으로 하나 → 바로 직전에 본 사진이면 한 번 더 뽑음 (localStorage)
// - 세션당 한 번만 재생 · OS '동작 줄이기' 설정이면 생략 · 아무 곳이나 누르거나 '건너뛰기'로 닫힘
// - 다시 보기: 주소 뒤에 ?intro=1   · 특정 사진 고정: ?intro=1&photo=3 (0부터)
// - 사진 추가: 아래 PHOTOS 에 [경로, 장소, 작가, 라이선스] 한 줄. 경로는 위키미디어 파일 주소의 'a/ab/파일명'
(() => {
  const PHOTOS = [
    ["5/51/Udo,_Jeju_Province,_South_Korea_04.jpg", "우도 밭담", "제주영상문화산업진흥원", "공공누리 제1유형"],
    ["9/97/Udo,_Jeju_Province,_South_Korea_05.jpg", "우도 밭담과 바다", "제주영상문화산업진흥원", "공공누리 제1유형"],
    ["8/89/Udo,_Jeju_Province,_South_Korea_03.jpg", "우도 마을", "제주영상문화산업진흥원", "공공누리 제1유형"],
    ["0/04/Udo,_Jeju_Province,_South_Korea_02.jpg", "우도 해안 마을", "제주영상문화산업진흥원", "공공누리 제1유형"],
    ["b/bf/Udo,_Jeju_Province,_South_Korea_10.jpg", "우도 해안", "제주영상문화산업진흥원", "공공누리 제1유형"],
    ["6/61/Hallasan_Sunrise_09.jpg", "한라산 해돋이와 운해", "제주영상문화산업진흥원", "공공누리 제1유형"],
    ["1/1a/Hallasan_2.jpg", "한라산 백록담", "", "퍼블릭 도메인"],
    ["c/c9/Geomunoreum.jpg", "거문오름", "강동희", "퍼블릭 도메인"],
    ["8/80/Bijarim_Forest,_Jeju_-_Bijarim2495.jpg", "비자림", "lumoplank", "CC0"],
    ["1/1d/O'Sulloc_Tea_Fields,_Jeju_-_Osulloc2567.jpg", "서광 차밭", "lumoplank", "CC0"],
    ["3/3d/Beaches_of_Jeju_-_JejuBeaches2458.jpg", "제주 바다와 비양도", "lumoplank", "CC0"],
    ["c/ca/Sanbangsan_Mountain_01.jpg", "산방산과 마을", "Bernard Gagnon", "CC0"],
    ["c/cb/Dol_Hareubangs_at_Daepo_Jusangjeolli_Cliff_02.jpg", "돌하르방", "Bernard Gagnon", "CC0"],
    ["5/57/Dol_Hareubangs_in_Jeju_Stone_Park_01.jpg", "돌문화공원 돌하르방", "Bernard Gagnon", "CC0"],
    ["f/f8/Seongsan,_Jeju_Island.jpg", "성산 마을", "Bernard Gagnon", "CC0"],
    ["0/0e/Hamdeok_Beach.jpg", "함덕 해변", "Hong Da Hyeon", "CC0"],
  ];
  const file = (path) => encodeURIComponent(path.split("/").pop());
  const url = (path, w) => `https://upload.wikimedia.org/wikipedia/commons/thumb/${path.split("/").slice(0, 2).join("/")}/${file(path)}/${w}px-${file(path)}`;
  const page = (path) => `https://commons.wikimedia.org/wiki/File:${file(path)}`;

  const seen = (() => { try { return sessionStorage.getItem("introSeen"); } catch { return null; } })();
  const reduce = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
  const forced = /[?&]intro=1/.test(location.search);
  if ((seen || reduce) && !forced) return;

  // 무작위로 한 장 (직전 사진은 피함)
  const fixed = (location.search.match(/[?&]photo=(\d+)/) || [])[1];
  const last = (() => { try { const v = localStorage.getItem("introLast"); return v === null ? -1 : +v; } catch { return -1; } })();
  let idx = Math.floor(Math.random() * PHOTOS.length);
  if (idx === last && PHOTOS.length > 1) idx = (idx + 1 + Math.floor(Math.random() * (PHOTOS.length - 1))) % PHOTOS.length;
  if (fixed !== undefined && PHOTOS[+fixed]) idx = +fixed;
  try { localStorage.setItem("introLast", String(idx)); } catch {}
  const [path, place, artist, license] = PHOTOS[idx];
  const width = innerWidth * (devicePixelRatio || 1) > 1400 ? 1920 : 1280;
  const PHOTO = { src: url(path, width), fallback: url(path, 960), page: page(path),
    credit: ["사진", place, artist, license].filter(Boolean).join(" · ") };

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
  img.addEventListener("error", () => {   // 원본이 작아 큰 썸네일이 없으면 960px 로 한 번 더 시도
    if (img.src !== PHOTO.fallback) { img.src = PHOTO.fallback; return; }
    img.remove(); start();
  });
  if (img.complete && img.naturalWidth) start();
  setTimeout(start, 1200);
})();
