/* Offline DOM component checks. This file only reads the public template/catalog.
 * Run: NODE_PATH=frontend/node_modules node --test luji-career-kit/assets/resume_gallery.test.cjs
 * jsdom does not verify browser layout, screenshots, or the iframe documents.
 */
'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { JSDOM, VirtualConsole } = require('jsdom');

const templateHtml = fs.readFileSync(path.join(__dirname, 'resume_gallery.html'), 'utf8');
const catalog = JSON.parse(fs.readFileSync(path.join(__dirname, '../references/resume-samples.json'), 'utf8'));
const templateNames = [
  ['evidence-archive', '证据档案'],
  ['classic-single', '经典单栏'],
  ['ats-minimal', '简洁文本'],
  ['project-first', '项目优先'],
  ['profile-split', '简介侧栏'],
  ['experience-first', '经历优先'],
];

function payload() {
  return {
    default_template: 'profile-split',
    default_avatar: 'a',
    templates: templateNames.map(([id, name]) => ({
      id, name, description: `${name}说明`,
      variants: Object.fromEntries(['a', 'b', 'none'].map(avatar => [avatar, `previews/${avatar}/${id}.html`])),
      embedded_variants: Object.fromEntries(['a', 'b', 'none'].map(avatar => [avatar, `embedded-previews/${avatar}/${id}.html`])),
    })),
    avatars: [
      { id: 'a', name: '头像 A', thumbnail: 'avatars/a.png' },
      { id: 'b', name: '头像 B', thumbnail: 'avatars/b.png' },
      { id: 'none', name: '不放头像', thumbnail: null },
    ],
    references: structuredClone(catalog.items),
    workbench_url: 'fixtures/a/views/overview.html',
  };
}

function gallery(t, { data = payload(), hash = '' } = {}) {
  const requests = [];
  const errors = [];
  const virtualConsole = new VirtualConsole();
  virtualConsole.on('jsdomError', error => errors.push(error));
  // Mirror the generator's JSON-in-script encoding, so external strings remain data.
  const json = JSON.stringify(data).replace(/</g, '\\u003c');
  const dom = new JSDOM(templateHtml.replace('__GALLERY_DATA__', json), {
    // A virtual local origin exercises history.replaceState; jsdom rejects it on file: URLs.
    // No server is started and subresource loading remains disabled.
    url: `http://127.0.0.1:8027/index.html${hash}`,
    runScripts: 'dangerously',
    // Omit `resources`: jsdom does not fetch images, scripts, or iframe files.
    virtualConsole,
    beforeParse(window) {
      window.fetch = (...args) => {
        requests.push(args);
        throw new Error('Network is disabled for gallery DOM tests');
      };
      window.XMLHttpRequest = class {
        constructor() {
          requests.push('XMLHttpRequest');
          throw new Error('Network is disabled for gallery DOM tests');
        }
      };
      window.WebSocket = class {
        constructor() {
          requests.push('WebSocket');
          throw new Error('Network is disabled for gallery DOM tests');
        }
      };
    },
  });
  t.after(() => dom.window.close());
  assert.deepEqual(errors, [], 'inline gallery script must execute without jsdom errors');
  return { window: dom.window, document: dom.window.document, data, requests, errors };
}

function assertSelection(ui, templateId, avatarId, { hash = true } = {}) {
  const { document, data, window } = ui;
  const chosenTemplate = data.templates.find(item => item.id === templateId);
  const chosenAvatar = data.avatars.find(item => item.id === avatarId);
  const expectedFile = chosenTemplate.variants[avatarId];
  const tabs = [...document.querySelectorAll('[data-template]')];
  const avatars = [...document.querySelectorAll('[data-avatar]')];
  assert.equal(tabs.length, 6);
  assert.equal(avatars.length, 3);
  for (const tab of tabs) {
    const selected = tab.dataset.template === templateId;
    assert.equal(tab.getAttribute('role'), 'tab');
    assert.equal(tab.getAttribute('aria-selected'), String(selected));
    assert.equal(tab.tabIndex, selected ? 0 : -1, 'only the selected template is in the tab order');
    assert.equal(tab.getAttribute('aria-controls'), 'preview-panel');
  }
  for (const avatar of avatars) {
    assert.equal(avatar.getAttribute('aria-pressed'), String(avatar.dataset.avatar === avatarId));
  }
  assert.equal(document.getElementById('preview-panel').getAttribute('aria-labelledby'), `template-${templateId}`);
  assert.equal(document.getElementById('preview-title').textContent, `${chosenTemplate.name} · ${chosenAvatar.name}`);
  assert.equal(document.getElementById('resume-preview').getAttribute('src'), chosenTemplate.embedded_variants[avatarId]);
  assert.equal(document.getElementById('resume-preview').getAttribute('title'), `${chosenTemplate.name} · ${chosenAvatar.name} · 虚构简历预览`);
  assert.equal(document.getElementById('open-preview').getAttribute('href'), expectedFile);
  assert.equal(document.getElementById('selection-status').textContent, `当前样式：${chosenTemplate.name}（${templateId}） · ${chosenAvatar.name}`);
  if (hash) {
    const params = new URLSearchParams(window.location.hash.slice(1));
    assert.equal(params.get('template'), templateId);
    assert.equal(params.get('avatar'), avatarId);
  }
  assert.deepEqual(ui.errors, []);
}

