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
  const state = { tab: 'home', catalog: null, progress: null, studyPlan: null, history: null, lesson: null, quiz: null, result: null, consent: null, busy: false, tutorStatus: null, tutorQuestion:'', tutorAnswer: null, tutorLessonId:'', tutorMode:'explain', tutorLevel:'standard', tutorProvider:'lesson', tutorHistory:[], tutorMessages:[], tutorError:'' };
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
  // Show original, local, topic-specific illustrations only for lessons that have them.
  const VISUAL_LESSONS = Object.freeze({
    "anat_1": {"src":"/static/illustrations/anat_1.svg","title":"Anatomiya: anatomik holat va sathlar","alt":"Odam tanasining sxemasi va anatomik yo‘nalishlar","facts":[["Caput","Bosh: Tananing yuqori qismi."],["Truncus","Gavda: Ko‘krak va qorin sohalari."],["Membrum superius","Yuqori qo‘l-oyoq: Qo‘l sohasi."],["Membrum inferius","Pastki qo‘l-oyoq: Oyoq sohasi."],["Planum sagittale","Sagittal sath: Tanani o‘ng va chap qismlarga ajratadi."]]},
    "anat_2": {"src":"/static/illustrations/anat_2.svg","title":"Umumiy osteologiya: umurtqa pog‘onasi","alt":"Umurtqa pog‘onasining bo‘limlari soddalashtirilgan sxemada","facts":[["Vertebrae cervicales","Bo‘yin umurtqalari: 7 ta bo‘yin umurtqasi."],["Vertebrae thoracicae","Ko‘krak umurtqalari: 12 ta ko‘krak umurtqasi."],["Vertebrae lumbales","Bel umurtqalari: 5 ta bel umurtqasi."],["Os sacrum","Dumg‘aza suyagi: Umurtqalarning qo‘shilishidan hosil."],["Os coxae","Chanoq suyagi: Tana va oyoqlarni bog‘laydi."]]},
    "anat_3": {"src":"/static/illustrations/anat_3.svg","title":"Ko‘krak qafasi: qovurg‘alar va to‘sh suyagi","alt":"Old tomondan qovurg‘alar, to‘sh suyagi va umurtqa","facts":[["Sternum","To‘sh suyagi: Ko‘krakning old o‘rtasida."],["Costae verae","Chin qovurg‘alar: 1–7-juft qovurg‘alar."],["Costae spuriae","Soxta qovurg‘alar: 8–10-juft qovurg‘alar."],["Costae fluctuantes","Erkin qovurg‘alar: 11–12-juft qovurg‘alar."],["Vertebrae thoracicae","Ko‘krak umurtqalari: Qovurg‘alarning orqa tayanchi."]]},
    "anat_4": {"src":"/static/illustrations/anat_4.svg","title":"Yelka kamari: o‘mrov va kurak suyaklari","alt":"Yelka kamarining old va orqa tuzilmalari","facts":[["Clavicula","O‘mrov suyagi: Yelka kamarining old qismi."],["Scapula","Kurak suyagi: Yassi uchburchak suyak."],["Spina scapulae","Kurak qirrasi: Kurakning orqa qismida."],["Cavitas glenoidalis","Bo‘g‘im chuqurchasi: Yelka suyagi boshchasiga tutashadi."],["Humerus","Yelka suyagi: Qo‘lning erkin qismi."]]},
    "anat_5": {"src":"/static/illustrations/anat_5.svg","title":"Qo‘l erkin qismi suyaklari","alt":"Yelka, bilak va qo‘l panjasi skeleti","facts":[["Humerus","Yelka suyagi: Yelkaning uzun suyagi."],["Radius","Bilak suyagi: Bosh barmoq tomonida."],["Ulna","Tirsak suyagi: Kichik barmoq tomonida."],["Ossa carpi","Kaft usti suyaklari: Bilak va kaft orasidagi 8 suyak."],["Ossa metacarpi","Kaft suyaklari: Kaftning besh naysimon suyagi."]]},
    "anat_6": {"src":"/static/illustrations/anat_6.svg","title":"Chanoq kamari: old ko‘rinish","alt":"Chanoq suyagining qismlari va dumg‘aza","facts":[["Os ilium","Yonbosh suyagi: Chanoqning keng yuqori qismi."],["Os ischii","O‘tirg‘ich suyagi: Past-orqa bo‘lagi."],["Os pubis","Qov suyagi: Old-pastki bo‘lagi."],["Os sacrum","Dumg‘aza suyagi: Chanoqning orqa devoriga tegishli."],["Foramen obturatum","Yopqich teshik: Qov va o‘tirg‘ich oralig‘idagi teshik."]]},
    "anat_7": {"src":"/static/illustrations/anat_7.svg","title":"Chanoq kamari: yon va bo‘g‘im ko‘rinishi","alt":"Yonbosh, o‘tirg‘ich, qov qismlari va son bo‘g‘imi","facts":[["Crista iliaca","Yonbosh qirrasi: Yonbosh suyagining yuqori qirrasi."],["Acetabulum","Son bo‘g‘imi kosachasi: Son suyagi boshchasi bilan tutashadi."],["Foramen obturatum","Yopqich teshik: Chanoq suyagidagi yirik teshik."],["Os ischii","O‘tirg‘ich suyagi: Chanoqning orqa-pastki qismi."],["Os pubis","Qov suyagi: Chanoqning old-pastki qismi."]]},
    "anat_8": {"src":"/static/illustrations/anat_8.svg","title":"Oyoq erkin qismi suyaklari","alt":"Son, tizza, boldir va oyoq panjasi skeleti","facts":[["Femur","Son suyagi: Tananing eng uzun suyagi."],["Patella","Tizza qopqog‘i: Tizza old tomonidagi suyak."],["Tibia","Katta boldir suyagi: Boldirning ichki, yirik suyagi."],["Fibula","Kichik boldir suyagi: Boldirning tashqi ingichka suyagi."],["Ossa tarsi","Oyoq kafti usti suyaklari: To‘piq va tovon sohasidagi suyaklar."]]},
    "anat_9": {"src":"/static/illustrations/anat_9.svg","title":"Kalla miya qismi: ensa va tepa suyaklari","alt":"Kalla suyagining orqa va yon tomonlari","facts":[["Ossa parietalia","Tepa suyaklari: Juft suyaklar, kalla gumbazi."],["Os occipitale","Ensa suyagi: Kallaning orqa-pastki qismi."],["Sutura sagittalis","Sagittal chok: Ikki tepa suyagi oralig‘ida."],["Sutura lambdoidea","Lambdasimon chok: Tepa va ensa suyaklari chegarasi."],["Protuberantia occipitalis","Ensa bo‘rtig‘i: Ensa tashqi yuzasidagi bo‘rtiq."]]},
    "anat_11": {"src":"/static/illustrations/anat_11.svg","title":"Ponasimon va chakka suyaklari","alt":"Ponasimon suyak va chakka suyagining yon tomondan tuzilishi","facts":[["Os sphenoidale","Ponasimon suyak: Kalla asosining markaziy suyagi."],["Ala major","Katta qanot: Ponasimon suyak yon qismi."],["Ala minor","Kichik qanot: Ponasimon suyak yuqori yon qismi."],["Os temporale","Chakka suyagi: Eshituv apparati atrofidagi suyak."],["Meatus acusticus externus","Tashqi eshituv yo‘li: Chakka suyagining yon teshigi."]]},
    "anat_12": {"src":"/static/illustrations/anat_12.svg","title":"Kalla yuz qismi: jag‘ va mayda suyaklar","alt":"Yuz skeleti va asosiy juft suyaklarning joylashuvi","facts":[["Maxilla","Yuqori jag‘: Yuqori tish qatorini tutadi."],["Mandibula","Pastki jag‘: Harakatchan pastki jag‘ suyagi."],["Os zygomaticum","Yonoq suyagi: Yonoq va orbita yon devori."],["Os nasale","Burun suyagi: Burun ko‘prigining suyak qismi."],["Os lacrimale","Ko‘z yosh suyagi: Ko‘z kosasining medial devori."]]},
    "anat_13": {"src":"/static/illustrations/anat_13.svg","title":"Butun kalla: orbita va burun bo‘shlig‘i","alt":"Ko‘z kosalari, burun bo‘shlig‘i va chakka sohasi","facts":[["Orbita","Ko‘z kosasi: Ko‘z olmasi joylashadigan suyak bo‘shlig‘i."],["Cavitas nasi","Burun bo‘shlig‘i: Nafas yo‘llarining bosh qismi."],["Fossa temporalis","Chakka chuqurchasi: Kalla yonidagi botiq soha."],["Arcus zygomaticus","Yonoq yoyi: Yuzning yon suyaksimon yoyi."],["Basis cranii","Kalla asosi: Kallaning tub qismi."]]},
    "anat_14": {"src":"/static/illustrations/anat_14.svg","title":"Kalla asosidagi teshiklar va yoriqlar","alt":"Kalla asosi va uning muhim anatomik teshiklari","facts":[["Foramen magnum","Katta ensa teshigi: Orqa miya o‘tadigan katta teshik."],["Foramen ovale","Oval teshik: Kalla asosidagi oval shaklli teshik."],["Foramen spinosum","Tikanli teshik: Kalla asosining kichik teshiklaridan."],["Canalis opticus","Ko‘ruv kanali: Ko‘ruv nervi yo‘li."],["Fissura orbitalis superior","Yuqori ko‘z kosasi yorig‘i: Orbita bilan kalla bo‘shlig‘i orasidagi yoriq."]]},

    anat_10: {
      src: '/static/illustrations/frontale-ethmoidale.svg',
      title: 'Peshona va g‘alvirsimon suyaklar',
      alt: 'Ikki qismli sxema: kallaning old ko‘rinishida os frontale va os ethmoidale joylashuvi, alohida etmoid suyak sxemasida crista galli, lamina cribrosa, lamina perpendicularis va labyrinthus ethmoidalis',
      facts: [
        ['Os frontale', 'Peshona sohasi, ko‘z kosasi ustki devori va margo supraorbitalis bilan bog‘liq.'],
        ['Os ethmoidale', 'Burun bo‘shlig‘i tomi va ko‘z kosasi ichki devorining bir qismini hosil qiladi.'],
        ['Crista galli', 'G‘alvirsimon suyakning yuqoriga yo‘nalgan o‘simtasi.'],
        ['Lamina cribrosa', 'Hid bilish nervi tolalari o‘tadigan mayda teshikli plastinka.'],
        ['Lamina perpendicularis', 'Burun to‘sig‘ining suyak qismiga qatnashadi.'],
        ['Labyrinthus ethmoidalis', 'G‘alvirsimon suyakning havo hujayralari joylashgan yon qismlari.']
      ]
    }
  });
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
  function showVisualLesson(){
    const l = state.lesson;
    const visual = l && VISUAL_LESSONS[l.id];
    if(!visual) { showLesson(); return; }
    state.tab = 'visual';
    const factCards = visual.facts.map(([name,explanation],i)=>
      '<div class="visual-fact"><span class="visual-number">'+(i+1)+'</span><div><strong>'+esc(name)+'</strong><p>'+esc(explanation)+'</p></div></div>').join('');
    shell('<button class="back" data-action="lesson" data-id="'+rawEsc(l.id)+'">← Mavzuga qaytish</button>'+
      '<p class="eyebrow">'+esc(l.subject_title)+'</p><h1>Rasm orqali tushuntirish</h1>'+
      '<p class="smallprint">'+esc(visual.title)+'</p>'+
      '<figure class="visual-figure"><img class="visual-image" src="'+rawEsc(visual.src)+'" alt="'+esc(visual.alt)+'" loading="eager" decoding="async" /><figcaption>Soddalashtirilgan o‘quv sxemasi. Haqiqiy anatomik preparat yoki atlas o‘rnini bosmaydi.</figcaption></figure>'+
      '<div class="card visual-guide"><h3>Rasmda ko‘rsatilgan tuzilmalar</h3>'+factCards+'</div>'+disclaimer);
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
      (VISUAL_LESSONS[l.id] ? '<button class="card lesson-card visual-entry" data-action="visual"><span class="lesson-icon">🦴</span><span class="lesson-content"><strong>Rasm orqali tushuntirish</strong><small>Lotincha nomlar bilan anatomik sxema</small></span><span class="chevron">›</span></button>' : '')+
      '<button class="card lesson-card" data-action="tutor" data-id="'+rawEsc(l.id)+'"><span class="lesson-icon">🎓</span><span class="lesson-content"><strong>AI Ustoz bilan o‘rganish</strong><small>Ushbu mavzuga oid savol-javob</small></span><span class="chevron">›</span></button>'+
      (l.questions?.length?'<button class="btn btn-primary btn-wide lesson-quiz-cta" data-action="start-quiz">✓ Testni boshlash ('+l.questions.length+')</button>':'')+disclaimer);
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
    state.tab='privacy';shell(`<p class="eyebrow">Shaxsiy ma’lumotlar</p><h1>Maxfiylik va xavfsizlik</h1><div class="card privacy"><h3>Qanday ma’lumotlar saqlanadi?</h3><p>Sinov davrida Telegram foydalanuvchi IDsi, rozilik vaqti, test javoblari va natijalari SQLite bazasida saqlanadi. Tanlangan Oq-yashil yoki Qora-yashil dizayn faqat qurilmangizdagi brauzer xotirasida saqlanadi. Ism, telefon raqami va yozishmalar saqlanmaydi. Dars Ustoz bepul rejimida savol faqat serverdagi dars matni bilan solishtiriladi; u OpenAI API'ga yuborilmaydi va bizning SQLite bazamizga yozilmaydi. AI Ustoz rejimi faqat alohida rozilikdan so‘ng savol va oxirgi uchta suhbat almashinuvini OpenAI APIga yuboradi. Suhbat matni SQLite bazasiga yozilmaydi va sahifa yangilanganda yo‘qoladi. AI javobi xato bo‘lishi mumkin.</p><h3>Ma’lumotlar kimga tegishli?</h3><p>Test natijalarini ilova administratori serverda boshqaradi. Ilova hozircha mustaqil o‘quv prototipi, universitetning rasmiy xizmati emas.</p><h3>Ma’lumotlarni o‘chirish</h3><p>Quyidagi tugma orqali shaxsiy test tarixingiz va rozilik yozuvini o‘chirishingiz mumkin.</p><button class="btn btn-danger btn-wide" data-action="delete">Ma’lumotlarimni o‘chirish</button></div>${disclaimer}`);
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
        case 'visual':if(state.lesson)showVisualLesson();break;
        case 'lesson': if(el.dataset.id)await getLesson(el.dataset.id);break;
        case 'start-quiz':if(state.lesson && state.lesson.questions?.length)startQuiz(state.lesson.questions,'full','required');break;
        case 'answer':state.quiz.answers[state.quiz.pos]=Number(el.dataset.value);renderQuiz();break;
        case 'next':await next();break;
        case 'retry':if(state.tab==='result')await retryWrong();else await init();break;
        case 'progress':await progress();break;
        case 'privacy':privacy();break;
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
