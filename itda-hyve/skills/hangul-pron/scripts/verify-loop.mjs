// 음성 폐루프 검증 — **한국인이 이 표기대로 읽으면 알아들을 수 있는가.**
//
// 원어민 감수가 불가능할 때 쓸 수 있는 가장 직접적인 증거다. 표기를 한국어 TTS 로 읽혀
// 원어 음성인식에 넣고, **원문이 복원되는지** 본다.
//
//   한글 표기 → [한국어 TTS] → 오디오 → [원어 ASR] → 복원된 문장  ↔  원문
//
// 실측 예: `{타이=4} {하오=3} {츠=1#} 러!` → "타이 하오 츠 러" → 太好 吃了 (원문 太好吃了)
//
// ## 이 지표를 어떻게 읽어야 하는가 (중요)
//
// **절대 점수를 그대로 믿으면 안 된다.** 세 가지 이유로 실제보다 낮게 나온다.
//   ① TTS 는 기호를 못 읽는다. 학습자는 `고˚`를 보고 유성음으로 내지만 TTS 는 그냥 "고" 다.
//      즉 이 루프가 재는 것은 **기호를 뺀 한글 골격**의 실효성이고, 사람이 읽으면 더 낫다.
//   ② TTS 의 한국어 낭독은 부모의 낭독과 다르다(속도·억양·외래어 처리).
//   ③ ASR 은 문맥으로 보정하기도, 반대로 짧은 발화에서 헛짚기도 한다.
//
// 그래서 **A/B 비교로 쓰는 것이 본령**이다. 같은 조건에서 두 표기를 견주면 ①②③ 이 양쪽에
// 똑같이 걸리므로 차이만 남는다. `--ab` 모드가 그것이다 (J1 의 테/떼 같은 쟁점 판정).
//
// 필요: macOS `say` (한국어 음성) + python3 + mlx-whisper
// 사용: node verify-loop.mjs [--lang zh|ja] [--limit N] [--python <경로>] [--verbose]
//       node verify-loop.mjs --ab <가나> --variants "표기A|표기B" [--lang ja]

import { readFileSync, mkdtempSync, rmSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const args = process.argv.slice(2);
const V = args.includes('--verbose');
const opt = (n, d) => { const i = args.indexOf(n); return i >= 0 ? args[i + 1] : d; };
const PY = opt('--python', `${process.env.HOME}/.venv/bin/python3`);
const DATA = opt('--data', `${process.env.HOME}/orca/workspaces/website/한글영어/demo-apps/hangul-pron/data.js`);
const LANG = opt('--lang', 'zh');
const LIMIT = Number(opt('--limit', '0'));
const KO_VOICE = opt('--voice', 'Yuna');
const MODEL = opt('--model', 'mlx-community/whisper-large-v3-turbo');

// ── 표기 → TTS 가 읽을 수 있는 문자열 ─────────────────────────────
// 기호는 뗀다(TTS 가 못 읽는다). `ー` 는 앞 모음을 한 번 더 적어 길이를 만든다 —
// 그대로 두면 TTS 가 "장음부호" 라고 읽어 버린다.
const V_OF = 'ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ';
const CHO = 'ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ';
function speakable(markup) {
  const plain = markup.replace(/\{([^}=]*)=[^}]*\}/g, '$1');
  let out = '';
  for (const ch of plain) {
    if (ch !== 'ー') { out += ch; continue; }
    const prev = out[out.length - 1];
    const o = prev ? prev.charCodeAt(0) - 0xac00 : -1;
    if (o < 0 || o > 11171) continue;
    out += String.fromCharCode(0xac00 + (11 * 21 + Math.floor((o % 588) / 28)) * 28);  // ㅇ + 같은 모음
  }
  return out;
}

// ── ASR (mlx-whisper 일괄) ────────────────────────────────────────
const ASR_SRC = `
import sys, json, warnings
warnings.filterwarnings("ignore")
import mlx_whisper
model, lang = sys.argv[1], sys.argv[2]
out = []
for path in json.load(sys.stdin):
    r = mlx_whisper.transcribe(path, path_or_hf_repo=model, language=lang,
                               temperature=0, condition_on_previous_text=False)
    out.append(r["text"].strip())
print(json.dumps(out, ensure_ascii=False))
`;
function asr(files, lang) {
  const res = execFileSync(PY, ['-c', ASR_SRC, MODEL, lang], { input: JSON.stringify(files), encoding: 'utf8', maxBuffer: 1 << 26 });
  return JSON.parse(res.slice(res.lastIndexOf('[')));
}

const tmp = mkdtempSync(join(tmpdir(), 'hploop-'));
let n = 0;
function tts(text, voice) {
  const f = join(tmp, `s${n++}.wav`);
  execFileSync('say', ['-v', voice, '-o', f, '--data-format=LEI16@22050', text]);
  return f;
}

// ── 유사도 — 글자 단위 F1 (문장부호·공백 무시) ────────────────────
const chars = (s) => [...(s ?? '').replace(/[\s.,!?。、！？]/g, '')];
function f1(a, b) {
  const A = chars(a), B = chars(b);
  if (!A.length || !B.length) return 0;
  const pool = [...B];
  let hit = 0;
  for (const c of A) { const i = pool.indexOf(c); if (i >= 0) { pool.splice(i, 1); hit++; } }
  return (2 * hit) / (A.length + B.length);
}

