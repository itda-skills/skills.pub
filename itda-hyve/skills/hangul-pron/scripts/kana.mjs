// 가나 파서 — 모라 분리 · 장음 판정 · 조사 떼어내기
//
// 중국어(pinyin.mjs)와 같은 자리에 있는 파일이다. 가나는 이미 음절 단위라 병음의 함정 6
// (성모+운모 최장일치)은 없지만, 대신 **모라가 글자와 일대일이 아니다** — 요음(きゃ),
// 촉음(っ), 발음(ん), 장음(ー·よう·いい)이 전부 예외다. 여기서 그걸 정리해서 넘긴다.
//
// 소비하지 못한 글자는 조용히 버리지 않고 `rest` 로 보고한다 (병음 파서와 같은 규율).

// ── 가타카나 → 히라가나 ───────────────────────────────────────────
// 표를 두 벌 두지 않으려고 먼저 접는다. ー(장음부호)는 가타카나 전용이지만 그대로 둔다.
const toHira = (s) => s.replace(/[ァ-ヶ]/g, (c) => String.fromCharCode(c.charCodeAt(0) - 0x60));

// ── 모라 표 ───────────────────────────────────────────────────────
// [자음, 모음] — 자음은 한글 첫소리를 정하고, 모음은 가운뎃소리를 정한다.
// sh·ch·ts·j 를 s·t·z 와 나눠 두는 이유: し 시 / す 스, ち 치 / た 타, つ 츠 처럼
// 한글 모음이 갈리고, J1 의 어중 된소리가 ち·つ 에는 걸리지 않기 때문이다.
const KANA = {
  あ: ['', 'a'], い: ['', 'i'], う: ['', 'u'], え: ['', 'e'], お: ['', 'o'],
  か: ['k', 'a'], き: ['k', 'i'], く: ['k', 'u'], け: ['k', 'e'], こ: ['k', 'o'],
  さ: ['s', 'a'], し: ['sh', 'i'], す: ['s', 'u'], せ: ['s', 'e'], そ: ['s', 'o'],
  た: ['t', 'a'], ち: ['ch', 'i'], つ: ['ts', 'u'], て: ['t', 'e'], と: ['t', 'o'],
  な: ['n', 'a'], に: ['n', 'i'], ぬ: ['n', 'u'], ね: ['n', 'e'], の: ['n', 'o'],
  は: ['h', 'a'], ひ: ['h', 'i'], ふ: ['f', 'u'], へ: ['h', 'e'], ほ: ['h', 'o'],
  ま: ['m', 'a'], み: ['m', 'i'], む: ['m', 'u'], め: ['m', 'e'], も: ['m', 'o'],
  や: ['y', 'a'], ゆ: ['y', 'u'], よ: ['y', 'o'],
  ら: ['r', 'a'], り: ['r', 'i'], る: ['r', 'u'], れ: ['r', 'e'], ろ: ['r', 'o'],
  わ: ['w', 'a'], ゐ: ['w', 'i'], ゑ: ['w', 'e'], を: ['w', 'o'],
  が: ['g', 'a'], ぎ: ['g', 'i'], ぐ: ['g', 'u'], げ: ['g', 'e'], ご: ['g', 'o'],
  ざ: ['z', 'a'], じ: ['j', 'i'], ず: ['z', 'u'], ぜ: ['z', 'e'], ぞ: ['z', 'o'],
  だ: ['d', 'a'], ぢ: ['j', 'i'], づ: ['z', 'u'], で: ['d', 'e'], ど: ['d', 'o'],
  ば: ['b', 'a'], び: ['b', 'i'], ぶ: ['b', 'u'], べ: ['b', 'e'], ぼ: ['b', 'o'],
  ぱ: ['p', 'a'], ぴ: ['p', 'i'], ぷ: ['p', 'u'], ぺ: ['p', 'e'], ぽ: ['p', 'o'],
  ゔ: ['b', 'u'],
};
const SMALL = { ゃ: 'ya', ゅ: 'yu', ょ: 'yo' };          // 요음 — 앞 모라에 붙어 한 모라가 된다
const SMALL_V = { ぁ: 'a', ぃ: 'i', ぅ: 'u', ぇ: 'e', ぉ: 'o' };  // ファ·ティ 같은 외래어 표기

