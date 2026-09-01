// 공통 프렐류드 — 모든 명령 JS 앞에 붙는다.
// ARGS 는 ulib.sh 가 __ARGS_JSON__ 자리에 주입한다.
const ARGS = __ARGS_JSON__;
const ORIGIN = "https://www.u-library.kr"; // ⚠️ www 필수 — 없으면 세션이 안 붙는다(실측 2026-08-21)

const out = (obj) => console.log("<<<ULIB_JSON>>>" + JSON.stringify(obj) + "<<<END>>>");

async function openLoggedIn(pathname) {
  const pg = await openTab(ORIGIN + pathname);
  await sleep(800);
  let title = await pg.title();
  if (/로그인/.test(title)) {
    if (!ARGS.id || !ARGS.pw) { out({ ok: false, error: "NEED_LOGIN" }); await closeTab(pg); return null; }
    await pg.fill('form[name=login] input[name=id]', ARGS.id);
    await pg.fill('form[name=login] input[name=password]', ARGS.pw);
    await pg.click('button.loginBtn');
    await sleep(2500);
    // 비밀번호 만료 인터스티셜은 무시하고 목표 경로로 직행한다(세션은 이미 유효).
    await pg.goto(ORIGIN + pathname);
    await sleep(1200);
    title = await pg.title();
    if (/로그인/.test(title)) { out({ ok: false, error: "LOGIN_FAILED", title }); await closeTab(pg); return null; }
  }
  return pg;
}

function parseLoanRows(rows) {
  return rows.map((r) => ({
    loan_no: r.cb,
    title: r.cells[2], author: r.cells[3], location: r.cells[4],
    reg_no: r.cells[5], loaned_at: r.cells[6], due_at: r.cells[7],
    renew_count: Number(r.cells[8] || 0),
  }));
}

// ── 한밭도서관 희망도서 (별개 사이트·같은 계정) ────────────────────────────
// ⚠️ u-library 와 origin·세션이 다르다. 로그인 폼 필드명이 name/cardNo 다(실측 2026-08-22).
const HB = "https://www.daejeon.go.kr";
const HB_LIST = HB + "/hanbatlibrary/wishBook/myList.do?menuSeq=6228";
const HB_WRITE = HB + "/hanbatlibrary/wishBook/write.do?menuSeq=6228";
const HB_WEEK_LIMIT = 2; // 안내: 1주일 1인 2권

const hbNeedLogin = (pg) => pg.evaluate(() => !!document.querySelector('input[name="cardNo"]'));

async function hbDoLogin(pg) {
  if (!ARGS.id || !ARGS.pw) return "NEED_LOGIN";
  await pg.fill('input[name="name"]', ARGS.id);
  await pg.fill('input[name="cardNo"]', ARGS.pw);
  await pg.evaluate(() => document.querySelector('form[action*="cardLogin"]').submit());
  await sleep(3000);
  return (await hbNeedLogin(pg)) ? "LOGIN_FAILED" : null;
}

async function openHanbat() {
  const pg = await openTab(HB_LIST);
  await sleep(1500);
  if (await hbNeedLogin(pg)) {
    const err = await hbDoLogin(pg);
    if (err) { out({ ok: false, error: err }); await closeTab(pg); return null; }
  }
  return pg;
}

// write.do 는 세션이 살아 있어도 안내 페이지로 리다이렉트될 수 있다 — 실측 2026-08-22:
// 주간 한도(2권)를 채우면 서버가 신청 화면 진입 자체를 막는다(버튼 경로도 동일).
// 그러니 여기서 실패했다고 로그아웃·재로그인 같은 처방을 하지 않는다. 원인은 호출자가 판정한다.
async function hbOpenWriteForm(pg) {
  for (let attempt = 0; attempt < 2; attempt++) {
    await pg.goto(HB_WRITE);
    if (await hbWaitFor(pg, "#wishForm #title", 10)) return true;
    if (await hbNeedLogin(pg)) { if (await hbDoLogin(pg)) return false; }
  }
  return false;
}

// 신청목록 스냅샷. 목록은 신청일 내림차순이라 주간 집계는 1페이지로 충분하다.
async function hbList(pg) {
  return pg.evaluate(() => {
    const total = Number(((document.body.innerText.match(/총\s*([\d,]+)\s*건/) || [])[1] || "0").replace(/,/g, ""));
    const items = [...document.querySelectorAll("table tbody tr")].map((tr) => {
      const c = [...tr.cells].map((x) => x.innerText.trim().replace(/\s+/g, " "));
      const o = c.length >= 8 ? 1 : 0; // 선두 빈 셀(체크박스 열) 보정
      return { no: c[o], title: c[o + 1], author: c[o + 2], location: c[o + 3],
               applied_at: c[o + 4], status: c[o + 5], reason: c[o + 6] || "" };
    }).filter((r) => r.title && r.title !== "결과가 없습니다.");
    return { total, items };
  });
}

const hbNorm = (s) => String(s || "").replace(/[\s()·:,\-]/g, "").toLowerCase();

// 주간 한도는 사이트가 최종 판정한다. 여기 계산은 '오늘 포함 7일' 가정이며
// 달력주 기준일 수 있어 --ignore-quota 로 넘길 수 있게 둔다.
function hbWeekUsage(items) {
  const d0 = new Date(); d0.setHours(0, 0, 0, 0);
  const from = new Date(d0.getTime() - 6 * 86400000);
  const fmt = (d) => d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
  const used = items.filter((i) => {
    const m = String(i.applied_at || "").match(/(\d{4})-(\d{2})-(\d{2})/);
    if (!m) return false;
    const d = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
    return d >= from && d <= d0;
  });
  return { window: fmt(from) + " ~ " + fmt(d0), limit: HB_WEEK_LIMIT, used: used.length,
           remaining: Math.max(0, HB_WEEK_LIMIT - used.length),
           items: used.map((i) => ({ title: i.title, applied_at: i.applied_at, status: i.status })) };
}

// 조건 대기 — 고정 sleep 은 SPA·느린 렌더에서 조용히 어긋난다(#실측 2026-08-22 write.do #title 미발견).
async function hbWaitFor(pg, sel, tries) {
  for (let i = 0; i < (tries || 12); i++) {
    if (await pg.evaluate((s) => !!document.querySelector(s), sel)) return true;
    await sleep(700);
  }
  return false;
}
