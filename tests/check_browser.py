"""Manual headless UI smoke test; not included in normal pytest run."""
import os, subprocess, time
import requests
from playwright.sync_api import sync_playwright
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
env=os.environ.copy();env['DEV_PREVIEW']='1'
p=subprocess.Popen(['python','-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8899'],cwd=ROOT,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
try:
 for _ in range(45):
  try:
   r=requests.get('http://127.0.0.1:8899/api/health',timeout=.3)
   if r.status_code==200:break
  except Exception:pass
  time.sleep(.2)
 else: raise RuntimeError(p.stderr.read().decode())
 with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
  page=browser.new_page(viewport={'width':390,'height':844},device_scale_factor=1)
  errors=[]
  page.on('pageerror',lambda exc:errors.append(str(exc)))
  page.goto('http://127.0.0.1:8899/?demo=1',wait_until='domcontentloaded')
  page.get_by_text('Roziman · Davom etish').click(timeout=5000)
  page.get_by_text('Darslar kutubxonasi').wait_for(timeout=5000)
  page.screenshot(path='/mnt/data/medstudy_miniapp_preview.png',full_page=True)
  page.locator('[data-action="lesson"]').first.click(timeout=5000)
  page.get_by_text('Bugungi maqsad').wait_for(timeout=5000)
  page.locator('[data-action="start-quiz"]').first.click()
  for _ in range(10):
   page.locator('[data-action="answer"]').first.click()
   page.locator('[data-action="next"]').click(timeout=5000)
  page.get_by_text('Test yakunlandi').wait_for(timeout=5000)
  page.locator('[data-action="progress"]').first.click()
  page.get_by_text('O‘quv natijalarim').wait_for(timeout=5000)
  print('BROWSER_TEST_OK',{'title':page.title(),'js_errors':errors,'screenshot':'/mnt/data/medstudy_miniapp_preview.png'})
  browser.close()
finally:
 p.terminate();
 try:p.wait(timeout=3)
 except subprocess.TimeoutExpired:p.kill()
