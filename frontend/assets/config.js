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

  // 조건에서 고를 수 있는 것 (key 는 백엔드 conditions 필드 이름)
  options: [
    { key: "remote_work", label: "원격근무", icon: "laptop" },
    { key: "prefer_quiet", label: "한적한 곳", icon: "leaf" },
    { key: "with_kids", label: "아이와 함께", icon: "baby" },
    { key: "with_pet", label: "반려동물", icon: "paw" },
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
