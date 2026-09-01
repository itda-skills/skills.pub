// 일본어 → 한글 발음 표기 — 1단계: **가나 입력**
//
// 입력은 한자 섞인 문장이 아니라 가나다 (SPEC-HANGUL-PRON-002 설계). 한자 혼용문에서
// 요미(읽기)를 얻으려면 형태소 분석이 필요하고, 그건 2단계다. 가나만으로도 3언어 앱
// 데이터 76건이 이미 가나 원문을 갖고 있어 즉시 검증 가능하다.
//
// 중국어와 같은 골격이고 **소리를 얻는 경로만 다르다.**
//
//   가나 → ① 모라 분리·장음 판정(kana.mjs) → ② 위치 규칙(J1·J7) → ③ 한글 + 기호
//
// 표기 규칙의 정본은 SPEC.md §2-3 (J1~J7). 기호는 일본어 3종:
//   v = ˚(탁음, AFTER) · ー(장음, 본문) · ㅅ받침(촉음, 본문)
//
// 사용: node ja.mjs "ごはんを たべよう。"

import { realpathSync as fsRealpath } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { tokenize } from './kana.mjs';

// ── 한글 자모 합성 ────────────────────────────────────────────────
const CHO = 'ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ';
const JUNG = 'ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ';
const JONG = ' ㄱㄲㄳㄴㄵㄶㄷㄹㄺㄻㄼㄽㄾㄿㅀㅁㅂㅄㅅㅆㅇㅈㅊㅋㅌㅍㅎ';
const compose = (cho, jung, jong = ' ') =>
  String.fromCharCode(0xac00 + (CHO.indexOf(cho) * 21 + JUNG.indexOf(jung)) * 28 + JONG.indexOf(jong));
const decompose = (ch) => {
  const o = ch.charCodeAt(0) - 0xac00;
  if (o < 0 || o > 11171) return null;
  return { cho: CHO[Math.floor(o / 588)], jung: JUNG[Math.floor((o % 588) / 28)], jong: JONG[o % 28] };
};

// ── 첫소리 (J1·J2·J7) ─────────────────────────────────────────────
//
// J1 — 어두 か·た행은 ㅋ·ㅌ, 어중은 ㄲ·ㄸ. 소리 재현이 우선이다(어중 무성 파열음은
//      한국어 귀에 된소리로 들린다). **단 촉음 받침 뒤에는 적용하지 않는다**(촛토·밧테).
//
//      촉음 뒤 예외의 진짜 경계는 **앞 받침이 무엇이냐**다. ㄱ·ㅂ 받침 뒤에서는 한국어가
//      저절로 경음화하므로 된소리로 적는 것이 소리와 맞고(육꾸리·입빠이), ㅅ받침 뒤에서는
//      거센소리가 그대로 난다(촛토·맛테). SPEC 의 예외 예시 두 개가 모두 ㅅ받침이다.
//
// J2 — 탁음(が·ざ·だ·ば행)은 **청음 한글 + ˚**. ぱ행은 반탁음이라 기호가 없다.
//
//      ぱ행도 か·た행과 같이 어중에서 된소리로 적는다. SPEC J1 은 か·た행만 말하지만
//      J3·J7 예시가 さんぽ 삼뽀 · いっぱい 입빠이 로 ㅃ 를 쓴다 — 같은 무기 파열음이니
//      같이 가는 것이 맞다.
const ONSET = {
  '': ['ㅇ'], k: ['ㅋ', 'ㄲ'], s: ['ㅅ'], sh: ['ㅅ'], t: ['ㅌ', 'ㄸ'], ch: ['ㅊ'], ts: ['ㅊ'],
  n: ['ㄴ'], h: ['ㅎ'], f: ['ㅎ'], m: ['ㅁ'], y: ['ㅇ'], r: ['ㄹ'], w: ['ㅇ'],
  g: ['ㄱ', null, 'v'], z: ['ㅈ', null, 'v'], j: ['ㅈ', null, 'v'],
  d: ['ㄷ', null, 'v'], b: ['ㅂ', null, 'v'], p: ['ㅍ', 'ㅃ'],
};
/** 촉음(ㄱ·ㅂ 받침) 뒤의 경음화 — 어중 규칙이 아니라 **한국어 음운**이다 */
const TENSE_AFTER_STOP = { k: 'ㄲ', t: 'ㅌ', p: 'ㅃ', s: 'ㅅ', sh: 'ㅅ', ch: 'ㅊ', ts: 'ㅊ' };

// ── 가운뎃소리 ────────────────────────────────────────────────────
// す·ず·つ 는 수·주·투가 아니라 **스·즈·츠** 다. 한국어에 그 자리 모음이 없어서
// ㅜ 로 적으면 다른 소리가 된다.
const VOWEL = { a: 'ㅏ', i: 'ㅣ', u: 'ㅜ', e: 'ㅔ', o: 'ㅗ', ya: 'ㅑ', yu: 'ㅠ', yo: 'ㅛ' };
const EU = new Set(['s', 'z', 'ts']);                     // 이 자음 뒤의 u 는 ㅡ
const W_JUNG = { a: 'ㅘ', i: 'ㅟ', e: 'ㅞ', o: 'ㅗ' };     // わ 와 · を(조사) 오
const Y_JUNG = { a: 'ㅑ', u: 'ㅠ', o: 'ㅛ' };              // や 야 · ゆ 유 · よ 요
// ㅈ·ㅊ 뒤에는 반모음을 적지 않는다 — 한국어에서 자/쟈, 초/쵸가 같은 소리라 적을 이유가 없다
// (외래어 표기법의 원칙이기도 하다). じょうず 조ー즈 · ちょっと 촛토.
const NO_GLIDE = { ya: 'a', yu: 'u', yo: 'o' };

