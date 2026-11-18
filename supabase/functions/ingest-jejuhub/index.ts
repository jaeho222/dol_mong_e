// 제주데이터허브 FILE 데이터 → private.staging (CSV 원문). 파싱·적재는 DB의 private.load_staged()가 한다.
import postgres from "npm:postgres@3.4.4";

const sql = postgres(Deno.env.get("SUPABASE_DB_URL")!, { prepare: false, max: 1 });
const HUB = "https://jejudatahub.net";
const J = (o: unknown, status = 200) => Response.json(o, { status });

async function getMeta(id: number) {
  const t = await (await fetch(`${HUB}/api/data/view?id=${id}`)).text();
  try { return JSON.parse(t); } catch { throw new Error("hub blocked or non-json: " + t.slice(0, 120)); }
}

Deno.serve(async (req) => {
  try {
    const [{ v: token }] = await sql`select v from private.ingest_config where k='token'`;
    if (req.headers.get("x-ingest-token") !== token) return J({ error: "forbidden" }, 403);
    const body = await req.json();
    const id = Number(body.data_id);
    const meta = await getMeta(id);
    if (!meta?.id) return J({ error: "not found", id }, 404);
    const all = meta?.dataFile?.fileInfos ?? [];
    const files = all.filter((f: any) => /\.csv$/i.test(f.fileName));

    if (body.mode === "catalog") {
      const type = meta.dataApi ? "API" : meta.dataLink ? "LINK" : all.length ? "FILE" : "?";
      const mb = Math.round(files.reduce((s: number, f: any) => s + (f.fileSize || 0), 0) / 1048576 * 10) / 10;
      const other = all.filter((f: any) => !/\.csv$/i.test(f.fileName)).map((f: any) => f.fileName).join(" | ");
      await sql`insert into raw._catalog (data_id, title, category, data_type, period, owner, description, csv_files, other_files, total_mb, hub_url)
        values (${id}, ${meta.title}, ${meta.categoryName}, ${type}, ${(meta.startDate ?? "") + " ~ " + (meta.endDate ?? "")}, ${meta.owner}, ${meta.description}, ${files.length}, ${other || null}, ${mb}, ${HUB + "/data/view/data/" + id})
        on conflict (data_id) do update set title=excluded.title, category=excluded.category, data_type=excluded.data_type, period=excluded.period, owner=excluded.owner,
          description=excluded.description, csv_files=excluded.csv_files, other_files=excluded.other_files, total_mb=excluded.total_mb, hub_url=excluded.hub_url, updated_at=now()`;
      return J({ id, type, csv: files.length, mb, other });
    }

    const f = files[Number(body.file_index ?? 0)];
    if (!f) return J({ error: "no csv file at index", csv_count: files.length }, 400);
    const q = new URLSearchParams({ id: String(f.id), fileId: String(f.fileId), fileName: f.fileName, fileSize: String(f.fileSize), contentType: f.contentType ?? "text/csv", saveFileName: f.saveFileName, downloadCount: String(f.downloadCount ?? 0), createAt: f.createAt ?? "", createBy: String(f.createBy ?? 1) });
    const res = await fetch(`${HUB}/api/file/test-download?${q}`);
    if (!res.ok) return J({ error: "download", status: res.status }, 502);
    const buf = new Uint8Array(await res.arrayBuffer());
    let text: string, encoding = "utf-8";
    try { text = new TextDecoder("utf-8", { fatal: true }).decode(buf); }
    catch { text = new TextDecoder("euc-kr").decode(buf); encoding = "euc-kr"; }
    text = text.replace(/^﻿/, "");
    const [{ id: sid }] = await sql`insert into private.staging (data_id, title, period, file_name, encoding, file_size, content)
      values (${id}, ${meta.title}, ${meta.startDate + "~" + meta.endDate}, ${f.fileName}, ${encoding}, ${buf.length}, ${text}) returning id`;
    return J({ id, staging_id: sid, file: f.fileName, encoding, bytes: buf.length, csv_count: files.length });
  } catch (e) {
    return J({ error: String(e) }, 500);
  }
});
