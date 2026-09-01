// 희망도서 신청현황 + 주간 한도. summary=true 면 한도만 낸다.
const pg = await openHanbat();
if (pg) {
  const r = await hbList(pg);
  const quota = hbWeekUsage(r.items);
  if (ARGS.summary) {
    out({ ok: true, total: r.total, quota,
          recent: r.items.slice(0, 3).map((i) => ({ title: i.title, applied_at: i.applied_at, status: i.status })) });
  } else {
    out({ ok: true, total: r.total, count: Math.min(r.items.length, ARGS.limit || 10), quota,
          items: r.items.slice(0, ARGS.limit || 10) });
  }
  await closeTab(pg);
}
