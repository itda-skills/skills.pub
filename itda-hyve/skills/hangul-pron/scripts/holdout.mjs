// 홀드아웃 검증 — 훈련 셋에서만 사전을 캐고 평가 셋으로 측정한다.
//
// **같은 코퍼스에서 캐서 같은 코퍼스로 재면 안 된다.** 실측으로 그 차이가 드러났다 —
// 사전 자동 채굴은 훈련 셋에서 +17.4pp 였지만 평가 셋에서는 +3.2pp 였다. 대부분이 암기였고,
// 이 분할이 없었으면 잘못된 우선순위를 잡았을 것이다(SPEC-HANGUL-PRON-002 함정 3·4).
//
// 원인은 어휘 분포다 — 코퍼스 어휘의 51%가 딱 한 번만 등장한다(hapax).
//
// 사용: node holdout.mjs <코퍼스경로>
//   코퍼스는 book-data.js 형태(globalThis.HP_BOOK)를 전제한다.
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { pathToFileURL, fileURLToPath } from 'node:url';

const ENGINE = fileURLToPath(new URL('./transcribe.mjs', import.meta.url));
const CORPUS = process.argv.find((a) => !a.startsWith('-') && /\.(js|json)$/.test(a));
if (!CORPUS) { console.error('사용: node holdout.mjs <코퍼스경로>'); process.exit(2); }
// 변형 엔진을 임시 폴더에 쓰는데, 엔진이 `./g2p.mjs` 와 `../data/cmudict.dict` 를 상대경로로
// 찾으므로 그 이웃도 함께 만들어 준다. 안 하면 ERR_MODULE_NOT_FOUND 로 죽는다.
const TMP = fs.mkdtempSync(path.join(os.tmpdir(), 'hp-holdout-'));
const HERE = path.dirname(fileURLToPath(import.meta.url));
fs.mkdirSync(path.join(TMP, '..', 'data'), { recursive: true });
for (const [from, to] of [
  [path.join(HERE, 'g2p.mjs'), path.join(TMP, 'g2p.mjs')],
  [path.join(HERE, '..', 'data', 'cmudict.dict'), path.join(path.dirname(TMP), 'data', 'cmudict.dict')],
]) { try { if (fs.existsSync(from) && !fs.existsSync(to)) fs.symlinkSync(from, to); } catch {} }
process.on('exit', () => { try { fs.rmSync(TMP, { recursive: true, force: true }); } catch {} });

new Function(fs.readFileSync(CORPUS, 'utf8'))();
const all = [];
for (const c of globalThis.HP_BOOK.chapters) for (const s of c.sections) for (const it of s.items) all.push([it[1], it[2]]);
// 결정론적 분할 — 5개 중 1개를 평가 셋으로
const train = all.filter((_, i) => i % 5 !== 0);
const test  = all.filter((_, i) => i % 5 === 0);

const plain = s => s.replace(/\{([^}=]*)=[^}]*\}/g, '$1');
const bare = s => plain(s).replace(/[\s.,!?()]/g, '');
const tok = s => (s.toLowerCase().replace(/[’]/g,"'").match(/[a-z']+/g) || []);
const units = mk => { const out=[]; const re=/\{([^}=]*)=([^}]*)\}|([가-힣])/g; let m;
  while ((m = re.exec(mk))) { if (m[1] !== undefined) for (const ch of m[1]) out.push({syl:ch, code:m[2]}); else out.push({syl:m[3], code:''}); } return out; };
const toMk = us => us.map(u => u.code ? `{${u.syl}=${u.code}}` : u.syl).join('');
const expect = w => ({'^':(w.match(/r/g)||[]).length, o:(w.match(/ph|[fv]/g)||[]).length, '~':(w.match(/th/g)||[]).length});
const marksOf = mk => { const c={'^':0,o:0,'~':0}; for (const m of mk.matchAll(/\{[^}=]*=([^}]*)\}/g)) for (const k of m[1]) if (k in c) c[k]++; return c; };

