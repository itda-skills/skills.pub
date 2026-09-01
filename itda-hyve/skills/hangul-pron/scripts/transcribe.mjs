import { realpathSync as fsRealpath } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { synthWord, spell2phones, cmuAdjust, loadCmu } from './g2p.mjs';

// 영어 → 한글 발음 표기 변환기 (프로토타입)
//
// 설계 근거 — book-data.js 784건을 측정해서 얻은 두 가지 사실이 구조를 정한다.
//
// 1. **한글에서 출발하면 안 된다.** 기호를 받는 음절 106종 중 42%가 같은 음절인데 기호가 갈린다
//    (`레`: ˇ×30 / ˜×1 / 무표기×155 — "레츠"(Let's, r 없음) vs "그레ˇ잍"(great, r 있음)).
//    한글만 보고는 기호를 정할 수 없으므로 반드시 영어 철자·소리에서 출발해 한글을 만들면서
//    기호를 같이 붙인다. 한글을 후처리하는 방식은 구조적으로 실패한다.
//
// 2. **원본과 100% 일치는 불가능하다.** 같은 영어 문장이 두 번 이상 나오는 46종 중 17%가
//    서로 다르게 적혀 있다(뤠일링/레일링, 히딩/히링, 두잍/두일). 저자의 재량이므로 규칙으로
//    한쪽만 낼 수 있다. 따라서 목표는 "원본 재현"이 아니라 "표기 체계의 일관된 적용"이다.
//
// 그래서 규칙으로 대부분을 처리하고, 저자 재량·관용 표기는 LEX(예외 사전)에 쌓는다.
// **규칙을 예외에 맞춰 비틀지 않는다** — 한 곳을 맞추면 다른 곳이 깨진다.
//
// 표기 규칙의 정본은 SPEC.md §2-1(E1~E8). 기호는 영어 3종: ^=ˇ(R) · o=˚(F·V) · ~=˜(Th).
// 출력은 book-data.js 와 같은 마크업 문자열이다.
//
// 사용: node transcribe.mjs "Let's go."      · 평가: node eval-transcribe.mjs

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

/** 앞 단어의 끝소리를 뒤 음절의 첫소리로 옮긴다 (연음 — SPEC 원리 5). */
const relink = (syl, cho) => {
  const d = decompose(syl);
  if (!d || d.cho !== 'ㅇ') return null; // 첫소리가 비어 있을 때만 옮길 수 있다
  return compose(cho, d.jung, d.jong);
};

