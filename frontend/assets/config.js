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
    { pose: "search", title: "말로 물어보기", sub: "리포트 아래 돌몽이 상담", consult: true },
  ],

  // 첫 방문 문답 (onboarding.js). 처음 온 사람에게 한 번 뜨고, 주소 뒤에 ?start=1 이면 다시 뜬다.
  //  set: 답을 고르면 채울 조건 / react: 고른 뒤 돌몽이가 하는 말 / pose: 그 질문에서의 돌몽이 모습
 
  onboarding: [
    {
      type: "intro",
      pose: "hello",
      say: "혼저 옵서예! 제주살이 동모 돌몽이우다!",
      sub: "동모는 제주말로 친구라는 뜻이우다. 몇 가지만 물어보고 같이 살 동네를 찾아보쿠다!",
      cta: "좋수다, 같이 찾아봅주!"
    },
    {
      type: "name",
      pose: "front",
      say: "돌몽이가 뭐라고 부르면 좋수꽈?",
      sub: "별명도 좋수다! 안 적고 넘어가도 괜찮수다."
    },
    {
      type: "month",
      pose: "front",
      say: "언제쯤 제주에 올 거우꽈?",
      react: "그때 제주는 어떤 모습인지 보여드리쿠다!"
    },
    {
      pose: "three4",
      say: "제주에서 얼마나 머물 거우꽈?",
      options: [
        {
          label: "2주",
          sub: "짧게 맛보기",
          set: { days: 14 },
          react: "짧고 굵게! 알차게 지내봅주!"
        },
        {
          label: "한 달",
          sub: "제일 많이 골라요",
          set: { days: 30 },
          react: "한 달이면 제주를 호꼼 더 알아갈 수 있수다!"
        },
        {
          label: "두 달",
          set: { days: 60 },
          react: "두 달이면 제주 생활에 제법 익숙해지쿠다!"
        },
        {
          label: "석 달",
          set: { days: 90 },
          react: "석 달이면 동네 삼춘들도 얼굴 알아보쿠다!"
        },
        {
          label: "반년",
          set: { days: 180 },
          react: "반년이면 연세 집도 같이 따져보쿠다!"
        },
        {
          label: "1년",
          sub: "진짜 살아보기",
          set: { days: 365 },
          react: "1년이면 거의 제주 사람 다 되쿠다!"
        }
      ]
    },
    {
      pose: "hello",
      say: "누구랑 같이 올 거우꽈?",
      options: [
        {
          label: "혼자",
          set: { people: 1, with_kids: false },
          react: "혼자 와도 걱정 마십서! 돌몽이가 있수다!"
        },
        {
          label: "둘이서",
          sub: "친구·연인·부부",
          set: { people: 2, with_kids: false },
          react: "둘이면 숙소비도 나눌 수 있수다!"
        },
        {
          label: "아이와 가족",
          set: { people: 3, with_kids: true },
          react: "아이랑 지내기 좋은 동네도 살펴보쿠다!"
        }
      ]
    },
    {
      pose: "hello",
      say: "반려동물도 같이 올 거우꽈?",
      options: [
        {
          label: "네, 같이 와요!",
          set: { with_pet: true },
          react: "반려동물이랑 산책하기 좋은 동네도 찾아보쿠다!"
        },
        {
          label: "아니요, 사람끼리 가요",
          set: { with_pet: false },
          react: "알았수다! 그럼 다음으로 가봅주!"
        }
      ]
    },
    {
      pose: "side",
      say: "제주에서 차는 빌릴 거우꽈?",
      options: [
        {
          label: "렌터카 빌릴래요",
          set: { car: true },
          react: "렌터카 비용도 꼼꼼히 챙겨보쿠다!"
        },
        {
          label: "버스 타고 걸을래요",
          set: { car: false },
          react: "그럼 버스 잘 다니는 동네가 좋쿠다!"
        }
      ]
    },
    {
      pose: "calc",
      say: "전부 합쳐서 예산은 얼마쯤 생각햄수꽈?",
      sub: "숙소, 차, 식비, 공과금까지 몽땅 합친 금액이우다!",
      options: [
        {
          label: "150만 원 이하",
          set: { budget: 150 }
        },
        {
          label: "200만 원 이하",
          set: { budget: 200 }
        },
        {
          label: "300만 원 이하",
          set: { budget: 300 }
        },
        {
          label: "600만 원 이하",
          set: { budget: 600 }
        },
        {
          label: "1,000만 원 이하",
          set: { budget: 1000 }
        },
        {
          label: "아직 모르겠어요",
          set: { budget: null },
          react: "괜찮수다! 동네마다 얼마 드는지 알려드리쿠다!"
        }
      ],
      react: "예산에 맞는 동네를 찾아보쿠다!"
    },
    {
      pose: "search",
      say: "밤 10시, 제주에서 뭐 하고 있을 거 닮수꽈?",
      options: [
        {
          label: "이미 꿈나라",
          sub: "일찍 자고 일찍 일어나요",
          set: { prefer_quiet: true },
          react: "조용하고 한적한 동네로 찾아보쿠다! 쉿!"
        },
        {
          label: "동네 술집에서 한 잔",
          sub: "밤에도 놀고 싶어요",
          set: { prefer_quiet: false },
          react: "밤에도 활기찬 동네가 좋쿠다!"
        }
      ]
    },
    {
      pose: "calc",
      say: "제주에서도 일해야 햄수꽈?",
      options: [
        {
          label: "노트북은 필수예요",
          set: { remote_work: true },
          react: "와이파이랑 공유오피스 있는 동네도 챙겨보쿠다!"
        },
        {
          label: "완전히 쉬러 가요",
          set: { remote_work: false },
          react: "좋수다! 일 생각은 공항에 두고 옵서!"
        }
      ]
    },
    {
      type: "ready",
      pose: "done",
      say: "이제 거의 다 됐수다! 우리 같이 살 동네 찾아봅주!",
      cta: "우리 동네 찾으러 갑주!"
    }
  ],


  // 로딩 화면: 세 장면을 frameMs 마다 넘긴다. {name} 은 문답에서 받은 이름 (없으면 nameless 문구)
  loader: {
    frameMs: 2500,
    minMs: 1200,   // 결과가 너무 빨리 와도 이만큼은 보여준다 (깜빡임 방지)
    
    frames: [
      { img: "assets/dolmong/sd-run.webp", text: "돌몽이가 {name}님에게 줄 귤을 갖고 오고 있어요.", nameless: "돌몽이가 귤을 갖고 오고 있어요." },
      { img: "assets/dolmong/sd-trip.webp", text: "돌몽이가 넘어졌어요. 잠시만 기다려주세요." },
      { img: "assets/dolmong/sd-pick.webp", text: "돌몽이가 귤을 주워담고 있어요. 잠시만 기다려주세요." },
    ],

  },

  // 동네 성격: 생활 점수 상위 2개로 '겨울 볕 좋고 조용한 동네' 같은 이름을 만든다 (점수 0.6 이상만)
  //  [꾸미는 말, 이어 주는 말] — '겨울 볕 좋고' + '조용한' + ' 동네'
  traits: {
    "교통": ["버스 잘 다니는", "버스 잘 다니고"], "생활편의": ["편의시설 가까운", "편의시설 가깝고"],
    "의료": ["병원 가까운", "병원 가깝고"], "날씨": ["날씨 좋은", "날씨 좋고"],
    "조용함": ["한적한", "한적하고"], "자연": ["자연 환경 좋은", "자연 환경 좋고"],
    "맛집": ["맛집 많은", "맛집 많고"], "밤길안심": ["안전한", "안전하고"],
  },

  // '가장 중요한 것 3가지' 선택지 (key 는 백엔드 region.PRIORITY_KEYS 와 같아야 함). 누른 순서 = 중요한 순서
  
  priorities: [
    { key: "비용", label: "비용", icon: "비용.svg" },
    { key: "교통", label: "교통", icon: "교통.svg" },
    { key: "생활편의", label: "편의시설", icon: "편의시설.svg" },
    { key: "의료", label: "의료", icon: "의료.svg" },
    { key: "조용함", label: "한적함", icon: "한적함.svg" },
    { key: "자연", label: "자연 환경", icon: "자연.svg" },
    { key: "날씨", label: "날씨", icon: "날씨.svg" },
    { key: "맛집", label: "맛집", icon: "맛집.svg" },
    { key: "밤길안심", label: "안전", icon: "안전.svg" },
  ],


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
    { months: [9], text: "선선한 바람과 함께 가을 제주가 시작되는 철" },
    { months: [8, 9], text: "태풍이 올 수 있어요", warn: true },
    { months: [10, 11], text: "오름에 억새 피는 철" },
  ],

  // 동네 지수 카드. 백엔드가 '보여줄 만한 차이'가 있는 지수만 indices[key] = { value, text, tone, score } 로 보낸다.
  // 여기 목록은 이름·순서·설명만 정한다. 결과에 없는 지수는 화면에 안 나온다. (backend/tools/indices.py)
  indices: [
    { key: "laundry", name: "빨래 지수", hint: "습도·바람·일조로 본 빨래 마르는 날" },
    { key: "hair", name: "산발 지수", hint: "강풍이 부는 날이 얼마나 되는지" },
    { key: "rentacar", name: "렌터카 수", hint: "관광 렌터카가 몰리는 정도" },
    { key: "gyul", name: "귤 시즌", hint: "머무는 달에 동네에서 나는 귤" },
    { key: "nopo", name: "노포 지수", hint: "오래 영업한 동네 식당 비율" },
    { key: "oreum", name: "오름 부자 지수", hint: "가까이 있는 오름 수" },
    { key: "trend", name: "요즘 뜨는 동네", hint: "최근 3년 새로 연 가게 비율" },
    { key: "gyul_sweet", name: "귤 당도", hint: "동네 고품질 감귤 당도 평균" },
    { key: "food", name: "맛집 지수", hint: "구글 평점 4.5 이상 식당 수" },
    { key: "festival", name: "동네 축제", hint: "머무는 동안 열리는 동네 축제" },
    { key: "pet", name: "댕댕이 지수", hint: "동물병원 수 (반려동물 동반 시)" },
    { key: "noise", name: "비행기 소리", hint: "공항 인근 항공기 소음도" },
    { key: "flood", name: "침수 주의", hint: "장마철 침수위험지구" },
    { key: "snow", name: "폭설 주의", hint: "눈 오면 통제되는 산간 도로" },
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
