// 음소(ARPABET) → 한글 마크업 합성기 (v2, 음절화 2패스) + 철자→음소 규칙 + CMUdict 로더
// SPEC §2-1 E1~E7 을 음소 층에서 구현. 결정론적. dev 기준: 훈련 채굴쌍 114개.
import fs from 'node:fs';

const CHO='ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ';
const JUNG='ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ';
const JONG=' ㄱㄲㄳㄴㄵㄶㄷㄹㄺㄻㄼㄽㄾㄿㅀㅁㅂㅄㅅㅆㅇㅈㅊㅋㅌㅍㅎ';
const comp=(c,v,j=' ')=>String.fromCharCode(0xac00+(CHO.indexOf(c)*21+JUNG.indexOf(v))*28+JONG.indexOf(j));

const VOWELS=new Set(['AA','AE','AH','AO','AW','AY','EH','ER','EY','IH','IY','OW','OY','UH','UW']);
const isV=p=>VOWELS.has(p.replace(/[0-9]/,''));
const b=p=>(p||'').replace(/[0-9]/,'');
const st=p=>{const m=p.match(/[0-9]/);return m?+m[0]:1;};

const ONS={P:'ㅍ',B:'ㅂ',T:'ㅌ',D:'ㄷ',K:'ㅋ',G:'ㄱ',CH:'ㅊ',JH:'ㅈ',S:'ㅆ',SH:'ㅅ',Z:'ㅈ',ZH:'ㅈ',
  HH:'ㅎ',M:'ㅁ',N:'ㄴ',L:'ㄹ',R:'ㄹ',F:'ㅃ',V:'ㅂ',TH:'ㅆ',DH:'ㄷ'};
const OMARK={R:['^',''],F:['','o'],V:['','o'],TH:['','~'],DH:['','~']};
const TENSE={P:'ㅃ',T:'ㄸ',K:'ㄲ'};
const EP={P:'프',B:'브',T:'트',D:'드',K:'크',G:'그',S:'스',Z:'즈',F:'쁘',V:'브',TH:'쓰',DH:'드',
  CH:'치',JH:'지',SH:'쉬',M:'므',N:'느',HH:'흐',L:'을',R:'르'};
const NASAL={M:'ㅁ',N:'ㄴ',NG:'ㅇ'};
const WG={'ㅏ':'ㅘ','ㅓ':'ㅝ','ㅔ':'ㅞ','ㅐ':'ㅙ','ㅣ':'ㅟ','ㅗ':'ㅝ','ㅜ':'ㅜ'};
const YG={'ㅏ':'ㅑ','ㅓ':'ㅕ','ㅗ':'ㅛ','ㅜ':'ㅠ','ㅔ':'ㅖ','ㅐ':'ㅒ','ㅣ':'ㅣ'};
const CODABLE=new Set(['M','N','NG','L','P','T','K','B','R']);

