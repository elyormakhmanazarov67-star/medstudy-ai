(() => {
  'use strict';
  const webapp = window.Telegram?.WebApp;
  webapp?.ready();
  webapp?.expand();
  try { webapp?.setHeaderColor('#0b1832'); } catch (_) {}

  const app = document.getElementById('app');
  const demo = new URLSearchParams(location.search).get('demo') === '1' && ['localhost', '127.0.0.1'].includes(location.hostname);
  const auth = webapp?.initData || '';
  const state = { tab: 'home', catalog: null, progress: null, studyPlan: null, history: null, lesson: null, quiz: null, result: null, consent: null, busy: false, tutorStatus: null, tutorQuestion:'', tutorAnswer: null, tutorLessonId:'' };
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
  const header = () => `<header class="sitehead"><div class="brand"><div class="logo">✦</div><div><strong>MedStudy AI</strong><small>O‘quv platforma</small></div></div><span class="pill"><span class="pill-dot"></span> SINOV v0.5</span></header>`;
  const nav = () => `<div class="footer-nav"><div class="nav-inner"><button class="nav ${state.tab==='home'?'active':''}" data-action="home"><b>⌂</b>Asosiy</button><button class="nav ${state.tab==='progress'?'active':''}" data-action="progress"><b>▥</b>Natijalar</button><button class="nav ${state.tab==='tutor'?'active':''}" data-action="tutor"><b>✧</b>AI Ustoz</button><button class="nav ${state.tab==='privacy'?'active':''}" data-action="privacy"><b>♢</b>Maxfiylik</button></div></div>`;
  const disclaimer = `<div class="caution">⚠️ Mazkur darslar sinov materialidir; mutaxassis ko‘rigidan o‘tmagan. Klinik amaliyot uchun yo‘riqnoma yoki rasmiy universitet xizmati emas.</div>`;
  const shell = content => { app.innerHTML = strings(header() + '<main>' + content + '</main>' + nav()); window.scrollTo(0,0); };
  const loading = () => { app.innerHTML = `<div class="boot"><div class="loader"></div><p>Ma’lumotlar yuklanmoqda…</p></div>`; };
  const fail = err => shell(`<div class="empty"><div class="symbol">⚠️</div><h2>Ulanishda xatolik</h2><p class="error">${esc(err.message)}</p><button class="btn btn-primary" data-action="retry">Qayta urinish</button><p class="smallprint">Telegram orqali qayta oching. Lokal demo uchun yo‘riqnoma bilan ishga tushiring.</p></div>`);
  const subjectSummary = () => (state.catalog?.subjects || []).flatMap(s=>s.lessons.map(l=>({...l,subject_title:s.title})));
  const sourcesReady = lesson => (lesson?.teacher_materials || []).length > 0;
  const hasQuestions = lesson => (lesson?.questions || []).length > 0;
  const displayCategory = (lesson, kind) => {
    const docs = kind === 'required' ? (lesson.teacher_materials || []) : (lesson.supplementary || []);
    const back = '<button class="back" data-action="lesson" data-id="'+rawEsc(lesson.id)+'">← Mavzuga qaytish</button>';
    const name = kind === 'required' ? 'Kerakli ma’lumotlar' : 'Qo‘shimcha ma’lumotlar';
    const intro = kind === 'required'
      ? 'Bu bo‘limda o‘qituvchi yuborgan materiallar va ulardan tayyorlangan testlar bor.'
      : 'Mavzuga oid bepul o‘quv konspektlari va SamMU elektron kutubxonasidagi kitob havolalari alohida ko‘rsatiladi.';
    const renderLink = doc => {
      const title = '<strong>'+rawEsc(doc.title)+'</strong>';
      const note = doc.access || doc.note || '';
      const hint = note ? '<p class="smallprint">'+esc(note)+'</p>' : '';
      if(typeof doc.url === 'string' && /^https:\/\//.test(doc.url)) {
        return '<div class="card"><a href="'+rawEsc(doc.url)+'" rel="noopener noreferrer" target="_blank">'+title+' ↗</a>'+hint+'</div>';
      }
      return '<div class="card">'+title+'<p class="smallprint">'+rawEsc(doc.filename || '')+'</p>'+hint+'</div>';
    };
    let cards = '';
    if(kind === 'required') {
      cards = docs.map(renderLink).join('');
      cards += (lesson.sections||[]).map(s=>'<section class="lesson-section"><h3>'+esc(s.heading)+'</h3><p>'+esc(s.body)+'</p></section>').join('');
      if(lesson.questions?.length) cards += '<div class="card"><h3>Kerakli ma’lumotlar testi</h3><button class="btn btn-primary btn-wide" data-action="start-quiz">Testni boshlash ('+lesson.questions.length+')</button></div>';
      if(!docs.length && !lesson.sections?.length)cards = '<div class="empty"><h3>Hozircha material yo‘q</h3><p>O‘qituvchi materiallari kelishi kutilmoqda.</p></div>';
    } else {
      const extraSections = lesson.supplement_sections || [];
      cards = '<div class="sectionhead"><h2>Bepul qo‘shimcha konspektlar</h2></div>';
      if(extraSections.length)cards += extraSections.map(s=>'<section class="lesson-section"><h3>'+esc(s.heading)+'</h3><p>'+esc(s.body)+'</p></section>').join('');
      else cards += '<div class="card"><p>Mavzu bo‘yicha bepul konspekt hozircha tayyor emas. Bu kitob matni o‘qilganini anglatmaydi.</p></div>';
      if(docs.length)cards += '<div class="sectionhead"><h2>Bepul xorijiy manbalar</h2></div>'+docs.map(renderLink).join('');
      if(lesson.supplement_questions?.length)cards += '<div class="card"><h3>Qo‘shimcha ma’lumotlar testi</h3><button class="btn btn-primary btn-wide" data-action="start-supplement-quiz">Qo‘shimcha testni boshlash ('+lesson.supplement_questions.length+')</button></div>';
      const books = lesson.sammu_books || [];
      cards += '<div class="sectionhead"><h2>SamMU elektron kutubxonasidagi kitoblar</h2></div>';
      if(books.length)cards += '<p class="smallprint">Bu kitob havolalari ma’lumotnoma sifatida saqlangan. To‘liq matnni o‘qish uchun SamMU HEMIS ruxsati kerak bo‘lishi mumkin.</p>'+books.map(renderLink).join('');
      else cards += '<div class="card"><p>Bu mavzu uchún SamMU katalogidan kitob aniqlanmagan.</p></div>';
    }
    shell(back+'<p class="eyebrow">'+esc(lesson.subject_title)+'</p><h1>'+name+'</h1><p class="smallprint">'+intro+'</p>'+cards+disclaimer);
  };
  function home() {
    state.tab='home';
    const subjects=state.catalog?.subjects || [];
    const lessons=subjectSummary();
    const completed=state.progress?.latest?.filter(x=>lessons.some(l=>l.id===x.lesson_id)).length || 0;
    const attempts=state.progress?.attempts_count || 0;
    const cards=subjects.map(s=>'<button class="card lesson-card" data-action="subject" data-id="'+rawEsc(s.id)+'"><span class="lesson-icon">📚</span><span class="lesson-content"><strong>'+esc(s.title)+'</strong><small>'+s.lessons.length+' ta mavzu</small></span><span class="chevron">›</span></button>').join('');
    shell('<section class="hero"><p class="eyebrow">Talabalar uchún o‘quv platforma</p><h1>MedStudy AI</h1><p>O‘qituvchi yuborgan materiallar va SamMU kutubxonasidan qo‘shimcha o‘qish — alohida bo‘limlarda.</p></section>'+
      '<div class="stats"><div class="stat"><strong>'+subjects.length+'</strong><small>Fan</small></div><div class="stat"><strong>'+lessons.length+'</strong><small>Mavzu</small></div><div class="stat"><strong>'+attempts+'</strong><small>Test urinish</small></div></div>'+
      '<div class="sectionhead"><h2>Fanlar</h2><span>'+completed+'/'+lessons.length+' o‘rganilgan</span></div>'+cards+disclaimer+
      '<div class="footer-logo">MedStudy AI · Mustaqil ta’lim loyihasi</div>');
  }
  function showSubject(id){
    const s=(state.catalog?.subjects||[]).find(x=>x.id===id);
    if(!s)return home();
    state.tab='subject';state.subjectId=id;
    const cards=s.lessons.map((l,i)=>'<button class="card lesson-card" data-action="lesson" data-id="'+rawEsc(l.id)+'"><span class="lesson-icon">📖</span><span class="lesson-content"><span class="tag">'+(i+1)+'-MAVZU</span><strong>'+esc(l.title)+'</strong><small>'+l.section_count+' bo‘lim · '+l.question_count+' savol</small></span><span class="chevron">›</span></button>').join('');
    shell('<button class="back" data-action="home">← Fanlar</button><h1>'+esc(s.title)+'</h1>'+
      '<p class="smallprint">Mavzuni tanlang, so‘ng kerakli yoki qo‘shimcha ma’lumotlarni oching.</p>'+cards);
  }
  async function getLesson(id) {
    loading();
    try { state.lesson=await api('/lessons/'+encodeURIComponent(id)); showLesson(); }
    catch(e){ fail(e); }
  }
  function showLesson(){
    state.tab='lesson';
    const l=state.lesson;
    const needed=(l.teacher_materials||[]).length;
    const extra=(l.supplement_sections||[]).length;
    const books=(l.sammu_books||[]).length;
    shell('<button class="back" data-action="subject" data-id="'+rawEsc(l.subject_id)+'">← Mavzular</button>'+
      '<p class="eyebrow">'+esc(l.subject_title)+'</p><h1>'+esc(l.title)+'</h1>'+
      '<p class="smallprint">Mavzu ichidagi bo‘limni tanlang.</p>'+
      '<button class="card lesson-card" data-action="category" data-kind="required"><span class="lesson-icon">📘</span><span class="lesson-content"><strong>Kerakli ma’lumotlar</strong><small>O‘qituvchi materiallari · '+needed+' fayl</small></span><span class="chevron">›</span></button>'+
      '<button class="card lesson-card" data-action="category" data-kind="supplementary"><span class="lesson-icon">📗</span><span class="lesson-content"><strong>Qo‘shimcha ma’lumotlar</strong><small>Bepul konspekt · '+extra+' bo‘lim · '+books+' kitob</small></span><span class="chevron">›</span></button>'+
      disclaimer);
  }
  function startQuiz(questions, mode='full', category='required') {
    if (!questions.length) { state.tab='lesson'; showLesson(); return; }
    state.quiz={questions,mode,category,answers:Array(questions.length).fill(null),pos:0};
    renderQuiz();
  }
  function renderQuiz() {
    state.tab='quiz';const qz=state.quiz;const q=qz.questions[qz.pos];const val=qz.answers[qz.pos];const n=qz.questions.length;
    shell(`<button class="back" data-action="lesson" data-id="${rawEsc(state.lesson.id)}">← Mavzuga qaytish</button><div class="quiz-top"><span>${qz.category==='supplementary'?'Qo‘shimcha ma’lumotlar testi':qz.mode==='retry'?'Xatolarni takrorlash':'Kerakli ma’lumotlar testi'}</span><strong>${qz.pos+1}/${n}</strong></div><div class="bar"><div class="bar-fill" style="width:${Math.round((qz.pos)/n*100)}%"></div></div><h2 class="question">${esc(q.q)}</h2><div class="answers">${q.options.map((opt,i)=>`<button class="answer ${val===i?'selected':''}" data-action="answer" data-value="${i}"><span class="letter">${'ABCD'[i]}</span>${esc(opt)}</button>`).join('')}</div><div class="quiz-actions"><button class="btn btn-primary btn-wide" data-action="next" ${val===null||state.busy?'disabled':''}>${qz.pos===n-1?'Testni yakunlash':'Keyingi savol →'}</button></div><p class="inline-note">To‘g‘ri javob va izohlar test yakunida ko‘rsatiladi.</p>`);
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
    if(state.quiz?.category==='supplementary'){startQuiz(state.lesson.supplement_questions,'full','supplementary');return;}
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
    const recommendations=plan.length ? `<div class="sectionhead"><h2>🎯 Shaxsiy o‘quv rejam</h2><span>${plan.length} mavzu</span></div><p class="smallprint">Tavsiyalar oxirgi to‘liq test va xato javoblardan hisoblanadi.</p>${plan.map(item=>`<button class="card lesson-card" data-action="lesson" data-id="${esc(item.lesson_id)}"><span class="lesson-icon">📖</span><span class="lesson-content"><strong>${esc(item.lesson_title)}</strong><small>${esc(item.action)} · ${esc(item.reason)}</small></span><span class="chevron">›</span></button>`).join('')}` : '';
    shell(`<p class="eyebrow">Mening o‘sishim</p><h1>O‘quv natijalarim</h1><p class="smallprint">Faqat shaxsiy test natijalaringiz ko‘rsatiladi.</p><div class="stats"><div class="stat"><strong>${p.attempts_count}</strong><small>Urinishlar</small></div><div class="stat"><strong>${p.latest.length}</strong><small>O‘rganilgan mavzu</small></div><div class="stat"><strong>${p.latest.length?Math.round(p.latest.reduce((x,r)=>x+r.percent,0)/p.latest.length):0}%</strong><small>Oxirgi o‘rtacha</small></div></div>${recommendations}${historyHtml}<div class="sectionhead"><h2>Mavzular kesimida</h2><span>Oxirgi urinishlar</span></div>${p.latest.length?`<div class="card">${p.latest.map(r=>`<div class="progress-row"><div class="progress-label"><strong>${esc(r.title)}</strong><span>${r.score}/${r.total} · ${r.percent}%</span></div><div class="bar"><div class="bar-fill" style="width:${r.percent}%"></div></div></div>`).join('')}<p class="smallprint">Eslatma: xatolarni takrorlash testida savollar soni kamroq bo‘lishi mumkin.</p></div>`:`<div class="empty"><div class="symbol">📊</div><h3>Natijalar hozircha yo‘q</h3><p>Birinchi testni topshiring — progress shu yerda ko‘rinadi.</p><button class="btn btn-primary" data-action="home">Darslarni ko‘rish →</button></div>`}`);
  }
  function privacy(){
    state.tab='privacy';shell(`<p class="eyebrow">Shaxsiy ma’lumotlar</p><h1>Maxfiylik va xavfsizlik</h1><div class="card privacy"><h3>Qanday ma’lumotlar saqlanadi?</h3><p>Sinov davrida faqat Telegram foydalanuvchi IDsi, rozilik vaqti, test javoblari va natijalari SQLite bazasida saqlanadi. Ism, telefon raqami va yozishmalar saqlanmaydi. Dars Ustoz bepul rejimida savol faqat serverdagi dars matni bilan solishtiriladi; u OpenAI API'ga yuborilmaydi va bizning SQLite bazamizga yozilmaydi. Kelajakda alohida AI rejimi yoqilsa, tashqi xizmat uchun yangi rozilik talab qilinadi.</p><h3>Ma’lumotlar kimga tegishli?</h3><p>Test natijalarini ilova administratori serverda boshqaradi. Ilova hozircha mustaqil o‘quv prototipi, universitetning rasmiy xizmati emas.</p><h3>Ma’lumotlarni o‘chirish</h3><p>Quyidagi tugma orqali shaxsiy test tarixingiz va rozilik yozuvini o‘chirishingiz mumkin.</p><button class="btn btn-danger btn-wide" data-action="delete">Ma’lumotlarimni o‘chirish</button></div>${disclaimer}`);
  }
  function consentScreen(){
    app.innerHTML=strings(header()+`<main class="privacy"><p class="eyebrow">Xush kelibsiz</p><h1>MedStudy AI’ga kirish</h1><div class="card"><h3>Yopiq sinovga rozilik</h3><p>Ta’limiy tajriba uchun Telegram ID, rozilik vaqti, test javoblari va natijalari administrator serveridagi SQLite bazasida saqlanadi. Ism, telefon va yozishmalar saqlanmaydi. Dars Ustoz bepul rejimida savolingiz serverdagi dars bilan solishtiriladi va bizning SQLite bazamizga saqlanmaydi. Tashqi AI xizmatiga hech narsa yuborilmaydi.</p><p>Keyin “Maxfiylik” bo‘limidan ularni o‘chirish mumkin. Materiallar ekspert tasdig‘ini olmagan.</p><button class="btn btn-primary btn-wide" data-action="consent">Roziman · Davom etish</button><div class="spacer"></div><p class="smallprint">Rozilik bermasangiz, natijalar saqlanmaydi va ilovadan foydalanish boshlanmaydi.</p></div></main>`);
  }

  async function tutorScreen(id='') {
    state.tab='tutor';
    if(id) state.tutorLessonId=id;
    loading();
    try { state.tutorStatus=await api('/tutor/status'); renderTutor(); }
    catch(e) { fail(e); }
  }
  function renderTutor() {
    state.tab='tutor';
    const t=state.tutorStatus;
    const lessons=subjectSummary();
    if (!state.tutorLessonId && lessons[0]) state.tutorLessonId=lessons[0].id;
    const select=lessons.map(l=>`<option value="${esc(l.id)}" ${l.id===state.tutorLessonId?'selected':''}>${esc(l.title)}</option>`).join('');
    let result='';
    if(state.tutorAnswer) {
      result=`<div class="card ai-result"><h3>✧ Dars yordamchisi javobi</h3><p>${esc(state.tutorAnswer.answer).replace(/\n/g,'<br>')}</p><div class="smallprint">Foydalanilgan dars bo‘limlari: ${esc(state.tutorAnswer.sections.join(' · '))}</div><p class="smallprint">${esc(state.tutorAnswer.notice)}</p></div>`;
    }
    shell(`<p class="eyebrow">Yuborilgan manbalar bo‘yicha yordamchi</p><h1>✧ Dars Ustoz</h1><p class="smallprint">Bepul rejim · Darslardan tayyor izohlar; bu ChatGPT yoki generativ AI emas.</p>${disclaimer}<div class="card"><p class="smallprint">Savollar darsning original konspekti va testlaridan javob oladi. OpenAI API chaqirilmaydi va to‘lov qilinmaydi.</p><label for="tutor-lesson">Mavzuni tanlang</label><select id="tutor-lesson" class="ai-input">${select}</select><label for="tutor-mode">O‘rganish usuli</label><select id="tutor-mode" class="ai-input"><option value="explain">Sodda tushuntirish</option><option value="example">Misol bilan tushuntirish</option><option value="recall">Bilimni tekshiruvchi savol</option></select><label for="tutor-question">Savolingiz</label><textarea id="tutor-question" class="ai-input" maxlength="500" rows="4" placeholder="Masalan: Ergonomika nima uchun kerak?">${esc(state.tutorQuestion)}</textarea><p class="smallprint">Savol serverdagi dars matnida qidiriladi. Bemor yoki maxfiy ma’lumotni kiritmang.</p><button class="btn btn-primary btn-wide" data-action="tutor-ask" ${state.busy?'disabled':''}>${state.busy?'Javob tayyorlanmoqda…':'Darsdan javob olish →'}</button></div>${result}`);
  }
  async function tutorAsk() {
    if(state.busy) return;
    const mode=document.getElementById('tutor-mode')?.value||'explain';
    const select=document.getElementById('tutor-lesson');
    const field=document.getElementById('tutor-question');
    state.tutorLessonId=select?.value||state.tutorLessonId;
    state.tutorQuestion=field?.value.trim()||'';
    if(state.tutorQuestion.length < 5) { alert('Savol kamida 5 ta belgi bo‘lsin'); return; }
    state.busy=true;
    renderTutor();
    try { state.tutorAnswer=await api('/tutor/lesson','POST',{lesson_id:state.tutorLessonId,question:state.tutorQuestion,mode}); }
    catch(e) { state.busy=false; fail(e); return; }
    state.busy=false;renderTutor();
  }

  async function init(){
    loading();try {
      const me=await api('/me');state.consent=me.consented;
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
        case 'subject':showSubject(el.dataset.id);break;
        case 'category':if(state.lesson)displayCategory(state.lesson,el.dataset.kind);break;
        case 'lesson': if(el.dataset.id)await getLesson(el.dataset.id);break;
        case 'start-quiz':if(state.lesson && state.lesson.questions?.length)startQuiz(state.lesson.questions,'full','required');break;
        case 'start-supplement-quiz':if(state.lesson && state.lesson.supplement_questions?.length)startQuiz(state.lesson.supplement_questions,'full','supplementary');break;
        case 'answer':state.quiz.answers[state.quiz.pos]=Number(el.dataset.value);renderQuiz();break;
        case 'next':await next();break;
        case 'retry':if(state.tab==='result')await retryWrong();else await init();break;
        case 'progress':await progress();break;
        case 'privacy':privacy();break;
        case 'tutor':await tutorScreen(el.dataset.id||'');break;
        case 'tutor-consent':await api('/tutor/consent','POST');await tutorScreen();break;
        case 'tutor-ask':await tutorAsk();break;
        case 'tutor-revoke':await api('/tutor/consent','DELETE');state.tutorAnswer=null;await tutorScreen();break;
        case 'consent':await api('/consent','POST');await init();break;
        case 'delete':if(!confirm('Barcha test natijalari o‘chirilsinmi?'))return;await api('/me','DELETE');state.catalog=null;state.progress=null;state.studyPlan=null;state.history=null;state.tutorAnswer=null;state.tutorQuestion='';await init();break;
      }
    }catch(e){fail(e);}
  });
  init();
})();
