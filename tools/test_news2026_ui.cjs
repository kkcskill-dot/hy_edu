/* DOM integration tests. Install jsdom in a temporary directory, then run:
 * NODE_PATH=/tmp/hyedu-ai2026-test/node_modules node tools/test_news2026_ui.cjs
 * No server, browser session, or production dependency is needed.
 */
'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { JSDOM } = require('jsdom');

const base = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(base, 'index.html'), 'utf8');
const read = p => JSON.parse(fs.readFileSync(path.join(base, p), 'utf8'));
const bank = read('practice/news2026/bank.json');
const mocks = [1, 2, 3, 4].map(n => read(`practice/news2026/mock${n}.json`));
const codeStart = html.indexOf('var MX_UNITS =');
const codeEnd = html.indexOf('window.$docsify =', codeStart);
assert.ok(codeStart > 0 && codeEnd > codeStart, 'Quiz script boundaries are present');
const quizCode = html.slice(codeStart, codeEnd);
const plain = text => text.replace(/\*\*/g, '').replace(/\s+/g, ' ').trim();

function setup() {
  const dom = new JSDOM('<!doctype html><main class="markdown-section"></main>', {
    url: 'https://hyedu.test/#/practice/news2026/quiz.md', runScripts: 'outside-only',
  });
  const w = dom.window;
  w.scrollTo = () => {};
  w.confirm = () => true;
  w.decorateNav = () => {};
  w.BUILD = 'test';
  w.eval(quizCode);
  let root;
  const mount = (data, filtered = false) => {
    root = w.document.createElement('div');
    root.className = 'mock-exam';
    w.document.querySelector('main').replaceChildren(root);
    w[filtered ? 'mxFilterBuild' : 'mxBuild'](root, data);
    return root;
  };
  return { dom, w, mount, root: () => w.document.querySelector('.mock-exam') };
}

function answer(root, data, wrongAt = -1, leaveAt = -1) {
  const qs = data.pool || data.questions;
  const rendered = [...root.querySelectorAll('.mx-q')];
  rendered.forEach((item, index) => {
    if (index === leaveAt) return;
    const text = plain(item.querySelector('.mx-q-text').textContent);
    const q = qs.find(candidate => plain(candidate.q) === text);
    assert.ok(q, `Rendered question matches source: ${text}`);
    const choice = q.choices[index === wrongAt ? q.answer % q.choices.length : q.answer - 1];
    const label = [...item.querySelectorAll('.mx-choice')]
      .find(el => plain(el.querySelector('.mx-text').textContent) === plain(choice));
    assert.ok(label, 'Original answer text exists in the shuffled choices');
    label.querySelector('input').click();
  });
  return rendered.length;
}

function result(root, correct, total) {
  assert.equal(root.querySelectorAll('.mx-q.is-correct').length, correct);
  assert.equal(root.querySelectorAll('.mx-q.is-wrong').length, total - correct);
  assert.ok(root.querySelector('.mx-score').textContent.includes(`${total}문항 중 ${correct}문항 정답`));
  assert.equal(root.querySelectorAll('input:not(:disabled)').length, 0);
  assert.equal(root.querySelectorAll('.mx-fb[hidden]').length, 0);
  assert.ok(root.querySelectorAll('.mx-fb a[href^="reader.html?doc=webzine-"]').length >= total);
}

function test(name, fn) {
  try { fn(); console.log(`PASS ${name}`); }
  catch (error) { console.error(`FAIL ${name}\n${error.stack}`); process.exitCode = 1; }
}

test('all inline scripts parse', () => {
  const dom = new JSDOM(html);
  [...dom.window.document.querySelectorAll('script:not([src])')].forEach(script => {
    new vm.Script(script.textContent);
  });
  dom.window.close();
});

