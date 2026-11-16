// 동네 카드 대표 사진 — 위키미디어 공용(Wikimedia Commons)의 자유 이용 사진.
// 모두 출처 표기 조건을 지키면 상업·비상업 이용 가능(CC0/CC BY/CC BY-SA/공공누리 1유형).
// 화면 카드 아래에 작가·라이선스를 표시하고 원본 페이지로 링크한다. (README '사진 출처' 참고)
//
// 사진 바꾸는 법: commons.wikimedia.org 에서 사진 페이지를 열고, 파일 경로(예: c/c7/Hyeopjae_Beach.jpg)와
// 작가·라이선스를 아래에 적으면 된다. CC BY-NC(비영리) 등 조건이 붙은 사진은 쓰지 않는다.
window.REGION_IMAGES = (() => {
  const T = (path) => `https://upload.wikimedia.org/wikipedia/commons/thumb/${path}/960px-${path.split("/").pop()}`;
  const I = (path, place, artist, license, page) => ({ src: T(path), place, artist, license, page });
  return {
    jeju_new: I("9/94/Yeon-dong_Jeju_City_Korea.jpg", "연동 일대", "제주특별자치도청", "공공누리 1유형",
      "https://commons.wikimedia.org/wiki/File:Yeon-dong_Jeju_City_Korea.jpg"),
    jeju_old: I("3/31/Gwandeokjeong_Pavilion_and_Jeju_Mok_Office_2.JPG", "관덕정·제주목 관아", "Thddbwnd", "CC BY-SA 3.0",
      "https://commons.wikimedia.org/wiki/File:Gwandeokjeong_Pavilion_and_Jeju_Mok_Office_2.JPG"),
    aewol: I("d/d4/Gwakji_Beach_in_Jeju_Island%2C_2022.jpg", "곽지해수욕장", "Jeong seolah", "CC0",
      "https://commons.wikimedia.org/wiki/File:Gwakji_Beach_in_Jeju_Island,_2022.jpg"),
    hallim: I("2/2e/Hyeopjae_Beach_Scenery.jpg", "협재해수욕장과 비양도", "Lcarrion88", "CC BY-SA 4.0",
      "https://commons.wikimedia.org/wiki/File:Hyeopjae_Beach_Scenery.jpg"),
    hangyeong: I("d/d3/View_from_Suwolbong.jpg", "수월봉에서 본 차귀도", "Sohyeon Bak", "CC BY-SA 3.0",
      "https://commons.wikimedia.org/wiki/File:View_from_Suwolbong.jpg"),
    jocheon: I("0/0e/Hamdeok_Beach.jpg", "함덕해수욕장", "Hong Da Hyeon", "CC0",
      "https://commons.wikimedia.org/wiki/File:Hamdeok_Beach.jpg"),
    gujwa: I("9/98/Jeju_woljeongri_beach_2.jpg", "월정리 해변", "Sgroey", "CC BY-SA 4.0",
      "https://commons.wikimedia.org/wiki/File:Jeju_woljeongri_beach_2.jpg"),
    seongsan: I("6/61/Seongsan_Ilchulbong_from_the_air.jpg", "성산일출봉", "Korea.net", "CC BY-SA 2.0",
      "https://commons.wikimedia.org/wiki/File:Seongsan_Ilchulbong_from_the_air.jpg"),
    pyoseon: I("6/62/%ED%91%9C%EC%84%A0%ED%95%B4%EB%B9%84%EC%B9%98%ED%95%B4%EB%B3%80_%282%29.jpg", "표선해비치해변", "Jocelyndurrey", "CC BY-SA 4.0",
      "https://commons.wikimedia.org/wiki/File:%ED%91%9C%EC%84%A0%ED%95%B4%EB%B9%84%EC%B9%98%ED%95%B4%EB%B3%80_(2).jpg"),
    namwon: I("a/a9/%EC%82%B0163_Wimi-ri%2C_Namwon-eup%2C_Seogwipo%2C_Jeju-do%2C_South_Korea_-_panoramio.jpg", "위미리 해안", "Maksim Safiullin", "CC BY 3.0",
      "https://commons.wikimedia.org/wiki/File:%EC%82%B0163_Wimi-ri,_Namwon-eup,_Seogwipo,_Jeju-do,_South_Korea_-_panoramio.jpg"),
    seogwipo_dong: I("c/ca/Jeongbang_Falls.jpg", "정방폭포", "Badara25.ba", "CC BY-SA 3.0",
      "https://commons.wikimedia.org/wiki/File:Jeongbang_Falls.jpg"),
    jungmun: I("5/56/Daepo_Jusangjeolli_Cliff_01.jpg", "대포 주상절리", "Bernard Gagnon", "CC0",
      "https://commons.wikimedia.org/wiki/File:Daepo_Jusangjeolli_Cliff_01.jpg"),
    andeok: I("c/ca/Sanbangsan_Mountain_01.jpg", "산방산", "Bernard Gagnon", "CC0",
      "https://commons.wikimedia.org/wiki/File:Sanbangsan_Mountain_01.jpg"),
    daejeong: I("f/fe/Songaksan.jpg", "송악산", "Lcarrion88", "CC BY-SA 4.0",
      "https://commons.wikimedia.org/wiki/File:Songaksan.jpg"),
  };
})();
