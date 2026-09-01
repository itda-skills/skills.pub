// 원천 데이터 검증 (일본어) — **로마자 필드가 가나와 맞는가.**
//
// 중국어의 `verify-pinyin.mjs` 와 같은 자리다. 다만 일본어는 원문이 **가나**라 읽기
// 모호성이 없어 사전이 필요 없다 — 가나에서 로마자를 기계적으로 만들어 대조하면 끝이다.
// (한자 혼용문이 되면 그때는 형태소 분석이 필요하다. 그것이 2단계다.)
//
// 로마자 표기는 데이터의 방식을 따른다 — **가나에 충실한 워프로식**이다:
// 장음을 ō 가 아니라 모음 반복으로 적고(`もう` mou · `ぎゅー` gyuu · `ページ` peeji),
// 촉음은 뒤 자음을 겹치며(`ちょっと` chotto · `こっち` kocchi), 조사는 읽는 대로 적는다
// (`を` o · `は` wa). 이 방식이라 가나에서 **결정론적으로** 산출된다.
//
// 띄어쓰기는 비교하지 않는다 — 데이터의 로마자 띄어쓰기와 한글 표기의 호흡 단위는
// 서로 다른 기준이고(원리 6), 어느 쪽도 틀린 것이 아니다.
//
// 사용: node verify-romaji.mjs [--data <data.js>] [--verbose]

import { readFileSync } from 'node:fs';
import { tokenize } from './kana.mjs';

const args = process.argv.slice(2);
const V = args.includes('--verbose');
const opt = (name, dflt) => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : dflt; };
const DATA = opt('--data', `${process.env.HOME}/orca/workspaces/website/한글영어/demo-apps/hangul-pron/data.js`);

new Function(readFileSync(DATA, 'utf8'))();
const D = globalThis.HP_DATA;
const rows = [];
for (const sit of D.situations) for (const it of (D.items.ja?.[sit.id] || [])) rows.push({ kana: it[0], roma: it[2], where: `${sit.id} ${it[0]}` });
for (const [sid, lines] of Object.entries(D.dialogs?.ja || {})) for (const ln of lines) rows.push({ kana: ln[1], roma: ln[3], where: `대화-${sid} ${ln[1]}` });

// ── 모라 → 로마자 ─────────────────────────────────────────────────
const CONS = { '': '', k: 'k', s: 's', sh: 'sh', t: 't', ch: 'ch', ts: 'ts', n: 'n', h: 'h',
  f: 'f', m: 'm', y: 'y', r: 'r', w: 'w', g: 'g', z: 'z', j: 'j', d: 'd', b: 'b', p: 'p' };
const VOW = { a: 'a', i: 'i', u: 'u', e: 'e', o: 'o' };
/** 요음 — sh·ch·j 는 반모음을 쓰지 않는다 (sha 지 shya 가 아니다) */
const YOON = { ya: 'a', yu: 'u', yo: 'o' };
const PALATAL = new Set(['sh', 'ch', 'j']);

function romaMora(m) {
  const c = CONS[m.cons] ?? '?';
  if (YOON[m.vowel]) return PALATAL.has(m.cons) ? c + YOON[m.vowel] : `${c}y${YOON[m.vowel]}`;
  return c + (VOW[m.vowel] ?? '?');
}

/** 낱말(모라 열) → 로마자. 촉음은 뒤 자음 겹침, ー 는 앞 모음 반복, ん 은 n */
function romaWord(morae) {
  let out = '';
  for (let i = 0; i < morae.length; i++) {
    const m = morae[i], next = morae[i + 1];
    if (m.moraicN) { out += 'n'; continue; }
    // 장음 — `ー` 는 앞 모음 반복(gyuu·peeji), 모음 연속은 **가나 그대로**(you·oishii).
    // 데이터의 로마자가 가나 충실형이라 이 둘을 갈라야 한다.
    if (m.chouon) { out += m.kana === 'う' ? 'u' : m.kana === 'い' ? 'i' : (out.slice(-1) || ''); continue; }
    // 촉음 — 뒤 자음의 **첫 글자를 겹친다**(kocchi·chotto·issho·ippai). 전통 헵번은
    // っち 를 tchi 로 적지만(itchi), 데이터가 워프로식이라 여기서는 cchi 로 간다.
    if (m.sokuon) {
      const r = next && !next.sokuon && !next.moraicN && !next.chouon ? romaMora(next) : '';
      out += r[0] ?? '';
      continue;
    }
    out += romaMora(m);
  }
  return out;
}

const norm = (s) => (s ?? '').toLowerCase().replace(/[^a-z]/g, '');

const bad = [];
let checked = 0;
for (const r of rows) {
  if (!r.roma) { bad.push([r.where, '(로마자 필드 없음)', '']); continue; }
  const gen = tokenize(r.kana).filter((t) => t.kind === 'word').map((t) => romaWord(t.morae)).join('');
  checked++;
  if (norm(gen) !== norm(r.roma)) bad.push([r.where, gen, r.roma]);
}

console.log(`로마자 대조 — 일본어 ${checked}항목 (가나에서 기계 생성, 띄어쓰기 무시)\n`);
if (!bad.length) console.log('불일치 없음');
for (const [where, gen, act] of (V ? bad : bad.slice(0, 15))) {
  console.log(`  ${where}\n    가나에서 생성 ${gen}\n    데이터        ${act}`);
}
if (!V && bad.length > 15) console.log(`  … 그 외 ${bad.length - 15}건 (--verbose)`);
console.log(`\n총 ${bad.length}건`);
process.exit(bad.length ? 1 : 0);
