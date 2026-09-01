// 원천 데이터 검증 — **병음이 그 한자의 올바른 읽기인가.**
//
// 지금까지의 검사(check-spec-zh · check-data)는 전부 "한글이 병음과 맞는가" 만 봤다.
// **병음 자체가 맞는지는 아무도 보지 않았다.** 병음이 틀리면 생성기는 그 틀린 병음을
// 충실하게 한글로 옮기고, 세 층 전부 통과한다. 다음자(多音字)가 걸린 자리가 특히 그렇다.
//
//   한자 → [pypinyin 사전] → 사전 병음 → [우리 성조 변화 C7~C9] → 기대 병음
//                                                                    ↕ 대조
//                                                          데이터의 병음 필드
//
// LLM 판정이 아니라 **사전 대조**라 증거로서 가장 강하다. 덤으로 우리 성조 변화 구현도
// 같이 검증된다 — 사전형(3성+3성)이 데이터의 변화형과 맞아떨어져야 하기 때문이다.
//
// 필요: python3 + pypinyin (`pip install pypinyin`)
// 사용: node verify-pinyin.mjs [--python <경로>] [--data <data.js>] [--verbose]

import { readFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { tokenize, applySandhi, respell } from './pinyin.mjs';

const args = process.argv.slice(2);
const V = args.includes('--verbose');
const opt = (name, dflt) => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : dflt; };
const PY = opt('--python', `${process.env.HOME}/.venv/bin/python3`);
const DATA = opt('--data', `${process.env.HOME}/orca/workspaces/website/한글영어/demo-apps/hangul-pron/data.js`);

// ── 데이터 읽기 ───────────────────────────────────────────────────
new Function(readFileSync(DATA, 'utf8'))();
const D = globalThis.HP_DATA;
const rows = [];
for (const sit of D.situations) for (const it of (D.items.zh?.[sit.id] || [])) rows.push({ han: it[0], py: it[2], where: `${sit.id} ${it[0]}` });
for (const [sid, lines] of Object.entries(D.dialogs?.zh || {})) for (const ln of lines) rows.push({ han: ln[1], py: ln[3], where: `대화-${sid} ${ln[1]}` });

// ── 사전 병음 (pypinyin) ──────────────────────────────────────────
const PY_SRC = `
import sys, json
from pypinyin import pinyin, Style
out = []
for line in sys.stdin.read().split("\\n"):
    if not line: continue
    # 구(句) 단위로 넘겨야 다음자가 문맥으로 갈린다 (낱자로 주면 1순위만 나온다)
    syls = [p[0] for p in pinyin(line, style=Style.TONE, errors=lambda x: None)]
    out.append([s for s in syls if any('\\u4e00' <= c <= '\\u9fff' for c in line) and s.strip()])
print(json.dumps(out, ensure_ascii=False))
`;
let dict;
try {
  const res = execFileSync(PY, ['-c', PY_SRC], { input: rows.map((r) => r.han).join('\n'), encoding: 'utf8' });
  dict = JSON.parse(res);
} catch (e) {
  console.error(`pypinyin 실행 실패 (${PY}): ${e.message}`);
  console.error('설치: python3 -m venv ~/.venv && ~/.venv/bin/pip install pypinyin');
  console.error('다른 파이썬을 쓰려면: node verify-pinyin.mjs --python <경로>');
  process.exit(2);
}

// ── 대조 ──────────────────────────────────────────────────────────
// 경성화는 **표기 선택**이지 오류가 아니다. 사전은 본디 성조를 주지만(个 gè · 服 fú ·
// 谢 xiè) 실제 발화에서는 경성이 된다 — 衣服 yīfu · 谢谢 xièxie · 帮帮 bāngbang.
// 그래서 **데이터가 경성인데 사전이 성조인 경우**는 따로 분류한다(오류 아님).
// 반대(데이터가 성조인데 사전이 경성)는 놓치면 안 되므로 성조 불일치로 본다.

