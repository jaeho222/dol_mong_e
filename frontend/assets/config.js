// 화면 문구·배너는 여기서만 고친다.
window.APP_CONFIG = {
  name: "ᄆᆞ슬",  // 제주어 '마을', 읽기 [모슬]
  apiBase: "",

  // 맨 위 한 줄 띠 배너 (노트폴리오 상단 광고 자리) → 제주愛인 메인
  topBanner: {
    tag: "제주愛인",
    text: "제주 한달살이 지원 확인하기",
    sub: "제주도 이주·체류 지원 안내",
    url: "https://www.jeju.go.kr/move/index.htm",
  },

  // 가로 스크롤 배너 카드
  //  eyebrow: 기능 설명(작은 글씨) / title: 메인 문장(큰 글씨, 줄바꿈 \n) / sub: 근거·조건
  //  art: gyul(귤) | hareubang(돌하르방) | hallasan(한라산) | dotdam(돌담·초가)  — app.js 의 ART
  //  action: { type: "link", url } | { type: "ask", text } (Agent에게 질문) | { type: "preset", conditions }
  //  tone: tangerine | moss | basalt | sea | sand  (style.css 의 .tone-*)
  banners: [
    {
      tone: "tangerine", art: "gyul",
      eyebrow: "제주愛인 · 청춘 정거장",
      title: "읍·면 숙소에 묵으면\n1박에 1만 원",
      sub: "도외 청년 · 14일 이상 체류 · 최대 30만 원",
      action: { type: "link", url: "https://www.jeju.go.kr/move/index.htm" },
    },
    {
      tone: "moss", art: "hareubang",
      eyebrow: "말로 묻기",
      title: "1월부터 석 달, 둘이서.\n제일 덜 드는 동네는",
      sub: "숙소·렌터카·식비·난방비 합계 비교",
      action: { type: "ask", text: "1월부터 3개월, 둘이서, 차 없이, 원격근무, 월 300 이내" },
    },
    {
      tone: "basalt", art: "hallasan",
      eyebrow: "겨울 한 달",
      title: "1월 볕은\n남쪽이 두 배",
      sub: "1월 일조 시간 · 서귀포 154h · 제주시 70h",
      action: { type: "preset", conditions: { days: 30, start_month: 1 } },
    },
    {
      tone: "sea", art: "dotdam",
      eyebrow: "반년 이상 머문다면",
      title: "단기숙소 대신\n연세라면 얼마",
      sub: "체류 기간별 숙소비 비교",
      action: { type: "preset", conditions: { days: 180 } },
    },
  ],

  // Agent 시트의 예시 질문
  examples: [
    "1월부터 3개월, 둘이서, 차 없이, 원격근무, 월 300 이내",
    "여름방학에 아이랑 셋이 2주, 렌터카",
    "애월이랑 성산 비교해줘, 한 달 혼자",
    "내년 3월부터 1년 살아보고 싶어, 조용한 곳",
  ],
};