export function synthWord(phonesIn){
  let ph=phonesIn.filter(p=>p!=='');
  if(!ph.length)return '';
  // ER + 모음 → AH + R온셋 (데인저러쓰·삐겨링)
  for(let k=0;k<ph.length-1;k++){
    if(b(ph[k])==='ER'&&isV(ph[k+1])){ph.splice(k,1,'AH'+st(ph[k]),'R');}
  }
  // ── 패스 1: 음절화 ──
  const syls=[]; // {onset:[], nuc:null, coda:[]}
  let i=0, cur={onset:[],nuc:null,coda:[]};
  const nuclei=ph.filter(isV).length;
  while(i<ph.length){
    if(isV(ph[i])){
      if(cur.nuc){syls.push(cur);cur={onset:[],nuc:null,coda:[]};}
      cur.nuc=ph[i];i++;
      continue;
    }
    // 자음 클러스터 수집
    const cl=[];while(i<ph.length&&!isV(ph[i])){cl.push(b(ph[i]));i++;}
    if(!cur.nuc){cur.onset.push(...cl);continue;}        // 어두
    if(i>=ph.length){cur.coda.push(...cl);continue;}     // 어말
    // 모음 사이: 클러스터 분배
    if(cl.length===1){
      if(cl[0]==='NG')cur.coda.push('NG');
      else{syls.push(cur);cur={onset:[cl[0]],nuc:null,coda:[]};}
    } else {
      let k=0;
      const stopNasal=['P','T','K','B','D','G'].includes(cl[0])&&['M','N'].includes(cl[1]);
      if(CODABLE.has(cl[0])&&!stopNasal&&!(cl[0]==='T'&&cl[1]==='H')){cur.coda.push(cl[0]);k=1;}
      syls.push(cur);cur={onset:cl.slice(k),nuc:null,coda:[]};
    }
  }
  if(cur.nuc||cur.onset.length||cur.coda.length)syls.push(cur);

  // ── 패스 2: 렌더 ──
  const out=[]; // {cho,jung,jong,top,aft}
  const push=(cho,jung,jong=' ',top='',aft='')=>out.push({cho,jung,jong,top,aft});
  const EPT={T:'뜨',K:'끄',P:'쁘'};
  const ep=(c,jong=' ',tense=false)=>{const s=(tense&&EPT[c])||EP[c]||'으';const d=s.charCodeAt(0)-0xac00;
    push(CHO[Math.floor(d/588)],JUNG[Math.floor((d%588)/28)],jong!==' '?jong:JONG[d%28],c==='R'?'^':'',
      (OMARK[c]&&c!=='R')?OMARK[c][1]:'');
    out[out.length-1].ep=true;};
  for(let si=0;si<syls.length;si++){
    const S=syls[si], prev=out[out.length-1];
    let onset=S.onset.slice();
    // 활음 분리
    let glide=null;
    if(onset.length>=2&&(onset[onset.length-1]==='W'||onset[onset.length-1]==='Y')&&onset[onset.length-2]!=='S')glide=onset.pop();
    else if(onset.length===1&&(onset[0]==='W'||onset[0]==='Y')){glide=onset[0];onset=[];}
    // 온셋 앞자음 → 에펜테시스 (E1 된소리 판단 포함)
    let tense=false;
    for(let k=0;k<onset.length-1;k++){
      const c=onset[k],nx=onset[k+1];
      if(c==='S'&&TENSE[nx]){push('ㅅ','ㅡ');out[out.length-1].ep=true;tense=true;continue;}
      if(nx==='L'){ep(c,'ㄹ',tense);continue;}   // 클라임·슬로우
      ep(c,' ',tense);continue;
    }
    let head=onset[onset.length-1];
    if(S.nuc==null){for(const c of S.coda)ep(c);if(head)ep(head);continue;}
    let cho=head?(tense&&TENSE[head]?TENSE[head]:ONS[head]||'ㅇ'):'ㅇ';
    let [top,aft]=head&&OMARK[head]?OMARK[head]:['',''];
    // 모음 사이 무강세 T·D → ㄷ (히딩·타이디·와이덜; 교재는 플랩을 ㄷ/ㄹ 로 오간다 — ㄷ 다수)
    if((head==='T'||head==='D')&&onset.length===1&&si>0&&syls[si-1].nuc&&!syls[si-1].coda.length&&st(S.nuc)===0){
      const pv=b(syls[si-1].nuc);
      cho=(head==='T'&&(pv==='IY'||pv==='EY'||b(S.nuc)==='ER'))?'ㄹ':'ㄷ';top='';aft='';}
    // L 겹침: 모음 뒤 초성 ㄹ(R 아님) → 앞 음절에 받침 ㄹ (빨로우·톨럴·삘링)
    if(head==='L'&&si>0&&prev&&prev.jong===' ')prev.jong='ㄹ';
    // 파열음 받침 + L 온셋 → 받침을 두고 '클·블·플' 을 끼운다 (quickly → 퀵클리).
    // 받침에 ㄹ 을 얹을 수 없어 L 이 통째로 사라지는 것을 막는다.
    else if(head==='L'&&si>0&&prev&&['ㄱ','ㅂ','ㄷ','ㅋ','ㅌ','ㅍ'].includes(prev.jong)){
      const back={'ㄱ':'K','ㅋ':'K','ㅂ':'P','ㅍ':'P','ㄷ':'T','ㅌ':'T'}[prev.jong];
      ep(back,'ㄹ');
    }
    const nb=b(S.nuc), stress=st(S.nuc);
    // 중성 결정
    let jung,second=null;
    const hasCoda=S.coda.length>0, codaSet=new Set(S.coda);
    switch(nb){
      case 'AA':jung='ㅏ';break; case 'AE':jung='ㅐ';break;
      case 'AH':jung='ㅓ';break; case 'AO':jung='ㅗ';break;
      case 'EH':jung='ㅔ';break; case 'IH':jung='ㅣ';break; case 'IY':jung='ㅣ';break;
      // UH 는 L 코다 앞에서 '우을' 로 벌어진다 (pull/pulling → 푸을) — E4 의 어중 확장
      case 'UH':jung='ㅜ';if(codaSet.has('L'))second='ㅡ';break; case 'UW':jung='ㅜ';break;
      case 'ER':jung='ㅓ';break;
      case 'AW':jung='ㅏ';second='ㅜ';break; case 'AY':jung='ㅏ';second='ㅣ';break;
      case 'EY':jung='ㅔ';second='ㅣ';break; case 'OY':jung='ㅗ';second='ㅣ';break;
      case 'OW':{
        // R 이 홀로 온셋일 때만 OW 를 원순화한다 (roll → 뤄ˇ을).
        // 자음군 안의 R 은 해당 없음 — stroke 는 스뜨로웈 이지 스뜨뤅 이 아니다.
        if(head==='R'&&onset.length===1){jung='ㅝ';break;}
        const nextIsV=si+1<syls.length&&!syls[si+1].onset.length;
        if(codaSet.has('M')||codaSet.has('N')||codaSet.has('L')||codaSet.has('V')||codaSet.has('F')||nextIsV)jung='ㅗ';
        else {jung='ㅗ';second='ㅜ';}
        break;}
      default:jung='ㅓ';
    }
    if(head==='F'&&b(S.nuc)==='AH'&&st(S.nuc)===0&&(S.coda[0]==='L'||0))jung='ㅜ';
    // 시블런트와 Z 사이 약모음 → 이 (피씨즈·페이지즈)
    if((nb==='AH'||nb==='IH')&&stress===0&&['S','Z','SH','CH','JH'].includes(head)&&S.coda.length===1&&S.coda[0]==='Z')jung='ㅣ';
    if(glide==='W')jung=WG[jung]||jung;
    if(glide==='Y')jung=YG[jung]||jung;
    if(head==='SH'){const SG={'ㅜ':'ㅠ','ㅔ':'ㅞ','ㅣ':'ㅟ','ㅏ':'ㅑ','ㅓ':'ㅕ','ㅗ':'ㅛ'};jung=SG[jung]||jung;}
    // CH 도 SH 처럼 뒤 모음을 활음화한다 (cheese → 취즈, chair → 췌얼)
    if(head==='CH'){const CG={'ㅣ':'ㅟ','ㅔ':'ㅞ'};jung=CG[jung]||jung;}
    if(head==='W'){jung=WG[jung]||jung;cho='ㅇ';}
    if(head==='Y'){jung=YG[jung]||jung;cho='ㅇ';}
    push(cho,jung,' ',top,aft);
    if(second)push('ㅇ',second);
    if(nb==='ER'){const l=out[out.length-1];l.jong='ㄹ';l.top+='^';}
    // ── 코다 렌더 ──
    let coda=S.coda.slice();
    const lastSyl=si===syls.length-1;
    // D 탈락: N·모음 + D + Z (엔즈·싸이즈·핸즈)
    for(let k=0;k<coda.length-1;k++)if(coda[k]==='D'&&coda[k+1]==='Z')coda.splice(k,1);
    for(let k=0;k<coda.length;k++){
      const c=coda[k], lastS=out[out.length-1], isFinal=lastSyl&&k===coda.length-1;
      const nxt=coda[k+1];
      if(NASAL[c]&&lastS.jong===' '){lastS.jong=NASAL[c];continue;}
      if(c==='M'&&lastS.jong==='ㄹ'){lastS.jong='ㄻ';continue;}   // 앎
      if(c==='N'&&lastS.jong==='ㄹ'){continue;}                    // 털즈
      if(c==='R'){
        if(lastS.jong===' '&&lastS.jung==='ㅏ'){lastS.jong='ㄹ';if(!lastS.top.includes('^'))lastS.top+='^';}
        else push('ㅇ','ㅓ','ㄹ','^','');
        continue;}
      if(c==='L'){
        if(nxt&&EP[nxt]&&isFinalCluster(k)){ep(nxt,'ㄹ');k++;continue;} // (미도달 가드)
        if(!lastSyl&&lastS.jong===' '){lastS.jong='ㄹ';continue;}       // 홀딩
        push('ㅇ','ㅡ','ㄹ');continue;}                                  // E4 을
      // C + L 어말 → 블·플·틀 (테이블·피플)
      if(EP[c]&&nxt==='L'&&lastSyl&&(k+1===coda.length-1||['Z','S'].includes(coda[k+2]))){ep(c,'ㄹ');k++;continue;}
      if(c==='T'&&nxt==='S'&&(lastS.jong==='ㄹ'||lastS.jong===' ')){push('ㅊ','ㅡ');k++;continue;} // 츠
      if(c==='T'&&lastS.jong===' '&&!lastS.ep){
        if(isFinal&&S.nuc&&st(S.nuc)===0&&b(S.nuc)==='AH'){ep('T');continue;} // 콰이어트
        lastS.jong='ㅌ';continue;}                                     // E3
      if(c==='P'&&lastS.jong===' '&&!lastS.ep){lastS.jong='ㅍ';continue;}
      if(c==='B'&&lastS.jong===' '&&!lastS.ep){lastS.jong='ㅂ';continue;}
      if(c==='K'&&lastS.jong===' '&&!lastS.ep){
        lastS.jong=((lastS.jung==='ㅣ'&&lastS.cho==='ㅇ')||(lastS.jung==='ㅜ'&&lastS.cho!=='ㄹ'))?'ㅋ':'ㄱ';
        continue;}
      if(c==='D'){ep('D');continue;}
      if(c==='S'){if(nxt&&!isFinal)push('ㅅ','ㅡ');else push('ㅆ','ㅡ');out[out.length-1].ep=true;continue;}
      if(c==='Z'){
        if(lastS.jong==='ㄹ'&&lastS.top.includes('^')&&S.nuc&&b(S.nuc)==='ER'&&st(S.nuc)===0)push('ㅅ','ㅡ'); // 삥걸스
        else push('ㅈ','ㅡ');
        out[out.length-1].ep=true;continue;}
      ep(c);
    }
    function isFinalCluster(){return false;}
  }
  // 어말 자음+AH0+L / +N 형은 철자단에서 @EL/@EN 로 이미 압축됨 (spell/cmu 후처리)
  return out.map(u=>{
    const syl=comp(u.cho,u.jung,u.jong);
    const code=(u.top.includes('^')?'^':'')+(u.aft||'');
    return code?`{${syl}=${code}}`:syl;
  }).join('');
}