// pypinyin 이 문맥을 못 잡는 자리 — 사전 쪽이 틀렸다고 판정된 것만 좁게 적는다.
// `哇` 는 문말 어기조사일 때 경성(wa)이지만 **문두 감탄사일 때는 wā** 다. pypinyin 은
// 기본 읽기로 경성을 주므로, 데이터의 wā 가 맞다.
// 전부 **문맥으로 갈리는 다음자**이고, 확인 결과 데이터 쪽이 맞다. 좁게 적는다 —
// 넓히면 진짜 오류를 덮는다.
const DICT_BLIND = [
  { han: '哇', dict: 'wa', data: 'wā', why: '문두 감탄사 (사전 기본은 문말 조사)' },
  { han: '地', dict: 'dì', data: 'de', why: '부사 접미사 (慢慢地·轻轻地)' },
  { han: '长', dict: 'zhǎng', data: 'cháng', why: '길다 (자라다가 아니다)' },
  { han: '长', dict: 'zháng', data: 'cháng', why: '길다 (자라다가 아니다)' },
  { han: '弹', dict: 'dàn', data: 'tán', why: '튀다 (탄알이 아니다)' },
  { han: '剥', dict: 'bō', data: 'bāo', why: '구어 — 껍질을 벗기다' },
  { han: '系', dict: 'xì', data: 'jì', why: '구어 — 매다 (안전벨트)' },
  { han: '谁', dict: 'shuí', data: 'shéi', why: '구어 발음' },
  { han: '咯', dict: 'gē', data: 'lo', why: '어기조사' },
  { han: '得', dict: 'dé', data: 'děi', why: '~해야 한다' },
  { han: '得', dict: 'dé', data: 'déi', why: '~해야 한다 (뒤 3성으로 C7 변화)' },
  { han: '待', dict: 'dài', data: 'dāi', why: '머무르다 (기다리다가 아니다)' },
  { han: '干', dict: 'gàn', data: 'gān', why: '마르다 (하다가 아니다)' },
  { han: '找', dict: 'zháo', data: 'zhǎo', why: '찾다' },
  { han: '倒', dict: 'dào', data: 'dǎo', why: '넘어지다 (붓다가 아니다)' },
  { han: '撒', dict: 'sā', data: 'sǎ', why: '흩뿌리다' },
  { han: '嘀', dict: 'dí', data: 'dī', why: '의성어 (경적)' },
  { han: '更', dict: 'gēng', data: 'gèng', why: '더욱' },
  { han: '杠', dict: 'gāng', data: 'gàng', why: '철봉' },
  { han: '只', dict: 'zhí', data: 'zhī', why: '양사' },
  { han: '两', dict: 'liáng', data: 'liǎng', why: '둘' },
  { han: '耳', dict: 'ér', data: 'ěr', why: '귀 (儿 이 아니다)' },
  { han: '很', dict: 'hén', data: 'hěn', why: '3성 — 뒤 글자 오독으로 인한 사전 쪽 변화' },
  { han: '有', dict: 'yóu', data: 'yǒu', why: '3성 — 뒤 글자 오독으로 인한 사전 쪽 변화' },
  { han: '蹼', dict: 'pú', data: 'pǔ', why: '물갈퀴' },
  { han: '呱', dict: 'gū', data: 'guā', why: '의성어 (개구리)' },
  { han: '头', dict: 'tou', data: 'tóu', why: '머리 — 경성 아님' },
  { han: '嗯', dict: '', data: 'en', why: '사전이 읽지 못함' },
  { han: '转', dict: 'zhuǎn', data: 'zhuàn', why: '회전하다 (방향을 틀다가 아니다)' },
  { han: '卷', dict: 'juàn', data: 'juǎn', why: '말리다 (책 권수가 아니다)' },
  { han: '卷', dict: 'juàn', data: 'juán', why: '말리다 — 뒤 3성으로 C7 변화' },
  { han: '有', dict: 'yǒu', data: 'yóu', why: '뒤 3성으로 C7 변화 (사전은 변화 전)' },
  { han: '一', dict: 'yì', data: 'yí', why: 'C9 — 사전과 一 변화 규칙이 다르다' },
];

