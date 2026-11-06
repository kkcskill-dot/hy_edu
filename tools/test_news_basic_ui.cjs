/* New basic exams through the actual Docsify quiz loader, using jsdom (no browser).
 * NODE_PATH=/tmp/hyedu-ai2026-test/node_modules node tools/test_news_basic_ui.cjs
 */
'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { JSDOM } = require('jsdom');
const base = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(base, 'index.html'), 'utf8');
const start = html.indexOf('var MX_UNITS =');
const end = html.indexOf('window.$docsify =', start);
const plain = s => s.replace(/\*\*/g, '').replace(/\s+/g, ' ').trim();
assert.ok(start > 0 && end > start);

async function main() {
  const dom = new JSDOM('<main class="markdown-section"></main>', {
    url: 'https://hyedu.test/#/practice/news-basic/README.md', runScripts: 'outside-only',
  });
  const w = dom.window;
  w.scrollTo = () => {};
  w.confirm = () => true;
  w.decorateNav = () => {};
  w.BUILD = 'basic-test';
  const fetched = [];
  w.fetch = async url => {
    fetched.push(url);
    assert.ok(url.endsWith('?v=basic-test'));
    return { ok: true, json: async () => JSON.parse(fs.readFileSync(path.join(base, url.split('?')[0]), 'utf8')) };
  };
  w.eval(html.slice(start, end));
  let load;
  w.mockExamPlugin({ doneEach: fn => { load = fn; } });
  const root = () => w.document.querySelector('.mock-exam');
  async function mount(name) {
    const markdown = fs.readFileSync(path.join(base, `practice/news-basic/${name}.md`), 'utf8');
    const widget = markdown.match(/<div class="mock-exam"[^>]*><\/div>/)[0];
    w.document.querySelector('main').innerHTML = widget;
    load();
    await new Promise(resolve => setImmediate(resolve));
    assert.equal(root().querySelectorAll('.mx-error').length, 0);
    assert.equal(root().querySelectorAll('.mx-q').length, 30);
    assert.equal(root().querySelectorAll('.mx-blank, .mx-ox').length, 0);
    assert.equal(root().querySelectorAll('input[type="radio"]').length, 150);
    const src = root().dataset.src;
    return JSON.parse(fs.readFileSync(path.join(base, src), 'utf8'));
  }
  function answer(data, wrongAt = -1, leaveAt = -1) {
    const pool = data.questions || data.pool;
    [...root().querySelectorAll('.mx-q')].forEach((li, index) => {
      if (index === leaveAt) return;
      const q = pool.find(q => plain(q.q) === plain(li.querySelector('.mx-q-text').textContent));
      assert.ok(q);
      const expected = q.choices[index === wrongAt ? q.answer % 5 : q.answer - 1];
      const label = [...li.querySelectorAll('.mx-choice')].find(el => plain(el.querySelector('.mx-text').textContent) === plain(expected));
      assert.ok(label);
      label.querySelector('input').click();
    });
  }
  function checkResult(correct, total = 30) {
    assert.equal(root().querySelectorAll('.mx-q.is-correct').length, correct);
    assert.equal(root().querySelectorAll('.mx-q.is-wrong').length, total - correct);
    assert.ok(root().querySelector('.mx-score').textContent.includes(`${total}문항 중 ${correct}문항 정답`));
    assert.equal(root().querySelectorAll('.mx-fb a[href^="reader.html?doc=webzine-"]').length, total);
    assert.equal(root().querySelectorAll('.mx-fb[hidden], input:not(:disabled)').length, 0);
  }
  const sentinels = ['set1', 'news2026-mock1-v1', 'news2026-bank-v1-all-all-all', 'u01-mc-mc', 'w01-ox-ox'];
  sentinels.forEach(id => w.localStorage.setItem(`hyedu.mock.${id}`, '{"history":[{"score":73}]}'));
  for (let n = 1; n <= 9; n++) {
    const data = await mount(`mock${n}`);
    assert.equal(root().querySelectorAll('input:checked').length, 0);
    answer(data);
    await mount(`mock${n}`);
    assert.equal(root().querySelectorAll('input:checked').length, 30);
    root().querySelector('.mx-submit').click();
    checkResult(30);
    await mount(`mock${n}`);
    checkResult(30);
    assert.equal(JSON.parse(w.localStorage.getItem(`hyedu.mock.${data.id}`)).history.length, 1);
  }
  console.log('PASS all 9 basic exams load, grade, resume, and show 270 source links');
  const first = await mount('mock1');
  root().querySelector('.mx-retry').click();
  answer(first, 0, 1);
  w.confirm = () => false;
  root().querySelector('.mx-submit').click();
  assert.equal(root().querySelectorAll('.mx-q.is-correct').length, 0);
  w.confirm = () => true;
  root().querySelector('.mx-submit').click();
  checkResult(28);
  root().querySelector('.mx-only-wrong').click();
  assert.ok(root().classList.contains('mx-wrong-only'));
  assert.equal(JSON.parse(w.localStorage.getItem(`hyedu.mock.${first.id}`)).history.length, 2);
  console.log('PASS wrong answers, unanswered confirmation, retry, and history');
  const bank = await mount('quiz');
  answer(bank);
  root().querySelector('.mx-submit').click();
  checkResult(30);
  root().querySelector('.mx-size').click();
  assert.equal(root().querySelectorAll('.mx-q').length, 270);
  answer(bank);
  root().querySelector('.mx-submit').click();
  checkResult(270, 270);
  sentinels.forEach(id => assert.equal(w.localStorage.getItem(`hyedu.mock.${id}`), '{"history":[{"score":73}]}'));
  assert.equal(JSON.parse(w.localStorage.getItem(`hyedu.mock.${first.id}`)).history.length, 2);
  console.log('PASS random practice and all 270 questions grade with shuffled options; existing records unchanged');
  assert.equal(new Set(fetched.map(url => url.split('?')[0])).size, 10);
  dom.window.close();
}
main().catch(error => { console.error(error); process.exitCode = 1; });
