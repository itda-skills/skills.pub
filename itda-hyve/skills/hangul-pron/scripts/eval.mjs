// transcribe.mjs 를 외부 코퍼스로 평가한다.
//
// 코퍼스는 이 저장소에 두지 않는다 — 이 모노레포는 skills.pub 으로 공개 발행되는데,
// 평가에 쓰는 자료가 시중 교재의 전사본이라 함께 공개할 수 없다. 그래서 경로를 인자로 받는다.
//
// 코퍼스 형식은 둘 중 하나다.
//   ① book-data.js 형태 — `globalThis.HP_BOOK.chapters[].sections[].items[]`,
//      항목은 `[뜻, 영어 원문, 발음 마크업, ...]`
//   ② JSON 배열 — `[{ "src": "Let's go.", "pron": "레츠 고우" }, ...]`
//
// 기준선은 "정답"이 아니다. 교재는 같은 문장을 다르게 적기도 하므로(측정: 중복 46종 중 17%)
// 완전 일치 100% 는 도달 불가능하다. 그래서 네 층으로 나눠 어디까지 규칙이 닿는지 본다.
//
// 사용: node eval.mjs <코퍼스경로> [--fail 20]

import fs from 'node:fs';
import path from 'node:path';
import { transcribe } from './transcribe.mjs';

const args = process.argv.slice(2);
const corpusPath = args.find((a) => !a.startsWith('--'));
if (!corpusPath) {
  console.error('사용: node eval.mjs <코퍼스경로(book-data.js 또는 .json)> [--fail 20]');
  process.exit(2);
}
const failN = args.includes('--fail')
  ? Number(args[args.indexOf('--fail') + 1]) || 20 : 0;

// ── 코퍼스 적재 ───────────────────────────────────────────────────
const raw = fs.readFileSync(corpusPath, 'utf8');
let items = [];
if (path.extname(corpusPath) === '.json') {
  items = JSON.parse(raw).map((o) => [o.src, o.pron]);
} else {
  new Function(raw)(); // book-data.js 는 globalThis 에 HP_BOOK 을 심는다
  const B = globalThis.HP_BOOK;
  if (!B) { console.error('HP_BOOK 을 찾지 못했다 — 코퍼스 형식을 확인하라.'); process.exit(2); }
  for (const c of B.chapters) for (const s of c.sections) for (const it of s.items) items.push([it[1], it[2]]);
}
if (!items.length) { console.error('코퍼스가 비었다.'); process.exit(2); }

// ── 지표 ──────────────────────────────────────────────────────────
const plain = (s) => s.replace(/\{([^}=]*)=[^}]*\}/g, '$1');
// 구두점·공백은 무시한다 — 교재도 같은 문장에 마침표를 붙였다 뗐다 한다
const bare = (s) => plain(s).replace(/[\s.,!?()]/g, '');
const marks = (s) => {
  const c = { '^': 0, o: 0, '~': 0 };
  for (const m of s.matchAll(/\{[^}=]*=([^}]*)\}/g)) for (const k of m[1]) if (k in c) c[k]++;
  return c;
};
const dice = (a, b) => {
  const pool = [...b];
  let hit = 0;
  for (const ch of a) { const i = pool.indexOf(ch); if (i >= 0) { pool.splice(i, 1); hit++; } }
  return (2 * hit) / Math.max(1, a.length + b.length);
};
const syls = (s) => [...plain(s).replace(/[^가-힣]/g, '')];

// 기호 재현율 — 이 스킬의 주 지표.
// 한국인이 약한 소리(R·F/V·Th)에 기호가 실제로 붙었는가를 본다. 영어 철자에서 기대되는
// 개수를 분모로 삼는다. 교재는 기호를 빠뜨리기도 하므로(측정: 50문장) 교재 기준선보다
// 높게 나오는 것이 정상이며, 그것이 이 스킬이 노리는 바다.
const expected = (src) => {
  // 겹자는 한 소리다 — off 는 ff 지만 ˚ 하나, carrot 은 rr 이지만 ˇ 하나다(교재로 확인).
  // 접지 않으면 분모가 부풀어 재현율이 실제보다 낮게 나온다.
  const w = src.toLowerCase().replace(/[’']/g, '')
    .replace(/rr/g, 'r').replace(/ff/g, 'f').replace(/vv/g, 'v');
  return { '^': (w.match(/r/g) || []).length,
           o: (w.match(/ph|[fv]/g) || []).length,
           '~': (w.match(/th/g) || []).length };
};

let exact = 0, korOnly = 0, markOk = 0, simSum = 0;
const recall = { '^': [0, 0], o: [0, 0], '~': [0, 0] };   // [붙은 수, 기대 수]
const goldRecall = { '^': [0, 0], o: [0, 0], '~': [0, 0] };
const fails = [];
for (const [src, gold] of items) {
  const got = transcribe(src);
  const k = bare(got) === bare(gold);
  const g = marks(got), h = marks(gold);
  const sim = dice(syls(got), syls(gold));
  if (got === gold) exact++;
  if (k) korOnly++;
  if (g['^'] === h['^'] && g.o === h.o && g['~'] === h['~']) markOk++;
  simSum += sim;
  const need = expected(src);
  for (const key of ['^', 'o', '~']) {
    recall[key][0] += Math.min(g[key], need[key]); recall[key][1] += need[key];
    goldRecall[key][0] += Math.min(h[key], need[key]); goldRecall[key][1] += need[key];
  }
  if (!k && fails.length < failN) fails.push({ src, gold, got, sim });
}

const pct = (n) => `${n} (${(n / items.length * 100).toFixed(1)}%)`;
const rate = ([a, b]) => b ? `${(a / b * 100).toFixed(1)}%` : '—';
console.log(`평가 ${items.length}건 — 기준선 ${path.basename(corpusPath)}\n`);
console.log('■ 기호 재현율 (주 지표) — 한국인이 약한 소리에 기호가 붙었는가');
console.log(`   R  ˇ   출력 ${rate(recall['^'])}   기준선 ${rate(goldRecall['^'])}   (기대 ${recall['^'][1]}개)`);
console.log(`   F·V ˚  출력 ${rate(recall.o)}   기준선 ${rate(goldRecall.o)}   (기대 ${recall.o[1]}개)`);
console.log(`   Th ˜   출력 ${rate(recall['~'])}   기준선 ${rate(goldRecall['~'])}   (기대 ${recall['~'][1]}개)`);
console.log('\n■ 교재 대비 일치도 (참고 — 교재 자체가 일관되지 않아 100% 도달 불가)');
console.log(`  1. 완전 일치        ${pct(exact)}`);
console.log(`  2. 한글만 일치      ${pct(korOnly)}   ← 표기 규칙 정확도`);
console.log(`  3. 기호 개수 일치   ${pct(markOk)}   ← 기호 층 정확도`);
console.log(`  4. 음절 유사도 평균 ${(simSum / items.length * 100).toFixed(1)}%`);

if (fails.length) {
  console.log(`\n■ 틀린 예 ${fails.length}건 (유사도 낮은 순)`);
  fails.sort((a, b) => a.sim - b.sim).forEach((f) => {
    console.log(`  ${f.src}\n     기준: ${f.gold}\n     출력: ${f.got}   (유사도 ${(f.sim * 100).toFixed(0)}%)`);
  });
}
