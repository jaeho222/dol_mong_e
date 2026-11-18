// 국토부 전월세 실거래가 → raw.molit_rent. body: { kind: apt|sh|offi, lawd: 50110|50130, ym: YYYYMM }
import postgres from "npm:postgres@3.4.4";

const sql = postgres(Deno.env.get("SUPABASE_DB_URL")!, { prepare: false, max: 1 });
const J = (o: unknown, s = 200) => Response.json(o, { status: s });
const EP: Record<string, string> = {
  apt: "RTMSDataSvcAptRent/getRTMSDataSvcAptRent",   // data.go.kr 15126474
  sh: "RTMSDataSvcSHRent/getRTMSDataSvcSHRent",      // 15126472 단독·다가구
  offi: "RTMSDataSvcOffiRent/getRTMSDataSvcOffiRent", // 15126475
};
const items = (xml: string) => [...xml.matchAll(/<item>([\s\S]*?)<\/item>/g)].map((m) => {
  const o: Record<string, string> = {};
  for (const f of m[1].matchAll(/<(\w+)>([^<]*)<\/\1>/g)) o[f[1]] = f[2].trim();
  return o;
});

Deno.serve(async (req) => {
  try {
    const [{ v: token }] = await sql`select v from private.ingest_config where k='token'`;
    if (req.headers.get("x-ingest-token") !== token) return J({ error: "forbidden" }, 403);
    const key = (Deno.env.get("DATA_GO_KR_KEY") ?? "").trim();
    const { kind, lawd, ym } = await req.json();
    const all: any[] = []; let page = 1, total = 0;
    do {
      const u = `https://apis.data.go.kr/1613000/${EP[kind]}?serviceKey=${encodeURIComponent(key)}&LAWD_CD=${lawd}&DEAL_YMD=${ym}&numOfRows=1000&pageNo=${page}`;
      const t = await (await fetch(u)).text();
      if (!/<resultCode>0+<\/resultCode>/.test(t)) return J({ error: "api", kind, lawd, ym, head: t.slice(0, 300) }, 502);
      total = Number(t.match(/<totalCount>(\d+)/)?.[1] ?? 0);
      all.push(...items(t)); page++;
    } while (all.length < total && page < 20);
    await sql`delete from raw.molit_rent where kind=${kind} and lawd_cd=${lawd} and deal_ym=${ym}`;
    if (all.length) await sql`insert into raw.molit_rent ${sql(all.map((it) => ({ kind, lawd_cd: lawd, deal_ym: ym, item: it })), "kind", "lawd_cd", "deal_ym", "item")}`;
    return J({ kind, lawd, ym, rows: all.length });
  } catch (e) { return J({ error: String(e) }, 500); }
});
