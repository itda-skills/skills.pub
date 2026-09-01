// 병음 파서 — 음절 분리 · 성조 추출 · 성조 변화(C7~C10)
//
// **공백으로 자르면 안 된다** (SPEC-HANGUL-PRON-002 함정 6). `wǒmen` 같은 두 음절 낱말이
// 한 덩어리로 세어지면 음절 정렬이 통째로 어긋난다 — 실측으로 검사기 오탐 49건 중 44건이
// 이 탓이었다. 성모+운모 조합으로 **앞에서부터 최장일치**로 잘라야 한다.
//
// 여기서는 3언어 앱의 `check-data.mjs` splitPinyin() 을 그대로 가져오지 않고 한 가지를
// 고쳤다 — 원본은 `word.match(SYL_RE)` 라 **매칭 안 된 글자를 조용히 버린다**. 얼화(儿化)의
// 남는 `r` 이나 오타가 그냥 사라져 검증이 통과해 버린다. 이 파서는 앞에서부터 소비하며
// 남은 글자를 `rest` 로 보고한다.

// ── 성조 부호 ─────────────────────────────────────────────────────
export const TONE_MARKS = {
  'ā': 1, 'á': 2, 'ǎ': 3, 'à': 4, 'ē': 1, 'é': 2, 'ě': 3, 'è': 4,
  'ī': 1, 'í': 2, 'ǐ': 3, 'ì': 4, 'ō': 1, 'ó': 2, 'ǒ': 3, 'ò': 4,
  'ū': 1, 'ú': 2, 'ǔ': 3, 'ù': 4, 'ǖ': 1, 'ǘ': 2, 'ǚ': 3, 'ǜ': 4,
};
const BARE = {
  'ā': 'a', 'á': 'a', 'ǎ': 'a', 'à': 'a', 'ē': 'e', 'é': 'e', 'ě': 'e', 'è': 'e',
  'ī': 'i', 'í': 'i', 'ǐ': 'i', 'ì': 'i', 'ō': 'o', 'ó': 'o', 'ǒ': 'o', 'ò': 'o',
  'ū': 'u', 'ú': 'u', 'ǔ': 'u', 'ù': 'u', 'ǖ': 'ü', 'ǘ': 'ü', 'ǚ': 'ü', 'ǜ': 'ü',
};
// 두 함수 모두 **소문자로 먼저 내린다.** 표에는 소문자만 있어서, 소문자화를 뒤에 두면
// 문장 첫 낱말(Ānjìng)이 통째로 파싱되지 않고 성조도 경성으로 읽힌다 — 실제로 그 두 버그가 났다.

/** 성조 부호를 떼고 소문자로. ü 는 v 로 통일한다(자판 입력도 받기 위해). */
export const deTone = (s) => [...s.toLowerCase()].map((c) => BARE[c] || c).join('').replace(/ü/g, 'v');
/** 음절 안의 성조 (없으면 0 = 경성) */
export const toneOf = (s) => { for (const c of s.toLowerCase()) if (TONE_MARKS[c]) return TONE_MARKS[c]; return 0; };

const LETTER = 'a-zāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜüv';
const WORD_RE = new RegExp(`[${LETTER}]+(?:['’][${LETTER}]+)*`, 'gi');

// ── 성모·운모 ─────────────────────────────────────────────────────
const INITIAL_RE = /^(zh|ch|sh|[bpmfdtnlgkhjqxrzcsyw])/;
// 길이 내림차순으로 최장일치 — 'ue' 가 'u' 보다 먼저 시도돼야 한다.
const FINALS = [
  'iang', 'iong', 'uang', 'ueng', 'van', 'ian', 'iao', 'ing', 'ong', 'uai', 'uan',
  'ang', 'eng', 'ia', 'ie', 'iu', 'in', 'ua', 'uo', 'ui', 'un', 've', 'vn', 'ue',
  'ai', 'ei', 'ao', 'ou', 'an', 'en', 'er', 'a', 'o', 'e', 'i', 'u', 'v',
].sort((a, b) => b.length - a.length);

