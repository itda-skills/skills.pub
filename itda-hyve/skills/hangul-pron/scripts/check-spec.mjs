// SPEC 규칙 준수 검사 — 이 스킬의 정본 지표.
//
// **교재 문자열을 그대로 재현하는 것은 목표가 아니다.** 교재는 같은 문장을 다르게 적기도 하고
// (중복 46종 중 17%), 저자 재량의 축약(`last`→라쓸)도 있다. 우리가 따르는 것은 교재의 **표기
// 철학**이다 — SPEC §2-1 의 E1~E8 과 기호 3종.
//
// 그래서 여기서는 "교재와 같은가"가 아니라 "규칙대로인가"를 본다. 각 규칙마다 SPEC 예시와
// 같은 성질의 케이스를 두고, 출력이 그 규칙의 **관찰 가능한 결과**를 갖는지 검사한다.
//
// 사용: node check-spec.mjs [--verbose]

import { transcribe } from './transcribe.mjs';

const V = process.argv.includes('--verbose');
const strip = (s) => s.replace(/\{([^}=]*)=[^}]*\}/g, '$1');

// 검사 항목: [규칙, 입력, 판정함수, 설명]
// 판정은 문자열 일치가 아니라 **규칙의 결과가 나타나는가**로 한다.
const has = (re) => (out) => re.test(out);

// 자모 단위 검사 — '스삩' 처럼 된소리가 받침과 합쳐진 글자를 음절 리터럴로 잡으려 하면
// 검사가 먼저 틀린다(실제로 그렇게 오탐이 났다). 초성·종성을 분해해서 본다.
const CHO = 'ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ';
const JONG = ' ㄱㄲㄳㄴㄵㄶㄷㄹㄺㄻㄼㄽㄾㄿㅀㅁㅂㅄㅅㅆㅇㅈㅊㅋㅌㅍㅎ';
const jamo = (ch) => {
  const o = ch.charCodeAt(0) - 0xac00;
  return (o < 0 || o > 11171) ? null : { cho: CHO[Math.floor(o / 588)], jong: JONG[o % 28] };
};
/** 출력 어딘가에 이 초성이 있는가 */
const onset = (c) => (out) => [...out].some((ch) => jamo(ch)?.cho === c);
/** 출력 어딘가에 이 종성이 있는가 */
const coda = (c) => (out) => [...out].some((ch) => jamo(ch)?.jong === c);
/** 마크업 코드에 이 기호가 있는가 (^o~ 가 겹쳐 붙는 경우 포함) */
const mark = (k) => (out) => [...out.matchAll(/\{[^}=]*=([^}]*)\}/g)].some((m) => m[1].includes(k));
const CASES = [
  // E1 — s 뒤의 p·t·k 는 된소리
  ['E1', 'step',    onset('ㄸ'), 's+t → ㄸ'],
  ['E1', 'spit',    onset('ㅃ'), 's+p → ㅃ'],
  ['E1', 'stairs',  onset('ㄸ'), 's+t → ㄸ'],
  ['E1', 'skip',    onset('ㄲ'), 's+k → ㄲ'],
  ['E1', 'stop',    onset('ㄸ'), 's+t → ㄸ'],

  // E2 — 모음 사이 t·d 는 ㄹ (flap)
  ['E2', 'water',   has(/워[러럴]/), '모음 사이 t → ㄹ'],
  ['E2', 'little',  has(/리[를르]/), '모음 사이 t → ㄹ'],
  ['E2', 'better',  has(/베[러럴]/), '모음 사이 t → ㄹ'],
  ['E2', 'get out', has(/게라|게러/), '단어 경계 넘어 flap'],

  // E3 — 어말 파열음은 받침
  ['E3', 'sit',     coda('ㅌ'), '어말 t → 받침'],
  ['E3', 'hat',     coda('ㅌ'), '어말 t → 받침'],
  ['E3', 'book',    (o) => coda('ㅋ')(o) || coda('ㄱ')(o), '어말 k → 받침'],

  // E4 — 어말 l 은 ㄹ + 을
  ['E4', 'all',     has(/을$/), '어말 l → 을'],
  ['E4', 'still',   has(/을$/), '어말 l → 을'],
  ['E4', 'milk',    has(/을/),  '어중 l → 을'],

  // E5 — 약세 -er/-or/-ar 는 얼ˇ
  ['E5', 'finger',  has(/\{[걸얼]=\^\}/), '-er → 얼ˇ'],
  ['E5', 'doctor',  has(/\{[털얼]=\^\}/), '-or → 얼ˇ'],
  ['E5', 'water',   has(/\{[럴얼]=\^\}/), '-er → 얼ˇ'],

  // E6 — -ing 은 잉
  ['E6', 'eating',  has(/링$|잉$/), '-ing → 잉'],
  ['E6', 'playing', has(/잉$|링$/), '-ing → 잉'],

  // E7 — 강세 없는 모음은 ㅓ 또는 생략
  ['E7', 'about',   has(/^어/),   'schwa → ㅓ'],
  ['E7', 'again',   has(/^어/),   'schwa → ㅓ'],

  // E8 — 굳어진 축약형
  ['E8', "let's",   has(/^레츠$/),        "Let's → 레츠"],
  ['E8', "i'll",    has(/^아[을올]$/),    "I'll → 아을"],
  ['E8', "you're",  has(/^유\{얼=\^\}$/), "You're → 유얼ˇ"],

  // 기호 — 한국어 화자가 약한 소리에 반드시 붙는다
  ['기호', 'right',  mark('^'), 'r → ˇ'],
  ['기호', 'fan',    mark('o'), 'f → ˚'],
  ['기호', 'very',   mark('o'), 'v → ˚'],
  ['기호', 'think',  mark('~'), 'th → ˜'],
  ['기호', 'father', mark('~'), 'th → ˜'],
  ['기호', 'first',  (o) => mark('^')(o) && mark('o')(o), 'r·f 겹침 → 두 기호 모두'],

  // 원리 5 — 연음은 소리 나는 대로 이어 적는다
  ['원리5', 'put it in',   has(/푸[리릴]린|푸리[린맅]/), '연쇄 연음'],
  ['원리5', 'take it out', has(/테이키[라러]/),          '연쇄 연음'],
];

const byRule = new Map();
let pass = 0;
for (const [rule, input, ok, why] of CASES) {
  const out = transcribe(input);
  const good = ok(strip(out)) || ok(out);
  if (good) pass++;
  if (!byRule.has(rule)) byRule.set(rule, [0, 0]);
  const r = byRule.get(rule);
  r[1]++; if (good) r[0]++;
  if (V || !good) console.log(`  ${good ? '✓' : '✗'} [${rule}] ${input.padEnd(12)} → ${out.padEnd(24)} ${why}`);
}

console.log(`\nSPEC 규칙 준수 ${pass}/${CASES.length} (${(pass / CASES.length * 100).toFixed(0)}%)`);
for (const [rule, [a, b]] of byRule) console.log(`  ${rule.padEnd(5)} ${a}/${b}`);
process.exit(pass === CASES.length ? 0 : 1);
