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
    { pose: "search", title: "말로 물어보기", sub: "돌몽이 상담", chat: true },
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