function changeHash(ui, hash) {
  ui.window.history.replaceState(null, '', hash);
  ui.window.dispatchEvent(new ui.window.HashChangeEvent('hashchange'));
}

test('initial default selection exposes six tabs, three avatar choices, and a sandboxed local preview', t => {
  const ui = gallery(t);
  assertSelection(ui, 'profile-split', 'a', { hash: false });
  assert.equal(ui.document.getElementById('template-list').getAttribute('aria-orientation'), 'vertical');
  assert.equal(ui.document.getElementById('resume-preview').getAttribute('sandbox'), '');
  assert.equal(ui.document.getElementById('open-preview').target, '_blank');
  assert.equal(ui.document.getElementById('open-preview').rel, 'noopener noreferrer');
  assert.match(ui.document.getElementById('open-preview').textContent, /打印/);
  assert.notEqual(ui.document.getElementById('open-preview').getAttribute('href'), ui.document.getElementById('resume-preview').getAttribute('src'));
  assert.equal(ui.document.getElementById('workbench').getAttribute('href'), ui.data.workbench_url);
});

test('all 18 template/avatar combinations synchronize preview, full link, hash, and accessible state', t => {
  const ui = gallery(t);
  for (const template of ui.data.templates) {
    ui.document.querySelector(`[data-template="${template.id}"]`).click();
    for (const avatar of ui.data.avatars) {
      ui.document.querySelector(`[data-avatar="${avatar.id}"]`).click();
      assertSelection(ui, template.id, avatar.id);
    }
  }
  assert.equal(ui.document.querySelector('[data-avatar="none"] img'), null);
  assert.equal(ui.document.querySelectorAll('#avatar-list img').length, 2);
});

test('arrow keys wrap, Home/End select endpoints, and focus follows the selected template', t => {
  const ui = gallery(t, { hash: '#template=classic-single&avatar=b' });
  const keyToTemplate = [
    ['ArrowRight', 'ats-minimal'],
    ['ArrowDown', 'project-first'],
    ['ArrowLeft', 'ats-minimal'],
    ['ArrowUp', 'classic-single'],
    ['Home', 'evidence-archive'],
    ['ArrowUp', 'experience-first'],
    ['ArrowDown', 'evidence-archive'],
    ['End', 'experience-first'],
    ['ArrowRight', 'evidence-archive'],
  ];
  ui.document.getElementById('template-classic-single').focus();
  for (const [key, templateId] of keyToTemplate) {
    const event = new ui.window.KeyboardEvent('keydown', { key, bubbles: true, cancelable: true });
    ui.document.activeElement.dispatchEvent(event);
    assert.equal(event.defaultPrevented, true, `${key} must not scroll the page`);
    assertSelection(ui, templateId, 'b');
    assert.equal(ui.document.activeElement.id, `template-${templateId}`);
  }
  const unrelated = new ui.window.KeyboardEvent('keydown', { key: 'PageDown', bubbles: true, cancelable: true });
  ui.document.activeElement.dispatchEvent(unrelated);
  assert.equal(unrelated.defaultPrevented, false);
  assertSelection(ui, 'evidence-archive', 'b');
});

test('initial hash and later hash changes restore the matching template and avatar', t => {
  const ui = gallery(t, { hash: '#template=project-first&avatar=none' });
  assertSelection(ui, 'project-first', 'none');
  changeHash(ui, '#template=experience-first&avatar=b');
  assertSelection(ui, 'experience-first', 'b');
  changeHash(ui, '#template=ats-minimal&avatar=a');
  assertSelection(ui, 'ats-minimal', 'a');
});

