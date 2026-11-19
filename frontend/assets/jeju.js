// 돌몽이 말투: 문장은 표준어 그대로, 문장 끝 어미만 '읽기 쉬운' 제주어로 일관되게 (서버 backend/tools/jeju.py 와 같은 규칙 — 같이 고칠 것)
//   받침 있는 말+어요/아요 → +수다 (적어요→적수다) · ~이에요/~예요 → ~이우다/~우다 · ~해요 → ~허우다 · ~워요 → ~웁수다
//   돼요 → 됨수다 · 그 밖의 받침 없는 말+요 → 받침ㅁ+수다 (달라요→달람수다) · ~ㄹ게요 → ~쿠다 · ~세요 → ~ㅂ서 · ~까요 → ~까마씸 · ~네요 → ~수다
//   묻는 말(?)은 ~다 → ~꽈. 특별한 말(인사 등)은 jeju_rules.json 의 words. 문장 끝(문장부호·줄 끝·괄호 앞)에서만 바꾼다.
// UI 문구에는 쓰지 않고 돌몽이 대사(한마디·온보딩)에만 window.jeju(text) 로 쓴다.
(function () {
  const B = 17, L = 8, M = 16;
  let words = [];
  window.jejuReady = fetch("assets/jeju_rules.json").then((r) => r.json()).then((d) => {
    words = Object.entries(d.words || {}).sort((a, b) => b[0].length - a[0].length);
  }).catch(() => {});
  const jong = (ch) => { const c = ch.charCodeAt(0) - 0xac00; return c >= 0 && c < 11172 ? c % 28 : -1; };
  const setJong = (ch, j) => { const c = ch.charCodeAt(0) - 0xac00; return c >= 0 && c < 11172 ? String.fromCharCode(0xac00 + c - (c % 28) + j) : ch; };

  function convertWord(w) {
    for (const [src, dst] of words) if (w.endsWith(src)) return w.slice(0, -src.length) + dst;
    if (w.endsWith("습니다")) return w.slice(0, -3) + "수다";
    if (w.endsWith("습니까")) return w.slice(0, -3) + "수꽈";
    if (w.length >= 3 && (w.endsWith("니다") || w.endsWith("니까")) && jong(w.at(-3)) === B)
      return w.slice(0, -3) + (w.at(-3) === "합" ? "허" : setJong(w.at(-3), 0)) + (w.endsWith("니다") ? "우다" : "우꽈");
    if (!w.endsWith("요") || w.length < 2) return w;
    const s = w.slice(0, -1), last = s.at(-1);
    if (s.endsWith("이에")) return s.slice(0, -2) + "이우다";
    if (last === "예") return s.slice(0, -1) + "우다";
    if (last === "세" && s.length >= 2) { const p = s.at(-2); return s.slice(0, -2) + (p === "하" ? "헙" : jong(p) === 0 ? setJong(p, B) : p + "읍") + "서"; }
    if (last === "게" && s.length >= 2 && jong(s.at(-2)) === L) return s.slice(0, -2) + setJong(s.at(-2), 0) + "쿠다";
    if (last === "까") return s + "마씸";
    if (last === "네" && s.length >= 2) return s.slice(0, -1) + "수다";  // 좋겠네요 → 좋겠수다
    if (last === "해") return s.slice(0, -1) + "허우다";
    if (last === "돼" || last === "되") return s.slice(0, -1) + "됨수다";
    if (last === "워" && s.length >= 2) return s.slice(0, -1) + "웁수다";
    if ((last === "어" || last === "아") && s.length >= 2 && jong(s.at(-2)) > 0) return s.slice(0, -1) + "수다";
    if (jong(last) === 0) return s.slice(0, -1) + setJong(last, M) + "수다";
    return w;
  }

  window.jeju = function (text) {
    if (!text) return text;
    text = String(text);
    return text.replace(/([^\s<>(]*?[가-힣])([^\s<>가-힣(]*)(?=\s|$|<|\()/g, (m, core, punct, off) => {
      if (core.includes("](") || core.startsWith("http")) return m;
      const after = text.slice(off + m.length, off + m.length + 3);
      if (!(/[.?!~:…]/.test(punct) || after === "" || "\n<".includes(after[0]) || after.trimStart().startsWith("("))) return m;
      if (!punct && after.trimStart().startsWith("(") && !/(어요|아요|해요|예요|에요|워요|돼요)$/.test(core)) return m;  // 괄호 앞은 확실한 해요체만
      let out = convertWord(core);
      if (punct.includes("?") && out !== core && (out.endsWith("수다") || out.endsWith("우다"))) out = out.slice(0, -1) + "꽈";
      return out + punct;
    });
  };
})();
