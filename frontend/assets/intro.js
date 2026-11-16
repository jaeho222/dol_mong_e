// 사이트 인트로: 한라산이 보이는 초가 마루에 한 사람이 걸어와 걸터앉아 한숨 → ᄆᆞ슬 로고
// - 세션당 한 번만 재생 (sessionStorage) · '동작 줄이기' 설정이면 재생하지 않음
// - 아무 곳이나 누르거나 '건너뛰기'로 바로 닫힘
// 장면 색: 집·돌담·로고는 서비스 색(현무암·이끼·감귤), 하늘·산·풀·사람은 본래 색
(() => {
  const seen = (() => { try { return sessionStorage.getItem("introSeen"); } catch { return null; } })();
  const reduce = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
  const forced = /[?&]intro=1/.test(location.search);           // ?intro=1 로 다시 보기
  if ((seen || reduce) && !forced) return;

  const root = document.createElement("div");
  root.id = "intro";
  root.innerHTML = `
  <svg class="scene" viewBox="0 0 1200 800" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
    <defs>
      <linearGradient id="in-sky" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#bcd8ea"/><stop offset=".55" stop-color="#e6eef0"/><stop offset="1" stop-color="#f6ead6"/>
      </linearGradient>
      <linearGradient id="in-field" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#8db163"/><stop offset="1" stop-color="#6f9447"/>
      </linearGradient>
      <radialGradient id="in-sun" cx=".5" cy=".5" r=".5">
        <stop offset="0" stop-color="#fff3c4"/><stop offset=".45" stop-color="#f9d27a"/><stop offset="1" stop-color="#f9d27a" stop-opacity="0"/>
      </radialGradient>
      <pattern id="in-stones" width="44" height="28" patternUnits="userSpaceOnUse">
        <rect width="44" height="28" fill="#2b2f31"/>
        <ellipse cx="11" cy="8" rx="10" ry="6.5" fill="#3a3f41"/><ellipse cx="33" cy="10" rx="10" ry="7.5" fill="#353a3c"/>
        <ellipse cx="22" cy="23" rx="11" ry="5.5" fill="#41474a"/>
      </pattern>
    </defs>

    <rect x="-200" y="-400" width="1600" height="1000" fill="#bcd8ea"/>
    <rect width="1200" height="800" fill="url(#in-sky)"/>
    <circle class="sun" cx="930" cy="170" r="120" fill="url(#in-sun)"/>
    <circle class="sun" cx="930" cy="170" r="42" fill="#fbe08f"/>

    <!-- 한라산: 완만한 방패 모양 + 백록담 + 눈 -->
    <g class="mountain">
      <path d="M-40 520 C 160 450, 360 330, 520 278 C 560 266, 600 262, 640 264 C 690 266, 730 282, 790 304 C 950 370, 1100 440, 1260 500 L1260 560 L-40 560 Z" fill="#7c97a3"/>
      <path d="M520 278 C 560 266, 600 262, 640 264 C 690 266, 730 282, 790 304 C 760 312, 742 300, 716 312 C 694 298, 670 312, 648 302 C 626 314, 600 300, 578 312 C 556 300, 538 312, 520 300 C 506 304, 494 300, 486 296 Z" fill="#f4f6f7"/>
      <path d="M200 540 C 300 470, 360 455, 430 470 C 480 480, 520 510, 560 540 Z" fill="#8aa48a"/>
      <path d="M800 545 C 860 500, 930 490, 990 505 C 1040 518, 1080 535, 1110 548 Z" fill="#8aa48a"/>
    </g>

    <!-- 들판과 풀 -->
    <rect x="-200" y="540" width="1600" height="260" fill="url(#in-field)"/>
    <rect x="-200" y="798" width="1600" height="600" fill="#6f9447"/>
    <g stroke="#5f8a3c" stroke-width="3" stroke-linecap="round" fill="none" opacity=".8">
      <path d="M60 640 q4 -18 0 -30 M70 642 q6 -14 12 -22 M140 700 q-4 -18 2 -30 M150 702 q8 -12 14 -18"/>
      <path d="M320 690 q4 -18 0 -30 M330 692 q6 -14 12 -22 M470 650 q-4 -16 2 -26 M480 652 q8 -12 14 -18"/>
      <path d="M520 760 q4 -18 0 -30 M532 762 q6 -14 12 -22 M260 770 q-4 -18 2 -30"/>
    </g>

    <!-- 돌담 -->
    <path d="M-10 590 Q 150 578 300 588 T 560 584 L 560 618 L -10 622 Z" fill="url(#in-stones)"/>

    <!-- 초가집과 마루 -->
    <g class="house">
      <ellipse cx="880" cy="742" rx="330" ry="22" fill="#5b7a3c" opacity=".45"/>
      <rect x="640" y="520" width="480" height="150" fill="#e9dfc9"/>                       <!-- 흙벽 -->
      <rect x="700" y="545" width="90" height="100" fill="#b98d5c"/>                        <!-- 문 -->
      <path d="M745 545 V645" stroke="#8a6440" stroke-width="3"/>
      <rect x="840" y="555" width="120" height="70" fill="#d8c7a2"/>
      <path d="M840 590 H960 M900 555 V625" stroke="#b39a6f" stroke-width="3"/>
      <!-- 초가 지붕 + 새끼줄 -->
      <path d="M600 540 C 640 440, 760 400, 880 398 C 1000 400, 1120 440, 1160 540 Z" fill="#cdb07a"/>
      <path d="M600 540 C 640 440, 760 400, 880 398 C 1000 400, 1120 440, 1160 540" fill="none" stroke="#a88a52" stroke-width="5"/>
      <g stroke="#a88a52" stroke-width="2.5" fill="none" opacity=".9">
        <path d="M630 500 Q 880 440 1130 500"/><path d="M660 468 Q 880 414 1100 468"/>
        <path d="M720 425 L 690 540 M800 404 L 790 540 M880 398 V 540 M960 404 L 970 540 M1040 425 L 1070 540"/>
      </g>
      <!-- 마루 -->
      <rect x="610" y="650" width="540" height="22" rx="2" fill="#b07a45"/>
      <path d="M610 661 H1150" stroke="#8e5f33" stroke-width="2"/>
      <rect x="610" y="672" width="540" height="18" fill="#7a5230"/>
      <rect x="630" y="690" width="16" height="50" fill="#6b4728"/><rect x="1110" y="690" width="16" height="50" fill="#6b4728"/>
      <rect x="640" y="690" width="480" height="40" fill="#4c3420" opacity=".55"/>
    </g>

    <!-- 걸어오는 사람 -->
    <g class="walker">
      <g class="bob">
        <g class="leg back"><rect x="-9" y="-72" width="14" height="72" rx="7" fill="#3f4c5a"/><rect x="-11" y="-6" width="20" height="8" rx="4" fill="#5a3b25"/></g>
        <g class="leg front"><rect x="-5" y="-72" width="14" height="72" rx="7" fill="#4b5a6b"/><rect x="-6" y="-6" width="20" height="8" rx="4" fill="#6b4a2e"/></g>
        <rect x="-20" y="-142" width="40" height="78" rx="16" fill="#e9e3d2"/>
        <path d="M-20 -128 h40" stroke="#d7cfba" stroke-width="3"/>
        <rect x="-26" y="-134" width="12" height="52" rx="6" fill="#e2dbc8" class="arm"/>
        <circle cx="0" cy="-166" r="22" fill="#f1c9a5"/>
        <path d="M-22 -170 C -20 -194, 20 -196, 22 -170 C 12 -180, -8 -182, -22 -170 Z" fill="#2e2a27"/>
        <rect x="8" y="-148" width="26" height="30" rx="6" fill="#c08a4e" opacity=".9"/>   <!-- 짐 가방 -->
      </g>
    </g>

    <!-- 마루에 걸터앉은 사람 -->
    <g class="sitter">
      <path d="M-6 -2 h44 a8 8 0 0 1 8 8 v40" stroke="#4b5a6b" stroke-width="15" stroke-linecap="round" fill="none"/>
      <rect x="40" y="40" width="20" height="8" rx="4" fill="#6b4a2e"/>
      <rect x="-22" y="-74" width="40" height="76" rx="16" fill="#e9e3d2"/>
      <rect x="-2" y="-62" width="12" height="48" rx="6" fill="#e2dbc8" transform="rotate(-24 4 -62)"/>
      <g class="head"><circle cx="0" cy="-98" r="22" fill="#f1c9a5"/>
        <path d="M-22 -102 C -20 -126, 20 -128, 22 -102 C 12 -112, -8 -114, -22 -102 Z" fill="#2e2a27"/></g>
      <rect x="-70" y="-30" width="30" height="30" rx="6" fill="#c08a4e"/>                 <!-- 내려놓은 가방 -->
    </g>

    <!-- 한숨 -->
    <g class="breath" fill="#ffffff">
      <circle class="p1" cx="0" cy="0" r="10"/><circle class="p2" cx="0" cy="0" r="14"/><circle class="p3" cx="0" cy="0" r="18"/>
      <text class="sigh" x="40" y="-30">휴—</text>
    </g>
  </svg>
  <div class="intro-logo"><img src="assets/logo.svg" alt="ᄆᆞ슬"></div>
  <button class="intro-skip" type="button">건너뛰기</button>`;

  // 세로 화면(휴대폰)에선 사람·마루·한라산 꼭대기가 가운데 오도록 보이는 범위를 옮긴다
  if (innerWidth / innerHeight < 0.9) root.querySelector(".scene").setAttribute("viewBox", "400 -150 760 1100");
  document.body.prepend(root);
  document.documentElement.classList.add("intro-on");

  let closed = false;
  const close = () => {
    if (closed) return;
    closed = true;
    try { sessionStorage.setItem("introSeen", "1"); } catch {}
    root.classList.add("out");
    document.documentElement.classList.remove("intro-on");
    setTimeout(() => root.remove(), 600);
  };
  root.addEventListener("click", close);
  root.querySelector(".scene").addEventListener("animationend", (e) => { if (e.animationName === "in-scene-out") close(); });
  setTimeout(close, 7000);   // 혹시 애니메이션 이벤트를 못 받아도 닫힘
})();