test('shuffled practice answers grade by content, persist, and retain history after retry', () => {
  const t = setup();
  const legacy = { answers: { 1: 2 }, history: [{ score: 57 }], graded: false };
  t.w.localStorage.setItem('hyedu.mock.set1', JSON.stringify(legacy));
  const data = t.w.mxFilteredData(bank, { topic: 'all', difficulty: 'all', format: 'all' });
  let root = t.mount(data);
  assert.equal(root.querySelectorAll('.mx-q').length, 10);
  answer(root, data);
  const chosen = [...root.querySelectorAll('input:checked')].map(el => el.value);
  const order = JSON.parse(t.w.localStorage.getItem(`hyedu.mock.${data.id}`)).order;
  root = t.mount(data);
  assert.deepEqual([...root.querySelectorAll('input:checked')].map(el => el.value), chosen);
  assert.deepEqual(JSON.parse(t.w.localStorage.getItem(`hyedu.mock.${data.id}`)).order, order);
  root.querySelector('.mx-submit').click();
  result(root, 10, 10);
  let state = JSON.parse(t.w.localStorage.getItem(`hyedu.mock.${data.id}`));
  assert.equal(state.history.length, 1);
  assert.equal(state.history[0].score, 100);
  root = t.mount(data);
  result(root, 10, 10);
  assert.equal(JSON.parse(t.w.localStorage.getItem(`hyedu.mock.${data.id}`)).history.length, 1);
  root.querySelector('.mx-retry').click();
  root = t.root();
  assert.equal(root.querySelectorAll('input:checked').length, 0);
  assert.equal(root.querySelectorAll('.mx-q.is-correct').length, 0);
  assert.equal(JSON.parse(t.w.localStorage.getItem(`hyedu.mock.${data.id}`)).history.length, 1);
  assert.deepEqual(JSON.parse(t.w.localStorage.getItem('hyedu.mock.set1')), legacy);
  t.dom.window.close();
});

test('wrong-only mode and unanswered confirmation preserve expected grading', () => {
  const t = setup();
  const data = t.w.mxFilteredData(bank, { topic: 'all', difficulty: 'all', format: 'all' });
  const root = t.mount(data);
  answer(root, data, 0, 1);
  t.w.confirm = () => false;
  root.querySelector('.mx-submit').click();
  assert.equal(root.querySelectorAll('.mx-q.is-correct').length, 0);
  assert.equal(root.querySelectorAll('input:disabled').length, 0);
  t.w.confirm = () => true;
  root.querySelector('.mx-submit').click();
  result(root, 8, 10);
  root.querySelector('.mx-only-wrong').click();
  assert.ok(root.classList.contains('mx-wrong-only'));
  assert.equal(root.querySelector('.mx-only-wrong').textContent, '전체 문제 보기');
  root.querySelector('.mx-only-wrong').click();
  assert.ok(!root.classList.contains('mx-wrong-only'));
  t.dom.window.close();
});

test('filter selections create disjoint saved sessions and exact subsets', () => {
  const t = setup();
  const first = t.w.mxFilteredData(bank, { topic: 'prism', difficulty: '상', format: 'all' });
  const second = t.w.mxFilteredData(bank, { topic: 'care', difficulty: '상', format: 'all' });
  assert.ok(first.pool.length && second.pool.length);
  assert.notEqual(first.id, second.id);
  assert.deepEqual(first.pool.map(q => q.id), bank.pool.filter(q => q.topic === 'prism' && q.difficulty === '상').map(q => q.id));
  let root = t.mount(first);
  answer(root, first);
  const saved = t.w.localStorage.getItem(`hyedu.mock.${first.id}`);
  root = t.mount(second);
  assert.equal(root.querySelectorAll('input:checked').length, 0);
  assert.equal(t.w.localStorage.getItem(`hyedu.mock.${first.id}`), saved);
  root = t.mount(first);
  assert.equal(root.querySelectorAll('input:checked').length, first.pool.length);
  t.dom.window.close();
});

