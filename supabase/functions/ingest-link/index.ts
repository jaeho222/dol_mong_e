// 허브 LINK 데이터(공공데이터포털 파일데이터) → private.staging
import postgres from "npm:postgres@3.4.4";

const sql = postgres(Deno.env.get("SUPABASE_DB_URL")!, { prepare: false, max: 1 });
const J = (o: unknown, s = 200) => Response.json(o, { status: s });
const UA = { "User-Agent": "Mozilla/5.0", "X-Requested-With": "XMLHttpRequest" };

Deno.serve(async (req) => {
  try {
    const [{ v: token }] = await sql`select v from private.ingest_config where k='token'`;
    if (req.headers.get("x-ingest-token") !== token) return J({ error: "forbidden" }, 403);
    const { data_id } = await req.json();
    const meta = await (await fetch(`https://jejudatahub.net/api/data/view?id=${data_id}`)).json();
    const page = meta?.dataLink?.url;
    if (!page) return J({ error: "no link", data_id }, 400);
    const html = await (await fetch(page, { headers: UA })).text();
    const m = html.match(/fn_fileDataDown\('(\d+)',\s*'([^']+)'/);
    if (!m) return J({ error: "no fn_fileDataDown", page }, 422); // 파일 없이 API만 있는 페이지
    const [, pk, dpk] = m;
    const q = new URLSearchParams({ publicDataPk: pk, publicDataDetailPk: dpk, fileDetailSn: "1" });
    const t1 = await (await fetch(`https://www.data.go.kr/tcs/dss/selectFileDataDownload.do?${q}`, { headers: { ...UA, Referer: page } })).text();
    let info: any; try { info = JSON.parse(t1); } catch { return J({ error: "select not json", head: t1.slice(0, 300) }, 422); }
    const vo = info.fileDataRegistVO ?? info.dataSetFileDetailInfo ?? info;
    const atch = vo?.atchFileId ?? JSON.stringify(info).match(/FILE_[0-9A-Za-z]+/)?.[0];
    if (!atch) return J({ error: "no atch", info: JSON.stringify(info).slice(0, 600) }, 422);
    const res = await fetch(`https://www.data.go.kr/cmm/cmm/fileDownload.do?atchFileId=${atch}&fileDetailSn=${vo?.fileDetailSn ?? 1}`, { headers: { ...UA, Referer: page } });
    const buf = new Uint8Array(await res.arrayBuffer());
    let text: string, enc = "utf-8";
    try { text = new TextDecoder("utf-8", { fatal: true }).decode(buf); } catch { text = new TextDecoder("euc-kr").decode(buf); enc = "euc-kr"; }
    text = text.replace(/^﻿/, "");
    if (/^\s*</.test(text.slice(0, 50)) || text.startsWith("PK")) return J({ error: "not csv", ct: res.headers.get("content-type") }, 422);
    const [{ id: sid }] = await sql`insert into private.staging (data_id, title, period, file_name, encoding, file_size, content)
      values (${data_id}, ${meta.title}, ${(meta.startDate ?? "") + "~" + (meta.endDate ?? "")}, ${"data.go.kr/" + pk + " " + (vo?.orginlFileNm ?? vo?.fileNm ?? "")}, ${enc}, ${buf.length}, ${text}) returning id`;
    return J({ data_id, staging_id: sid, bytes: buf.length, enc });
  } catch (e) { return J({ error: String(e) }, 500); }
});
