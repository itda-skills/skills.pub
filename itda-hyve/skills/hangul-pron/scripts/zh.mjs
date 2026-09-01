// 중국어(보통화) → 한글 발음 표기 — 1단계: **병음 입력**
//
// 입력은 한자가 아니라 병음이다 (SPEC-HANGUL-PRON-002 설계). 한자에서 병음을 얻으려면
// 사전이 필요하고 다음자(多音字) 문제가 따라오는데, 그건 2단계다. 병음 입력만으로도
// 3언어 앱 데이터(76건)가 이미 병음 필드를 갖고 있어 **즉시 검증 가능**하다.
//
// 설계의 핵심은 함정 1 — **한글에서 출발하지 않는다.** 성모·운모에서 한글을 만들면서
// 기호를 같이 붙인다. 한글을 먼저 만들고 나중에 기호를 붙이면 `쯔`(zi/zhi)나 `추`(cu/chu)
// 처럼 같은 글자가 서로 다른 기호를 받는 자리에서 원리적으로 실패한다.
//
//   병음 → ① 음절 분리(pinyin.mjs) → ② 성조 변화 C7~C10 → ③ 성모·운모 → 한글 + 기호
//
// 표기 규칙의 정본은 SPEC.md §2-2 (C1~C10). 기호는 중국어 4종:
//   1·2·3·4 = ˉˊˇˋ(성조, TOP) · # = ˘(권설음) · o = ˚(f) · u = ¨(ü)
//
// 사용: node zh.mjs "Wǒmen chī fàn ba."

import { realpathSync as fsRealpath } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { tokenize, applySandhi, respellSentence } from './pinyin.mjs';

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

// ── C1·C2 성모 → 첫소리(+AFTER 기호) ──────────────────────────────
//
// C1 무기음 b·d·g·j·z·zh → 된소리, C2 유기음 p·t·k·q·c·ch → 거센소리.
// 한국어의 평음(ㅂㄷㄱ)은 어중에서 유성음이 돼 중국어 무기음과 어긋난다 — 그래서 된소리다.
// zh·ch·sh·r 은 권설음이라 AFTER 슬롯에 ˘(#) 를 함께 받는다 (C1a).
// ㅉ 3중 배정(j·z·zh)·ㅊ 3중 배정(q·c·ch)은 뒤따르는 운모와 ˘ 로 갈린다 (SPEC 각주).
const INITIALS = {
  b: ['ㅃ'], p: ['ㅍ'], m: ['ㅁ'], f: ['ㅍ', 'o'],          // f 는 ˚ (SPEC 기호표)
  d: ['ㄸ'], t: ['ㅌ'], n: ['ㄴ'], l: ['ㄹ'],
  g: ['ㄲ'], k: ['ㅋ'], h: ['ㅎ'],
  j: ['ㅉ'], q: ['ㅊ'], x: ['ㅅ'],
  zh: ['ㅉ', '#'], ch: ['ㅊ', '#'], sh: ['ㅅ', '#'], r: ['ㄹ', '#'],
  z: ['ㅉ'], c: ['ㅊ'], s: ['ㅆ'],
};
const RETRO = new Set(['zh', 'ch', 'sh', 'r']);
/** C4 — 이 성모 뒤의 i 는 이가 아니라 **으** 다 (chī → 츠, sì → 쓰) */
const I_IS_EU = new Set(['zh', 'ch', 'sh', 'r', 'z', 'c', 's']);