test('missing and invalid hash values independently fall back to configured defaults', t => {
  const ui = gallery(t, { hash: '#template=unknown&avatar=unknown' });
  assertSelection(ui, 'profile-split', 'a', { hash: false });
  for (const [hash, templateId, avatarId] of [
    ['#template=unknown&avatar=b', 'profile-split', 'b'],
    ['#template=classic-single&avatar=unknown', 'classic-single', 'a'],
    ['#avatar=none', 'profile-split', 'none'],
    ['#template=project-first', 'project-first', 'a'],
    ['#template=%3Cscript%3E&avatar=%00', 'profile-split', 'a'],
    ['#', 'profile-split', 'a'],
  ]) {
    changeHash(ui, hash);
    assertSelection(ui, templateId, avatarId, { hash: false });
  }
  ui.document.querySelector('[data-avatar="b"]').click();
  assertSelection(ui, 'profile-split', 'b');
});

test('seven public references keep licenses and restrictions visible and load no remote media', t => {
  const ui = gallery(t);
  const cards = [...ui.document.querySelectorAll('#reference-list .reference-card')];
  assert.equal(cards.length, 7);
  assert.equal(catalog.items.length, 7);
  cards.forEach((card, index) => {
    const reference = catalog.items[index];
    assert.equal(card.querySelector('h3').textContent, reference.title);
    assert.equal(card.querySelector('.license').textContent, reference.license);
    assert.equal(card.querySelector('p').textContent, reference.usage);
    const links = [...card.querySelectorAll('a')];
    assert.deepEqual(links.map(link => link.textContent), ['项目', '官方样例', '许可证']);
    assert.deepEqual(links.map(link => link.href), [reference.repo_url, reference.preview_url, reference.license_url]);
    for (const link of links) {
      assert.equal(link.target, '_blank');
      assert.equal(link.rel, 'noopener noreferrer');
    }
    assert.equal(Boolean(card.querySelector('.restricted-note')), reference.restricted);
    assert.equal(card.querySelectorAll('img,iframe,object,embed,video,audio,script').length, 0);
  });
  assert.equal(ui.document.querySelectorAll('.restricted-note').length, 2);
  const media = ui.document.querySelectorAll('img[src],iframe[src],script[src],link[href],source[src],video[src],audio[src],object[data],embed[src]');
  for (const element of media) {
    const source = element.getAttribute('src') || element.getAttribute('href') || element.getAttribute('data');
    const resolved = new URL(source, ui.window.location.href);
    assert.ok(resolved.origin === ui.window.location.origin || resolved.protocol === 'data:', source);
  }
  assert.doesNotMatch(ui.document.querySelector('style').textContent, /(?:url\(\s*["']?https?:|@import)/i);
  const csp = ui.document.querySelector('meta[http-equiv="Content-Security-Policy"]').content;
  assert.match(csp, /connect-src 'none'/);
  assert.match(csp, /img-src 'self' file: data:/);
  assert.match(csp, /frame-src 'self' file:/);
  assert.deepEqual(ui.requests, [], 'gallery code must not initiate fetch, XHR, or WebSocket requests');
});

test('external labels remain literal text and unsafe non-HTTPS reference links stay inactive', t => {
  const data = payload();
  const reference = data.references[0];
  reference.title = '<img id="injected-reference" src="https://example.invalid/x" onerror="window.pwned=1">';
  reference.usage = '</p><script>window.pwned=2</script><p>';
  reference.license = '<a href="javascript:alert(1)">MIT</a>';
  reference.repo_url = 'javascript:window.pwned=3';
  reference.preview_url = 'http://example.invalid/untrusted';
  reference.license_url = 'data:text/html,<script>window.pwned=4</script>';
  const ui = gallery(t, { data });
  const card = ui.document.querySelector('.reference-card');
  assert.equal(card.querySelector('h3').textContent, reference.title);
  assert.equal(card.querySelector('p').textContent, reference.usage);
  assert.equal(card.querySelector('.license').textContent, reference.license);
  assert.equal(ui.document.querySelector('#injected-reference'), null);
  assert.equal(card.querySelectorAll('script,img').length, 0);
  assert.equal(ui.window.pwned, undefined);
  for (const link of card.querySelectorAll('a')) {
    assert.equal(link.hasAttribute('href'), false);
    assert.equal(link.hasAttribute('target'), false);
  }
  assert.equal(ui.document.querySelectorAll('#reference-list a[href]').length, 18, 'the remaining six references keep all three HTTPS links');
  assert.deepEqual(ui.requests, []);
});
