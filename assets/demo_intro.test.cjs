const assert = require('node:assert/strict');
const { test, before, after } = require('node:test');
const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { JSDOM } = require('jsdom');

let temporary, site, report;
const prefix = 'https://example.invalid/projects/lvji-career-kit/';

before(() => {
  temporary = fs.mkdtempSync(path.join(os.tmpdir(), 'lvji-static-component-'));
  site = path.join(temporary, 'site');
  const script = path.resolve(__dirname, '../scripts/demo_site.py');
  const result = spawnSync(process.env.LVJI_TEST_PYTHON || 'python3', ['-B', script, '--output', site], {
    encoding: 'utf8', env: { ...process.env, LUJI_WORKSPACE_DIR: path.join(temporary, 'never-read-personal-data') },
  });
  assert.equal(result.status, 0, result.stdout + result.stderr);
  report = JSON.parse(result.stdout);
});

after(() => { if (temporary) fs.rmSync(temporary, { recursive: true, force: true }); });

function load(relative, scripts = false) {
  return new JSDOM(fs.readFileSync(path.join(site, relative), 'utf8'), {
    url: prefix + relative,
    ...(scripts ? { runScripts: 'dangerously', pretendToBeVisual: true } : {}),
  });
}

function localDestination(link) {
  const url = new URL(link.href);
  assert.equal(url.origin, new URL(prefix).origin);
  assert.ok(url.pathname.startsWith(new URL(prefix).pathname));
  const relative = decodeURIComponent(url.pathname.slice(new URL(prefix).pathname.length));
  assert.ok(fs.statSync(path.join(site, relative)).isFile(), relative);
  return relative;
}

test('dialogue intro exposes a real read-only journey with working result entries', () => {
  const dom = load('index.html');
  const document = dom.window.document;
  assert.equal(document.querySelectorAll('h1').length, 1);
  assert.ok(document.querySelector('#demo-loop'));
  assert.equal(document.querySelectorAll('#conversation > article').length, 4);
  assert.equal(document.querySelectorAll('form,input,textarea,button,script').length, 0);
  const targets = Array.from(document.querySelectorAll('.scene-result a'), localDestination);
  assert.equal(targets.length, 4);
  assert.ok(targets.some(p => p.startsWith('records/')));
  assert.ok(targets.includes('workbench/plan.html'));
  assert.ok(targets.includes('workbench/applications.html'));
  assert.equal(report.published, false);
  dom.window.close();
});

test('four result views keep navigation beneath a GitHub project prefix and never offer saving', () => {
  for (const view of ['overview', 'plan', 'roles', 'applications']) {
    const dom = load('workbench/' + view + '.html');
    const document = dom.window.document;
    const tabs = Array.from(document.querySelectorAll('nav[aria-label="工作区视图"] a'));
    assert.equal(tabs.length, 4);
    assert.equal(tabs.filter(a => a.getAttribute('aria-current') === 'page').length, 1);
    assert.equal(document.querySelectorAll('form,input,textarea,button,script').length, 0);
    for (const anchor of document.querySelectorAll('a[href]')) localDestination(anchor);
    dom.window.close();
  }
});

test('public gallery switches all combinations to local resources and sandboxed inert previews', () => {
  const dom = load('gallery/index.html', true);
  const document = dom.window.document;
  const avatars = Array.from(document.querySelectorAll('[data-avatar]'));
  const layouts = Array.from(document.querySelectorAll('[data-template]'));
  assert.equal(avatars.length, 3);
  assert.equal(layouts.length, 6);
  for (const avatar of avatars) {
    avatar.click();
    for (const layout of layouts) {
      layout.click();
      const frame = document.querySelector('#resume-preview');
      assert.equal(frame.getAttribute('sandbox'), '');
      const url = new URL(frame.src);
      assert.ok(url.href.startsWith(prefix + 'gallery/embedded-previews/'));
      const relative = decodeURIComponent(url.pathname.slice(new URL(prefix).pathname.length));
      const sample = new JSDOM(fs.readFileSync(path.join(site, relative), 'utf8'));
      assert.equal(sample.window.document.querySelectorAll('a,button,form,script').length, 0);
      sample.window.close();
      assert.ok(localDestination(document.querySelector('#open-preview')).startsWith('gallery/previews/'));
    }
  }
  assert.equal(localDestination(document.querySelector('#workbench')), 'workbench/overview.html');
  for (const image of document.querySelectorAll('img')) {
    assert.ok(image.src.startsWith(prefix + 'assets/'));
  }
  dom.window.close();
});
