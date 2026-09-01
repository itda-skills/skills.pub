// 희망도서 신청 — 2단계 계약(write → dupCheck → 접수하기 → insert.do).
// ⚠️ dupCheck 화면에서 멈추면 아무 에러 없이 미접수로 끝난다(실측 2026-08-22).
//    그래서 성공 판정은 화면 문구가 아니라 '목록 총건수 증가 + 최상단 행 일치'로 한다.
const B = ARGS.book;
const pg = await openHanbat();
if (pg) {
  const before = await hbList(pg);
  const quota = hbWeekUsage(before.items);
  const mine = before.items.find((i) => hbNorm(i.title) === hbNorm(B.title));

  const blockers = [];
  if (Number(B.price) > 50000) blockers.push({ code: "PRICE_LIMIT", detail: B.price + "원 — 한 권당 50,000원 초과는 선정제외" });
  if (quota.remaining <= 0 && !ARGS.ignore_quota) blockers.push({ code: "WEEK_QUOTA_REACHED", detail: quota.window + " 기준 " + quota.used + "/" + quota.limit + "권 사용" });
  if (mine) blockers.push({ code: "ALREADY_REQUESTED", detail: mine.applied_at + " 신청(" + mine.status + ")" });

  if (ARGS.submit && blockers.length) {
    out({ ok: false, error: blockers[0].code, blockers, quota, book: B });
  } else {
    const ready = await hbOpenWriteForm(pg);
    if (!ready) {
      // 한도 소진이면 사이트가 신청 화면을 아예 안 준다 — 그 사실을 그대로 말한다.
      const quotaOut = quota.remaining <= 0;
      out({ ok: false, error: quotaOut ? "WEEK_QUOTA_REACHED_BY_SITE" : "WRITE_FORM_NOT_READY",
            url: await pg.url(), quota,
            head: (await pg.evaluate(() => document.body.innerText.replace(/\s+/g, " "))).slice(0, 200),
            message: quotaOut
              ? "사이트가 신청 화면 진입을 막았습니다 — 주간 한도(" + quota.used + "/" + quota.limit + "권) 소진으로 보입니다."
              : "신청 폼이 뜨지 않았습니다(세션 또는 화면 계약 변경)." });
      await closeTab(pg);
      throw new Error("WRITE_FORM_NOT_READY");
    }
    await pg.fill("#title", B.title);
    await pg.fill('input[name="author"]', B.author);
    await pg.fill('input[name="publisher"]', B.publisher);
    await pg.fill('input[name="current_price"]', String(B.price));
    await pg.fill('input[name="pub_year"]', String(B.year));
    if (B.isbn) await pg.fill('input[name="isbn"]', B.isbn);
    if (B.edition) await pg.fill('input[name="edition"]', B.edition);
    if (B.reason) await pg.fill("#user_remark", B.reason);
    const filled = await pg.evaluate(() => ({
      title: document.querySelector("#title").value,
      author: document.querySelector('input[name="author"]').value,
      publisher: document.querySelector('input[name="publisher"]').value,
      price: document.querySelector('input[name="current_price"]').value,
      year: document.querySelector('input[name="pub_year"]').value,
      isbn: document.querySelector('input[name="isbn"]').value,
      reason_len: document.querySelector("#user_remark").value.length,
    }));

    await pg.evaluate(() => document.querySelector("#wishForm").submit());
    await hbWaitFor(pg, "#frm", 12);
    await sleep(500);

    // 중복확인 화면 — 도서관 측 판정이 그대로 표로 나온다. 우리가 흉내 내지 않는다.
    const dup = await pg.evaluate(() => {
      const sections = [];
      document.querySelectorAll("table").forEach((tb) => {
        let label = "", n = tb.previousElementSibling;
        while (n && !label) { label = (n.innerText || "").trim().split("\n")[0]; n = n.previousElementSibling; }
        const rows = [...tb.querySelectorAll("tbody tr")]
          .map((tr) => [...tr.cells].map((c) => c.innerText.trim().replace(/\s+/g, " ")))
          .filter((r) => r.length && !/도서가\s*존재\s*하지\s*않습니다/.test(r.join(" ")));
        if (/소장|입수/.test(label)) sections.push({ label, hits: rows });
      });
      const hasAccept = [...document.querySelectorAll("a,button,input[type=submit],input[type=button]")]
        .some((b) => /접수하기/.test(b.textContent || b.value || ""));
      return { url: location.href, sections, hasAccept };
    });
    const dupHits = dup.sections.reduce((n, s) => n + s.hits.length, 0);

    if (!dup.hasAccept) {
      out({ ok: false, error: "ACCEPT_BUTTON_MISSING", dup, filled,
            message: "중복확인 화면에 접수하기가 없습니다 — 화면 계약이 바뀌었을 수 있습니다." });
    } else if (dupHits > 0) {
      out({ ok: false, error: "DUPLICATE_OR_OWNED", dup, filled, quota,
            message: "도서관이 소장 중이거나 입수과정/중복 신청으로 판정했습니다." });
    } else if (!ARGS.submit) {
      out({ ok: true, staged: true, submitted: false, book: B, filled, quota, blockers,
            dup_clear: true, next: "접수하려면 --submit --reason \"<사유>\" 로 다시 실행하세요." });
    } else {
      await pg.evaluate(() => {
        const el = [...document.querySelectorAll("a,button,input[type=submit],input[type=button]")]
          .find((b) => /접수하기/.test(b.textContent || b.value || ""));
        el.click();
      });
      await sleep(4000);
      await pg.goto(HB_LIST);
      await sleep(2500);
      const after = await hbList(pg);
      const top = after.items[0] || {};
      const ok = after.total === before.total + 1 && hbNorm(top.title) === hbNorm(B.title);
      out({ ok, submitted: ok, error: ok ? undefined : "SUBMIT_UNVERIFIED",
            before_total: before.total, after_total: after.total, top,
            quota_after: hbWeekUsage(after.items), book: B, filled });
    }
  }
  await closeTab(pg);
}
