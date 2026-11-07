"""UI smoke test without network or public browser access."""
from playwright.sync_api import sync_playwright
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
CAT=json.loads((ROOT/'content'/'lessons.json').read_text())
CSS=(ROOT/'app/static/style.css').read_text()
JS=(ROOT/'app/static/app.js').read_text()
mockdata=json.dumps(CAT,ensure_ascii=False)
with sync_playwright() as pw:
 browser=pw.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox','--disable-web-security'])
 page=browser.new_page(viewport={'width':390,'height':844},device_scale_factor=1)
 errors=[]
 page.on('pageerror',lambda exc:errors.append(str(exc)))
 page.set_content(f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body><div id="app"></div></body></html>')
 page.evaluate('''(catalog) => {
 window.Telegram={WebApp:{ready(){},expand(){},setHeaderColor(){},initData:'mock-signed'}};
 let consented=false; let count=0;
 window.fetch=async (url,opts={})=>{
 const path=url.replace(/^\\/api/,''); let data={},status=200;
 if(path==='/me'&&opts.method==='POST'){consented=true;data={consented:true};}
 else if(path==='/consent'){consented=true;data={consented:true};}
 else if(path==='/me')data={consented};
 else if(path==='/catalog')data={subjects:catalog.subjects.map(s=>({...s,lessons:s.lessons.map(l=>({id:l.id,title:l.title,section_count:l.sections.length,question_count:l.questions.length}))}))};
 else if(path==='/progress')data={latest:[],attempts_count:count};
 else if(path.startsWith('/lessons/')){const l=catalog.subjects[0].lessons.find(x=>x.id===path.split('/').at(-1));data={...l,questions:l.questions.map(q=>({id:q.id,q:q.q,options:q.options}))};}
 else if(path==='/attempts'){count++;let b=JSON.parse(opts.body);let qs=catalog.subjects[0].lessons[0].questions;let details=qs.map((q,i)=>({question_id:q.id,chosen:b.answers[i],answer:q.answer,correct:b.answers[i]===q.answer,explanation:q.explanation}));let score=details.filter(x=>x.correct).length;data={score,total:details.length,percent:Math.round(100*score/details.length),details};}
 else {status=404;data={detail:'not found'};}
 return {ok:status===200,status,json:async()=>data};
 };
}''',CAT)
 page.add_script_tag(content=JS)
 page.get_by_text('Roziman · Davom etish').click()
 page.get_by_text('Darslar kutubxonasi').wait_for()
 page.screenshot(path='/mnt/data/medstudy_miniapp_preview.png',full_page=True)
 page.locator('[data-action="lesson"]').first.click()
 page.get_by_text('Bugungi maqsad').wait_for()
 page.locator('[data-action="start-quiz"]').first.click()
 for i in range(10):
  page.locator('[data-action="answer"]').first.click()
  page.locator('[data-action="next"]').click()
 page.get_by_text('Test yakunlandi').wait_for()
 print('FRONTEND_SMOKE_TEST_OK',{'errors':errors,'screenshot':'/mnt/data/medstudy_miniapp_preview.png','quiz_result':page.get_by_text('to‘g‘ri javob',exact=False).first.inner_text()})
 browser.close()