// C+AH0+L(+Z) / C+AH0+N 압축: 핸들·젠틀·오픈 — 음소 열 선처리
export function reduceWeak(phones){
  const ph=phones.slice();
  for(let i=ph.length-1;i>=2;i--){
    if(b(ph[i])==='L'&&/^AH0$/.test(ph[i-1])&&!isV(ph[i-2])&&(i===ph.length-1||['Z','S'].includes(b(ph[i+1])))){
      ph.splice(i-1,1); // AH0 삭제 → C L 클러스터 → 에펜테시스+ㄹ받침 경로
    }
    if(b(ph[i])==='N'&&/^AH0$/.test(ph[i-1])&&!isV(ph[i-2])&&['P','K','T','D'].includes(b(ph[i-2]))
       &&(i===ph.length-1||(b(ph[i+1]||'')==='IH'&&b(ph[i+2]||'')==='NG'))){
      ph.splice(i-1,1);
    }
  }
  return ph;
}

export function loadCmu(p){
  const map=new Map();
  for(const line of fs.readFileSync(p,'utf8').split('\n')){
    if(!line||line.startsWith(';;;'))continue;
    const sp=line.indexOf(' ');if(sp<0)continue;
    const w=line.slice(0,sp);
    if(w.includes('('))continue;
    map.set(w.toLowerCase(),line.slice(sp+1).trim().split(/\s+/));
  }
  return map;
}