// y·w 는 성모가 아니라 **운모 i·u·ü 의 표기 변형**이다. 원래 운모로 되돌려야
// 규칙(C6·C6a)이 한 곳에서만 적용된다.
const Y_MAP = { i: 'i', in: 'in', ing: 'ing', a: 'ia', e: 'ie', ao: 'iao', ou: 'iou',
  an: 'ian', ang: 'iang', ong: 'iong', u: 'v', ue: 've', uan: 'van', un: 'vn' };
const W_MAP = { u: 'u', a: 'ua', o: 'uo', ai: 'uai', ei: 'ui', an: 'uan',
  en: 'un', ang: 'uang', eng: 'ueng' };
// j·q·x·y 뒤의 u 는 언제나 ü 다 (ju = jü). 병음 표기 관례라 여기서 되돌린다.
const U_IS_V = { u: 'v', ue: 've', uan: 'van', un: 'vn' };

/**
 * 한 낱말을 음절로 자른다.
 * @returns {{syls: {raw,initial,final,tone,erhua}[], rest: string}}
 *   rest 는 어느 음절로도 소비되지 않은 나머지 — 비어 있어야 정상이다.
 */
function splitWord(word) {
  const bare = deTone(word);
  const syls = [];
  let p = 0;
  while (p < bare.length) {
    const im = INITIAL_RE.exec(bare.slice(p));
    let initial = im ? im[1] : '';
    let final = null;
    for (const f of FINALS) {
      if (bare.startsWith(f, p + initial.length)) { final = f; break; }
    }
    // 성모로 읽은 글자가 실은 운모의 일부일 수 있다 (예: 'er' 의 e). 운모가 안 붙으면 물러선다.
    if (!final && initial) {
      initial = '';
      for (const f of FINALS) if (bare.startsWith(f, p)) { final = f; break; }
    }
    if (!final) break;                                  // 소비 못 한 나머지는 rest 로

    // **최장일치만으로는 n·ng 경계가 어긋난다.** `lángān`(栏杆)을 그냥 자르면 láng+ān 이
    // 되지만 옳은 것은 lán+gān 이다. 병음 표기법상 **모음으로 시작하는 음절 앞에는
    // 격음부호(')가 필요**하므로, 부호가 없는데 다음이 모음으로 시작한다면 그 분리는
    // 틀린 것이다 — 끝의 n·g 를 다음 음절의 성모로 넘긴다.
    //   lángān → lán+gān · dàngāo → dàn+gāo · kěnéng → kě+néng · nánguò → nán+guò
    // (격음부호가 있는 `Wǎn’ān` 은 tokenize 가 미리 갈라 두므로 여기 오지 않는다.)
    if (/n$|ng$/.test(final)) {
      const restAt = p + initial.length + final.length;
      const rest = bare.slice(restAt);
      // 단 **er 은 성모를 받지 않는다** — `yīngér`(婴儿)에서 g 를 넘기면 gér 라는 없는
      // 음절이 된다. 그런 자리는 원래대로 두고 다음 음절이 모음으로 시작하게 둔다.
      if (/^[aeiouv]/.test(rest) && !/^er($|[^aeiouv])/.test(rest)) {
        const shorter = final.slice(0, -1);            // ang→an · an→a · ing→in …
        if (FINALS.includes(shorter)) final = shorter;
      }
    }

    const start = p, end = p + initial.length + final.length;
    p = end;
    // C10 얼화 — 낱말 끝의 남는 r (단, 'er' 자체는 위에서 운모로 먹혔다)
    let erhua = false;
    if (bare[p] === 'r' && p + 1 === bare.length && final !== 'er') { erhua = true; p += 1; }
    if (initial === 'y') final = Y_MAP[final] ?? final;
    else if (initial === 'w') final = W_MAP[final] ?? final;
    else if ('jqx'.includes(initial)) final = U_IS_V[final] ?? final;
    if (initial === 'y' || initial === 'w') initial = '';
    syls.push({ raw: word.slice(start, end), initial, final, tone: toneOf(word.slice(start, end)), erhua });
  }
  return { syls, rest: bare.slice(p) };
}

/**
 * 문장을 토큰 열로 자른다. 낱말 사이 공백·문장부호는 그대로 보존한다 —
 * 띄어쓰기가 곧 호흡 단위이고(SPEC 원리 6), 출력의 띄어쓰기는 병음의 낱말 경계를 따른다.
 * @returns {({kind:'word', syls, rest, text}|{kind:'other', text})[]}
 */