const KANA_RE = /[ぁ-ゖァ-ヺー]/;
const WORD_RE = /[ぁ-ゖァ-ヺー]+/g;

/**
 * 한 낱말을 모라 열로 자른다.
 * @returns {{morae: object[], rest: string}}
 *   모라는 {cons, vowel} · {sokuon:true} · {moraicN:true} · {chouon:true} 중 하나다.
 */
function splitWord(word) {
  const s = toHira(word);
  const morae = [];
  let rest = '';
  for (let i = 0; i < s.length; i++) {
    const c = s[i];
    if (c === 'っ') { morae.push({ sokuon: true }); continue; }
    if (c === 'ん') { morae.push({ moraicN: true }); continue; }
    if (c === 'ー') { morae.push({ chouon: true, kana: c }); continue; }
    if (SMALL[c]) {                                   // 요음 — 앞 모라의 모음을 갈아끼운다
      const prev = morae[morae.length - 1];
      if (prev?.vowel === 'i') prev.vowel = SMALL[c];
      else rest += c;
      continue;
    }
    if (SMALL_V[c]) {
      const prev = morae[morae.length - 1];
      if (prev?.cons) prev.vowel = SMALL_V[c];
      else rest += c;
      continue;
    }
    const k = KANA[c];
    if (!k) { rest += c; continue; }
    morae.push({ cons: k[0], vowel: k[1], kana: c });
  }

  // J4 장음 — **길이가 뜻을 바꾼다.** ー 만이 아니라 모음 연속으로도 길어진다.
  //   お·う단 + う → ー (よう 요ー · もう 모ー · あらおう 아라오ー)
  //   い단 + い → ー (いい 이ー · おいしい 오이시ー)
  //   え단 + い → ー (せんせい 센세ー) — 일본어 교육 표기의 관례를 따른다
  // 앞 모라의 모음이 다르면 장음이 아니다 (おいしい 의 お+い 는 오이).
  for (let i = 1; i < morae.length; i++) {
    const p = morae[i - 1], m = morae[i];
    if (!m.kana || p.chouon || p.sokuon || p.moraicN) continue;
    const long = (m.kana === 'う' && (p.vowel === 'o' || p.vowel === 'u' || p.vowel === 'yo' || p.vowel === 'yu'))
      || (m.kana === 'い' && (p.vowel === 'i' || p.vowel === 'e'));
    // 원래 가나를 남긴다 — 한글은 어느 쪽이든 ー 지만, 로마자는 가나 충실형이라
    // `よう` 를 you 로, `おいしい` 를 oishii 로 적어야 한다 (verify-romaji.mjs).
    if (long && !m.cons) morae[i] = { chouon: true, kana: m.kana };
  }
  return { morae, rest };
}

// ── 조사 떼어내기 (J6 · SPEC 원리 6) ──────────────────────────────
//
// 띄어쓰기는 철자가 아니라 **호흡 단위**로 한다. SPEC J6 예시가 `ごはんを → 고˚항 오` 로
// 조사를 떼어 적는다.
//
// 문제는 **조사인지 낱말의 일부인지**다. この 의 の 를 떼면 `코 노` 가 된다. 형태소 분석
// 없이 가르는 기준 두 가지:
//   · を 는 현대 일본어에서 **언제나 조사**다 — 낱말 안에 있어도 거기서 끊는다. 그래야
//     띄어쓰기가 없는 입력도 같은 결과를 낸다 (ごはんをたべよう ≡ ごはんを たべよう).
//   · 나머지(は·が·に·の·へ)는 낱말 끝일 때만, 그리고 **앞에 2모라 이상 남을 때만** 뗀다.
//     この·その·どの(앞이 1모라)가 이 조건에서 걸러진다.
//   · だよ·だね 는 조사가 아니라 **지정사 だ + 종조사**지만, 앞 명사와 호흡이 끊기므로
//     같이 뗀다(`じかんだよ` → 지깡 다요). だ 하나만으로 판정하면 からだ·あいだ 처럼
//     낱말의 일부인 だ 까지 떼게 되므로 **だよ·だね 로 끝날 때만** 본다.
//   · **떼는 조사는 첫소리가 か·た행이면 안 된다.** 떼면 그 모라가 어두가 되어 J1 이
//     거센소리로 뒤집는다 — `さむいから` 를 떼면 까라가 카라로 바뀐다. 띄어쓰기는 호흡을
//     나타내는 표기일 뿐 소리를 바꾸지 않아야 하므로(원리 5·6), から 는 떼지 않는다.
//     J6 이 명시하는 조사(を·は·へ)와 が·に·の·だよ·だね 는 모두 첫소리가 か·た행이 아니라
//     이 문제가 없다.
const TAIL = ['だよ', 'だね', 'は', 'が', 'に', 'の', 'へ'];
/** 조사 읽기 — は 와, へ 에, を 오 (J6). 표기와 소리가 다른 셋만 여기서 바꾼다. */
const PARTICLE_READ = { は: 'わ', へ: 'え', を: 'お' };

