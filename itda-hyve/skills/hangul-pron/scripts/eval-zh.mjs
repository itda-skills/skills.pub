// 참고 지표 — 3언어 앱 데이터(data.js)의 중국어 표기와 문자열 대조.
//
// **일치율이 목표가 아니다** (함정 2). 앱 데이터도 사람이 손으로 적은 것이라 저자 재량이
// 섞여 있다 (`piàoliang` → 량 인데 `xiǎng` → 시앙 처럼 같은 iang 이 갈린다). 정본 지표는
// check-spec-zh.mjs 의 규칙 준수이고, 여기는 **회귀 감시용**이다.
//
// 사용: node eval-zh.mjs [data.js 경로] [--verbose]

import { readFileSync } from 'node:fs';
import { transcribeZh } from './zh.mjs';

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
  console.error('경로를 인자로 넘겨라: node eval-zh.mjs <data.js 경로>');
  process.exit(2);
}

const rows = [];
for (const sit of D.situations) for (const it of (D.items.zh?.[sit.id] || [])) rows.push([it[2], it[3]]);
for (const lines of Object.values(D.dialogs?.zh || {})) for (const ln of lines) rows.push([ln[3], ln[4]]);

let hit = 0;
const misses = [];
for (const [pinyin, gold] of rows) {
  const out = transcribeZh(pinyin);
  if (out === gold) hit++;
  else misses.push([pinyin, gold, out]);
}

// 음절 단위로도 본다 — 문장 하나가 한 음절 때문에 통째로 틀린 것과 여러 군데가 틀린 것은 다르다.
const units = (mk) => [...mk.matchAll(/\{([^}=]*)=([^}]*)\}|([가-힣]+)/g)]
  .map((m) => (m[3] ? m[3] : `${m[1]}=${m[2]}`));
let uHit = 0, uAll = 0;
for (const [pinyin, gold] of rows) {
  const a = units(gold), b = units(transcribeZh(pinyin));
  uAll += a.length;
  for (let i = 0; i < a.length; i++) if (a[i] === b[i]) uHit++;
}

console.log(`문장 일치 ${hit}/${rows.length} (${(hit / rows.length * 100).toFixed(1)}%)`);
console.log(`덩어리 일치 ${uHit}/${uAll} (${(uHit / uAll * 100).toFixed(1)}%)`);
if (misses.length) {
  console.log(`\n불일치 ${misses.length}건${V ? '' : ' (앞 15건 · --verbose 로 전량)'}`);
  for (const [p, g, o] of (V ? misses : misses.slice(0, 15))) {
    console.log(`  ${p}\n    교재 ${g}\n    출력 ${o}`);
  }
}
