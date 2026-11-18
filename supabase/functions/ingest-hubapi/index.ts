// 제주데이터허브 Open API → raw.hub_{id} (전 페이지, 100건씩). body: { data_id, params?: {startDate,endDate,...}, max_rows? }
import postgres from "npm:postgres@3.4.4";

const sql = postgres(Deno.env.get("SUPABASE_DB_URL")!, { prepare: false, max: 1 });
const J = (o: unknown, s = 200) => Response.json(o, { status: s });

Deno.serve(async (req) => {
  try {
    const [{ v: token }] = await sql`select v from private.ingest_config where k='token'`;
    if (req.headers.get("x-ingest-token") !== token) return J({ error: "forbidden" }, 403);
    const hk = (Deno.env.get("JEJU_HUB_KEY") ?? "").trim();
    const { data_id, params = {}, max_rows = 80000 } = await req.json();
    const meta = await (await fetch(`https://jejudatahub.net/api/data/view?id=${data_id}`)).json();
    const base = `https://open.jejudatahub.net/api/proxy/${meta.dataKey}/${hk}`;
    const rows: any[] = []; let page = 1; let last: any = null; let more = true;
    while (more && rows.length < max_rows && page <= 2000) {
      const q = new URLSearchParams({ ...params, limit: "100", number: String(page) });
      const r = await fetch(`${base}?${q}`);
      const t = await r.text();
      // 403 Forbidden = 허브 마이페이지 프로젝트에 이 API를 담지 않음
      try { last = JSON.parse(t); } catch { return J({ error: "non-json", status: r.status, head: t.slice(0, 300), got: rows.length, page }, 502); }
      const d = last.data ?? [];
      rows.push(...d);
      more = !!last.hasMore && d.length > 0;
      page++;
    }
    if (!rows.length) return J({ data_id, rows: 0, last: JSON.stringify(last).slice(0, 300) });
    const table = `hub_${data_id}`;
    const cols = [...new Set(rows.flatMap((r) => Object.keys(r)))].map((c) => c.replace(/"/g, ""));
    await sql.unsafe(`drop table if exists raw."${table}"`);
    await sql.unsafe(`create table raw."${table}" (_row_id bigserial primary key, _source_file text)`);
    for (const c of cols) await sql.unsafe(`alter table raw."${table}" add column "${c}" text`);
    await sql.unsafe(`comment on table raw."${table}" is $c$${String(meta.title).replace(/\$c\$/g, "")} (제주데이터허브 API ID ${data_id})$c$`);
    const src = "API " + JSON.stringify(params);
    const data = rows.map((r) => { const o: any = { _source_file: src }; for (const c of cols) o[c] = r[c] == null ? null : (typeof r[c] === "object" ? JSON.stringify(r[c]) : String(r[c])); return o; });
    for (let i = 0; i < data.length; i += 1000) await sql`insert into raw.${sql(table)} ${sql(data.slice(i, i + 1000), ["_source_file", ...cols])}`;
    await sql`delete from raw._ingest_log where data_id=${data_id}`;
    await sql`insert into raw._ingest_log (data_id, title, table_name, file_name, file_size, encoding, row_count) values (${data_id}, ${meta.title}, ${table}, ${src}, 0, 'json', ${data.length})`;
    return J({ data_id, rows: data.length, pages: page - 1, totCnt: last?.totCnt, truncated: more });
  } catch (e) { return J({ error: String(e) }, 500); }
});
