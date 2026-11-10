/** Exercise the Mini App's actual rendered lesson UI with an authorized mock API. */
'use strict';
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');

const js = fs.readFileSync('app/static/app.js', 'utf8');
const lessonData = JSON.parse(fs.readFileSync('content/lessons.json', 'utf8'));
const preklinik = lessonData.subjects.find(s => s.id === 'stom_prerest');
const first = preklinik.lessons[0];
assert.equal(first.id, 'ergonomika');
const illustrations = JSON.parse(
  fs.readFileSync('app/static/illustrations/preklinik/catalog.json', 'utf8')
);
const events = {};
const app = {innerHTML: ''};
const document = {
  documentElement: {dataset: {}, style: {}},
  getElementById(id) {return id === 'app' ? app : null;},
  querySelector() {return null;},
  addEventListener(type, fn) {events[type] = fn;},
};
const webapp = {
  initData: 'test-auth',
  ready() {},
  expand() {},
  setHeaderColor() {},
  setBackgroundColor() {},
};
const mockFetch = async (url) => {
  let payload;
  if (url === '/api/me') payload = {consented: true, approval_required: false};
  else if (url === '/api/catalog') payload = {
    subjects: [{
      id: preklinik.id,
      title: preklinik.title,
      lessons: preklinik.lessons.map(l => ({
        id: l.id,
        title: l.title,
        section_count: l.sections.length,
        question_count: l.questions.length,
      })),
    }],
  };
  else if (url === '/api/progress') payload = {latest: [], attempts_count: 0};
  else if (url === '/api/lessons/ergonomika') payload = {
    ...first,
    subject_id: preklinik.id,
    subject_title: preklinik.title,
  };
  else if (url === '/static/illustrations/preklinik/catalog.json') payload = illustrations;
  else throw new Error('Unexpected HTTP request '+url);
  return {ok: true, status: 200, json: async () => payload};
};
const window = {
  Telegram: {WebApp: webapp},
  scrollTo() {},
  localStorage: {getItem() {return null;}, setItem() {}},
};
vm.runInNewContext(js, {
  window, document, fetch: mockFetch,
  location: {search: '', hostname: 'medstudy.example.org'},
  URLSearchParams,
}, {filename: 'app.js'});

function click(action, id) {
  return events.click({target: {closest: () => ({
    disabled: false, dataset: {action, id},
  })}});
}
async function tick() {
  await new Promise(resolve => setImmediate(resolve));
}
(async () => {
  await tick();
  await click('lesson', 'ergonomika');
  assert.match(app.innerHTML, /Mutaxassislikka kirish/);
  assert.match(app.innerHTML, /data-action="category"/);
  assert.match(app.innerHTML, /data-action="preklinik-visual"/);
  assert.match(app.innerHTML, /data-action="tutor"/);

  await click('preklinik-visual');
  assert.match(app.innerHTML, /Rasm orqali tushuntirish/);
  assert.match(app.innerHTML, /preklinik\/ergonomika\.svg/);
  assert.match(app.innerHTML, /Bemor kreslosi/);
  assert.match(app.innerHTML, /Yoritgich/);
  assert.match(app.innerHTML, /Asboblar bloki/);
  console.log('PREKLINIK_UI_OK: authorized lesson has a visual entry and a functional diagram screen');
})().catch(err => {console.error(err); process.exitCode = 1;});
