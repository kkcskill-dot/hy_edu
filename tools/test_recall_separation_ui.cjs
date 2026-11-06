/* Focused DOM/state regression tests; install jsdom outside the repository.
 * NODE_PATH=/tmp/hyedu-ai2026-test/node_modules node tools/test_recall_separation_ui.cjs
 */
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { JSDOM } = require('jsdom');
const base = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(base, 'index.html'), 'utf8');
const read = file => JSON.parse(fs.readFileSync(path.join(base, file), 'utf8'));
const quizCode = html.slice(html.indexOf('var MX_UNITS ='), html.indexOf('window.$docsify ='));
const lectureCode = html.slice(html.indexOf('function lecPrepare('), html.indexOf('function lecVoice('));
const scoreCode = html.slice(html.indexOf('function lastQuizScore('), html.indexOf('function decorateNav('));

function setup() {
  const dom = new JSDOM('<main class="markdown-section"></main>', { url: 'https://hyedu.test/', runScripts: 'outside-only' });
  const w = dom.window;
  w.scrollTo = () => {};
  w.confirm = () => true;
  w.decorateNav = () => {};
  w.BUILD = 'test';
  w.eval(quizCode + lectureCode + scoreCode);
  return { dom, w };
}

const tests = [];
function test(name, action) { tests.push([name, action]); }

test('mixed pools separate regular MC and both forms of blank without changing original data', () => {
  const { dom, w } = setup();
  const unit = read('quiz/u01.json');
  const news = read('quiz/w01.json');
  const before = JSON.stringify([unit, news]);
  const unitMain = w.mxPartData(unit, 'mc', 'mc');
  const unitCloze = w.mxPartData(unit, 'mc', 'blank');
  assert.equal(unitMain.pool.length, 2);
  assert.equal(unitCloze.pool.length, 8);
  assert.equal(w.mxPartData(news, 'list', 'mc').pool.length, 48);
  assert.equal(w.mxPartData(news, 'list', 'blank').pool.length, 37);
  assert.equal(w.mxPartData(news, 'num', 'blank').pool.length, 144);
  assert.notEqual(unitMain.id, unitCloze.id);
  assert.equal(w.mxPartData(unit, 'ox', null).id, 'u01-ox');
  assert.equal(w.mxPartData(unit, 'blank', null).id, 'u01-blank');
  assert.equal(w.mxPracticeType({ type: 'mc', q: 'AICC(스마트 고객센터)의 기능은?' }), 'mc');
  assert.equal(JSON.stringify([unit, news]), before);
  dom.window.close();
});

test('the real page loader applies data-type before building quiz questions', async () => {
  const { dom, w } = setup();
  const sources = { 'quiz/u01.json': read('quiz/u01.json'), 'quiz/w01.json': read('quiz/w01.json') };
  w.fetch = async url => ({ ok: true, json: async () => sources[url.split('?')[0]] });
  w.document.querySelector('main').innerHTML =
    '<div id="unit" class="mock-exam" data-src="quiz/u01.json" data-part="mc" data-type="mc"></div>' +
    '<div id="list" class="mock-exam" data-src="quiz/w01.json" data-part="list" data-type="mc"></div>' +
    '<div id="cloze" class="mock-exam" data-src="quiz/u01.json" data-part="mc" data-type="blank"></div>';
  w.mockExamPlugin({ doneEach: callback => callback() });
  await new Promise(resolve => w.setTimeout(resolve, 10));
  assert.equal(w.document.querySelectorAll('.mx-error').length, 0);
  assert.equal(w.document.querySelectorAll('#unit .mx-q').length, 2);
  assert.equal(w.document.querySelectorAll('#list .mx-q').length, 20);
  assert.equal(w.document.querySelectorAll('#list .mx-blank').length, 0);
  assert.equal(w.document.querySelectorAll('#cloze .mx-q').length, 8);
  assert.equal(w.document.querySelectorAll('#cloze .mx-passage').length, 8);
  dom.window.close();
});

