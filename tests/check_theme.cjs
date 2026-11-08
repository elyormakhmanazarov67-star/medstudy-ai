/** MedStudy theme switch: no dependencies and no network. */
'use strict';
const fs=require('node:fs');
const vm=require('node:vm');
const assert=require('node:assert/strict');
const code=fs.readFileSync('app/static/app.js','utf8');
const css=fs.readFileSync('app/static/style.css','utf8');
const key='medstudy_theme_v1';
function boot(seed={}){
  const values=new Map(Object.entries(seed));
  const changed={headerColors:[],backgroundColors:[],events:{},meta:null};
  const app={innerHTML:''};
  const root={dataset:{},style:{}};
  const meta={setAttribute(name,value){if(name==='content')changed.meta=value;}};
  const document={
    documentElement:root,
    getElementById(id){return id==='app'?app:null;},
    querySelector(query){return query==='meta[name="theme-color"]'?meta:null;},
    addEventListener(name,cb){changed.events[name]=cb;}
  };
  const webapp={initData:'mock',ready(){},expand(){},
    setHeaderColor(value){changed.headerColors.push(value);},
    setBackgroundColor(value){changed.backgroundColors.push(value);}};
  const window={Telegram:{WebApp:webapp},scrollTo(){},localStorage:{
    getItem(k){return values.get(k)||null;},setItem(k,v){values.set(k,v);}
  }};
  const fetch=async()=>({ok:true,status:200,json:async()=>({consented:false})});
  const context={window,document,fetch,location:{search:'',hostname:'localhost'},URLSearchParams};
  vm.runInNewContext(code,context,{filename:'app.js'});
  return {app,root,values,changed};
}
async function main(){
  let b=boot();
  await Promise.resolve();await Promise.resolve();
  assert.equal(b.root.dataset.theme,'white');
  assert.equal(b.root.style.colorScheme,'light');
  assert.match(code,/Dizayn ranglari/); // header appears after consent check
  assert.match(code,/MedStudy AI<\\/h1>/);
  assert.match(code,/pill-dot<\\/span> Bepul/);
  assert.doesNotMatch(code,/\\bv\\d+\\.\\d+(?:\\.\\d+)?\\b/); // no visible version text
  const html=fs.readFileSync('app/static/index.html','utf8');
  assert.match(html,/app\\.js\\?v=1\\.0\\.2/); // force fresh bundle after rollout

  for(const [name,color,scheme] of [
    ['black','#001a10','dark'],['white','#f6faf6','light']
  ]){
    b.changed.events.change({target:{id:'theme-select',value:name}});
    assert.equal(b.root.dataset.theme,name);
    assert.equal(b.root.style.colorScheme,scheme);
    assert.equal(b.changed.meta,color);
    assert.equal(b.changed.headerColors.at(-1),color);
    assert.equal(b.values.get(key),name);
  }
  const persisted=boot({[key]:'black'});
  assert.equal(persisted.root.dataset.theme,'black');
  assert.equal(persisted.root.style.colorScheme,'dark');
  assert.equal(persisted.values.get(key),'black');
  const invalid=boot({[key]:'attack'});
  assert.equal(invalid.root.dataset.theme,'white');
  assert.equal(invalid.values.get(key),'attack'); // invalid preference isn't executed
  const oldBlue=boot({[key]:'blue'});
  assert.equal(oldBlue.root.dataset.theme,'white');
  assert.equal(oldBlue.values.get(key),'white');
  assert.match(code,/Oq-yashil/);
  assert.match(code,/Qora-yashil/);
  assert.doesNotMatch(code,/\['blue','Ko‘k'\]/);
  assert.match(css,/:root\[data-theme="white"\]/);
  assert.match(css,/:root\[data-theme="black"\]/);
  for(const cls of ['.hero','.answer','.footer-nav','.ai-input','.tutor-student','.alphabet-item','.caution','.btn-primary']){
    assert.ok(css.includes(cls),cls+' must be theme-aware');
  }
  // Both monochrome designs keep primary text/buttons comfortably legible.
  const contrast=(a,b)=>{
    const lum=hex=>{
      const n=hex.replace('#','').match(/.{2}/g).map(x=>parseInt(x,16)/255)
        .map(c=>c<=0.04045?c/12.92:((c+0.055)/1.055)**2.4);
      return .2126*n[0]+.7152*n[1]+.0722*n[2];
    };
    const x=lum(a),y=lum(b);return (Math.max(x,y)+.05)/(Math.min(x,y)+.05);
  };
  assert.ok(contrast('#173727','#ffffff')>=7);
  assert.ok(contrast('#f5fff8','#001a10')>=7);
  console.log('THEME_SWITCH_OK: white-green/black-green, migration, persistence, contrast');
}
main().catch(e=>{console.error(e);process.exitCode=1;});
