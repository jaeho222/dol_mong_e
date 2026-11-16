// 화면 문구·배너는 여기서만 고치면 됩니다. (서비스 이름 확정 전 가칭)
window.APP_CONFIG = {
  name: { main: "제주살이", accent: "메이트" },
  apiBase: "",

  // 맨 위 한 줄 띠 배너 (노트폴리오 상단 광고 자리)
  topBanner: {
    tag: "제주愛인",
    text: "청년 제주 한달살이 지원 확인하기",
    sub: "만 19~39세 · 최대 30만 원",
    url: "https://www.jeju.go.kr/move/intro/list.htm?act=view&seq=1153232",
  },

  // 가로 스크롤 배너 카드
  //  action: { type: "link", url } | { type: "ask", text } (Agent에게 질문) | { type: "preset", conditions }
  //  tone: tangerine | moss | basalt | sea | sand  (style.css 의 .tone-*)
  banners: [
    {
      tone: "tangerine",
      eyebrow: "청춘 정거장 in 제주",
      title: "읍·면에 묵으면\n1박에 1만 원 지원",
      sub: "도외 청년 · 14일 이상 체류 시 최대 30만 원 (2026년 5~11월)",
      action: { type: "link", url: "https://www.jeju.go.kr/move/intro/list.htm?act=view&seq=1153232" },
    },
    {
      tone: "moss",
      eyebrow: "물어보면 계산해요",
      title: "1월에 석 달, 둘이서.\n어디가 제일 덜 들까?",
      sub: "숙소·렌터카·식비·난방비까지 동네별로",
      action: { type: "ask", text: "1월부터 3개월, 둘이서, 차 없이, 원격근무, 월 300 이내" },
    },
    {
      tone: "basalt",
      eyebrow: "겨울 한 달이라면",
      title: "1월 햇볕은\n남쪽이 두 배 길어요",
      sub: "1월 일조 서귀포 154시간 · 제주시 70시간",
      action: { type: "preset", conditions: { days: 30, start_month: 1 } },
    },
    {
      tone: "sea",
      eyebrow: "반년 넘게 있을 거라면",
      title: "단기숙소 말고\n연세도 같이 따져봐요",
      sub: "체류 기간을 바꾸면 숙소 형태별로 다시 계산해요",
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
