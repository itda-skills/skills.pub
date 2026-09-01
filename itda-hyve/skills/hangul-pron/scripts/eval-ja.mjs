// 참고 지표 — 3언어 앱 데이터(data.js)의 일본어 표기와 문자열 대조.
//
// **일치율이 목표가 아니다** (함정 2). 정본 지표는 check-spec-ja.mjs 의 규칙 준수이고,
// 여기는 회귀 감시용이다. 앱 데이터도 사람이 손으로 적은 것이라 같은 자리에서 갈린다
// (같은 어말 た 가 `みつけた` 는 따, `できました` 는 타).
//
// 사용: node eval-ja.mjs [data.js 경로] [--verbose]

import { readFileSync } from 'node:fs';
import { transcribeJa } from './ja.mjs';

const args = process.argv.slice(2);
const V = args.includes('--verbose');
const path = args.find((a) => !a.startsWith('--'))
  ?? `${process.env.HOME}/orca/workspaces/website/한글영어/demo-apps/hangul-pron/data.js`;

let D;
try {
  new Function(readFileSync(path, 'utf8'))();
  D = globalThis.HP_DATA;
} catch (e) {
  console.error(`데이터를 읽지 못했다: ${path}\n  ${e.message}`);
  process.exit(2);
}

const rows = [];
for (const sit of D.situations) for (const it of (D.items.ja?.[sit.id] || [])) rows.push([it[0], it[3]]);
for (const lines of Object.values(D.dialogs?.ja || {})) for (const ln of lines) rows.push([ln[1], ln[4]]);

let hit = 0;
const misses = [];
for (const [kana, gold] of rows) {
  const out = transcribeJa(kana);
  if (out === gold) hit++; else misses.push([kana, gold, out]);
}

// 글자 단위로도 본다 — 문장 하나가 한 글자 때문에 통째로 틀린 것과 여러 군데가 틀린 것은 다르다.
const units = (mk) => [...mk.matchAll(/\{([^}=]*)=([^}]*)\}|([^\s{}])/g)]
  .map((m) => (m[3] ? m[3] : `${m[1]}=${m[2]}`));
let uHit = 0, uAll = 0;
for (const [kana, gold] of rows) {
  const a = units(gold), b = units(transcribeJa(kana));
  uAll += a.length;
  for (let i = 0; i < a.length; i++) if (a[i] === b[i]) uHit++;
}

console.log(`문장 일치 ${hit}/${rows.length} (${(hit / rows.length * 100).toFixed(1)}%)`);
console.log(`글자 일치 ${uHit}/${uAll} (${(uHit / uAll * 100).toFixed(1)}%)`);
if (misses.length) {
  console.log(`\n불일치 ${misses.length}건${V ? '' : ' (앞 20건 · --verbose 로 전량)'}`);
  for (const [k, g, o] of (V ? misses : misses.slice(0, 20))) {
    console.log(`  ${k}\n    교재 ${g}\n    출력 ${o}`);
  }
}
