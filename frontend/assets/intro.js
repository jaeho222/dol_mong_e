// 사이트 인트로 (약 3초): 한라산이 보이는 시골 초가 마당 → ᄆᆞ슬 로고
// 장면: 한라산(완만한 방패 모양 + 백록담 화구벽 + 계곡을 따라 내려온 눈), 오름, 돌담 두른 귤밭,
//       정낭(나무 대문), 돌하르방, 장독대, 초가와 마루
// - 세션당 한 번만 재생 · OS '동작 줄이기' 설정이면 생략 · 아무 곳이나 누르거나 '건너뛰기'로 닫힘
// - 다시 보기: 주소 뒤에 ?intro=1
// 색: 집·돌담·로고는 서비스 색(현무암·이끼·감귤), 하늘·산·풀·나무는 본래 색
(() => {
  const seen = (() => { try { return sessionStorage.getItem("introSeen"); } catch { return null; } })();
  const reduce = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
  const forced = /[?&]intro=1/.test(location.search);
  if ((seen || reduce) && !forced) return;

  // 귤나무 한 그루 (잎 덩어리 + 귤 몇 알)
  const tree = (x, y, s = 1) => `
    <g transform="translate(${x} ${y}) scale(${s})">
      <rect x="-3" y="-6" width="6" height="18" fill="#5a4330"/>
      <ellipse cx="0" cy="-20" rx="24" ry="20" fill="#3f6b2f"/>
      <ellipse cx="-8" cy="-26" rx="12" ry="10" fill="#4f7d3a"/>
      <g fill="#f08a24"><circle cx="-12" cy="-16" r="3.4"/><circle cx="6" cy="-28" r="3.2"/><circle cx="12" cy="-12" r="3.4"/><circle cx="-2" cy="-8" r="3"/><circle cx="16" cy="-24" r="2.8"/></g>
    </g>`;
  // 돌담 한 줄 (현무암 돌을 엇갈려 쌓음)
  const wall = (x0, x1, y, h = 14) => {
    let s = "", x = x0, i = 0;
    while (x < x1) { const w = 16 + ((i * 7) % 9); s += `<ellipse cx="${x + w / 2}" cy="${y + (i % 2 ? -2 : 1)}" rx="${w / 2}" ry="${h / 2}" fill="${i % 3 ? "#2f3335" : "#3b4042"}"/>`; x += w - 2; i++; }
    return s;
  };

  const root = document.createElement("div");
  root.id = "intro";
  root.innerHTML = `
  <svg class="scene" viewBox="0 0 1200 800" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
    <defs>
      <linearGradient id="in-sky" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#9fc4de"/><stop offset=".6" stop-color="#dfe9ee"/><stop offset="1" stop-color="#f3ead8"/>
      </linearGradient>
      <linearGradient id="in-mt" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#6d8090"/><stop offset="1" stop-color="#8ea2a6"/>
      </linearGradient>
      <linearGradient id="in-slope" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#6f8d6c"/><stop offset="1" stop-color="#7f9c6a"/>
      </linearGradient>
      <linearGradient id="in-field" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#93ad62"/><stop offset="1" stop-color="#76964a"/>
      </linearGradient>
    </defs>

    <rect x="-300" y="-400" width="1800" height="1000" fill="#9fc4de"/>
    <rect width="1200" height="800" fill="url(#in-sky)"/>
    <g fill="#fff" opacity=".7"><ellipse cx="220" cy="140" rx="90" ry="18"/><ellipse cx="290" cy="128" rx="60" ry="16"/><ellipse cx="980" cy="110" rx="80" ry="14"/></g>

    <!-- 한라산: 북쪽(제주시)에서 본 완만한 방패 모양, 정상부 화구벽은 서쪽이 조금 높음 -->
    <g class="mountain">
      <path d="M-120 500 C 60 470, 230 420, 380 360 C 470 322, 530 292, 568 268 L 584 256 L 600 252 L 616 258 L 632 262 L 650 258 L 668 262 L 684 270
               C 730 296, 800 330, 900 372 C 1020 420, 1150 460, 1320 500 Z" fill="url(#in-mt)"/>
      <path d="M540 286 C 556 274, 570 262, 586 255 C 600 250, 612 254, 624 259 C 636 263, 646 257, 658 259 C 672 262, 690 272, 716 288
               C 708 296, 702 304, 698 318 C 694 306, 688 300, 680 302 C 674 312, 670 322, 666 332 C 660 318, 654 308, 646 308
               C 640 318, 637 330, 634 342 C 629 326, 622 314, 614 312 C 608 320, 604 328, 600 334 C 596 320, 590 308, 582 304
               C 576 312, 572 320, 568 326 C 564 312, 556 300, 540 286 Z" fill="#f2f5f7"/>
      <path d="M514 300 C 526 292, 536 288, 546 284 C 550 296, 548 306, 542 314 C 536 306, 528 302, 514 300 Z M722 292 C 734 296, 744 302, 752 308 C 744 312, 736 312, 730 306 Z" fill="#e6ecef"/>
      <path d="M-120 500 C 120 470, 300 430, 430 420 C 520 414, 600 430, 700 424 C 820 418, 1000 450, 1320 500 Z" fill="url(#in-slope)" opacity=".85"/>
      <path d="M150 492 Q 205 446 262 492 Z M300 488 Q 340 458 382 488 Z M820 486 Q 880 444 942 486 Z M990 494 Q 1030 466 1072 494 Z" fill="#7b9868"/>
    </g>

    <!-- 들판 + 돌담 두른 귤밭 -->
    <rect x="-300" y="490" width="1800" height="900" fill="url(#in-field)"/>
    <g class="orchard">
      ${wall(-40, 560, 520, 10)}
      ${[40, 100, 160, 220, 280, 340, 400, 460].map((x) => tree(x, 560, 0.75)).join("")}
      ${wall(-40, 520, 588, 12)}
      ${[10, 80, 150, 220, 290, 360, 430].map((x) => tree(x + 20, 640, 0.95)).join("")}
    </g>

    <!-- 정낭(나무 세 개를 걸친 대문)과 돌하르방 -->
    <g class="gate">
      <rect x="474" y="626" width="20" height="96" rx="5" fill="#33383a"/><rect x="566" y="626" width="20" height="96" rx="5" fill="#33383a"/>
      <g fill="#8a6440"><rect x="470" y="640" width="120" height="7" rx="3"/><rect x="470" y="664" width="120" height="7" rx="3" transform="rotate(-6 530 667)"/><rect x="470" y="688" width="120" height="7" rx="3"/></g>
      <g transform="translate(436 724)" fill="#3a3f41">
        <path d="M-17 -88 C -17 -104, 17 -104, 17 -88 Z"/><rect x="-21" y="-90" width="42" height="6" rx="3"/>
        <path d="M-15 -84 C -19 -54, -17 -22, -14 0 L 14 0 C 17 -22, 19 -54, 15 -84 Z"/>
        <g fill="#5d6466"><circle cx="-7" cy="-72" r="4.5"/><circle cx="7" cy="-72" r="4.5"/><rect x="-3.5" y="-68" width="7" height="14" rx="3.5"/>
          <rect x="-15" y="-38" width="17" height="5" rx="2.5"/><rect x="-1" y="-30" width="16" height="5" rx="2.5"/></g>
      </g>
    </g>

    <!-- 초가와 마루 -->
    <g class="house">
      <ellipse cx="900" cy="742" rx="330" ry="20" fill="#5f7d3f" opacity=".5"/>
      <rect x="660" y="540" width="470" height="138" fill="#e9dfc9"/>
      <rect x="700" y="560" width="86" height="102" fill="#b98d5c"/><path d="M743 560 V662" stroke="#8a6440" stroke-width="3"/>
      <rect x="840" y="572" width="116" height="66" fill="#d8c7a2"/><path d="M840 605 H956 M898 572 V638" stroke="#b39a6f" stroke-width="3"/>
      <rect x="1000" y="560" width="86" height="102" fill="#b98d5c"/>
      <rect x="660" y="660" width="470" height="18" fill="#2f3335"/>
      <path d="M622 556 C 660 462, 780 424, 895 422 C 1010 424, 1130 462, 1168 556 Z" fill="#cdb07a"/>
      <path d="M622 556 C 660 462, 780 424, 895 422 C 1010 424, 1130 462, 1168 556" fill="none" stroke="#a88a52" stroke-width="5"/>
      <g stroke="#a88a52" stroke-width="2.5" fill="none" opacity=".9">
        <path d="M650 516 Q 895 456 1140 516"/><path d="M684 484 Q 895 432 1106 484"/>
        <path d="M740 446 L 708 556 M818 428 L 806 556 M895 422 V556 M972 428 L 984 556 M1050 446 L 1082 556"/>
      </g>
      <rect x="630" y="672" width="530" height="20" rx="2" fill="#b07a45"/>
      <path d="M630 682 H1160" stroke="#8e5f33" stroke-width="2"/>
      <rect x="630" y="692" width="530" height="16" fill="#7a5230"/>
      <rect x="648" y="708" width="14" height="36" fill="#6b4728"/><rect x="1128" y="708" width="14" height="36" fill="#6b4728"/>
      <rect x="660" y="708" width="470" height="30" fill="#4c3420" opacity=".55"/>
      <path d="M930 672 q 0 -22 30 -22 q 30 0 30 22 Z" fill="#a8844f"/>
      <g fill="#f08a24"><circle cx="948" cy="652" r="7"/><circle cx="962" cy="647" r="7"/><circle cx="975" cy="653" r="7"/></g>
      <g transform="translate(1178 742)">
        <path d="M-20 0 C -26 -28, -18 -46, 0 -46 C 18 -46, 26 -28, 20 0 Z" fill="#5a3a24"/><rect x="-14" y="-52" width="28" height="7" rx="3" fill="#4a2f1d"/>
        <path d="M-58 0 C -62 -18, -56 -30, -44 -30 C -32 -30, -26 -18, -30 0 Z" fill="#6a4529"/>
      </g>
    </g>

    <!-- 앞쪽 돌담 -->
    <g class="front-wall">${wall(-60, 640, 768, 22)}${wall(-40, 620, 748, 20)}</g>
  </svg>
  <div class="intro-logo"><img src="assets/logo.svg" alt="ᄆᆞ슬"></div>
  <button class="intro-skip" type="button">건너뛰기</button>`;

  // 세로 화면(휴대폰): 한라산 정상·마루·정낭이 함께 보이도록 범위 조정
  if (innerWidth / innerHeight < 0.9) root.querySelector(".scene").setAttribute("viewBox", "330 -60 720 980");
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
  root.addEventListener("click", close);
  setTimeout(close, 2600);   // 2.6초 뒤 0.4초 동안 사라짐 → 약 3초
})();