// ── C3·C5·C6·C6a 운모 → 한글 조각 ─────────────────────────────────
//
// 조각은 **첫소리가 비어 있는(ㅇ) 한글 글자의 배열**이다. 뒤에서 성모를 첫 조각에 얹고,
// 필요하면 활음(이·우)을 다음 조각과 합친다. 이렇게 나눠 둬야 `이엔`(미엔)과 `옌`(yan),
// `우안`(추안)과 `완`(꽌)이 한 표에서 갈린다.
//
// C3 n → ㄴ 받침, ng → ㅇ 받침 / C5 e → ㅓ, er → 얼 / C6 ian → 이엔, uo → 워
// C6a 복모음은 소리 나는 대로: ao → 아오, ai → 아이, ei → 에이, ou → 어우, ui → 우에이
const FINALS = {
  a: ['아'], o: ['오'], e: ['어'], i: ['이'], u: ['우'], v: ['위'], er: ['얼'],
  ai: ['아', '이'], ei: ['에', '이'], ao: ['아', '오'], ou: ['어', '우'],
  an: ['안'], en: ['언'], ang: ['앙'], eng: ['엉'], ong: ['옹'],
  ia: ['이', '아'], ie: ['이', '에'], iao: ['이', '아', '오'], iu: ['이', '우'],
  iou: ['이', '어', '우'], ian: ['이', '엔'], iang: ['이', '앙'],
  in: ['인'], ing: ['잉'], iong: ['이', '옹'],
  ua: ['우', '아'], uo: ['우', '어'], uai: ['우', '아', '이'], ui: ['우', '에', '이'],
  uan: ['우', '안'], un: ['운'], uang: ['우', '앙'], ueng: ['우', '엉'],
  ve: ['위', '에'], van: ['위', '엔'], vn: ['윈'],
};
/** ü 계열 운모는 ¨(u) 를 받는다 */
const isV = (final) => final.startsWith('v');

// 활음 합치기 — ㅜ+ㅏ→ㅘ 처럼 한글 겹모음이 있는 경우만.
const COMBINE = {
  'ㅜㅏ': 'ㅘ', 'ㅜㅐ': 'ㅙ', 'ㅜㅓ': 'ㅝ', 'ㅜㅔ': 'ㅞ', 'ㅜㅣ': 'ㅟ',
  'ㅣㅏ': 'ㅑ', 'ㅣㅐ': 'ㅒ', 'ㅣㅓ': 'ㅕ', 'ㅣㅔ': 'ㅖ', 'ㅣㅗ': 'ㅛ', 'ㅣㅜ': 'ㅠ',
};
function combine(a, b) {
  const x = decompose(a), y = decompose(b);
  const j = COMBINE[x.jung + y.jung];
  return j ? compose('ㅇ', j, y.jong) : null;
}

/**
 * 음절 하나 → { unit, code }
 *   unit — 한글 덩어리 (성조가 얹히는 단위. `hǎo` 는 두 글자여도 한 음절이라 통째로 묶는다)
 *   code — 마크업 기호 코드 (성조 1~4 + AFTER 기호. 비어 있으면 맨글자로 적는다)
 */
export function renderSyllable(syl) {
  const [cho, mark] = INITIALS[syl.initial] ?? ['ㅇ', ''];
  let final = syl.final;
  if (final === 'i' && I_IS_EU.has(syl.initial)) final = 'eu';          // C4
  let chunks = final === 'eu' ? ['으'] : FINALS[final];
  if (!chunks) return { unit: syl.raw, code: '', unknown: true };
  chunks = [...chunks];

  // 활음(이·우) 합치기.
  //  · 이-활음은 **성모가 없을 때만** 합친다 — yào 는 야오지만 jiào 는 찌아오다(SPEC C6 예시).
  //  · 우-활음은 권설음 뒤에서만 떼어 둔다 — chuān 추안·shuā 슈아. 그 외는 합친다(guān 꽌).
  //  · ui 는 C6a 가 명시적으로 **우에이** 라 성모가 있으면 합치지 않는다 (duì 뚜에이).
  const glide = chunks[0];
  if (chunks.length > 1) {
    const mergeI = glide === '이' && !syl.initial;
    const mergeU = glide === '우' && (!syl.initial || (!RETRO.has(syl.initial) && final !== 'ui'));
    if (mergeI || mergeU) {
      const m = combine(chunks[0], chunks[1]);
      if (m) chunks.splice(0, 2, m);
    }
  }

  // 성모를 첫 조각에 얹는다. sh + 우 는 `수` 가 아니라 **슈** 다 (shū 슈 · shuā 슈아).
  const head = decompose(chunks[0]);
  const jung = (syl.initial === 'sh' && head.jung === 'ㅜ') ? 'ㅠ' : head.jung;
  chunks[0] = compose(cho, jung, head.jong);

  // C10 얼화 — 앞 음절과 한 덩어리로 합치고 n 은 탈락시킨다 (wánr → 왈)
  if (syl.erhua) {
    const last = decompose(chunks[chunks.length - 1]);
    if (last.jong === ' ' || last.jong === 'ㄴ') chunks[chunks.length - 1] = compose(last.cho, last.jung, 'ㄹ');
    else chunks.push('얼');
  }

  const after = mark || (isV(final) ? 'u' : '');
  return { unit: chunks.join(''), code: (syl.tone ? String(syl.tone) : '') + after };
}

