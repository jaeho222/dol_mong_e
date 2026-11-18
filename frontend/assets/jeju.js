// 돌몽이 말투: 문장은 표준어, 끝 어미만 제주어 (규칙은 jeju_rules.json — 서버 backend/tools/jeju.py 와 같은 파일)
// UI 문구에는 쓰지 않고 돌몽이 대사(한마디·온보딩)에만 window.jeju(text) 로 쓴다.
(function () {
  const END = "(?=[\\s.,:;!?~…)\\]\"'”<]|$)";
  let rules = [];
  window.jejuReady = fetch("assets/jeju_rules.json").then((r) => r.json()).then((d) => {
    rules = d.rules.map(([src, dst]) => [new RegExp(src + END), dst]);
  }).catch(() => {});
  window.jeju = function (text) {
    if (!rules.length || !text) return text;
    return String(text).replace(/[^\s<>]+/g, (w) => {
      if (w.includes("](") || w.startsWith("http")) return w;
      for (const [re, dst] of rules) { if (re.test(w)) return w.replace(re, dst); }
      return w;
    });
  };
})();
