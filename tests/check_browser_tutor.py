"""Headless front-end AI page smoke test, with all network calls faked."""
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT = Path(__file__).resolve().parents[1]
JS=(ROOT/'app/static/app.js').read_text(encoding='utf-8')
CSS=(ROOT/'app/static/style.css').read_text(encoding='utf-8')
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':390,'height':844})
    page.set_default_timeout(3000)
    errors=[]
    page.on('pageerror', lambda err: errors.append(str(err)))
    page.set_content(f'<html><head><meta charset="utf-8"><style>{CSS}</style></head><body><div id="app"></div></body></html>')
    page.evaluate('''() => {
      window.Telegram={WebApp:{initData:'mock',ready(){},expand(){},setHeaderColor(){}}};
      let consented=false, aiConsent=false, used=0;
      window.fetch=async(url,opts={})=>{
        const path=url.replace(/^\\/api/,''); let data={};
        if(path==='/me') data={consented};
        else if(path==='/consent'){consented=true;data={consented:true};}
        else if(path==='/catalog')data={subjects:[{id:'dent',title:'Preklinik stomatologiya',lessons:[{id:'ergonomika',title:'Ergonomika',section_count:7,question_count:10}]}]};
        else if(path==='/progress')data={latest:[],attempts_count:0};
        else if(path==='/tutor/status')data={consented:aiConsent,enabled:true,used,limit:5,remaining:5-used};
        else if(path==='/tutor/consent'&&opts.method==='POST'){aiConsent=true;data={consented:true};}
        else if(path==='/tutor/ask'){used++;data={answer:'Ergonomika ish joyini qulay tashkil etishga yordam beradi.',sections:['Ergonomika tushunchasi'],remaining:4,notice:'AI javobi tekshirilmagan'};}
        else throw Error(path);
        return {ok:true,status:200,json:async()=>data};
      };
    }''')
    page.add_script_tag(content=JS)
    print('JS_LOADED', page.locator('#app').inner_text()[:180], flush=True)
    print('CLICK_CONSENT',flush=True)
    page.get_by_text('Roziman · Davom etish').click()
    print('WAIT_HOME', flush=True)
    page.get_by_text('Darslar kutubxonasi').wait_for()
    print('CLICK_TUTOR',flush=True)
    page.locator('[data-action="tutor"]').first.click()
    page.locator('#tutor-provider').select_option('ai')
    page.get_by_text('OpenAI API orqali savol berish uchun alohida rozilik kerak', exact=False).wait_for()
    page.get_by_text('Roziman · AI Ustozni ochish').click()
    page.locator('#tutor-question').fill('Ergonomika nima uchun kerak?')
    page.get_by_text('AI Ustozdan so‘rash →').click()
    page.get_by_text('Ergonomika ish joyini qulay', exact=False).wait_for()
    page.screenshot(path='/mnt/data/MedStudy_AI_v0.4_UI_preview.png',full_page=True)
    assert not errors,errors
    print('AI_TUTOR_BROWSER_SMOKE_OK: separate consent, question, answer, no JS errors')
    browser.close()
