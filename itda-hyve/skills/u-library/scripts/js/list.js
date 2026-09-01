const pg = await openLoggedIn("/myloan/list");
if (pg) {
  const raw = await pg.evaluate(() =>
    [...document.querySelectorAll("table tbody tr")].map((tr) => ({
      cells: [...tr.querySelectorAll("td,th")].map((td) => td.innerText.trim()),
      cb: tr.querySelector("input[type=checkbox]")?.value || null,
    })).filter((r) => r.cb)
  );
  const today = new Date(); today.setHours(0, 0, 0, 0);
  const items = parseLoanRows(raw).map((it) => {
    const due = new Date(it.due_at + "T00:00:00");
    // 사이트 정책: 연장 1회까지 (ULIBRARY_MAX_RENEW 로 조정)
    const max = ARGS.max_renew ?? 1;
    return { ...it, days_left: Math.round((due - today) / 86400000),
             renewable: it.renew_count < max };
  });
  out({ ok: true, count: items.length, items });
  await closeTab(pg);
}
