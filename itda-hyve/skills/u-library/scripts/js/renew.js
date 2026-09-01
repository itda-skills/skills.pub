const pg = await openLoggedIn("/myloan/list");
if (pg) {
  const before = parseLoanRows(await pg.evaluate(() =>
    [...document.querySelectorAll("table tbody tr")].map((tr) => ({
      cells: [...tr.querySelectorAll("td,th")].map((td) => td.innerText.trim()),
      cb: tr.querySelector("input[type=checkbox]")?.value || null,
    })).filter((r) => r.cb)
  ));
  // 사이트 정책: 연장은 1회까지. 이미 1회 쓴 건은 요청해도 거부되므로 보내지 않는다.
  const MAX = ARGS.max_renew ?? 1;
  const eligible = (b) => b.renew_count < MAX;
  const want = ARGS.all ? before.filter(eligible).map((b) => b.loan_no) : (ARGS.loan_nos || []);
  const unknown = want.filter((n) => !before.some((b) => b.loan_no === n));
  const maxed = want
    .map((n) => before.find((b) => b.loan_no === n))
    .filter((b) => b && !eligible(b))
    .map((b) => ({ loan_no: b.loan_no, title: b.title, renew_count: b.renew_count }));
  if (!want.length) {
    out({ ok: false, error: ARGS.all && before.length ? "MAX_RENEW_REACHED" : "NO_TARGET",
          max_renew: MAX, available: before,
          maxed: before.filter((b) => !eligible(b)).map((b) => ({ loan_no: b.loan_no, title: b.title, renew_count: b.renew_count })) });
    await closeTab(pg);
  }
  else if (unknown.length) { out({ ok: false, error: "UNKNOWN_LOAN_NO", unknown, available: before }); await closeTab(pg); }
  else if (maxed.length) { out({ ok: false, error: "MAX_RENEW_REACHED", max_renew: MAX, maxed, available: before }); await closeTab(pg); }
  else {
    const checked = await pg.evaluate((nos) => {
      let n = 0;
      document.querySelectorAll('form[name=frm] input[type=checkbox][name=checkbox]').forEach((cb) => {
        cb.checked = nos.includes(cb.value); if (cb.checked) n++;
      });
      return n;
    }, want);
    await pg.click('form[name=frm] input[type=submit]');
    await sleep(3000);
    // 사이트 안내: 연장제 미운영 도서관은 연장횟수가 0이어도 "연기횟수 초과" 로 표시된다.
    const notice = await pg.evaluate(() => {
      const t = document.body.innerText;
      const m = t.match(/(실패사유[^\n]*|연기횟수[^\n]*|연장[^\n]*(완료|실패|되었)[^\n]*)/g);
      return m ? [...new Set(m)].slice(0, 6) : [];
    });
    await pg.goto(ORIGIN + "/myloan/list"); await sleep(1500);
    const after = parseLoanRows(await pg.evaluate(() =>
      [...document.querySelectorAll("table tbody tr")].map((tr) => ({
        cells: [...tr.querySelectorAll("td,th")].map((td) => td.innerText.trim()),
        cb: tr.querySelector("input[type=checkbox]")?.value || null,
      })).filter((r) => r.cb)
    ));
    // 판정은 문구가 아니라 반납예정일 변화로 한다(문구는 오해를 부른다).
    const results = want.map((no) => {
      const b = before.find((x) => x.loan_no === no), a = after.find((x) => x.loan_no === no);
      return { loan_no: no, title: b?.title, due_before: b?.due_at, due_after: a?.due_at,
               renewed: !!(a && b && a.due_at !== b.due_at) };
    });
    out({ ok: true, checked, renewed: results.filter((r) => r.renewed).length,
          failed: results.filter((r) => !r.renewed).length, results, site_notice: notice });
    await closeTab(pg);
  }
}