/**
 * 병음 문장 → 마크업 문자열.
 * @param {string} pinyin  성조 부호가 붙은 병음 ("Wǒmen chī fàn ba.")
 * @param {{sandhi?: boolean}} opt  sandhi=false 면 성조 변화(C7~C10)를 적용하지 않는다
 */
export function transcribeZh(pinyin, opt = {}) {
  return render(analyzeZh(pinyin, opt)).markup;
}

/**
 * 분석 결과를 통째로 — 변화 후 병음 줄도 같이 필요할 때 쓴다 (SPEC §2-2 총칙)
 * @param {{sandhi?: boolean, lexical?: boolean, chars?: Map, hanzi?: string}} opt
 *   hanzi    원문 한자. 주면 C8·C9(不·一)를 **정확히** 적용한다 — 음절과 한자를 짝지어
 *            一·不 인 자리만 고르므로 동음자(衣·布)가 걸리지 않는다. **이 방법을 권한다.**
 *   lexical  한자 없이 병음만으로 C8·C9 를 켠다. 동음자를 가릴 수 없어 위험하다.
 */
export function analyzeZh(pinyin, opt = {}) {
  const tokens = tokenize(pinyin);
  if (opt.sandhi === false) return tokens;
  let { lexical, chars } = opt;
  // 한자를 주면 어휘 규칙을 **정확히** 켤 수 있다 — 음절과 한자를 순서대로 짝지어
  // 一·不 인 자리만 고른다. 동음자(衣·布)는 이 방식에서 걸리지 않는다.
  if (opt.hanzi) {
    const han = [...opt.hanzi].filter((c) => c >= '\u4e00' && c <= '\u9fff');
    const syls = tokens.flatMap((t) => (t.kind === 'word' ? t.syls : []));
    if (han.length === syls.length) { chars = new Map(syls.map((sy, i) => [sy, han[i]])); lexical = true; }
  }
  applySandhi(tokens, { lexical, chars });
  return tokens;
}

function render(tokens) {
  let markup = '';
  const unknown = [];
  for (const t of tokens) {
    if (t.kind === 'other') { markup += t.text; continue; }
    if (t.rest) unknown.push(`${t.text} (남은 글자 '${t.rest}')`);
    for (const s of t.syls) {
      const { unit, code, unknown: bad } = renderSyllable(s);
      if (bad) unknown.push(s.raw);
      markup += code ? `{${unit}=${code}}` : unit;
    }
  }
  return { markup, unknown };
}

/** 마크업에서 기호를 떼고 한글만 */
export const plain = (mk) => mk.replace(/\{([^}=]*)=[^}]*\}/g, '$1');

// 심볼릭 링크로 실행되면 argv[1] 과 import.meta.url 이 어긋나므로 양쪽 다 realpath 로 맞춘다.
const isMain = (() => {
  try { return fsRealpath(fileURLToPath(import.meta.url)) === fsRealpath(process.argv[1] ?? ''); }
  catch { return false; }
})();

if (isMain) {
  const args = process.argv.slice(2);
  const noSandhi = args.includes('--no-sandhi');
  const lexical = args.includes('--lexical');      // 不·一 성조 변화 — 동음자 오발화 주의
  const arg = args.filter((a) => !a.startsWith('--')).join(' ');
  if (!arg) {
    console.log('사용: node zh.mjs "Wǒmen chī fàn ba." [--no-sandhi] [--lexical]');
    process.exit(1);
  }
  const tokens = analyzeZh(arg, { sandhi: !noSandhi, lexical });
  const { markup, unknown } = render(tokens);
  const after = respellSentence(tokens);
  if (after.toLowerCase() !== arg.toLowerCase()) console.log(`병음(변화 후) ${after}`);
  console.log(markup);
  if (unknown.length) console.error(`\n[경고] 병음으로 읽지 못한 부분: ${unknown.join(', ')}`);
}