test('filter controls persist choices, resume answers, and handle an empty intersection', () => {
  const t = setup();
  let root = t.mount(bank, true);
  function choose(field, value) {
    const select = root.querySelector(`select[data-filter="${field}"]`);
    assert.ok(select);
    select.value = value;
    select.dispatchEvent(new t.w.Event('change', { bubbles: true }));
  }
  assert.equal(root.querySelectorAll('.mx-q').length, 10);
  choose('topic', 'prism');
  const firstInput = root.querySelector('input[type="radio"]');
  const chosenText = firstInput.closest('.mx-q').querySelector('.mx-q-text').textContent;
  firstInput.click();
  choose('topic', 'care');
  assert.equal(root.querySelectorAll('input:checked').length, 0);
  assert.equal(JSON.parse(t.w.localStorage.getItem(`hyedu.news2026.filters.${bank.id}`)).topic, 'care');
  choose('topic', 'prism');
  assert.equal(root.querySelectorAll('input:checked').length, 1);
  assert.equal(root.querySelector('input:checked').closest('.mx-q').querySelector('.mx-q-text').textContent, chosenText);
  root = t.mount(bank, true);
  assert.equal(root.querySelector('select[data-filter="topic"]').value, 'prism');
  assert.equal(root.querySelectorAll('input:checked').length, 1);

  const formats = [...root.querySelector('select[data-filter="format"]').options]
    .map(option => option.value).filter(value => value !== 'all');
  let empty;
  for (const topic of Object.keys(bank.topics)) {
    for (const difficulty of ['중', '상']) {
      for (const format of formats) {
        if (!bank.pool.some(q => q.topic === topic && q.difficulty === difficulty && q.format === format)) {
          empty = { topic, difficulty, format };
        }
      }
    }
  }
  assert.ok(empty, 'A genuine empty filter combination exists');
  for (const [field, value] of Object.entries(empty)) choose(field, value);
  assert.ok(root.querySelector('.mx-empty'));
  assert.equal(root.querySelectorAll('.mx-q').length, 0);
  assert.equal(root.querySelector('.mx-submit'), null);
  assert.ok(root.querySelector('.mx-filter-status').textContent.includes('0문항'));
  choose('format', 'all');
  assert.ok(root.querySelectorAll('.mx-q').length > 0);
  assert.equal(root.querySelector('.mx-empty'), null);
  t.dom.window.close();
});

test('whole-bank mode and nested retry retain working filter controls', () => {
  const t = setup();
  const root = t.mount(bank, true);
  root.querySelector('.mx-size').click();
  assert.equal(root.querySelectorAll('.mx-q').length, 120);
  answer(root, bank);
  root.querySelector('.mx-submit').click();
  result(root, 120, 120);
  root.querySelector('.mx-retry').click();
  assert.equal(root.querySelectorAll('input:checked').length, 0);
  root.querySelector('.mx-size').click();
  assert.equal(root.querySelectorAll('.mx-q').length, 10);
  const select = root.querySelector('select[data-filter="topic"]');
  select.value = 'aicc';
  select.dispatchEvent(new t.w.Event('change', { bubbles: true }));
  assert.equal(root.querySelectorAll('.mx-q').length, 10);
  const aicc = bank.pool.filter(q => q.topic === 'aicc');
  assert.ok([...root.querySelectorAll('.mx-q-text')].every(el => aicc.some(q => plain(q.q) === plain(el.textContent))));
  t.dom.window.close();
});

test('all four fixed mock exams grade all 30 and report all twelve topics', () => {
  for (const data of mocks) {
    const t = setup();
    const root = t.mount(data);
    assert.equal(answer(root, data), 30);
    root.querySelector('.mx-submit').click();
    result(root, 30, 30);
    assert.equal(root.querySelectorAll('.mx-units li').length, 12);
    assert.equal(JSON.parse(t.w.localStorage.getItem(`hyedu.mock.${data.id}`)).history[0].score, 100);
    t.dom.window.close();
  }
});

test('old textbook exam still grades by its own state and source format', () => {
  const t = setup();
  const data = read('mock/set1.json');
  const root = t.mount(data);
  assert.equal(answer(root, data), 20);
  root.querySelector('.mx-submit').click();
  assert.equal(root.querySelectorAll('.mx-q.is-correct').length, 20);
  assert.equal(root.querySelectorAll('.mx-fb a[href^="#/original/"]').length, 20);
  assert.equal(JSON.parse(t.w.localStorage.getItem('hyedu.mock.set1')).history[0].score, 100);
  t.dom.window.close();
});