// ── 예외 사전 ─────────────────────────────────────────────────────
// 형식: [단독형, 연음형(뒤가 모음으로 시작할 때), 넘길 첫소리]
// 넘길 첫소리는 'ㅂ' 처럼 자모만 쓰거나, 기호가 함께 넘어가야 하면 'ㅂ|o' 처럼 적는다.
// give it → 기 + ㅂ˚ → 기{빝=o} — 연음한다고 F·V 기호를 잃으면 안 된다(그것이 이 표기의 핵심).
// 연음형이 null 이면 연음하지 않는다. 상위 빈도어와 규칙으로 안 되는 관용 표기를 담는다.
// 마크업 그대로 쓰므로 기호도 여기서 확정된다.
const LEX = {
  // 최상위 기능어
  "the": ["{더=~}", null, null], "a": ["어", null, null], "an": ["언", null, null],
  "to": ["투", null, null], "and": ["앤", null, null], "of": ["어{브=o}", null, null],
  "it": ["잍", null, null], "its": ["이츠", null, null], "it's": ["이츠", null, null],
  "is": ["이즈", null, null], "in": ["인", null, null], "on": ["온", null, null],
  "at": ["앹", null, null], "for": ["{뽈=^o}", null, null], "with": ["{윋=~}", null, null],
  "i": ["아이", null, null], "i'm": ["아임", null, null], "i'll": ["아을", null, null],
  "you": ["유", null, null], "your": ["유{얼=^}", null, null], "you're": ["유{얼=^}", null, null],
  "yourself": ["유{얼=^}쎌{쁘=o}", null, null], "me": ["미", null, null], "my": ["마이", null, null],
  "we": ["위", null, null], "we're": ["위{알=^}", null, null], "he": ["히", null, null],
  "she": ["쉬", null, null], "they": ["{데=~}이", null, null], "them": ["{뎀=~}", null, null],
  "this": ["{디=~}쓰", null, null], "that": ["{댙=~}", null, null], "that's": ["{대=~}츠", null, null],
  "there": ["{데=~}{얼=^}", null, null], "here": ["히{얼=^}", null, null],
  "what": ["왙", null, null], "what's": ["왓츠", null, null], "where": ["웨{얼=^}", null, null],
  "who": ["후", null, null], "which": ["위치", null, null], "how": ["하우", null, null],
  "let's": ["레츠", null, null], "don't": ["돈", null, null], "can": ["캔", null, null],
  "can't": ["캔트", null, null], "do": ["두", null, null], "does": ["더즈", null, null],
  "did": ["디드", "디", null], "will": ["윌", null, null], "would": ["우드", null, null],
  "shall": ["쉘", null, null], "no": ["노", null, null], "not": ["낱", null, null],
  "too": ["투", null, null], "so": ["쏘우", null, null], "all": ["오을", null, null],
  "one": ["원", null, null], "more": ["모{얼=^}", null, null], "some": ["썸", null, null],
  "again": ["어게인", null, null], "now": ["나우", null, null], "back": ["백", null, null],
  "up": ["엎", null, null], "down": ["다운", null, null], "out": ["아웉", null, null],
  "off": ["어{쁘=o}", null, null], "over": ["오{벌=^o}", null, null], "away": ["어웨이", null, null],
  "good": ["굳", null, null], "great": ["그{레=^}잍", null, null], "okay": ["오케이", null, null],
  "please": ["플리즈", null, null], "thank": ["{땡=~}크", null, null], "thanks": ["{땡=~}쓰", null, null],

  // 동사·명사 (연음이 잦은 것은 연음형을 함께 둔다)
  "go": ["고우", null, null], "going": ["고잉", null, null], "come": ["컴", null, null],
  "put": ["풑", "푸", 'ㄹ'], "get": ["겥", "게", 'ㄹ'], "take": ["테잌", "테이", 'ㅋ'],
  "give": ["기{브=o}", "기", 'ㅂ|o'], "hold": ["호을드", null, null], "help": ["헤읊", null, null],
  "look": ["룩", "루", 'ㅋ'], "see": ["씨", null, null], "say": ["쎄이", null, null],
  "eat": ["이잍", "이이", 'ㄹ'], "drink": ["드{링=^}크", null, null], "wash": ["워쉬", null, null],
  "wipe": ["와이프", "와이", 'ㅍ'], "dry": ["드{라=^}이", null, null], "brush": ["브{러=^}쉬", null, null],
  "open": ["오픈", null, null], "close": ["클로우즈", null, null], "turn": ["{털=^}ㄴ", null, null],
  "pull": ["푸을", "풀", 'ㄹ'], "push": ["푸쉬", null, null], "throw": ["{쓰=~}{로=^}우", null, null],
  "catch": ["캐치", null, null], "find": ["{빠=o}인드", null, null], "make": ["메잌", "메이", 'ㅋ'],
  "play": ["플레이", null, null], "sit": ["앁", "씨", 'ㄹ'], "stand": ["스땐드", null, null],
  "wait": ["웨잍", "웨이", 'ㄹ'], "want": ["원트", "워너", null], "try": ["트{라=^}이", null, null],
  "hand": ["핸드", null, null], "hands": ["핸즈", null, null], "foot": ["{뿥=o}", null, null],
  "book": ["붘", null, null], "ball": ["버을", null, null], "block": ["블럭", null, null],
  "blocks": ["블럭쓰", null, null], "water": ["워{럴=^}", null, null], "food": ["{뿌=o}드", null, null],
  "door": ["도{얼=^}", null, null], "box": ["박쓰", null, null], "car": ["{칼=^}", null, null],
  "bus": ["버쓰", null, null], "mommy": ["마미", null, null], "daddy": ["대디", null, null],
  "mommy's": ["마미즈", null, null], "grandma": ["그{랜=^}마", null, null],
  "friend": ["{쁘=o}{렌=^}드", null, null], "friends": ["{쁘=o}{렌=^}즈", null, null],
  "together": ["투게{덜=^~}", null, null], "careful": ["케{얼=^}{뿔=o}", null, null],
  "slowly": ["슬로울리", null, null], "gentle": ["젠틀", null, null], "gently": ["젠틀리", null, null],
  "little": ["리를", null, null], "turn!": ["{털=^}ㄴ!", null, null],

  // 빈도 상위 보강 (SPEC E1~E8 을 손으로 적용한 것)
  "have": ["해{브=o}", "해", 'ㅂ|o'], "has": ["해즈", null, null], "are": ["{알=^}", null, null],
  "be": ["비", null, null], "time": ["타임", null, null], "step": ["스뗖", null, null],
  "job": ["잡", null, null], "use": ["유즈", null, null], "button": ["벝은", null, null],
  "page": ["페이지", null, null], "ready": ["{레=^}디", null, null], "clean": ["클린", null, null],
  "first": ["{뻘=^o}스트", null, null], "keep": ["킾", null, null], "teeth": ["티{쓰=~}", null, null],
  "press": ["프{레=^}쓰", null, null], "watch": ["워치", null, null], "bring": ["브{링=^}", null, null],
  "right": ["{롸=^}잍", null, null], "cup": ["컵", null, null], "big": ["빅", null, null],
  "goodbye": ["굳바이", null, null], "done": ["던", null, null], "hole": ["호을", null, null],
  "grab": ["그{랩=^}", null, null], "by": ["바이", null, null], "from": ["{쁘=o}{롬=^}", null, null],
  "hug": ["허그", null, null], "let": ["렡", null, null], "diaper": ["다이{펄=^}", null, null],
  "read": ["{리=^}드", "{리=^}", 'ㄷ'], "next": ["넥쓰트", null, null], "nose": ["노우즈", null, null],
  "apart": ["어{팔=^}트", null, null], "dance": ["댄쓰", null, null], "sticker": ["스띠{껄=^}", null, null],
  "hide": ["하이드", null, null], "tight": ["타잍", null, null], "hang": ["행", null, null],
  "love": ["러{브=o}", null, null], "almost": ["올모쓰트", null, null], "eating": ["이링", null, null],
  "stay": ["스떼이", null, null], "pat": ["팯", null, null], "shoes": ["슈즈", null, null],
  "top": ["탚", null, null], "hello": ["헬로우", null, null], "bow": ["바우", null, null],
  "stroller": ["스뜨{롤=^}{럴=^}", null, null], "climb": ["클라임", null, null],
  "slide": ["슬라이드", null, null], "found": ["{빠=o}운드", "{빠=o}운", 'ㄷ'],
  "kick": ["킥", "키", 'ㅋ'], "high": ["하이", null, null], "sound": ["싸운드", null, null],
  "drive": ["드{라=^}이{브=o}", null, null], "both": ["보우{쓰=~}", null, null],
  "swing": ["스윙", null, null], "sand": ["쌘드", null, null], "bar": ["{발=^}", null, null],
  "handle": ["핸들", null, null], "just": ["쪄스트", null, null], "head": ["헤드", null, null],
  "chair": ["체{얼=^}", null, null], "helping": ["헬핑", null, null], "yummy": ["여미", null, null],
  "fill": ["{삘=o}", null, null], "bottom": ["버럼", null, null], "hot": ["핱", null, null],
  "pants": ["팬츠", null, null], "towel": ["타우얼", null, null], "socks": ["싹쓰", null, null],
  "shirt": ["{셜=^}츠", null, null], "hat": ["햍", null, null], "jacket": ["재킽", null, null],
  "snack": ["스낵", null, null], "bed": ["베드", null, null], "sleep": ["슬맆", null, null],
  "night": ["나잍", null, null], "bath": ["배{쓰=~}", null, null], "milk": ["미을크", null, null],
  "trash": ["트{래=^}쉬", null, null], "toys": ["토이즈", null, null], "cars": ["{칼=^}즈", null, null],
  "basket": ["배스킽", null, null], "sing": ["씽", null, null], "cook": ["쿡", null, null],
  "ride": ["{라=^}이드", null, null], "share": ["쉐{얼=^}", null, null], "hurt": ["{헐=^}트", null, null],
  "cry": ["크{라=^}이", null, null], "kiss": ["키스", null, null], "happy": ["해피", null, null],
  "sad": ["쌔드", null, null], "sorry": ["쏘{리=^}", null, null], "scared": ["스께{얼=^}드", null, null],
  "run": ["{런=^}", null, null], "walk": ["웤", null, null], "stop": ["스땊", null, null],
};