const orig = fs.readFileSync(ENGINE, 'utf8');
const MARKER = '// ── 철자 → 한글 폴백';
const baseKeys = new Set([...orig.slice(orig.indexOf('const LEX = {'), orig.indexOf(MARKER)).matchAll(/"([^"]+)":/g)].map(m => m[1]));

const extra = new Map();
let round = 0, trans = null, lexKeys = null;

async function build() {
  let inject = '';
  for (const [w, mk] of extra) inject += `  ${JSON.stringify(w)}: [${JSON.stringify(mk)}, null, null],\n`;
  const p = path.join(TMP, `e${round}.mjs`);
  fs.writeFileSync(p, orig.replace(MARKER, `Object.assign(LEX, {\n${inject}});\n${MARKER}`));
  trans = (await import(pathToFileURL(p).href + `?r=${round}`)).transcribe;
  lexKeys = new Set([...baseKeys, ...extra.keys()]);
}

function mine(corpus) {  // 훈련 셋에서만 캔다
  const found = new Map();
  for (const [s, g] of corpus) {
    if (/\(/.test(g)) continue;
    const ts = tok(s);
    const unk = ts.map((t, i) => lexKeys.has(t) ? -1 : i).filter(i => i >= 0);
    if (unk.length !== 1) continue;
    const i = unk[0];
    const before = ts.slice(0, i).length ? trans(ts.slice(0, i).join(' ')) : '';
    const after = ts.slice(i + 1).length ? trans(ts.slice(i + 1).join(' ')) : '';
    const G = units(g), Bu = units(before), Au = units(after);
    let ok = Bu.length + Au.length < G.length + 1;
    for (let k = 0; k < Bu.length && ok; k++) if (G[k].syl !== Bu[k].syl) ok = false;
    for (let k = 0; k < Au.length && ok; k++) if (G[G.length - Au.length + k].syl !== Au[k].syl) ok = false;
    if (!ok) continue;
    const mid = G.slice(Bu.length, G.length - Au.length);
    if (!mid.length) continue;
    const w = ts[i];
    if (!found.has(w)) found.set(w, new Map());
    const mk = toMk(mid);
    found.get(w).set(mk, (found.get(w).get(mk) || 0) + 1);
  }
  let added = 0;
  for (const [w, forms] of found) {
    if (extra.has(w)) continue;
    const best = [...forms].sort((a, b) => b[1] - a[1])[0][0];
    const n = expect(w), gm = marksOf(best);
    if (gm['^'] < n['^'] || gm.o < n.o || gm['~'] < n['~']) continue;
    extra.set(w, best); added++;
  }
  return added;
}

const score = (corpus) => {
  let k = 0;
  for (const [s, g] of corpus) if (bare(trans(s)) === bare(g)) k++;
  return `${k}/${corpus.length} (${(k / corpus.length * 100).toFixed(1)}%)`;
};

await build();
console.log(`분할 — 훈련 ${train.length} · 평가 ${test.length}\n`);
console.log(`채굴 전   훈련 ${score(train)}   평가 ${score(test)}`);
for (round = 1; round <= 4; round++) {
  const n = mine(train);          // ← 훈련 셋에서만
  if (!n) break;
  await build();
  console.log(`라운드 ${round}  +${n}개 (누적 ${extra.size})   훈련 ${score(train)}   평가 ${score(test)}`);
}
console.log(`\n채굴 엔트리 ${extra.size}개 — 평가 셋은 채굴에 한 번도 쓰이지 않았다.`);

// ── 평가 셋 실패의 내역 ────────────────────────────────────────────
const trainVocab = new Set(train.flatMap(([s]) => tok(s)));
let failUnseen = 0, failKnown = 0;
for (const [s, g] of test) {
  if (bare(trans(s)) === bare(g)) continue;
  if (tok(s).some(w => !lexKeys.has(w))) failUnseen++; else failKnown++;
}
console.log(`\n평가 셋 실패 ${failUnseen + failKnown}건 내역`);
console.log(`  사전에 없는 단어 포함 (폴백 품질 문제)  ${failUnseen}건`);
console.log(`  전부 사전에 있는데 실패 (규칙 문제)     ${failKnown}건`);