// CMU 발음의 철자 기반 후처리 — 교재 표기 관행에 맞춘다
export function cmuAdjust(word,phones){
  let ph=phones.slice();
  // -ed 를 철자대로 '드' 로 (드레스드·삐니쉬드): 어말 T 이고 철자가 ed 로 끝나면 D
  if(/[^aeiou]ed$/.test(word)&&b(ph[ph.length-1])==='T')ph[ph.length-1]='D';
  // 모음 사이 TH → DH — -ther 형과 without 만 (씽 계열 오적용 방지)
  if(/ther|^without$/.test(word))for(let i=1;i<ph.length-1;i++)if(ph[i]==='TH'&&isV(ph[i-1])&&isV(ph[i+1]))ph[i]='DH';
  return reduceWeak(ph);
}

// ── 철자 → 음소 (무의존 규칙 G2P) ──
export function spell2phones(word){
  let w=word.toLowerCase().replace(/[^a-z]/g,'');
  if(!w)return [];
  const ph=[];let stressGiven=false;
  const V=(sym)=>{ph.push(sym+(stressGiven?0:1));stressGiven=true;};
  const VW=/[aeiouy]/;
  let suffix=[];
  if(w.length>4&&w.endsWith('ing')){suffix=['IH0','NG'];w=w.slice(0,-3);
    if(w.length>2&&w.at(-1)===w.at(-2))w=w.slice(0,-1);}
  let plural=false;
  if(w.length>3&&w.endsWith('s')&&!w.endsWith('ss')&&!w.endsWith('us')&&!w.endsWith('is')){plural=true;w=w.slice(0,-1);
    if(w.endsWith('ie')){w=w.slice(0,-2)+'y';}}
  let past=false;
  if(w.length>4&&w.endsWith('ed')&&!VW.test(w[w.length-3])===false){past=true;w=w.slice(0,-2);
    if(w.length>2&&w.at(-1)===w.at(-2))w=w.slice(0,-1);}
  let magic=false;
  if(w.length>2&&w.endsWith('e')&&!/[aeiou]e$/.test(w)&&!w.endsWith('le')){magic=true;w=w.slice(0,-1);}
  let i=0;
  const CMAP={b:'B',c:'K',d:'D',f:'F',g:'G',h:'HH',j:'JH',k:'K',l:'L',m:'M',n:'N',p:'P',r:'R',s:'S',t:'T',v:'V',w:'W',x:'X',y:'Y',z:'Z'};
  while(i<w.length){
    const r3=w.slice(i,i+3), r2=w.slice(i,i+2), c=w[i];
    const atEnd=(n)=>i+n>=w.length;
    if(w.slice(i)==='tion'){ph.push('SH','AH0','N');break;}
    if(w.slice(i)==='sion'){ph.push('ZH','AH0','N');break;}
    if(w.slice(i)==='ture'){ph.push('CH','ER0');break;}
    if(r3==='igh'){V('AY');i+=3;continue;}
    if(r3==='ear'&&atEnd(3)){V('IH');ph.push('R');i+=3;continue;}
    if(r2==='ck'){ph.push('K');i+=2;continue;}
    if(r2==='ng'&&(atEnd(2)||!VW.test(w[i+2]))){ph.push('NG');i+=2;continue;}
    if(r2==='ng'){ph.push('NG','G');i+=2;continue;}
    if(r2==='wh'){ph.push('W');i+=2;continue;}
    if(r2==='ph'){ph.push('F');i+=2;continue;}
    if(r2==='sh'){ph.push('SH');i+=2;continue;}
    if(r2==='ch'){ph.push('CH');i+=2;continue;}
    if(r2==='th'){ph.push(i>0&&VW.test(w[i-1]||'')&&VW.test(w[i+2]||'')?'DH':'TH');i+=2;continue;}
    if(r2==='kn'&&i===0){ph.push('N');i+=2;continue;}
    if(r2==='wr'&&i===0){ph.push('R');i+=2;continue;}
    if(r2==='qu'){ph.push('K','W');i+=2;continue;}
    if(r2==='ee'||r2==='ea'){V('IY');i+=2;continue;}
    if(r2==='oo'){V('UW');i+=2;continue;}
    if(r2==='oa'){V('OW');i+=2;continue;}
    if(r2==='ou'){V('AW');i+=2;continue;}
    if(r2==='ow'){V(atEnd(2)?'OW':'AW');i+=2;continue;}
    if(r2==='ai'||r2==='ay'||r2==='ei'||r2==='ey'){V('EY');i+=2;continue;}
    if(r2==='oi'||r2==='oy'){V('OY');i+=2;continue;}
    if(r2==='au'||r2==='aw'){V('AO');i+=2;continue;}
    if(r2==='ew'||r2==='ue'){V('UW');i+=2;continue;}
    if(VW.test(c)){
      if(w[i+1]==='r'&&(atEnd(2)||!VW.test(w[i+2]))){
        if(c==='a'){V('AA');ph.push('R');}
        else if(c==='o'){V('AO');ph.push('R');}
        else ph.push('ER'+(stressGiven?0:1)),stressGiven=true;
        i+=2;continue;}
      if(c==='y'){ if(atEnd(1)){ph.push('IY0');} else if(VW.test(w[i+1]))ph.push('Y'); else V('IH'); i++;continue;}
      if(magic&&i===w.length-2){V({a:'EY',i:'AY',o:'OW',u:'UW',e:'IY'}[c]||'EH');i++;continue;}
      if(c==='a'&&w[i+1]==='l'&&w[i+2]==='l'){V('AO');i++;continue;}
      if(i===0&&c==='w'&&0){}
      if(!stressGiven){
        let sym={a:'AE',e:'EH',i:'IH',o:'AA',u:'AH'}[c];
        if(c==='a'&&ph[ph.length-1]==='W')sym='AA';
        V(sym);
      } else ph.push(c==='i'?'IH0':'AH0');
      i++;continue;
    }
    if(c===w[i+1]){i++;continue;}
    if(c==='c'&&/[eiy]/.test(w[i+1]||''))ph.push('S');
    else if(c==='g'&&/[eiy]/.test(w[i+1]||'')&&i>0)ph.push('JH');
    else if(c==='x')ph.push('K','S');
    else if(c==='l'&&w[i+1]==='e'&&atEnd(2)){ph.push('AH0','L');i+=2;continue;}
    else ph.push(CMAP[c]||'T');
    i++;
  }
  if(past){const l=ph[ph.length-1];if(l==='T'||l==='D')ph.push('IH0','D');else ph.push('D');}
  if(plural){const l=ph[ph.length-1];if(['S','SH','CH','Z','ZH','JH'].includes(l))ph.push('IH0','Z');else if(['P','T','K','F','TH'].includes(l))ph.push('S');else ph.push('Z');}
  ph.push(...suffix);
  return reduceWeak(ph);
}
