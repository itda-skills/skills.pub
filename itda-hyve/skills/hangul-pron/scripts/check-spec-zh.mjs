// SPEC 규칙 준수 검사 (중국어) — 이 스킬 중국어 파트의 정본 지표.
//
// 영어 쪽(check-spec.mjs)과 같은 원칙이다: **문자열 일치가 아니라 규칙의 관찰 가능한 결과**를
// 본다. 다만 SPEC §2-2 는 C1~C10 예시를 마크업 완전 표기로 적어 두었으므로, 그 예시들은
// 규칙 자체의 정의에 해당해 exact 로 잡아도 브리틀하지 않다. 반대로 C1·C2·C4 처럼 규칙이
// **자모 하나**를 말하는 것은 자모 단위로 본다 — 음절 리터럴로 잡으면 받침과 합쳐진 글자에서
// 검사가 먼저 틀린다(영어 쪽에서 실제로 오탐 3건이 났다).
//
// 사용: node check-spec-zh.mjs [--verbose]

import { transcribeZh } from './zh.mjs';
import { tokenize, applySandhi, respellSentence } from './pinyin.mjs';

const V = process.argv.includes('--verbose');
const strip = (s) => s.replace(/\{([^}=]*)=[^}]*\}/g, '$1');

const CHO = 'ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ';
const JONG = ' ㄱㄲㄳㄴㄵㄶㄷㄹㄺㄻㄼㄽㄾㄿㅀㅁㅂㅄㅅㅆㅇㅈㅊㅋㅌㅍㅎ';
const jamo = (ch) => {
  const o = ch.charCodeAt(0) - 0xac00;
  return (o < 0 || o > 11171) ? null : { cho: CHO[Math.floor(o / 588)], jong: JONG[o % 28] };
};
/** 마크업 그대로 같은가 (SPEC 예시 검증용) */
const eq = (s) => (out) => out === s;
/** eq 와 같되 어휘 성조 변화(C8·C9)를 켜고 돌린다 */
const eqL = (s) => Object.assign((out) => out === s, { lexical: true });
/** eq 와 같되 한자를 주고 돌린다 — 一·不 만 정확히 골라 적용된다 */
const eqH = (hanzi, s) => Object.assign((out) => out === s, { hanzi });
/** 첫소리가 이 자모인가 — 규칙이 자모를 말할 때 */
const onset = (c) => (out) => [...strip(out)].some((ch) => jamo(ch)?.cho === c);
/** 종성이 이 자모인가 */
const coda = (c) => (out) => [...strip(out)].some((ch) => jamo(ch)?.jong === c);
/** 마크업 코드에 이 기호가 있는가 */
const mark = (k) => (out) => [...out.matchAll(/\{[^}=]*=([^}]*)\}/g)].some((m) => m[1].includes(k));
const and = (...fs) => (out) => fs.every((f) => f(out));