// ── A/B 모드 — 두 표기를 같은 조건에서 견준다 ─────────────────────
if (args.includes('--ab')) {
  const target = opt('--ab');                      // 원문 (가나·한자)
  const variants = opt('--variants', '').split('|').filter(Boolean);
  const nativeVoice = LANG === 'ja' ? 'Kyoko' : 'Tingting';
  // 기준선 — 원어 TTS 를 같은 ASR 에 통과시킨 결과. ASR 의 표기 습관(한자 변환 등)을
  // 상쇄해 준다. 후보는 이 기준선과 견준다.
  const files = [tts(target, nativeVoice), ...variants.map((v) => tts(speakable(v), KO_VOICE))];
  const [ref, ...cands] = asr(files, LANG);
  console.log(`원문        ${target}`);
  console.log(`원어 TTS→ASR ${ref}   ← 기준선\n`);
  variants.forEach((v, i) => {
    console.log(`  ${v.padEnd(20)} → ${cands[i].padEnd(24)} 원문 ${(f1(cands[i], target) * 100).toFixed(0)}% · 기준선 ${(f1(cands[i], ref) * 100).toFixed(0)}%`);
  });
  rmSync(tmp, { recursive: true, force: true });
  process.exit(0);
}

// ── 전수 모드 ─────────────────────────────────────────────────────
new Function(readFileSync(DATA, 'utf8'))();
const D = globalThis.HP_DATA;
const rows = [];
for (const sit of D.situations) for (const it of (D.items[LANG]?.[sit.id] || [])) rows.push({ src: it[0], mk: it[3] });
for (const lines of Object.values(D.dialogs?.[LANG] || {})) for (const ln of lines) rows.push({ src: ln[1], mk: ln[4] });
const work = LIMIT ? rows.slice(0, LIMIT) : rows;

// 원어 TTS 를 같은 ASR 에 통과시켜 **기준선**을 만든다. ASR 은 가나 원문을 한자로 바꿔
// 적으므로(`もう ひとくち` → `もう一口`) 원문과 직접 견주면 완전 복원인데도 점수가 깎인다.
// 같은 ASR 을 거친 기준선과 견주면 그 표기 습관이 상쇄된다.
const NATIVE_VOICE = LANG === 'ja' ? 'Kyoko' : 'Tingting';
console.error(`TTS ${work.length * 2}건 생성 중… (한국어 ${KO_VOICE} + 기준선 ${NATIVE_VOICE})`);
const files = work.map((r) => tts(speakable(r.mk), KO_VOICE));
const refFiles = work.map((r) => tts(r.src, NATIVE_VOICE));
console.error(`ASR(${LANG}) 인식 중… (모델 ${MODEL})`);
const heard = asr(files, LANG);
const refs = asr(refFiles, LANG);
rmSync(tmp, { recursive: true, force: true });

const scored = work.map((r, i) => ({
  ...r, heard: heard[i], ref: refs[i],
  score: Math.max(f1(heard[i], r.src), f1(heard[i], refs[i])),   // 원문·기준선 중 좋은 쪽
  voiced: /=[^}]*v/.test(r.mk),                                   // 탁음(˚)이 있는 항목인가
}));
scored.sort((a, b) => a.score - b.score);
const avg = scored.reduce((s, x) => s + x.score, 0) / scored.length;
const exact = scored.filter((x) => chars(x.heard).join('') === chars(x.src).join('')).length;

console.log(`\n음성 폐루프 — ${LANG} ${work.length}건 (한국어 TTS ${KO_VOICE} → ${LANG} ASR)\n`);
console.log(`  글자 F1 평균  ${(avg * 100).toFixed(1)}%`);
console.log(`  완전 복원     ${exact}/${work.length} (${(exact / work.length * 100).toFixed(0)}%)`);
console.log(`  80% 이상      ${scored.filter((x) => x.score >= 0.8).length}/${work.length}`);
// 탁음 유무로 갈라 본다 — TTS 가 ˚ 를 못 읽으므로 탁음 항목은 원리적으로 손해다.
// 두 무리의 차이가 크면 그것은 표기의 결함이 아니라 **이 측정 방법의 한계**다.
const grp = (f) => { const g = scored.filter(f); return g.length ? (g.reduce((s, x) => s + x.score, 0) / g.length * 100).toFixed(1) : '—'; };
if (LANG === 'ja') console.log(`  탁음 있음/없음 ${grp((x) => x.voiced)}% / ${grp((x) => !x.voiced)}%  ← 차이는 측정 한계(TTS 가 ˚ 를 못 읽음)`);

console.log(`\n낮은 순 (표기를 의심할 자리):`);
for (const x of (V ? scored : scored.slice(0, 15))) {
  console.log(`  ${(x.score * 100).toFixed(0).padStart(3)}%${x.voiced ? '˚' : ' '} ${x.src}\n        표기 ${x.mk.replace(/\{([^}=]*)=[^}]*\}/g, '$1')}  →  들린 것 ${x.heard}${x.ref && x.ref !== x.heard ? `   (기준선 ${x.ref})` : ''}`);
}
console.log(`\n※ 절대 점수는 하한이다 — TTS 는 기호를 못 읽는다(파일 머리주석 참조).`);
console.log(`   ˚ 표시된 항목은 탁음이 있어 이 측정에서 원리적으로 손해를 본다.`);