/** 낱말 끝의 조사를 뗀다 → [{text, particle}] */
function peelTail(word) {
  const hira = toHira(word);
  for (const p of TAIL) {
    if (!hira.endsWith(p) || hira.length <= p.length) continue;
    const { morae } = splitWord(word.slice(0, -p.length));
    if (morae.length >= 2) return [{ text: word.slice(0, -p.length) }, { text: p, particle: true }];
  }
  return [{ text: word }];
}

/**
 * 낱말을 조사 경계로 가른다 — 낱말 안의 を 에서 먼저 끊고, 남은 조각의 끝 조사를 뗀다.
 * **조사인지 아닌지를 값으로 들고 다닌다.** 위치로 짐작하면 `はを`(歯を, 이를)의 は 를
 * 조사로 읽어 하 가 와 로 뒤집힌다 — 실제로 그 버그가 났다.
 */
function peelParticle(word) {
  const chunks = [];
  let buf = '';
  for (const ch of word) {
    if (toHira(ch) === 'を' && buf) { chunks.push(buf, ch); buf = ''; }
    else buf += ch;
  }
  if (buf) chunks.push(buf);
  return chunks.flatMap((c) => (toHira(c) === 'を' && chunks.length > 1
    ? [{ text: c, particle: true }] : peelTail(c)));
}

// ── 문장 토큰화 ───────────────────────────────────────────────────
// 일본어 문장부호는 한글 표기에서 ASCII 로 적는다 (앱 데이터와 SPEC 예시가 그렇다).
const PUNCT = { '。': '.', '、': ',', '！': '!', '？': '?', '　': ' ', '「': '"', '」': '"' };

/**
 * 문장을 토큰 열로. 조사는 **제 낱말로 떼어** 호흡 단위를 만든다.
 * @returns {({kind:'word', morae, rest, text}|{kind:'other', text})[]}
 */
export function tokenize(text) {
  const out = [];
  const push = (word) => {
    const parts = peelParticle(word);
    for (const [i, part] of parts.entries()) {
      if (i > 0) out.push({ kind: 'other', text: ' ' });
      // 뗀 조사만 읽기가 달라진다 (は 와 · へ 에 · を 오). 낱말 안의 は·へ 는 그대로 둔다.
      const read = part.particle ? PARTICLE_READ[toHira(part.text)] : null;
      out.push({ kind: 'word', ...splitWord(read ?? part.text), text: part.text });
    }
  };
  let last = 0;
  for (const m of text.matchAll(WORD_RE)) {
    if (m.index > last) out.push({ kind: 'other', text: mapPunct(text.slice(last, m.index)) });
    push(m[0]);
    last = m.index + m[0].length;
  }
  if (last < text.length) out.push({ kind: 'other', text: mapPunct(text.slice(last)) });
  // 문장부호 뒤에 바로 낱말이 오면 한 칸 띄운다 — 일본어 원문은 「だ！にげて！」처럼 붙여
  // 쓰지만 한글로 옮기면 붙은 채로 읽히지 않는다. 한국어 조판 관례에 맞춘다.
  for (let i = 0; i < out.length - 1; i++) {
    if (out[i].kind === 'other' && out[i + 1].kind === 'word' && /[.,!?]$/.test(out[i].text)) out[i].text += ' ';
  }
  return out;
}

const mapPunct = (s) => [...s].map((c) => PUNCT[c] ?? c).join('');

export { splitWord, KANA_RE };
