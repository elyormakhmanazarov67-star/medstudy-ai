(() => {
  'use strict';
  const webapp = window.Telegram?.WebApp;
  webapp?.ready();
  webapp?.expand();

  // Only appearance preferences persist in the browser, never learning conversations.
  // Migrating earlier blue preference to the new white-and-green design.
  const THEME_KEY='medstudy_theme_v1';
  const THEME_COLORS={white:'#f6faf6',black:'#001a10'};
  const ALLOWED_THEMES=new Set(['white','black']);
  let currentTheme='white';
  try {
    const previous=window.localStorage.getItem(THEME_KEY);
    if(ALLOWED_THEMES.has(previous))currentTheme=previous;
    else if(previous==='blue')window.localStorage.setItem(THEME_KEY,'white');
  }catch(_){}
  function applyTheme(theme,persist=true){
    currentTheme=ALLOWED_THEMES.has(theme)?theme:'white';
    document.documentElement.dataset.theme=currentTheme;
    document.documentElement.style.colorScheme=currentTheme==='white'?'light':'dark';
    const themeColor=THEME_COLORS[currentTheme];
    const meta=document.querySelector('meta[name="theme-color"]');
    if(meta)meta.setAttribute('content',themeColor);
    try {webapp?.setHeaderColor(themeColor);webapp?.setBackgroundColor(themeColor);}catch(_){}
    if(persist)try{window.localStorage.setItem(THEME_KEY,currentTheme);}catch(_){}
  }
  applyTheme(currentTheme,false);

  const app = document.getElementById('app');
  const demo = new URLSearchParams(location.search).get('demo') === '1' && ['localhost', '127.0.0.1'].includes(location.hostname);
  const auth = webapp?.initData || '';
  const state = { tab: 'home', catalog: null, progress: null, studyPlan: null, history: null, lesson: null, quiz: null, result: null, consent: null, busy: false, tutorStatus: null, tutorQuestion:'', tutorAnswer: null, tutorLessonId:'', tutorMode:'explain', tutorLevel:'standard', tutorProvider:'lesson', tutorHistory:[], tutorMessages:[], tutorError:'', anatomyFile:null, anatomyPreview:'', anatomyQuestion:'', anatomyAnswer:'', anatomyError:'', anatomyBusy:false, anatomyStatus:null, anatomyLabels:[], anatomyShowLabels:true, anatomyImageWidth:null };
  // Preserve original Uzbek Latin digraphs (Sh/sh, Ch/ch); never rewrite text.
  const uz = val => String(val ?? '');
  const esc = val => uz(val).replace(/[&<>"']/g, s => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[s]));
  const rawEsc = val => String(val ?? '').replace(/[&<>"']/g, s => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[s]));
  const strings = html => html.replace(/>([^<>]+)</g,(all,txt)=>'>'+uz(txt)+'<');


  async function api(path, method='GET', data) {
    const headers = { 'X-Telegram-Init-Data': auth };
    if (demo) headers['X-Dev-Preview'] = 'local-only';
    if (data !== undefined) headers['Content-Type'] = 'application/json';
    const response = await fetch('/api' + path, {method, headers, body: data === undefined ? undefined : JSON.stringify(data), cache: 'no-store'});
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(body?.detail || 'Server bilan aloqa xatosi');
    return body;
  }
  const themeOptions=()=>[['white','Oq-yashil'],['black','Qora-yashil']].map(([id,name])=>
    '<option value="'+id+'" '+(currentTheme===id?'selected':'')+'>'+name+'</option>').join('');
  const header=()=>'<header class="sitehead"><div class="brand"><div class="logo">🎓</div><div><strong>MedStudy AI</strong><small>O‘quv platforma</small></div></div>'+
    '<div class="head-actions"><label class="sr-only" for="theme-select">Dizayn ranglari</label><select class="theme-select" id="theme-select" aria-label="Dizayn ranglari">'+themeOptions()+'</select>'+
    '<span class="pill"><span class="pill-dot"></span> Bepul</span></div></header>';
  const nav = () => '<div class="footer-nav"><div class="nav-inner">'+
    '<button class="nav '+(state.tab==='home'?'active':'')+'" data-action="home"><b>⌂</b>Asosiy</button>'+
    '<button class="nav '+(state.tab==='subjects'||state.tab==='subject'?'active':'')+'" data-action="subjects"><b>▤</b>Fanlar</button>'+
    '<button class="nav '+(state.tab==='progress'?'active':'')+'" data-action="progress"><b>▥</b>Natijalar</button>'+
    '<button class="nav '+(state.tab==='privacy'?'active':'')+'" data-action="privacy"><b>⚙</b>Sozlamalar</button>'+
    '</div></div>';
  const disclaimer = `<div class="caution">⚠️ Mazkur darslar sinov materialidir; mutaxassis ko‘rigidan o‘tmagan. Klinik amaliyot uchun yo‘riqnoma yoki rasmiy universitet xizmati emas.</div>`;
  // Original, offline-friendly anatomy illustrations are independent of Pro AI.
  const ANATOMY_VISUAL_URL='/static/illustrations/catalog.json';
  let anatomyVisualIndex=null;
  const shell = content => { app.innerHTML = strings(header() + '<main>' + content + '</main>' + nav()); window.scrollTo(0,0); };
  const loading = () => { app.innerHTML = `<div class="boot"><div class="loader"></div><p>Ma’lumotlar yuklanmoqda…</p></div>`; };
  const fail = err => shell(`<div class="empty"><div class="symbol">⚠️</div><h2>Ulanishda xatolik</h2><p class="error">${esc(err.message)}</p><button class="btn btn-primary" data-action="retry">Qayta urinish</button><p class="smallprint">Telegram orqali qayta oching. Lokal demo uchun yo‘riqnoma bilan ishga tushiring.</p></div>`);
  const subjectSummary = () => (state.catalog?.subjects || []).flatMap(s=>s.lessons.map(l=>({...l,subject_title:s.title})));
  const displayCategory = lesson => {
    const back = '<button class="back" data-action="lesson" data-id="'+rawEsc(lesson.id)+'">← Mavzuga qaytish</button>';
    const alphabet = lesson.alphabet || [];
    let cards = alphabet.length ? '<div class="card"><h3>Lotin alifbosi — 25 ta harf</h3><p class="smallprint">Siz yuborgan rasm asosida tibbiy misollar.</p><div class="alphabet-grid">'+alphabet.map(a=>'<div class="alphabet-item"><strong>'+esc(a.letter)+'</strong><span><b>'+esc(a.term)+'</b><small>'+esc(a.meaning)+'</small></span></div>').join('')+'</div></div>' : '';
    cards += (lesson.sections||[]).map(s=>'<section class="lesson-section"><h3>'+esc(s.heading)+'</h3><p>'+esc(s.body)+'</p></section>').join('');
    if(lesson.questions?.length) cards += '<div class="card"><h3>Kerakli ma’lumotlar testi</h3><button class="btn btn-primary btn-wide" data-action="start-quiz">Testni boshlash ('+lesson.questions.length+')</button></div>';
    if(!cards) cards = '<div class="empty"><h3>Hozircha ma’lumot yo‘q</h3><p>Ushbu mavzu bo‘yicha konspekt hali berilmagan.</p></div>';
    shell(back+'<p class="eyebrow">'+esc(lesson.subject_title)+'</p><h1>Kerakli ma’lumotlar</h1>'+cards+disclaimer);
  };
  async function showPresetAnatomyVisual(){
    const lesson=state.lesson;
    if(!lesson || lesson.subject_id!=='odam_anatomiyasi_1'){showLesson();return;}
    state.tab='anatomy-visual';
    loading();
    try{
      if(!anatomyVisualIndex){
        const response=await fetch(ANATOMY_VISUAL_URL,{cache:'no-store'});
        if(!response.ok)throw new Error('Anatomiya rasmlari yuklanmadi');
        anatomyVisualIndex=await response.json();
      }
      const visual=anatomyVisualIndex[lesson.id];
      if(!visual || !visual.src || !Array.isArray(visual.facts))throw new Error('Ushbu mavzuning rasmi topilmadi');
      const facts=visual.facts.map(([latin,explanation],index)=>'<div class="anatomy-visual-fact"><span class="anatomy-visual-number">'+(index+1)+'</span><div><strong>'+esc(latin)+'</strong><p>'+esc(explanation)+'</p></div></div>').join('');
      shell('<button class="back" data-action="lesson" data-id="'+rawEsc(lesson.id)+'">← Mavzuga qaytish</button>'+
        '<p class="eyebrow">'+esc(lesson.subject_title)+'</p><h1>Rasm orqali tushuntirish</h1><p class="smallprint">'+esc(visual.title)+'</p>'+
        '<figure class="anatomy-visual-figure"><img src="'+rawEsc(visual.src)+'" alt="'+esc(visual.alt)+'" loading="eager" decoding="async" />'+
        '<figcaption>Mustaqil yaratilgan soddalashtirilgan o‘quv sxemasi. Anatomik atlas va haqiqiy preparat o‘rnini bosmaydi.</figcaption></figure>'+
        '<section class="card anatomy-visual-facts"><h3>Lotincha atamalar va izohlar</h3>'+facts+'</section>'+
        (lesson.anatomy_image_explain?'<button class="btn btn-flat btn-wide" data-action="anatomy-image">O‘z rasmingizni AI bilan tahlil qilish (sinov)</button>':'')+
        disclaimer);
    }catch(error){fail(error);}
  }
  function home() {
    state.tab='home';
    const subjects=state.catalog?.subjects || [];
    const lessons=subjectSummary();
    const completed=state.progress?.latest?.filter(x=>lessons.some(l=>l.id===x.lesson_id)).length || 0;
    const attempts=state.progress?.attempts_count || 0;
    const cards=subjects.map(s=>'<button class="card lesson-card" data-action="subject" data-id="'+rawEsc(s.id)+'"><span class="lesson-icon">📚</span><span class="lesson-content"><strong>'+esc(s.title)+'</strong><small>'+s.lessons.length+' ta mavzu</small></span><span class="chevron">›</span></button>').join('');
    const menu=[
      ['tutor','🎓','AI Ustoz 2.0','Tushuntiradi, misol keltiradi va bilimingizni tekshiradi'],
      ['subjects','📖','Konspektlar','Fanlar va mavzular bo‘yicha ma’lumotlar'],
      ['subjects','✅','Testlar','Mavzular bo‘yicha test savollari'],
      ['progress','▥','O‘quv rejasi','Test natijasiga mos tavsiyalar'],
      ['privacy','⚙','Sozlamalar','Dizayn, maxfiylik va AI roziligi']
    ].map((row,i)=>'<button class="card feature-card '+(i===0?'feature-ai':'')+'" data-action="'+row[0]+'" '+(i===2?'data-purpose="tests"':'')+'><span class="feature-icon">'+row[1]+'</span><span class="feature-copy"><strong>'+row[2]+'</strong><small>'+row[3]+'</small></span><span class="chevron">›</span></button>').join('');
    shell('<section class="hero"><div class="hero-text"><p class="eyebrow">Tibbiyot talabalari uchun</p><h1>MedStudy AI</h1><p>Tibbiyot fanlarini o‘rganish, takrorlash va mustahkamlash uchun aqlli o‘quv yordamchisi.</p></div><div class="hero-illustration" aria-hidden="true">📚<span>🩺</span></div></section>'+
      '<div class="features">'+menu+'</div>'+
      '<div class="stats"><div class="stat"><strong>'+subjects.length+'</strong><small>Fan</small></div><div class="stat"><strong>'+lessons.length+'</strong><small>Mavzu</small></div><div class="stat"><strong>'+attempts+'</strong><small>Test urinish</small></div></div>'+
      '<div class="sectionhead"><h2>Fanlar</h2><span>'+completed+'/'+lessons.length+' o‘rganilgan</span></div>'+cards+disclaimer+
      '<div class="footer-logo">MedStudy AI · Mustaqil ta’lim loyihasi</div>');
  }
  function showSubjects(purpose='notes'){
    state.tab='subjects';
    state.subjectsPurpose=purpose;
    const subjects=state.catalog?.subjects||[];
    const cards=subjects.map(s=>'<button class="card lesson-card" data-action="subject" data-id="'+rawEsc(s.id)+'"><span class="lesson-icon">📚</span><span class="lesson-content"><strong>'+esc(s.title)+'</strong><small>'+s.lessons.length+' ta mavzu</small></span><span class="chevron">›</span></button>').join('');
    shell('<button class="back" data-action="home">← Asosiy</button><p class="eyebrow">'+(purpose==='tests'?'Bilimni sinash':'O‘quv materiallari')+'</p><h1>'+ (purpose==='tests'?'Testlar':'Fanlar va konspektlar') +'</h1><p class="smallprint">Fan va mavzuni tanlang.</p>'+cards);
  }
  function showSubject(id){
    const s=(state.catalog?.subjects||[]).find(x=>x.id===id);
    if(!s)return home();
    state.tab='subject';state.subjectId=id;
    const cards=s.lessons.map((l,i)=>'<button class="card lesson-card" data-action="lesson" data-id="'+rawEsc(l.id)+'"><span class="lesson-icon">📖</span><span class="lesson-content"><span class="tag">'+(i+1)+'-MAVZU</span><strong>'+esc(l.title)+'</strong><small>'+l.section_count+' bo‘lim · '+l.question_count+' savol</small></span><span class="chevron">›</span></button>').join('');
    shell('<button class="back" data-action="home">← Fanlar</button><h1>'+esc(s.title)+'</h1>'+
      '<p class="smallprint">'+(state.subjectsPurpose==='tests'?'Test uchun mavzuni tanlang.':'Mavzuni tanlang va kerakli ma’lumotlarni oching.')+'</p>'+cards);
  }
  async function getLesson(id) {
    loading();
    try { state.lesson=await api('/lessons/'+encodeURIComponent(id)); showLesson(); }
    catch(e){ fail(e); }
  }
  function showLesson(){
    state.tab='lesson';
    const l=state.lesson;
    shell('<button class="back" data-action="subject" data-id="'+rawEsc(l.subject_id)+'">← Mavzular</button>'+
      '<p class="eyebrow">'+esc(l.subject_title)+'</p><h1>'+esc(l.title)+'</h1>'+
      '<button class="card lesson-card" data-action="category" data-kind="required"><span class="lesson-icon">📘</span><span class="lesson-content"><strong>Kerakli ma’lumotlar</strong><small>Mavzu konspekti va testlar</small></span><span class="chevron">›</span></button>'+
      '<button class="card lesson-card" data-action="tutor" data-id="'+rawEsc(l.id)+'"><span class="lesson-icon">🎓</span><span class="lesson-content"><strong>AI Ustoz bilan o‘rganish</strong><small>Ushbu mavzuga oid savol-javob</small></span><span class="chevron">›</span></button>'+
      (l.subject_id==='odam_anatomiyasi_1'?'<button class="card lesson-card anatomy-visual-entry" data-action="anatomy-visual"><span class="lesson-icon">🦴</span><span class="lesson-content"><strong>Rasm orqali tushuntirish</strong><small>Har bir mavzuga mos tayyor sxema va lotincha nomlar</small></span><span class="chevron">›</span></button>':'')+
      (l.questions?.length?'<button class="btn btn-primary btn-wide lesson-quiz-cta" data-action="start-quiz">✓ Testni boshlash ('+l.questions.length+')</button>':'')+disclaimer);
  }

  function resetAnatomyImage(){
    if(state.anatomyPreview)URL.revokeObjectURL(state.anatomyPreview);
    state.anatomyFile=null;state.anatomyPreview='';
    state.anatomyQuestion='';state.anatomyAnswer='';state.anatomyError='';state.anatomyLabels=[];state.anatomyShowLabels=true;state.anatomyImageWidth=null;
  }
  async function anatomyImageScreen(){
    if(!state.lesson?.anatomy_image_explain){showLesson();return;}
    state.tab='anatomy-image';loading();
    try{state.anatomyStatus=await api('/tutor/status');renderAnatomyImage();}
    catch(e){fail(e);}
  }
  function renderAnatomyImage(){
    state.tab='anatomy-image';
    const l=state.lesson,t=state.anatomyStatus||{};
    const ready=Boolean(t.enabled&&t.consented&&t.remaining>0);
    const labels=Array.isArray(state.anatomyLabels)?state.anatomyLabels:[];
    const annotations=state.anatomyShowLabels?labels.map((item,i)=>{
      const x=Math.max(0,Math.min(100,Number(item.x)/10));
      const y=Math.max(0,Math.min(100,Number(item.y)/10));
      const side=x>=60?'on-left':'on-right';
      const vertical=y<=23?'under-dot':'above-dot';
      return '<span class="anatomy-marker '+side+' '+vertical+'" style="left:'+x+'%;top:'+y+'%" aria-label="'+esc(item.latin)+'"><span class="anatomy-pin">'+(i+1)+'</span><span class="anatomy-label">'+esc(item.latin)+'</span></span>';
    }).join(''):'';
    const preview=state.anatomyPreview
      ?'<div class="anatomy-picture-wrap"><div class="anatomy-annotated-picture" '+(state.anatomyImageWidth?'style="width:'+state.anatomyImageWidth+'px"':'')+'><img class="anatomy-preview" src="'+rawEsc(state.anatomyPreview)+'" alt="Tanlangan anatomiya rasmi">'+annotations+'</div></div>'+
       (labels.length?'<button class="btn btn-flat btn-wide" data-action="anatomy-toggle">'+(state.anatomyShowLabels?'Belgilarni yashirish':'Belgilarni ko‘rsatish')+'</button>'+
        '<div class="anatomy-legend" aria-label="Rasmdagi anatomik belgilar">'+labels.map((item,i)=>'<div class="anatomy-legend-item"><span class="anatomy-number">'+(i+1)+'</span><strong>'+esc(item.latin)+'</strong></div>').join('')+'</div>':
        state.anatomyAnswer?'<p class="smallprint">Rasmda ishonch bilan belgilash mumkin bo‘lgan anatomik suyak yoki tuzilma aniqlanmadi.</p>':'')
      :'<p class="smallprint">Hozircha rasm tanlanmagan.</p>';
    shell('<button class="back" data-action="lesson" data-id="'+rawEsc(l.id)+'">← Mavzuga qaytish</button>'+
      '<p class="eyebrow">Odam anatomiyasi</p><h1>Rasm orqali tushuntirish</h1>'+
      '<div class="card"><strong>'+esc(l.title)+'</strong><p class="smallprint">Faqat suyak yoki anatomiya sxemasini yuboring. Bemor rasmi, shaxsiy hujjat yoki shaxsiy ma’lumot yubormang. Tasvir OpenAI xizmatiga jo‘natiladi, bizning serverimizda saqlanmaydi.</p>'+
      '<label for="anatomy-file">Suyak rasmini tanlash (JPG, PNG, WEBP; 5 MB gacha)</label>'+
      '<input class="ai-input anatomy-file" type="file" id="anatomy-file" accept="image/jpeg,image/png,image/webp" '+(state.anatomyBusy?'disabled':'')+'>'+preview+
      '<label for="anatomy-question">Qo‘shimcha savol (ixtiyoriy)</label>'+
      '<textarea id="anatomy-question" class="ai-input" maxlength="500" rows="2" placeholder="Masalan: Lotincha nomlarini ko‘rsat">'+esc(state.anatomyQuestion)+'</textarea>'+
      (!t.enabled?'<p class="smallprint">OpenAI rasm tahlili hozir o‘chirilgan yoki sizga ochilmagan. Oddiy konspektlar ishlaydi.</p>':
        !t.consented?'<p class="smallprint">Rasmni OpenAI xizmatiga yuborish uchun alohida rozilik kerak.</p><button class="btn btn-flat btn-wide" data-action="anatomy-consent">Roziman · AI rasm tahlilini ochish</button>':
        '<p class="smallprint">Bugungi qolgan AI so‘rovlar: '+t.remaining+'/'+t.limit+'</p>')+
      '<button class="btn btn-primary btn-wide" data-action="anatomy-send" '+(!ready||!state.anatomyFile||state.anatomyBusy?'disabled':'')+'>'+
      (state.anatomyBusy?'Tahlil qilinmoqda…':'Rasmni tushuntirish →')+'</button>'+
      (state.anatomyError?'<p role="alert" class="error">'+esc(state.anatomyError)+'</p>':'')+
      (state.anatomyAnswer?'<div class="anatomy-answer" aria-live="polite"><h3>ChatGPT tushuntirishi</h3><p>'+esc(state.anatomyAnswer).replace(/\n/g,'<br>')+'</p><p class="smallprint">Javobni darslikdagi anatomik rasmlar bilan tekshiring.</p></div>':'')+
      '</div>'+disclaimer);
  }
  function selectAnatomyFile(file){
    const question=state.anatomyQuestion;
    resetAnatomyImage();state.anatomyQuestion=question;
    if(!file){renderAnatomyImage();return;}
    if(!['image/jpeg','image/png','image/webp'].includes(file.type)){state.anatomyError='Faqat JPG, PNG yoki WEBP rasm tanlang';renderAnatomyImage();return;}
    if(file.size===0||file.size>5*1024*1024){state.anatomyError='Rasm hajmi 5 MB dan oshmasin';renderAnatomyImage();return;}
    state.anatomyFile=file;state.anatomyPreview=URL.createObjectURL(file);
    const previewUrl=state.anatomyPreview;
    // Set overlay width to the *rendered* image width, even for tall portraits.
    const probe=new Image();
    probe.onload=()=>{
      if(state.anatomyPreview!==previewUrl)return;
      state.anatomyImageWidth=Math.max(1,Math.round(Math.min(
        probe.naturalWidth,340*probe.naturalWidth/probe.naturalHeight)));
      if(state.tab==='anatomy-image')renderAnatomyImage();
    };
    probe.onerror=()=>{
      if(state.anatomyPreview===previewUrl){
        state.anatomyError='Rasmni ko‘rsatib bo‘lmadi. Boshqa rasm tanlang.';
        state.anatomyFile=null;renderAnatomyImage();
      }
    };
    probe.src=previewUrl;
    renderAnatomyImage();
  }
  async function sendAnatomyImage(){
    if(state.anatomyBusy||!state.anatomyFile)return;
    const t=state.anatomyStatus;if(!t?.enabled||!t?.consented||t.remaining<=0)return;
    state.anatomyQuestion=document.getElementById('anatomy-question')?.value.trim()||'';
    const body=new FormData();
    body.append('lesson_id',state.lesson.id);body.append('question',state.anatomyQuestion);
    body.append('image',state.anatomyFile,state.anatomyFile.name);
    const headers={'X-Telegram-Init-Data':auth};if(demo)headers['X-Dev-Preview']='local-only';
    state.anatomyBusy=true;state.anatomyError='';renderAnatomyImage();
    try{
      const response=await fetch('/api/anatomy/image-explain',{method:'POST',headers,body,cache:'no-store'});
      const data=await response.json().catch(()=>({}));
      if(!response.ok)throw new Error(data.detail||'Rasmni tahlil qilishda xato');
      state.anatomyAnswer=data.answer||'';
      state.anatomyLabels=Array.isArray(data.labels)?data.labels:[];state.anatomyShowLabels=true;
      state.anatomyStatus.remaining=data.remaining;state.anatomyStatus.used+=1;
    }catch(e){state.anatomyError=e.message;}
    state.anatomyBusy=false;renderAnatomyImage();
  }

  function startQuiz(questions, mode='full', category='required') {
    if (!questions.length) { state.tab='lesson'; showLesson(); return; }
    state.quiz={questions,mode,category,answers:Array(questions.length).fill(null),pos:0};
    renderQuiz();
  }
  function renderQuiz() {
    state.tab='quiz';const qz=state.quiz;const q=qz.questions[qz.pos];const val=qz.answers[qz.pos];const n=qz.questions.length;
    shell(`<button class="back" data-action="lesson" data-id="${rawEsc(state.lesson.id)}">← Mavzuga qaytish</button><div class="quiz-top"><span>${qz.mode==='retry'?'Xatolarni takrorlash':'Kerakli ma’lumotlar testi'}</span><strong>${qz.pos+1}/${n}</strong></div><div class="bar"><div class="bar-fill" style="width:${Math.round((qz.pos)/n*100)}%"></div></div><h2 class="question">${esc(q.q)}</h2><div class="answers">${q.options.map((opt,i)=>`<button class="answer ${val===i?'selected':''}" data-action="answer" data-value="${i}"><span class="letter">${'ABCD'[i]}</span>${esc(opt)}</button>`).join('')}</div><div class="quiz-actions"><button class="btn btn-primary btn-wide" data-action="next" ${val===null||state.busy?'disabled':''}>${qz.pos===n-1?'Testni yakunlash':'Keyingi savol →'}</button></div><p class="inline-note">To‘g‘ri javob va izohlar test yakunida ko‘rsatiladi.</p>`);
  }
  async function next() {
    if(state.busy) return;
    const qz=state.quiz;if(qz.answers[qz.pos]===null)return;
    if(qz.pos<qz.questions.length-1){qz.pos++;renderQuiz();return;}
    state.busy=true;renderQuiz();
    try {
      state.result=await api('/attempts','POST',{lesson_id:state.lesson.id, question_ids:qz.questions.map(q=>q.id), answers:qz.answers,category:qz.category});
      state.progress=await api('/progress');state.busy=false;showResult();
    } catch(e){state.busy=false;fail(e);}
  }
  function showResult(){
    state.tab='result';const r=state.result;const qz=state.quiz;
    const mapped=qz.questions.map((q,i)=>({q,detail:r.details[i]}));
    shell(`<button class="back" data-action="home">← Asosiy menyu</button><div class="result-score"><span class="eyebrow">Test yakunlandi</span><div class="big-score">${r.percent}%</div><h2>${r.score} / ${r.total} to‘g‘ri javob</h2><p>${r.percent>=80?'Zo‘r! Bilimingizni mustahkamlang.':'Natijani ko‘rib chiqing va mavzuni qayta takrorlang.'}</p></div><div class="card"><h3>Keyingi qadam</h3><button class="btn btn-primary btn-wide" data-action="lesson" data-id="${esc(state.lesson.id)}">Mavzuni qayta o‘qish</button><div class="spacer"></div><button class="btn btn-flat btn-wide" data-action="retry">${r.score===r.total?'Testni yana yechish':'Xato savollarni takrorlash'}</button></div><div class="sectionhead"><h2>Javoblar tahlili</h2><span>${r.total} ta savol</span></div>${mapped.map(({q,detail},i)=>`<div class="review-row"><strong>${i+1}. ${esc(q.q)}</strong><p class="${detail.correct?'ok':'bad'}">${detail.correct?'✓ To‘g‘ri':'✕ Xato'} · Siz: ${esc(q.options[detail.chosen])}</p>${!detail.correct?`<p class="ok">To‘g‘ri: ${esc(q.options[detail.answer])}</p>`:''}<p>${esc(detail.explanation)}</p></div>`).join('')}`);
  }
  async function retryWrong(){
    if(state.result?.score===state.result?.total){startQuiz(state.lesson.questions,'full');return;}
    loading();try{const r=await api('/review/'+encodeURIComponent(state.lesson.id));if(!r.questions.length){startQuiz(state.lesson.questions);return;}startQuiz(r.questions,'retry','required');}catch(e){fail(e);}
  }
  async function progress(){
    state.tab='progress';loading();try{[state.progress,state.studyPlan,state.history]=await Promise.all([api('/progress'),api('/study-plan'),api('/history?limit=12')]);renderProgress();}catch(e){fail(e);}
  }
  function renderProgress(){
    state.tab='progress';const p=state.progress||{latest:[],attempts_count:0};
    const plan=state.studyPlan?.items || [];
    const history=state.history?.items || [];
    const historyHtml=history.length ? `<div class="sectionhead"><h2>🕒 So‘nggi urinishlar</h2><span>${history.length} ta</span></div><div class="card">${history.map(row=>`<div class="progress-row"><div class="progress-label"><strong>${esc(row.title)}</strong><span>${row.score}/${row.total} · ${row.percent}%</span></div><p class="smallprint">${row.mode==='retry'?'Xatolarni takrorlash':'To‘liq test'} · ${esc(row.created_at.slice(0,16).replace('T',' '))} UTC</p></div>`).join('')}</div>` : '';
    const recommendations=plan.length ? `<div class="sectionhead"><h2>🎯 Shaxsiy o‘quv rejam</h2><span>${plan.length} mavzu</span></div><p class="smallprint">Tavsiyalar oxirgi to‘liq test va xato javoblardan hisoblanadi.</p>${plan.map(item=>`<button class="card lesson-card" data-action="lesson" data-id="${esc(item.lesson_id)}"><span class="lesson-icon">📖</span><span class="lesson-content"><strong>${esc(item.lesson_title)}</strong><small>${esc(item.action)} · ${esc(item.reason)}</small></span><span class="chevron">›</span></button><button class="btn btn-flat btn-wide" data-action="tutor" data-id="${esc(item.lesson_id)}" data-level="${esc(item.recommended_level||'standard')}">AI Ustoz bilan mashq (${esc(item.recommended_level||'standard')})</button>`).join('')}` : '';
    shell(`<p class="eyebrow">Mening o‘sishim</p><h1>O‘quv natijalarim</h1><p class="smallprint">Faqat shaxsiy test natijalaringiz ko‘rsatiladi.</p><div class="stats"><div class="stat"><strong>${p.attempts_count}</strong><small>Urinishlar</small></div><div class="stat"><strong>${p.latest.length}</strong><small>O‘rganilgan mavzu</small></div><div class="stat"><strong>${p.latest.length?Math.round(p.latest.reduce((x,r)=>x+r.percent,0)/p.latest.length):0}%</strong><small>Oxirgi o‘rtacha</small></div></div>${recommendations}${historyHtml}<div class="sectionhead"><h2>Mavzular kesimida</h2><span>Oxirgi urinishlar</span></div>${p.latest.length?`<div class="card">${p.latest.map(r=>`<div class="progress-row"><div class="progress-label"><strong>${esc(r.title)}</strong><span>${r.score}/${r.total} · ${r.percent}%</span></div><div class="bar"><div class="bar-fill" style="width:${r.percent}%"></div></div></div>`).join('')}<p class="smallprint">Eslatma: xatolarni takrorlash testida savollar soni kamroq bo‘lishi mumkin.</p></div>`:`<div class="empty"><div class="symbol">📊</div><h3>Natijalar hozircha yo‘q</h3><p>Birinchi testni topshiring — progress shu yerda ko‘rinadi.</p><button class="btn btn-primary" data-action="home">Darslarni ko‘rish →</button></div>`}`);
  }
  function privacy(){
    state.tab='privacy';shell(`<p class="eyebrow">Shaxsiy ma’lumotlar</p><h1>Maxfiylik va xavfsizlik</h1><div class="card privacy"><h3>Qanday ma’lumotlar saqlanadi?</h3><p>Sinov davrida Telegram foydalanuvchi IDsi, rozilik vaqti, test javoblari va natijalari SQLite bazasida saqlanadi. Tanlangan Oq-yashil yoki Qora-yashil dizayn faqat qurilmangizdagi brauzer xotirasida saqlanadi. Ism, telefon raqami va yozishmalar saqlanmaydi. Dars Ustoz bepul rejimida savol faqat serverdagi dars matni bilan solishtiriladi; u OpenAI API'ga yuborilmaydi va bizning SQLite bazamizga yozilmaydi. AI Ustoz rejimi faqat alohida rozilikdan so‘ng savol va oxirgi uchta suhbat almashinuvini OpenAI APIga yuboradi. Suhbat matni SQLite bazasiga yozilmaydi va sahifa yangilanganda yo‘qoladi. AI javobi xato bo‘lishi mumkin. Anatomiya rasm tahlilida tasvir OpenAI xizmatiga alohida rozilik bilan yuboriladi; serverimizda saqlanmaydi.</p><h3>Ma’lumotlar kimga tegishli?</h3><p>Test natijalarini ilova administratori serverda boshqaradi. Ilova hozircha mustaqil o‘quv prototipi, universitetning rasmiy xizmati emas.</p><h3>Ma’lumotlarni o‘chirish</h3><p>Quyidagi tugma orqali shaxsiy test tarixingiz va rozilik yozuvini o‘chirishingiz mumkin.</p><button class="btn btn-danger btn-wide" data-action="delete">Ma’lumotlarimni o‘chirish</button></div>${disclaimer}`);
  }
  function accessScreen(status){
    const stateText={
      pending:'⏳ So‘rovingiz administrator tasdig‘ini kutmoqda.',
      rejected:'❌ Kirish so‘rovingiz rad etildi.',
      revoked:'⛔ Mini App ruxsatingiz bekor qilindi.',
      not_requested:'📨 Mini App’dan foydalanish uchun avval botga obuna bo‘ling.'
    }[status]||'Administrator ruxsati kerak.';
    app.innerHTML=strings(header()+'<main class="privacy"><p class="eyebrow">Kirish uchun ruxsat</p><h1>MedStudy AI</h1><div class="card"><h3>'+stateText+'</h3><p>Telegram botda /start yuboring. Administrator tasdiqlagach Mini App ochiladi. Pro va pullik obuna hozircha mavjud emas.</p><button class="btn btn-primary btn-wide" data-action="retry">Holatni yangilash</button></div></main>');
  }
  function consentScreen(){
    app.innerHTML=strings(header()+`<main class="privacy"><p class="eyebrow">Xush kelibsiz</p><h1>MedStudy AI’ga kirish</h1><div class="card"><h3>Maxfiylik shartlariga rozilik</h3><p>Ta’limiy tajriba uchun Telegram ID, rozilik vaqti, test javoblari va natijalari administrator serveridagi SQLite bazasida saqlanadi. Ism, telefon va yozishmalar saqlanmaydi. Dars Ustoz bepul rejimida savolingiz serverdagi dars bilan solishtiriladi va bizning SQLite bazamizga saqlanmaydi. Tashqi AI xizmatiga hech narsa yuborilmaydi.</p><p>Keyin “Maxfiylik” bo‘limidan ularni o‘chirish mumkin. Materiallar ekspert tasdig‘ini olmagan.</p><button class="btn btn-primary btn-wide" data-action="consent">Roziman · Davom etish</button><div class="spacer"></div><p class="smallprint">Rozilik bermasangiz, natijalar saqlanmaydi va ilovadan foydalanish boshlanmaydi.</p></div></main>`);
  }

  function tutorClear() {
    state.tutorHistory=[];state.tutorMessages=[];state.tutorAnswer=null;
    state.tutorError='';state.tutorQuestion='';
  }
  function tutorModeOptions() {
    return [['explain','Tushuntirish'],['example','Misol bilan'],['recall','Bilimni tekshirish'],['oral','Og‘zaki imtihon']].map(([id,name]) =>
      '<option value="'+id+'" '+(state.tutorMode===id?'selected':'')+'>'+name+'</option>').join('');
  }
  function tutorLevelOptions() {
    return [['basic','Boshlang‘ich'],['standard','O‘rta'],['advanced','Murakkab']].map(([id,name]) =>
      '<option value="'+id+'" '+(state.tutorLevel===id?'selected':'')+'>'+name+'</option>').join('');
  }
  async function tutorScreen(id='') {
    if(id && id!==state.tutorLessonId){state.tutorLessonId=id;tutorClear();}
    state.tab='tutor';
    loading();
    try {
      state.tutorStatus=await api('/tutor/status');
      renderTutor();
    } catch(e){fail(e);}
  }
  function renderTutor() {
    state.tab='tutor';
    const t=state.tutorStatus||{enabled:false,consented:false,used:0,limit:5,remaining:0};
    const lessons=subjectSummary();
    if(!state.tutorLessonId&&lessons[0])state.tutorLessonId=lessons[0].id;
    const select=lessons.map(l=>'<option value="'+esc(l.id)+'" '+(l.id===state.tutorLessonId?'selected':'')+'>'+esc(l.subject_title)+' · '+esc(l.title)+'</option>').join('');
    const chosen=lessons.find(l=>l.id===state.tutorLessonId);
    const usingAI=state.tutorProvider==='ai';
    const aiInfo=t.enabled
      ? (t.consented?'<p class="smallprint">Haqiqiy AI suhbat · Qolgan kunlik so‘rov: '+t.remaining+'/'+t.limit+'.</p>'
        :'<p class="smallprint">OpenAI API orqali suhbat uchun alohida rozilik kerak. Savol va oxirgi uchta suhbat almashinuvi OpenAI xizmatiga yuboriladi; botimizning SQLite bazasida saqlanmaydi.</p><button class="btn btn-flat btn-wide" data-action="tutor-consent">Roziman · AI Ustozni ochish</button>')
      :'<p class="smallprint">Haqiqiy AI hozir sozlanmagan yoki o‘chirilgan. Bepul dars yordamchisi ishlaydi.</p>';
    const log=state.tutorMessages.map(item=>
      '<div class="card tutor-message '+(item.role==='user'?'tutor-student':'tutor-teacher')+'"><p class="smallprint">'+(item.role==='user'?'Talaba':'AI Ustoz')+'</p><p>'+esc(item.content).replace(/\n/g,'<br>')+'</p></div>').join('');
    const error=state.tutorError?'<p class="error" role="alert">'+esc(state.tutorError)+'</p>':'';
    const canAsk=!(state.busy||(usingAI&&(!t.enabled||!t.consented||t.remaining<=0)));
    const btnText=state.busy?'Javob tayyorlanmoqda…':usingAI?'AI Ustozga yuborish →':'Darsdan javob olish →';
    shell('<div class="tutor-banner">🎓 AI Ustoz 2.0 <span>· '+(state.tutorMode==='oral'?'Og‘zaki imtihon':'Dars rejimi')+'</span></div>'+
      '<div class="card tutor-subject"><span class="feature-icon">🦷</span><div><p class="smallprint">Tanlangan mavzu</p><strong>'+esc(chosen?.title||'Mavzuni tanlang')+'</strong></div></div>'+
      '<div class="card tutor-settings"><p class="smallprint">Suhbatni davom ettirishingiz yoki yangi mavzu tanlashingiz mumkin.</p>'+
      '<label for="tutor-lesson">Mavzu</label><select id="tutor-lesson" class="ai-input">'+select+'</select>'+
      '<label for="tutor-provider">Yordamchi turi</label><select id="tutor-provider" class="ai-input"><option value="lesson" '+(!usingAI?'selected':'')+'>Bepul konspekt yordamchisi</option><option value="ai" '+(usingAI?'selected':'')+'>AI Ustoz — OpenAI (rozilik va limit)</option></select>'+
      '<div class="tutor-config-grid"><div><label for="tutor-mode">O‘rganish usuli</label><select id="tutor-mode" class="ai-input">'+tutorModeOptions()+'</select></div>'+
      '<div><label for="tutor-level">Qiyinchilik darajasi</label><select id="tutor-level" class="ai-input">'+tutorLevelOptions()+'</select></div></div>'+
      (usingAI?aiInfo:'<p class="smallprint">Bepul rejim darsdagi tayyor ma’lumotlardan foydalanadi, yozma javobingizni avtomatik baholamaydi.</p>')+'</div>'+
      (log?'<section class="tutor-chat" aria-live="polite">'+log+'</section>':'<div class="tutor-empty">✧ Savolingizni yozing. AI Ustoz ushbu mavzu bo‘yicha yordam beradi.</div>')+
      '<div class="card tutor-composer"><label for="tutor-question">Savolingiz yoki javobingiz</label><textarea id="tutor-question" class="ai-input" maxlength="500" rows="3" placeholder="Xabar yozing…">'+esc(state.tutorQuestion)+'</textarea>'+
      '<button class="btn btn-primary btn-wide" data-action="tutor-ask" '+(!canAsk?'disabled':'')+'>'+btnText+'</button>'+
      '<button class="btn btn-flat btn-wide" data-action="tutor-new">Yangi suhbat</button>'+
      (t.consented?'<button class="btn btn-flat btn-wide" data-action="tutor-revoke">AI roziligini bekor qilish</button>':'')+error+
      '<p class="smallprint">Bemor, telefon, email yoki maxfiy ma’lumot kiritmang. Suhbat sahifa yopilganda yoki yangilanganda yo‘qoladi.</p></div>'+disclaimer);
  }
  async function tutorAsk() {
    if(state.busy) return;
    const text=document.getElementById('tutor-question')?.value.trim()||'';
    state.tutorQuestion=text;
    if(text.length<5){state.tutorError='Savol kamida 5 ta belgidan iborat bo‘lsin';renderTutor();return;}
    if(state.tutorProvider==='ai' && (!state.tutorStatus?.enabled||!state.tutorStatus?.consented)) {
      state.tutorError='Avval AI xizmatiga alohida rozilik bering';renderTutor();return;
    }
    state.tutorError='';
    const payload={lesson_id:state.tutorLessonId,question:text,mode:state.tutorMode};
    const ai=state.tutorProvider==='ai';
    if(ai){payload.level=state.tutorLevel;payload.history=state.tutorHistory.slice(-6);}
    state.busy=true;renderTutor();
    try {
      const result=await api(ai?'/tutor/ask':'/tutor/lesson','POST',payload);
      state.tutorAnswer=result;
      state.tutorMessages.push({role:'user',content:text},{role:'assistant',content:result.answer});
      state.tutorMessages=state.tutorMessages.slice(-12);
      if(ai){
        state.tutorHistory.push({role:'user',content:text},{role:'assistant',content:result.answer.slice(0,500)});
        state.tutorHistory=state.tutorHistory.slice(-6);
        state.tutorStatus.remaining=result.remaining;
        state.tutorStatus.used+=1;
      }
      state.tutorQuestion='';
    }catch(e){state.tutorError=e.message;}
    state.busy=false;renderTutor();
  }
  async function init(){
    loading();try {
      const me=await api('/me');state.consent=me.consented;
      if(me.approval_required && me.access_status!=='approved'){accessScreen(me.access_status);return;}
      if(!me.consented){consentScreen();return;}
      [state.catalog,state.progress]=await Promise.all([api('/catalog'),api('/progress')]);home();
    } catch(e){fail(e);}
  }
  document.addEventListener('click',async evt=>{
    const el=evt.target.closest('[data-action]');if(!el||el.disabled)return;
    const act=el.dataset.action;
    try{
      switch(act){
        case 'home': if(state.catalog)home();else init();break;
        case 'subjects':showSubjects(el.dataset.purpose||'notes');break;
        case 'subject':showSubject(el.dataset.id);break;
        case 'category':if(state.lesson)displayCategory(state.lesson);break;
        case 'lesson': if(el.dataset.id)await getLesson(el.dataset.id);break;
        case 'start-quiz':if(state.lesson && state.lesson.questions?.length)startQuiz(state.lesson.questions,'full','required');break;
        case 'answer':state.quiz.answers[state.quiz.pos]=Number(el.dataset.value);renderQuiz();break;
        case 'next':await next();break;
        case 'retry':if(state.tab==='result')await retryWrong();else await init();break;
        case 'progress':await progress();break;
        case 'privacy':privacy();break;
        case 'anatomy-visual':await showPresetAnatomyVisual();break;
        case 'anatomy-image':resetAnatomyImage();await anatomyImageScreen();break;
        case 'anatomy-consent':await api('/tutor/consent','POST');await anatomyImageScreen();break;
        case 'anatomy-send':await sendAnatomyImage();break;
        case 'anatomy-toggle':state.anatomyShowLabels=!state.anatomyShowLabels;renderAnatomyImage();break;
        case 'tutor':if(el.dataset.level)state.tutorLevel=el.dataset.level;await tutorScreen(el.dataset.id||'');break;
        case 'tutor-consent':await api('/tutor/consent','POST');state.tutorStatus.consented=true;await tutorScreen();break;
        case 'tutor-ask':await tutorAsk();break;
        case 'tutor-new':tutorClear();renderTutor();break;
        case 'tutor-revoke':await api('/tutor/consent','DELETE');tutorClear();state.tutorProvider='lesson';await tutorScreen();break;
        case 'consent':await api('/consent','POST');await init();break;
        case 'delete':if(!confirm('Barcha test natijalari o‘chirilsinmi?'))return;await api('/me','DELETE');state.catalog=null;state.progress=null;state.studyPlan=null;state.history=null;tutorClear();state.tutorProvider='lesson';await init();break;
      }
    }catch(e){fail(e);}
  });
  document.addEventListener('change',evt=>{
    const id=evt.target.id;
    if(id==='theme-select'){applyTheme(evt.target.value);return;}
    if(id==='anatomy-file'){state.anatomyQuestion=document.getElementById('anatomy-question')?.value||'';selectAnatomyFile(evt.target.files?.[0]);return;}
    if(['tutor-lesson','tutor-provider','tutor-mode','tutor-level'].includes(id))state.tutorQuestion=document.getElementById('tutor-question')?.value||'';
    if(id==='tutor-lesson'){
      if(evt.target.value!==state.tutorLessonId){state.tutorLessonId=evt.target.value;tutorClear();}
      renderTutor();
    }
    if(id==='tutor-provider'){
      state.tutorProvider=evt.target.value;tutorClear();renderTutor();
    }
    if(id==='tutor-mode'){state.tutorMode=evt.target.value;tutorClear();renderTutor();}
    if(id==='tutor-level'){state.tutorLevel=evt.target.value;renderTutor();}
  });
  init();
})();