// 검사 항목: [규칙, 병음, 판정, 설명]  — 예시는 SPEC §2-2 표에서 그대로 가져왔다.
const CASES = [
  // C1 — 무기음 b·d·g·j·z·zh 는 된소리. 한국어 평음은 어중에서 유성음이 돼 어긋난다.
  ['C1', 'ba',    eq('빠'),           'b → ㅃ'],
  ['C1', 'zǒu',   eq('{쩌우=3}'),     'z → ㅉ'],
  ['C1', 'jiù',   eq('{찌우=4}'),     'j → ㅉ'],
  ['C1', 'dēng',  onset('ㄸ'),        'd → ㄸ'],
  ['C1', 'gāi',   onset('ㄲ'),        'g → ㄲ'],
  ['C1', 'ge',    onset('ㄲ'),        '경성도 C1 대상 (一个 yí ge → 꺼)'],

  // C1a — zh 는 무기음 + 권설음이라 ㅉ 와 ˘ 를 함께 받는다 (슬롯이 다르므로 충돌 없음)
  ['C1a', 'zhè',   eq('{쩌=4#}'),     'zh → ㅉ + ˘'],
  ['C1a', 'zhōng', eq('{쫑=1#}'),     'zh → ㅉ + ˘'],

  // C2 — 유기음 p·t·k·q·c·ch 는 거센소리. ch 는 권설음이라 ˘ 를 더 받는다.
  ['C2', 'chī',   eq('{츠=1#}'),      'ch → ㅊ + ˘'],
  ['C2', 'pǎo',   eq('{파오=3}'),     'p → ㅍ'],
  ['C2', 'kàn',   onset('ㅋ'),        'k → ㅋ'],
  ['C2', 'qǐng',  onset('ㅊ'),        'q → ㅊ'],

  // C3 — n 받침은 ㄴ, ng 받침은 ㅇ
  ['C3', 'fàn',   and(eq('{판=4o}'), coda('ㄴ')), 'n → ㄴ 받침'],
  ['C3', 'máng',  and(eq('{망=2}'),  coda('ㅇ')), 'ng → ㅇ 받침'],

  // C4 — zh·ch·sh·r·z·c·s 뒤의 i 는 이가 아니라 으
  ['C4', 'sì',    eq('{쓰=4}'),       's + i → 으'],
  ['C4', 'shí',   eq('{스=2#}'),      'sh + i → 으'],
  ['C4', 'bù',    eq('{뿌=4}'),       '그 외 자음 뒤 u 는 우 그대로'],

  // C5 — e → ㅓ, er → 얼
  ['C5', 'hē',    eq('{허=1}'),       'e → ㅓ'],
  ['C5', 'èr',    eq('{얼=4}'),       'er → 얼'],

  // C6 — ian → 이엔, uo → 워
  ['C6', 'tiān',  eq('{티엔=1}'),     'ian → 이엔'],
  ['C6', 'wǒ',    eq('{워=3}'),       'uo → 워'],
  ['C6', 'liàng', eq('{리앙=4}'),     'iang → 이앙'],

  // C6a — 복모음은 소리 나는 대로 이어 적는다
  ['C6a', 'hǎo',  eq('{하오=3}'),     'ao → 아오'],
  ['C6a', 'tài',  eq('{타이=4}'),     'ai → 아이'],
  ['C6a', 'zǒu',  eq('{쩌우=3}'),     'ou → 어우'],
  ['C6a', 'méi',  eq('{메이=2}'),     'ei → 에이'],
  ['C6a', 'duì',  eq('{뚜에이=4}'),   'ui(uei) → 우에이'],

  // C7~C9 — 성조 변화는 **바뀐 소리로 적는다**
  ['C7', 'Nǐ hǎo.',  eq('{니=2} {하오=3}.'), '3성+3성 → 앞이 2성 (음운 규칙 — 기본 적용)'],
  // C8·C9 는 **어휘 규칙**이라 기본으로 끈다 — 병음만으로는 一/不 와 동음자(衣·布)를
  // 가릴 수 없다. 한자를 아는 호출자만 {lexical:true} 로 켠다. 근거는 pinyin.mjs 주석.
  ['C8', 'Bù shì.',  eqL('{뿌=2} {스=4#}.'),  '不 는 4성 앞에서 2성 (--lexical)'],
  ['C9', 'Yī ge.',   eqL('{이=2} 꺼.'),        '一 는 경성화된 4성 앞에서 2성 (--lexical)'],
  ['C9', 'Yī tiān.', eqL('{이=4} {티엔=1}.'),  '一 는 1성 앞에서 4성 (--lexical)'],
  ['C9', 'Yīfu.',    eq('{이=1}{푸=o}.'),      '衣 는 一 이 아니다 — 어휘 규칙이 오발화하면 안 된다'],
  ['C9', 'Yī qǐ.',   eqH('一起', '{이=4} {치=3}.'), '한자를 주면 一 만 정확히 골라 4성으로'],
  ['C9', 'Yīfu.',    eqH('衣服', '{이=1}{푸=o}.'), '한자를 주면 衣 는 건드리지 않는다'],

  // 음절 분리 — 모음으로 시작하는 음절 앞에는 격음부호가 필요하다. 부호가 없으면
  // 끝의 n·g 를 다음 음절 성모로 넘겨야 한다 (최장일치만 쓰면 랑안·땅아오가 나온다).
  ['음절분리', 'lángān',  eq('{란=2}{깐=1}'),     '栏杆 → lán+gān (láng+ān 이 아니다)'],
  ['음절분리', 'dàngāo',  eq('{딴=4}{까오=1}'),   '蛋糕 → dàn+gāo'],
  ['음절분리', 'kěnéng',  eq('{커=3}{넝=2}'),     '可能 → kě+néng'],
  ['음절분리', 'nánguò',  eq('{난=2}{꿔=4}'),     '难过 → nán+guò'],
  ['음절분리', 'ānjìng',  eq('{안=1}{찡=4}'),     '安静 — 정상 분리를 깨지 않는다'],
  ['음절분리', 'yīngér',  eq('{잉=1}{얼=2}'),     '婴儿 → yīng+ér. er 은 성모를 못 받으므로 g 를 넘기지 않는다'],

  // C10 — 얼화는 앞 음절과 한 덩어리, n 은 탈락
  ['C10', 'wánr',  eq('{왈=2}'),      '儿化 → 한 덩어리 + ㄹ 받침'],

  // 기호 — 이 표기법의 존재 이유. 빠지면 소리가 뭉개진다.
  ['기호', 'fàn',   mark('o'),        'f → ˚'],
  ['기호', 'chī',   mark('#'),        '권설음 → ˘'],
  ['기호', 'jù',    mark('u'),        'ü → ¨'],
  ['기호', 'shuǐ',  and(mark('#'), mark('3')), '권설음(AFTER) + 성조(TOP) 동시 부착'],
  ['기호', 'zhe',   eq('{쩌=#}'),     '경성이어도 AFTER 기호는 붙는다'],

  // 덩어리 성조 — 성조 기호는 음절 **덩어리 전체**의 중앙 위에 하나만 얹는다
  ['덩어리', 'hǎo',  (o) => /^\{하오=3\}$/.test(o),           '두 글자 한 음절 → 성조 하나'],
  ['덩어리', 'tài',  (o) => /^\{타이=4\}$/.test(o),           '{타=4}이 가 아니다'],
  ['덩어리', 'jiào', (o) => (o.match(/[1234]/g) || []).length === 1, '세 글자여도 성조 하나'],
];

