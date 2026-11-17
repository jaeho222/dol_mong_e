// 화면 문구는 여기서만 고친다.
window.APP_CONFIG = {
  name: "돌몽이",
  tagline: "제주살이 AI Agent",
  apiBase: "",

  // 돌몽이 포즈 이미지 (원본 SVG를 렌더링한 webp — frontend/assets/dolmong/)
  pose: {
    hello: "assets/dolmong/hello.webp",       // 인사하기
    search: "assets/dolmong/search.webp",     // 찾아보기 (지도)
    calc: "assets/dolmong/calc.webp",         // 계산하기
    done: "assets/dolmong/done.webp",         // 완성하기
    main: "assets/dolmong/main.webp",         // 원본 (지도 든 모습)
    signature: "assets/dolmong/signature.webp", // 모자에서 귤 꺼내기
    front: "assets/dolmong/front.webp",
    three4: "assets/dolmong/three4.webp",
    side: "assets/dolmong/side.webp",
    back: "assets/dolmong/back.webp",
  },

  // 첫 화면 사진 (위키미디어 공용, 자유 이용) — 하나를 무작위로 띄운다
  //  path: 위키미디어 파일 경로 'a/ab/파일명' / place: 장소 / artist / license
  heroPhotos: [
    { path: "f/f8/Seongsan,_Jeju_Island.jpg", place: "성산 마을", artist: "Bernard Gagnon", license: "CC0" },
    { path: "0/0e/Hamdeok_Beach.jpg", place: "함덕 해변", artist: "Hong Da Hyeon", license: "CC0" },
    { path: "c/ca/Sanbangsan_Mountain_01.jpg", place: "산방산과 마을", artist: "Bernard Gagnon", license: "CC0" },
  ],

  // 검색바 아래 체크 조건 (key 는 백엔드 conditions 필드 이름)
  options: [
    { key: "remote_work", label: "원격근무" },
    { key: "prefer_quiet", label: "한적한 곳" },
    { key: "with_kids", label: "아이와 함께" },
    { key: "with_pet", label: "반려동물" },
  ],

  // 첫 화면 돌몽이 타일: 누르면 조건을 채워서 바로 찾거나(preset), 상담을 연다(chat)
  //  preset 필드: month(1~12), days, people, car, budget, 그리고 options 의 key
  quick: [
    { pose: "front", title: "겨울 한 달", sub: "1월, 둘이서", preset: { month: 1, days: 30, people: 2 } },
    { pose: "calc", title: "원격근무 석 달", sub: "노트북 들고", preset: { days: 90, people: 1, remote_work: true } },
    { pose: "hello", title: "아이와 2주", sub: "여름방학에", preset: { month: 7, days: 14, people: 3, with_kids: true } },
    { pose: "done", title: "1년 살아보기", sub: "연세 집 기준", preset: { days: 365, people: 2 } },
    { pose: "signature", title: "돌몽이랑 고르기", sub: "질문 몇 개로", onboarding: true },
    { pose: "search", title: "말로 물어보기", sub: "돌몽이 상담", chat: true },
  ],

  // 첫 방문 문답 (onboarding.js). 처음 온 사람에게 한 번 뜨고, 주소 뒤에 ?start=1 이면 다시 뜬다.
  //  set: 답을 고르면 채울 조건 / react: 고른 뒤 돌몽이가 하는 말 / pose: 그 질문에서의 돌몽이 모습
  onboarding: [
    { type: "intro", pose: "hello", say: "안녕하세요! 저는 제주살이 동모 돌몽이에요!",
      sub: "동모는 제주말로 친구라는 뜻이에요. 몇 가지만 물어보고 우리가 같이 살 동네를 찾아볼게요.", cta: "좋아요, 같이 찾아요" },
    { type: "month", pose: "front", say: "언제쯤 제주에 올 거예요?", react: "그때 제주는 이런 모습이에요" },
    { pose: "three4", say: "얼마나 머물 거예요?", options: [
      { label: "2주", sub: "짧게 맛보기", set: { days: 14 }, react: "짧고 굵게! 좋아요." },
      { label: "한 달", sub: "제일 많이 골라요", set: { days: 30 }, react: "제주 한 달 살기, 정석이죠." },
      { label: "두 달", set: { days: 60 }, react: "계절 하나를 통째로 겪어 보겠네요." },
      { label: "석 달", set: { days: 90 }, react: "이 정도면 동네 삼춘들이 얼굴을 알아봐요." },
      { label: "반년", set: { days: 180 }, react: "반년이면 연세 집도 같이 따져 볼게요." },
      { label: "1년", sub: "진짜 살아보기", set: { days: 365 }, react: "1년이면 거의 제주 사람이에요!" },
    ] },
    { pose: "hello", say: "누구랑 같이 와요?", options: [
      { label: "혼자", set: { people: 1, with_kids: false, with_pet: false }, react: "혼자여도 제가 있잖아요." },
      { label: "둘이서", sub: "친구·연인·부부", set: { people: 2, with_kids: false, with_pet: false }, react: "둘이면 숙소비를 나눌 수 있어요." },
      { label: "아이와 가족", set: { people: 3, with_kids: true, with_pet: false }, react: "소아과 가까운 동네를 챙길게요." },
      { label: "반려동물도 같이", set: { people: 2, with_pet: true, with_kids: false }, react: "산책하기 좋은 동네로 볼게요." },
    ] },
    { pose: "side", say: "차는 빌릴 거예요?", options: [
      { label: "렌터카 빌릴래요", set: { car: true }, react: "렌터카 값도 비용에 넣을게요." },
      { label: "버스 타고 걸을래요", set: { car: false }, react: "버스 잘 다니는 동네가 중요하겠네요." },
    ] },
    { pose: "calc", say: "전부 합쳐서 예산은 얼마쯤이에요?", sub: "숙소, 차, 식비, 공과금을 다 더한 금액이에요.", options: [
      { label: "150만 원 이하", set: { budget: 150 } },
      { label: "200만 원 이하", set: { budget: 200 } },
      { label: "300만 원 이하", set: { budget: 300 } },
      { label: "600만 원 이하", set: { budget: 600 } },
      { label: "1,000만 원 이하", set: { budget: 1000 } },
      { label: "아직 모르겠어요", set: { budget: null }, react: "괜찮아요. 동네마다 얼마 드는지 보여드릴게요." },
    ], react: "예산 안에서 찾아볼게요." },
    { pose: "search", say: "밤 10시, 제주에서 뭐 하고 있을 것 같아요?", options: [
      { label: "이미 꿈나라", sub: "일찍 자고 일찍 일어나요", set: { prefer_quiet: true }, react: "조용한 동네 위주로 볼게요. 쉿!" },
      { label: "동네 술집에서 한 잔", sub: "밤에도 놀고 싶어요", set: { prefer_quiet: false }, react: "밤에도 불 켜진 동네가 좋겠네요." },
    ] },
    { pose: "calc", say: "제주에서 일도 해야 해요?", options: [
      { label: "노트북은 필수예요", set: { remote_work: true }, react: "와이파이랑 공유오피스 있는 동네를 챙길게요." },
      { label: "완전히 쉬러 가요", set: { remote_work: false }, react: "일 생각은 공항에 두고 오세요!" },
    ] },
    { type: "ready", pose: "done", say: "거의 다 끝났어요! 이제 우리가 살 동네를 찾아볼까요?", cta: "우리 동네 찾기" },
  ],
  onboardingLoading: [
    { pose: "search", say: "제주 지도를 펼쳐 보는 중이에요" },
    { pose: "calc", say: "동네마다 한 달 비용을 계산하고 있어요" },
    { pose: "main", say: "거의 다 찾았어요" },
  ],

  // 동네 성격: 생활 점수 상위 2개로 '겨울 볕 좋고 조용한 동네' 같은 이름을 만든다 (점수 0.6 이상만)
  //  [꾸미는 말, 이어 주는 말] — '겨울 볕 좋고' + '조용한' + ' 동네'
  traits: {
    "교통": ["버스 잘 다니는", "버스 잘 다니고"], "생활편의": ["편의시설 가까운", "편의시설 가깝고"],
    "의료": ["병원 가까운", "병원 가깝고"], "겨울날씨": ["겨울 볕 좋은", "겨울 볕 좋고"],
    "한적함": ["조용한", "조용하고"], "원격근무": ["일하기 좋은", "일하기 좋고"],
  },

  // 제주 계절 달력: 머무는 기간에 걸리는 것만 보여준다 (warn: 미리 알아둘 것)
  // TODO[DATA]: 축제는 VISIT JEJU 축제행사 데이터(xlsx 590)로 바꿀 것
  seasons: [
    { months: [10, 11, 12, 1], text: "노지 귤 따는 철" },
    { months: [12, 1, 2, 3], text: "동백꽃 피는 철" },
    { months: [12, 1, 2], text: "한라산에 눈, 산간 도로가 자주 통제돼요", warn: true },
    { months: [3, 4], text: "유채꽃과 벚꽃 피는 철" },
    { months: [3, 4, 5], text: "황사·미세먼지가 잦은 철", warn: true },
    { months: [4, 5], text: "고사리 꺾는 철" },
    { months: [6, 7], text: "수국 피는 철" },
    { months: [6, 7], text: "장마철, 빨래가 잘 안 말라요", warn: true },
    { months: [7, 8], text: "해수욕장 여는 철" },
    { months: [8, 9], text: "태풍이 올 수 있어요", warn: true },
    { months: [10, 11], text: "오름에 억새 피는 철" },
  ],

  // 동네 지수 카드. 백엔드 결과에 indices[key] = { value: 0~100, text: "돌몽이 한마디" } 가 오면 채워지고,
  // 없으면 '데이터 연결 전'으로 보인다. (재미-포인트-아이디어.md 참고)
  indices: [
    { key: "laundry", name: "빨래 지수", hint: "습도·바람·일조로 본 빨래 마르는 날" },
    { key: "hair", name: "산발 지수", hint: "강풍이 부는 날이 얼마나 되는지" },
    { key: "rentacar", name: "렌터카 습격 지수", hint: "관광 렌터카가 몰리는 정도" },
    { key: "gyul", name: "귤 시즌", hint: "머무는 달에 동네에서 나는 귤" },
    { key: "nopo", name: "노포 지수", hint: "오래 영업한 동네 식당 비율" },
    { key: "oreum", name: "오름 부자 지수", hint: "가까이 있는 오름 수" },
  ],

  // Agent 대화창 예시 질문
  examples: [
    "1월부터 3개월, 둘이서, 차 없이, 원격근무, 월 300 이내",
    "여름방학에 아이랑 셋이 2주, 렌터카",
    "애월이랑 성산 비교해줘, 한 달 혼자",
    "내년 3월부터 1년 살아보고 싶어, 조용한 곳",
  ],

  support: { text: "제주 한달살이 지원사업 보기", url: "https://www.jeju.go.kr/move/index.htm" },
};