// ── 받침 (J3·J7) ──────────────────────────────────────────────────
/** J3 — ん 은 **뒤 자음에 맞춘** 받침. 어말은 ㅇ (고항·지깡·홍·웅) */
function nCoda(next) {
  const c = next?.cons;
  if (!next || next.chouon) return 'ㅇ';
  if (['p', 'b', 'm'].includes(c)) return 'ㅁ';                       // さんぽ 삼뽀
  if (['t', 'd', 'n', 'r', 's', 'z', 'sh', 'ch', 'ts', 'j'].includes(c)) return 'ㄴ';  // ごめんね 고멘 네
  return 'ㅇ';                                                        // か·が행·모음·어말
}
/** J7 — 촉음 받침은 뒤 자음에 동화: か행 앞 ㄱ, ぱ행 앞 ㅂ, 그 외 ㅅ */
function sokuonCoda(next) {
  if (next?.cons === 'k') return 'ㄱ';
  if (next?.cons === 'p') return 'ㅂ';
  return 'ㅅ';
}

/**
 * 모라 하나 → { unit, code }
 * @param pos 'first' 어두 · 'mid' 어중 · 'sokuon' 촉음 뒤
 *   촉음 뒤는 어중이 아니라 **따로 갈린다** — ㅅ받침 뒤면 어두형(촛토·맛테),
 *   ㄱ·ㅂ받침 뒤면 된소리(육꾸리·입빠이). J1 예외와 한국어 경음화가 만나는 자리다.
 */
function renderMora(m, pos) {
  const spec = ONSET[m.cons];
  if (!spec) return null;
  const cho = pos === 'tense' ? (TENSE_AFTER_STOP[m.cons] ?? spec[0])
    : pos === 'mid' ? (spec[1] ?? spec[0])
    : spec[0];
  const vowel = (m.cons === 'j' || m.cons === 'ch') ? (NO_GLIDE[m.vowel] ?? m.vowel) : m.vowel;
  const jung = m.cons === 'w' ? (W_JUNG[vowel] ?? 'ㅗ')
    : m.cons === 'y' ? (Y_JUNG[vowel] ?? VOWEL[vowel])
    : (EU.has(m.cons) && vowel === 'u') ? 'ㅡ'
    : VOWEL[vowel];
  if (!jung) return null;
  return { unit: compose(cho, jung), code: spec[2] ?? '' };
}

/** 한 낱말(모라 열) → 마크업 조각 */
function renderWord(morae) {
  const out = [];                       // {unit, code} — unit 은 한글 한 글자 또는 'ー'
  const bad = [];
  let pos = 'first';
  for (let i = 0; i < morae.length; i++) {
    const m = morae[i], next = morae[i + 1];
    if (m.chouon) { out.push({ unit: 'ー', code: '' }); pos = 'mid'; continue; }
    if (m.sokuon || m.moraicN) {
      const coda = m.sokuon ? sokuonCoda(next) : nCoda(next);
      const prev = out[out.length - 1];
      const d = prev && decompose(prev.unit);
      if (!d || d.jong !== ' ') { bad.push(m.sokuon ? 'っ' : 'ん'); continue; }
      prev.unit = compose(d.cho, d.jung, coda);
      // ㅅ받침 뒤는 어두형(J1 예외), ㄱ·ㅂ받침 뒤는 된소리(한국어 경음화)
      if (m.sokuon) pos = coda === 'ㅅ' ? 'first' : 'tense';
      continue;
    }
    const r = renderMora(m, pos);
    if (!r) { bad.push(m.kana ?? '?'); continue; }
    out.push(r);
    pos = 'mid';
  }
  // 이웃한 무기호 글자는 묶어서 적는다 — `{고=v}항` 처럼 기호 있는 글자만 중괄호로 감싼다
  let markup = '';
  for (const o of out) markup += o.code ? `{${o.unit}=${o.code}}` : o.unit;
  return { markup, bad };
}

/** 가나 문장 → 마크업 문자열 */
export function transcribeJa(kana) {
  return render(tokenize(kana)).markup;
}

function render(tokens) {
  let markup = '';
  const unknown = [];
  for (const t of tokens) {
    if (t.kind === 'other') { markup += t.text; continue; }
    if (t.rest) unknown.push(`${t.text} (읽지 못한 글자 '${t.rest}')`);
    const { markup: mk, bad } = renderWord(t.morae);
    if (bad.length) unknown.push(`${t.text} (붙일 자리가 없는 ${bad.join('·')})`);
    markup += mk;
  }
  return { markup, unknown };
}

/** 마크업에서 기호를 떼고 한글만 */
export const plain = (mk) => mk.replace(/\{([^}=]*)=[^}]*\}/g, '$1');

const isMain = (() => {
  try { return fsRealpath(fileURLToPath(import.meta.url)) === fsRealpath(process.argv[1] ?? ''); }
  catch { return false; }
})();

if (isMain) {
  const arg = process.argv.slice(2).filter((a) => !a.startsWith('--')).join(' ');
  if (!arg) { console.log('사용: node ja.mjs "ごはんを たべよう。"'); process.exit(1); }
  const { markup, unknown } = render(tokenize(arg));
  console.log(markup);
  if (unknown.length) console.error(`\n[경고] 읽지 못한 부분: ${unknown.join(', ')}`);
}