// ── 미등록어 처리: 발음 사전(G2P) 우선, 철자 규칙은 폴백 ──────────
//
// 코퍼스 어휘의 51%가 1회성(hapax)이라 **사전 확장만으로는 새 문장에서 듣지 않는다**.
// 훈련 80%/평가 20% 홀드아웃 실측: 사전 채굴만 하면 평가 셋 +3.2pp 에 그치는데,
// 발음 사전 기반 G2P 를 넣으면 34.4% → 51.6% 로 올라간다. 처음 보는 단어를 제대로
// 근사하는 것이 일반화의 지렛대다.
//
// 경로: CMUdict 조회 → 없으면 철자→음소 규칙 → 그래도 안 되면 옛 철자 폴백.
// 셋 다 결정론적이다(제1발음만 사용, 런타임 LLM 없음).
const CMU_PATH = new URL('../data/cmudict.dict', import.meta.url);
let CMU = null;
const cmu = () => (CMU ??= loadCmu(fileURLToPath(CMU_PATH)));   // 첫 호출에만 읽는다(84ms·약 140MB)

function fallback(word) {
  const w = (word || '').toLowerCase().replace(/[^a-z']/g, '');
  if (!w) return '';
  try {
    const bare = w.replace(/[^a-z]/g, '');
    const dict = cmu();
    if (dict.has(w)) return synthWord(cmuAdjust(bare, dict.get(w))) || fallbackOld(word);
    return synthWord(spell2phones(w)) || fallbackOld(word);
  } catch {
    return fallbackOld(word);   // 사전 파일이 없거나 깨져도 동작은 계속된다
  }
}

// ── 철자 → 한글 폴백 규칙 (최후 수단) ─────────────────────────────
// G2P 경로가 실패했을 때만 쓴다. 정확도보다 "읽히는 근사치"가 목표다.
const ONSET = [
  ['sch', '스ㅋ'], ['sh', '쉬'], ['ch', '치'], ['th', '{ㅆ=~}'], ['ph', '{ㅃ=o}'], ['wh', 'ㅇ'],
  ['str', '스뜨ㄹ'], ['spr', '스쁘ㄹ'], ['scr', '스끄ㄹ'],
  ['sp', '스ㅃ'], ['st', '스ㄸ'], ['sk', '스ㄲ'], ['sc', '스ㄲ'],
];
const VOWEL = /[aeiouy]/;

/** 아주 단순한 음절 근사 — 자음군 + 모음 + 종성 후보로 자른다. */
function fallbackOld(word) {
  let w = word.toLowerCase().replace(/[^a-z]/g, '');
  if (!w) return '';
  // 어말 묵음 e — home→호메, outside→아웉시데 같은 오류의 원인이다.
  // 단 -le(little·table)은 '을' 로 살려 읽으므로 건드리지 않는다.
  if (w.length > 2 && w.endsWith('e') && !/[aeiou]e$/.test(w) && !w.endsWith('le')) w = w.slice(0, -1);
  let out = '';
  let i = 0;
  const MAP_C = { b: 'ㅂ', c: 'ㅋ', d: 'ㄷ', f: 'ㅍ', g: 'ㄱ', h: 'ㅎ', j: 'ㅈ', k: 'ㅋ', l: 'ㄹ',
    m: 'ㅁ', n: 'ㄴ', p: 'ㅍ', q: 'ㅋ', r: 'ㄹ', s: 'ㅅ', t: 'ㅌ', v: 'ㅂ', w: 'ㅇ', x: 'ㅋㅅ', y: 'ㅇ', z: 'ㅈ' };
  const MAP_V = { a: 'ㅐ', e: 'ㅔ', i: 'ㅣ', o: 'ㅗ', u: 'ㅓ' };
  // 강세 없는 모음은 ㅓ 로 뭉갠다 (SPEC E7) — moment→모먼트, second→쎄컨드
  const MAP_V_WEAK = { a: 'ㅓ', e: 'ㅓ', i: 'ㅣ', o: 'ㅗ', u: 'ㅓ' };
  let seenVowel = false;
  while (i < w.length) {
    let cho = 'ㅇ', top = '', aft = '';
    // 두 글자 자음 조합
    const two = w.slice(i, i + 2);
    if (two === 'th') { cho = 'ㅆ'; aft = '~'; i += 2; }
    else if (two === 'ph') { cho = 'ㅃ'; aft = 'o'; i += 2; }
    else if (two === 'sh') { cho = 'ㅅ'; i += 2; }
    else if (two === 'ch') { cho = 'ㅊ'; i += 2; }
    else if (!VOWEL.test(w[i])) {
      const c = w[i];
      cho = MAP_C[c] || 'ㅇ';
      if (c === 'r') top = '^';
      if (c === 'f' || c === 'v') { cho = 'ㅃ'; aft = 'o'; }
      i++;
    }
    // 모음
    let jung = 'ㅡ';
    if (i < w.length && VOWEL.test(w[i])) {
      const pair = w.slice(i, i + 2);
      if (pair === 'ee' || pair === 'ea') { jung = 'ㅣ'; i += 2; }
      else if (pair === 'oo') { jung = 'ㅜ'; i += 2; }
      else if (pair === 'ou' || pair === 'ow') { jung = 'ㅏ'; i += 2; out += compose(cho, jung); cho = 'ㅇ'; jung = 'ㅜ'; }
      else if (pair === 'ai' || pair === 'ay') { jung = 'ㅔ'; i += 2; out += compose(cho, jung); cho = 'ㅇ'; jung = 'ㅣ'; }
      else { jung = (seenVowel ? (MAP_V_WEAK[w[i]] || 'ㅓ') : (MAP_V[w[i]] || 'ㅓ')); i++; }
      seenVowel = true;
    } else if (cho !== 'ㅇ') {
      jung = 'ㅡ'; // 모음 없는 자음은 '으' 를 붙여 읽힌다
    }
    // 종성 후보: 다음이 자음이고 그 다음도 자음이면 하나를 받침으로
    let jong = ' ';
    if (i < w.length && !VOWEL.test(w[i]) && (i + 1 >= w.length || !VOWEL.test(w[i + 1]))) {
      const JONGABLE = { b: 'ㅂ', d: 'ㄷ', g: 'ㄱ', k: 'ㄱ', l: 'ㄹ', m: 'ㅁ', n: 'ㄴ', p: 'ㅂ', t: 'ㅌ', s: 'ㅅ' };
      // th·ph·sh·ch 의 앞 글자를 받침으로 먹으면 그 소리가 통째로 사라진다
      // (father → 뺕˚헐ˇ 처럼 ˜ 가 없어진다). 두 글자 조합이면 받침으로 쓰지 않는다.
      const digraph = /^(th|ph|sh|ch)/.test(w.slice(i, i + 2));
      if (w[i] === 'r') { jong = 'ㄹ'; top = '^'; i++; }   // car→칼ˇ : R 은 받침으로 살리고 ˇ 를 얹는다
      else if (!digraph && JONGABLE[w[i]]) { jong = JONGABLE[w[i]]; i++; }
    }
    const syl = compose(cho === 'ㅇ' && jung === 'ㅡ' ? 'ㅇ' : cho, jung, jong);
    const code = top + aft;   // SPEC 원리 3: TOP(ˇ) 과 AFTER(˚·˜) 는 한 글자에 함께 붙을 수 있다
    out += code ? `{${syl}=${code}}` : syl;
  }
  return out;
}


// ── 일반 연음 (SPEC 원리 5) ────────────────────────────────────────
// 교재는 단어 경계를 무시하고 소리 나는 대로 이어 적는다 — put it in → 푸리린.
// 사전의 연음형만으로는 한 단계밖에 못 잇고, 실패의 31%가 여기서 나온다(측정).
// 그래서 렌더된 음절 흐름에 규칙으로 연음을 건다.
//
//   ① 앞 음절에 받침이 있고 뒤 음절 초성이 ㅇ 이면 받침을 뒤 초성으로 옮긴다
//   ② 옮길 소리가 ㄷ·ㅌ 이고 앞뒤가 모두 모음이면 ㄹ 로 바꾼다 (플랩 — E2)
//   ③ 이어진 두 단어는 붙여 쓴다 (호흡 단위 — 원리 6)
//
// 기호는 음절에 붙어 있으므로 옮겨도 유지된다.
const FLAPPABLE = new Set(['ㄷ', 'ㅌ']);
// 교재는 아무 데나 잇지 않는다 — 앞말에 달라붙는 짧은 기능어에만 연음한다.
// (step at → 스뗖 애러 : step+at 은 안 잇고 at+a 만 잇는다)
// 목록은 측정으로 정했다. 환경변수 HP_LIAISON 으로 실험할 수 있다.
const LIAISON_WORDS = new Set(
  (process.env.HP_LIAISON || "it,it's,its,in,on,up,out,of,a,an")
    .split(',').map((x) => x.trim()).filter(Boolean));

/** 마크업 문자열을 [{syl, code}] 로 쪼갠다. */
function toUnits(text) {
  const units = [];
  for (const part of text.split(/(\{[^}]*\})/)) {
    if (!part) continue;
    if (part.startsWith('{')) {
      const [u, code = ''] = part.slice(1, -1).split('=');
      for (let i = 0; i < u.length; i++) units.push({ syl: u[i], code: i === u.length - 1 ? code : '' });
    } else {
      for (const ch of part) units.push({ syl: ch, code: '' });
    }
  }
  return units;
}

const fromUnits = (units) =>
  units.map((u) => (u.code ? `{${u.syl}=${u.code}}` : u.syl)).join('');

/** 두 단어를 연음으로 잇는다. 이을 수 없으면 null. */
function liaise(leftText, rightText) {
  const L = toUnits(leftText), R = toUnits(rightText);
  if (!L.length || !R.length) return null;
  const last = L[L.length - 1], first = R[0];
  const dl = decompose(last.syl), dr = decompose(first.syl);
  if (!dl || !dr) return null;
  if (dl.jong === ' ' || dr.cho !== 'ㅇ') return null;   // 받침이 없거나 뒤가 자음으로 시작
  let moved = dl.jong;
  if (FLAPPABLE.has(moved)) moved = 'ㄹ';                // 모음 사이 t·d → ㄹ (E2)
  L[L.length - 1] = { ...last, syl: compose(dl.cho, dl.jung) };
  R[0] = { ...first, syl: compose(moved, dr.jung, dr.jong) };
  return fromUnits(L) + fromUnits(R);
}

// ── 단어 → 표기 ───────────────────────────────────────────────────
const startsVowel = (w) => VOWEL.test((w || '').toLowerCase()[0] || '');

function renderWord(word, nextWord) {
  const key = word.toLowerCase().replace(/[’]/g, "'").replace(/[.,!?]/g, '');
  const e = LEX[key];
  if (!e) return { text: fallback(key), carry: null };
  const [solo, link, carry] = e;
  if (link && carry && startsVowel(nextWord)) return { text: link, carry };
  return { text: solo, carry: null };
}

/** 넘어온 첫소리(+기호)를 다음 표기의 첫 음절에 얹는다. 불가능하면 그대로 이어 붙인다. */
function applyCarry(text, carry) {
  const [cho, mark] = String(carry).split('|');
  const m = text.match(/^(\{?)([가-힣])/);
  if (!m) return text;
  const moved = relink(m[2], cho);
  if (!moved) return text;
  if (!mark) return text.replace(m[2], moved);
  // 이미 마크업 안이면 코드에 더하고, 아니면 새로 감싼다
  if (m[1] === '{') return text.replace(/^\{([가-힣])=([^}]*)\}/, (_, __, code) => `{${moved}=${code.includes(mark) ? code : code + mark}}`);
  return text.replace(m[2], `{${moved}=${mark}}`);
}

export function transcribe(sentence) {
  const words = sentence.match(/[A-Za-z’']+|[.,!?]/g) || [];
  const out = [];
  let carry = null;
  for (let i = 0; i < words.length; i++) {
    const w = words[i];
    if (/^[.,!?]$/.test(w)) { if (out.length) out[out.length - 1] += w; continue; }
    let next = words[i + 1];
    if (/^[.,!?]$/.test(next || '')) next = words[i + 2];
    let { text, carry: c } = renderWord(w, next);
    if (carry) { text = applyCarry(text, carry); out[out.length - 1] += text; }
    else if (out.length && LIAISON_WORDS.has(w.toLowerCase().replace(/[’]/g, "'").replace(/[.,!?]/g, ''))) {
      const joined = liaise(out[out.length - 1], text);
      if (joined) out[out.length - 1] = joined;   // 이어졌으면 붙여 쓴다
      else out.push(text);
    } else out.push(text);
    carry = c;
  }
  return out.join(' ');
}

// 심볼릭 링크(~/.claude/skills/…)로 실행되면 argv[1] 은 링크 경로, import.meta.url 은 실제 경로라
// 단순 비교가 어긋나 CLI 블록이 통째로 건너뛰어진다. 양쪽 모두 realpath 로 맞춘 뒤 비교한다.
const isMain = (() => {
  try {
    return fsRealpath(fileURLToPath(import.meta.url)) === fsRealpath(process.argv[1] ?? '');
  } catch { return false; }
})();

if (isMain) {
  const arg = process.argv.slice(2).join(' ');
  if (!arg) { console.log('사용: node transcribe.mjs "Let\'s go."'); process.exit(1); }
  console.log(transcribe(arg));
}