const byRule = new Map();
let pass = 0;
for (const [rule, input, ok, why] of CASES) {
  const out = transcribeZh(input, { lexical: ok.lexical === true, hanzi: ok.hanzi });
  const good = ok(out);
  if (good) pass++;
  if (!byRule.has(rule)) byRule.set(rule, [0, 0]);
  const r = byRule.get(rule);
  r[1]++; if (good) r[0]++;
  if (V || !good) console.log(`  ${good ? '✓' : '✗'} [${rule}] ${input.padEnd(10)} → ${out.padEnd(22)} ${why}`);
}

// 병음 줄도 변화 후로 낸다 (SPEC §2-2 총칙) — 한글과 병음이 다른 소리를 가리키면 안 된다.
const PINYIN = [['Nǐ hǎo.', 'ní hǎo.'], ['Bù shì.', 'bú shì.'], ['Yī ge.', 'yí ge.']];
let pOk = 0;
for (const [inp, want] of PINYIN) {
  const got = respellSentence(applySandhi(tokenize(inp), { lexical: true })).toLowerCase();
  const good = got === want;
  if (good) pOk++;
  if (V || !good) console.log(`  ${good ? '✓' : '✗'} [병음줄] ${inp.padEnd(10)} → ${got.padEnd(22)} 변화 후 병음`);
}

const total = CASES.length + PINYIN.length;
const all = pass + pOk;
console.log(`\nSPEC 규칙 준수(중국어) ${all}/${total} (${(all / total * 100).toFixed(0)}%)`);
for (const [rule, [a, b]] of byRule) console.log(`  ${rule.padEnd(6)} ${a}/${b}`);
console.log(`  ${'병음줄'.padEnd(6)} ${pOk}/${PINYIN.length}`);
process.exit(all === total ? 0 : 1);