const bad = { 읽기: [], 성조: [], 경성: [], 사전한계: [] };
let checked = 0;

rows.forEach((r, i) => {
  const dictSyls = dict[i] || [];
  if (!dictSyls.length) return;                       // 한자가 없는 줄
  // 사전 병음에 성조 변화를 적용한다. 여기서는 **한자를 알기 때문에** 어휘 규칙(C8·C9)도
  // 정확히 켤 수 있다 — 一·不 인 음절만 고른다. (병음만 보면 衣·布 까지 걸린다.)
  const hanzi = [...r.han].filter((c) => c >= '\u4e00' && c <= '\u9fff');
  const dictToks = tokenize(dictSyls.join(' '));
  const dictSylList = dictToks.flatMap((t) => (t.kind === 'word' ? t.syls : []));
  const chars = new Map(dictSylList.map((s, n) => [s, hanzi[n]]));
  applySandhi(dictToks, { lexical: true, chars });
  const expect = dictSylList;
  const actual = tokenize(r.py).flatMap((t) => (t.kind === 'word' ? t.syls : []));
  checked++;

  if (expect.length !== actual.length) {
    // 사전이 못 읽는 글자(嗯)나 얼화(哪儿 nǎr)는 음절 수가 어긋난다 — 데이터가 맞다.
    const blind = /[嗯呗嘞噢哦嗨哟]/.test(r.han) || actual.some((a) => a.erhua);
    bad[blind ? '사전한계' : '읽기'].push([r.where,
      blind ? '음절 수 차이 — 사전이 못 읽는 글자 또는 얼화' : `음절 수 ${expect.length} vs 데이터 ${actual.length}`,
      expect.map(respell).join(' '), actual.map(respell).join(' ')]);
    return;
  }
  expect.forEach((e, k) => {
    const a = actual[k];
    const eBase = e.initial + e.final, aBase = a.initial + a.final;
    if (eBase !== aBase) {
      const blind = DICT_BLIND.find((b) => b.han === chars.get(e) && b.data === respell(a));
      bad[blind ? '사전한계' : '읽기'].push([r.where,
        blind ? `${blind.han} — ${blind.why}` : `${k + 1}번째 음절`, respell(e), respell(a)]);
      return;
    }
    if (e.tone === a.tone) return;
    if (a.tone === 0) { bad.경성.push([r.where, aBase, respell(e), respell(a)]); return; }  // 경성화 — 오류 아님
    const blind = DICT_BLIND.find((b) => b.han === chars.get(e) && b.dict === respell(e) && b.data === respell(a));
    if (blind) { bad.사전한계.push([r.where, `${blind.han} — ${blind.why}`, respell(e), respell(a)]); return; }
    bad.성조.push([r.where, `${k + 1}번째 음절`, respell(e), respell(a)]);
  });
});

// ── 보고 ──────────────────────────────────────────────────────────
console.log(`병음 사전 대조 — 중국어 ${checked}항목 (pypinyin)\n`);
const label = { 읽기: '읽기 불일치 (다음자 오선택 의심 — 중대)', 성조: '성조 불일치',
  경성: '경성 처리 (오류 아님)', 사전한계: 'pypinyin 한계 (데이터가 맞다)' };
for (const k of ['읽기', '성조', '경성', '사전한계']) {
  const list = bad[k];
  console.log(`■ ${label[k]} — ${list.length}건`);
  for (const [where, what, exp, act] of (V ? list : list.slice(0, 8))) {
    console.log(`   ${where}\n     ${what}: 사전 ${exp} / 데이터 ${act}`);
  }
  if (!V && list.length > 8) console.log(`   … 그 외 ${list.length - 8}건 (--verbose)`);
  console.log();
}
const fatal = bad.읽기.length + bad.성조.length;
console.log(fatal ? `확인 필요 ${fatal}건` : '읽기·성조 불일치 없음');
process.exit(fatal ? 1 : 0);