test('archived input blank, O/X, and choice-cloze still grade correctly and preserve legacy histories', () => {
  const { dom, w } = setup();
  const data = read('quiz/u01.json');
  const legacy = { history: [{ t: 1, score: 70 }], answers: {}, graded: false };
  w.localStorage.setItem('hyedu.mock.u01-mc', JSON.stringify(legacy));
  const cases = [
    w.mxPartData(data, 'blank', null),
    w.mxPartData(data, 'ox', null),
    w.mxPartData(data, 'mc', 'blank'),
  ];
  for (const view of cases) {
    view.pool = view.pool.slice(0, 1);
    w.localStorage.setItem('hyedu.mock.' + view.id, JSON.stringify({ history: [{ t: 1, score: 55 }] }));
    const q = view.pool[0];
    const root = w.document.createElement('div');
    w.document.querySelector('main').replaceChildren(root);
    w.mxBuild(root, view);
    if (q.type === 'blank') {
      [...root.querySelectorAll('.mx-blank')].forEach((input, i) => {
        input.value = q.answers[i][0];
        input.dispatchEvent(new w.Event('input', { bubbles: true }));
      });
    } else {
      const correctText = q.choices[q.answer - 1].replace(/\*\*/g, '');
      const correctLabel = [...root.querySelectorAll('.mx-choice')].find(label => {
        const content = label.querySelector(q.type === 'ox' ? '.mx-mark' : '.mx-text');
        return content.textContent === correctText;
      });
      assert.ok(correctLabel);
      correctLabel.querySelector('input').click();
    }
    root.querySelector('.mx-submit').click();
    assert.equal(root.querySelectorAll('.mx-q.is-correct').length, 1);
    assert.ok(root.querySelector('.mx-score').textContent.includes('100'));
    const history = JSON.parse(w.localStorage.getItem('hyedu.mock.' + view.id)).history;
    assert.deepEqual(history.map(entry => entry.score), [55, 100]);
  }
  assert.deepEqual(JSON.parse(w.localStorage.getItem('hyedu.mock.u01-mc')), legacy);
  dom.window.close();
});

test('the primary navigation score excludes archived and formerly mixed scores', () => {
  const { dom, w } = setup();
  for (const [id, score] of [['u01-blank', 100], ['u01-ox', 90], ['u01-mc', 80], ['u01-mc-blank', 70]]) {
    w.localStorage.setItem('hyedu.mock.' + id, JSON.stringify({ history: [{ score }] }));
  }
  assert.equal(w.lastQuizScore(1), null);
  w.localStorage.setItem('hyedu.mock.u01-mc-mc', JSON.stringify({ history: [{ score: 40 }, { score: 60 }] }));
  assert.equal(w.lastQuizScore(1), 60);
  assert.equal(JSON.parse(w.localStorage.getItem('hyedu.mock.u01-ox')).history[0].score, 90);
  dom.window.close();
});

test('every lecture uses only regular MC checks while retaining its teaching slides', () => {
  const { dom, w } = setup();
  let checks = 0;
  for (let n = 1; n <= 7; n++) {
    const suffix = String(n).padStart(2, '0');
    const lecture = read(`lecture/u${suffix}.json`);
    const questions = read(`quiz/u${suffix}.json`);
    const prepared = w.lecPrepare(lecture, questions);
    const quizzes = prepared.slides.filter(slide => slide.type === 'quiz');
    checks += quizzes.length;
    assert.ok(quizzes.every(slide => w.mxPracticeType(slide.q) === 'mc'), `Unit ${n}`);
    const teaching = prepared.slides.filter(slide => !['quiz', 'end'].includes(slide.type));
    assert.equal(teaching.length, lecture.steps.length);
    assert.deepEqual(Array.from(teaching, slide => slide.p), lecture.steps.map(step => step.p));
  }
  assert.ok(checks > 0);
  dom.window.close();
});

(async () => {
  for (const [name, action] of tests) {
    try { await action(); console.log(`PASS ${name}`); }
    catch (error) { console.error(`FAIL ${name}\n${error.stack}`); process.exitCode = 1; }
  }
})();
