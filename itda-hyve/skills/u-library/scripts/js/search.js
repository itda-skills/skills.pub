const url = ORIGIN + "/search/tot/result?st=KWRD&si=TOTAL&q=" + encodeURIComponent(ARGS.query);
const pg = await openTab(url);
await sleep(3000);
const r = await pg.evaluate((limit) => {
  const total = (document.body.innerText.match(/총\s*([\d,]+)\s*건/) || [])[1] || null;
  const items = [...document.querySelectorAll("li.items")].slice(0, limit).map((li) => {
    const f = {};
    li.querySelectorAll("dt.title").forEach((dt) => {
      const dd = dt.nextElementSibling;
      if (dd) f[dt.innerText.trim()] = dd.innerText.trim().replace(/\s*상세보기$/, "").replace(/\n+/g, " ");
    });
    const holdRaw = f["소장현황"] || "";
    const holdings = holdRaw.split(/\s{2,}|,/).map((s) => s.trim()).filter(Boolean).map((s) => {
      const m = s.match(/^(.*?도서관|.*?자료실|.*?)(대출가능|대출중|예약중|정리중|비치중)$/);
      return m ? { library: m[1].trim(), status: m[2] } : { library: s, status: null };
    });
    return { title: f["서명"] || null, author: f["저자"] || null, publisher: f["출판사"] || null,
             year: f["출판년"] || null, isbn: f["ISBN"] || null, call_no: f["청구기호"] || null,
             type: f["자료유형"] || null, holdings,
             detail_url: li.querySelector('a[href*="/search/detail"]')?.getAttribute("href") || null };
  });
  return { total, items };
}, ARGS.limit || 10);
out({ ok: true, query: ARGS.query, total: r.total, count: r.items.length,
      items: r.items.map((i) => ({ ...i, detail_url: i.detail_url ? ORIGIN + i.detail_url : null })) });
await closeTab(pg);