export function tokenize(text) {
  const out = [];
  let last = 0;
  for (const m of text.matchAll(WORD_RE)) {
    if (m.index > last) out.push({ kind: 'other', text: text.slice(last, m.index) });
    // 격음부호(’)는 음절 경계 표시일 뿐이라 낱말을 쪼개지 않는다 (Wǎn’ān → 완안, 붙여 씀)
    const parts = m[0].split(/['’]/);
    const syls = [];
    let rest = '';
    for (const part of parts) { const r = splitWord(part); syls.push(...r.syls); rest += r.rest; }
    out.push({ kind: 'word', syls, rest, text: m[0] });
    last = m.index + m[0].length;
  }
  if (last < text.length) out.push({ kind: 'other', text: text.slice(last) });
  return out;
}

/** 문장 전체의 음절을 순서대로 (성조 변화는 낱말 경계를 넘나든다 — 你好가 그렇다) */
export const allSyls = (tokens) => tokens.flatMap((t) => (t.kind === 'word' ? t.syls : []));

// ── 성조 변화 (C7~C10) ────────────────────────────────────────────
//
// **사전 표기가 아니라 실제로 나는 소리대로 적는다** (SPEC §2-2 총칙). 병음 줄도 변화 후로 낸다.
//
// 규칙은 **사전형에만 발화**하므로 이미 변화가 적용된 입력에는 아무 일도 하지 않는다(멱등).
// 3언어 앱 데이터의 병음이 이미 변화 후 표기라 그대로 넣어도 안전하다.
//
// 경성화된 4성: `一个 yí ge` 의 个 는 경성이지만 본디 4성이라 一 를 2성으로 만든다(C9).
// 병음만 보고는 알 수 없어 흔한 것만 목록으로 둔다 — 늘리려면 여기에 더한다.
const NEUTRAL_FROM_4 = new Set(['ge']);

// **C7 과 C8·C9 는 성격이 다르다 — 기본값도 달라야 한다.**
//
// C7(3성+3성)은 **음운 규칙**이다. 성조만 보고 판정하므로 어떤 글자든 안전하다.
// C8(不)·C9(一)은 **어휘 규칙**이다. 특정 글자에만 일어나는데 병음만 보면 동음자를
// 가릴 수 없다 — `衣 yī`(衣服 yīfu)가 一 규칙에 걸려 yì 로, `布·步·部 bù` 가 不 규칙에
// 걸려 bú 로 뒤집힌다. 실제로 pypinyin 대조에서 `衣服` 가 그렇게 잡혔다.
//
// 1단계(병음 입력)에서는 **애초에 필요 없다.** SPEC §2-2 총칙이 병음 줄을 변화 후로
// 적으라 하므로 입력이 이미 변화형이다. 그래서 어휘 규칙은 **끄는 것이 기본**이고,
// 한자를 아는 호출자(2단계·검수기)만 `{lexical: true}` 로 켠다.
const isLexicalTarget = (syl, chars) => {
  if (!chars) return true;                       // 글자를 모르면 병음으로만 판정 (구식 동작)
  const c = chars.get(syl);
  return c === '一' || c === '不';
};

/**
 * 문장 단위 성조 변화. syls 를 제자리에서 고치고 같은 배열을 돌려준다.
 * @param {{lexical?: boolean, chars?: Map}} opt
 *   lexical  C8·C9(不·一)까지 적용할지. 기본 false — 위 주석 참조.
 *   chars    음절 객체 → 한자 매핑. 주면 一·不 만 정확히 골라낸다.
 */
export function applySandhi(tokens, opt = {}) {
  // 문장부호에서 끊는다 — 3성 연속은 호흡 단위 안에서만 일어난다.
  const groups = [];
  let cur = [];
  for (const t of tokens) {
    if (t.kind === 'word') cur.push(...t.syls);
    else if (/[.,!?;:。，！？；：]/.test(t.text)) { if (cur.length) groups.push(cur); cur = []; }
  }
  if (cur.length) groups.push(cur);

  for (const g of groups) {
    // C8·C9 — 不 bù / 一 yī. 어휘 규칙이라 기본으로는 적용하지 않는다 (위 주석).
    if (opt.lexical) for (let i = 0; i < g.length - 1; i++) {
      const s = g[i], n = g[i + 1];
      if (!isLexicalTarget(s, opt.chars)) continue;
      const nextIs4 = n.tone === 4 || (n.tone === 0 && NEUTRAL_FROM_4.has(deTone(n.raw)));
      if (deTone(s.raw) === 'bu' && s.tone === 4 && nextIs4) s.tone = 2;
      if (deTone(s.raw) === 'yi' && s.tone === 1) {
        if (nextIs4) s.tone = 2;
        else if (n.tone >= 1 && n.tone <= 3) s.tone = 4;
      }
    }
    // C7 — 3성이 이어지면 마지막만 남고 앞은 전부 2성
    for (let i = 0; i < g.length; i++) {
      if (g[i].tone === 3 && g[i + 1]?.tone === 3) g[i].tone = 2;
    }
  }
  return tokens;
}

// ── 병음 다시 쓰기 (변화 후 성조로) ───────────────────────────────
const VOWEL_TONE = {
  a: ['a', 'ā', 'á', 'ǎ', 'à'], o: ['o', 'ō', 'ó', 'ǒ', 'ò'], e: ['e', 'ē', 'é', 'ě', 'è'],
  i: ['i', 'ī', 'í', 'ǐ', 'ì'], u: ['u', 'ū', 'ú', 'ǔ', 'ù'], v: ['ü', 'ǖ', 'ǘ', 'ǚ', 'ǜ'],
};
/** 성조 부호를 붙일 자리 — a·o·e 우선, 없으면 iu·ui 는 뒤 모음, 그 외 유일 모음 */
function toneIndex(bare) {
  for (const v of ['a', 'o', 'e']) { const i = bare.indexOf(v); if (i >= 0) return i; }
  const m = [...bare].map((c, i) => ('iuv'.includes(c) ? i : -1)).filter((i) => i >= 0);
  return m.length ? m[m.length - 1] : -1;
}
// 파서는 y·w 를 운모 i·u·ü 로 되돌려 두었다(규칙을 한 곳에서만 적용하려고).
// 다시 병음으로 적을 때는 표기 관례로 되돌린다.
const ZERO_SPELL = { i: 'yi', in: 'yin', ing: 'ying', ia: 'ya', ie: 'ye', iao: 'yao',
  iou: 'you', iu: 'you', ian: 'yan', iang: 'yang', iong: 'yong',
  u: 'wu', ua: 'wa', uo: 'wo', uai: 'wai', ui: 'wei', uan: 'wan', un: 'wen',
  uang: 'wang', ueng: 'weng', v: 'yu', ve: 'yue', van: 'yuan', vn: 'yun' };
const JQX_SPELL = { v: 'u', ve: 'ue', van: 'uan', vn: 'un' };

/** 음절 하나를 변화 후 성조로 다시 적는다 (얼화는 r 을 되붙인다) */
export function respell(syl) {
  let final = syl.final;
  if (!syl.initial) final = ZERO_SPELL[final] ?? final;
  else if ('jqxy'.includes(syl.initial)) final = JQX_SPELL[final] ?? final;
  const bare = syl.initial + final;
  const i = toneIndex(bare);
  let out = bare;
  if (i >= 0) out = bare.slice(0, i) + VOWEL_TONE[bare[i]][syl.tone] + bare.slice(i + 1);
  return out.replace(/v/g, 'ü') + (syl.erhua ? 'r' : '');
}
/**
 * 문장 전체를 변화 후 병음으로 (SPEC §2-2 총칙 — 병음 줄도 변화 후).
 * 낱말 안에서 **모음으로 시작하는 음절 앞에는 격음부호(’)를 넣는다** — 없으면 다시 읽을 때
 * 음절 경계가 어긋난다(`qǐé` 를 qiě 로, `wǎnān` 을 wǎ+nān 으로 읽게 된다).
 */
export function respellSentence(tokens) {
  return tokens.map((t) => {
    if (t.kind === 'other') return t.text;
    return t.syls.map(respell).reduce((acc, cur, i) =>
      acc + (i && /^[aeiouv]/.test(deTone(cur)) ? '’' : '') + cur, '');
  }).join('');
}
