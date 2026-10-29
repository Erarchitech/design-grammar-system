import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import ModelScreen from '../src/screens/ModelScreen.jsx';
import EnvironmentToggle from '../src/landing/EnvironmentToggle.jsx';
import { setLang } from '../src/i18n/index.js';
import '../src/styles/styles.css';

window.IS_REACT_ACT_ENVIRONMENT = true;
const results = [];
const errors = [];
window.addEventListener('error', e => errors.push(e.message));
window.addEventListener('unhandledrejection', e => errors.push(String(e.reason)));
const entities = n => Array.from({ length: n }, (_, i) => ({ dgEntityId: `entity-${n}-${i}` }));
window.fetch = async url => {
  let body;
  if (url.includes('/validation/runs/')) body = { runs: [{ runId: 'layout-run', createdAt: '2026-10-25', ruleIds: [], ruleCount: 1 }] };
  else if (url.includes('/validation/view/')) body = { runId: 'layout-run', rules: [], objectSets: { failed: entities(188), passed: entities(121), unknown: entities(4) } };
  else throw new Error(`Unexpected request: ${url}`);
  return new Response(JSON.stringify(body), { status: 200 });
};
const check = (ok, message) => { if (!ok) throw new Error(message); };
const tick = () => act(async () => { await new Promise(resolve => setTimeout(resolve, 0)); });
const container = document.createElement('div');
container.style.cssText = 'position:relative;height:780px';
document.body.style.margin = '0';
document.body.append(container);
const root = createRoot(container);
async function run(name, fn) {
  try { await fn(); results.push({ name, status: 'PASS' }); }
  catch (error) { results.push({ name, status: 'FAIL', error: error.message }); }
}
(async () => {
  for (const lang of ['ru', 'en']) {
    setLang(lang);
    for (const width of [1600, 1280, 1100]) {
      container.style.width = `${width}px`;
      await act(async () => root.render(<ModelScreen key={`${lang}-${width}`} active project="layout-fixture" onBack={() => {}} />));
      for (let i = 0; i < 10; i++) await tick();
      await document.fonts.ready;
      await run(`${lang} ${width}: three counters stay in the card with aligned values`, () => {
        const sidebar = container.querySelectorAll('aside')[1];
        const counts = [...sidebar.querySelectorAll('span')].filter(el => el.style.letterSpacing === 'var(--tracking-heading)' && ['188', '121', '4'].includes(el.textContent));
        check(counts.length === 3, `Expected 3 counters, got ${counts.length}`);
        const card = counts[0].parentElement.parentElement.parentElement.getBoundingClientRect();
        const boxes = counts.map(el => el.getBoundingClientRect());
        check(Math.max(...boxes.map(r => r.top)) - Math.min(...boxes.map(r => r.top)) <= 1, 'Counter values are vertically misaligned');
        for (const count of counts) {
          const label = count.previousElementSibling.getBoundingClientRect();
          check(label.left >= card.left && label.right <= card.right, `Label escapes the card: ${count.previousElementSibling.textContent}`);
          check(count.previousElementSibling.scrollWidth <= count.previousElementSibling.clientWidth + 1, 'Label overflows its column');
        }
        check(sidebar.scrollWidth <= sidebar.clientWidth + 1, 'Properties sidebar overflows horizontally');
      });
      await run(`${lang} ${width}: panels resize inward and keep viewport space`, async () => {
        for (const [id, key] of [['model-states-resize', 'ArrowRight'], ['model-properties-resize', 'ArrowLeft']]) {
          const handle = container.querySelector(`[data-testid="${id}"]`);
          const start = handle.parentElement.getBoundingClientRect().width;
          await act(async () => handle.dispatchEvent(new KeyboardEvent('keydown', { key, bubbles: true })));
          check(handle.parentElement.getBoundingClientRect().width > start, `${id} did not expand`);
        }
        const main = container.querySelector('main').getBoundingClientRect();
        check(main.width >= 240, 'Viewer lost its minimum width');
        check(container.querySelectorAll('aside')[1].scrollWidth <= container.querySelectorAll('aside')[1].clientWidth + 1, 'Properties overflow after resize');
      });
      await run(`${lang} ${width}: opacity controls do not overlap`, () => {
        const toolbar = container.querySelector('main').firstElementChild;
        const sliders = [...toolbar.querySelectorAll('div')].filter(el => el.children.length === 3 && el.firstElementChild?.tagName === 'SPAN' && el.lastElementChild?.tagName === 'SPAN');
        check(sliders.length === 3, `Expected 3 opacity controls, got ${sliders.length}`);
        for (const slider of sliders) {
          const box = slider.getBoundingClientRect();
          const [label, track, value] = [...slider.children].map(el => el.getBoundingClientRect());
          check(label.right <= track.left && track.right <= value.left, 'Opacity label, track or percentage overlap');
          check(value.right <= box.right + 1, 'Percentage escapes the opacity control');
          check(box.left >= toolbar.getBoundingClientRect().left && box.right <= toolbar.getBoundingClientRect().right + 1, 'Opacity control escapes toolbar');
        }
      });
    }
  }
  await run('environment details wait one second and cancel short hover', async () => {
    await act(async () => root.render(<EnvironmentToggle />));
    const button = container.querySelector('[role="switch"]');
    const wait = ms => act(async () => { await new Promise(resolve => setTimeout(resolve, ms)); });
    check(!container.querySelector('[role="status"]'), 'Details initially visible');
    await act(async () => button.dispatchEvent(new PointerEvent('pointerover', { bubbles: true, pointerType: 'mouse' })));
    await wait(700);
    check(!container.querySelector('[role="status"]'), 'Details opened too early');
    await wait(400);
    check(container.querySelector('[role="status"]'), 'Details did not open');
    await act(async () => container.querySelector('.dg-environment').dispatchEvent(new PointerEvent('pointerout', { bubbles: true, relatedTarget: document.body })));
    check(!container.querySelector('[role="status"]'), 'Details did not close');
    await act(async () => button.dispatchEvent(new PointerEvent('pointerover', { bubbles: true, pointerType: 'mouse' })));
    await wait(200);
    await act(async () => button.dispatchEvent(new PointerEvent('pointerout', { bubbles: true, relatedTarget: document.body })));
    await wait(900);
    check(!container.querySelector('[role="status"]'), 'Cancelled hover reopened details');
  });
  await run('narrow container clamps panels without horizontal page overflow', async () => {
    container.style.width = '682px';
    await act(async () => root.render(<ModelScreen key="narrow" active project="layout-fixture" onBack={() => {}} />));
    for (let i = 0; i < 10; i++) await tick();
    const handle = container.querySelector('[data-testid="model-states-resize"]');
    for (let i = 0; i < 40; i++) await act(async () => handle.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true })));
    check(container.querySelector('main').getBoundingClientRect().width >= 239, 'Narrow viewer lost centre space');
    check(container.scrollWidth <= container.clientWidth + 1, 'Narrow layout overflows its container');
  });
  await run('hosted toggle sends only a generation-scoped intent and handles refusal', async () => {
    const original = location.href;
    history.replaceState(null, '', '?host=degram&dgTarget=developer&dgGeneration=7&dgTargetLocked=0');
    await act(async () => root.render(<EnvironmentToggle key="hosted" />));
    const button = container.querySelector('[role="switch"]');
    await act(async () => button.click());
    check(location.hash === '#degram-target=demo:7', 'Unexpected native switch intent');
    check(button.getAttribute('aria-busy') === 'true', 'Missing pending state');
    await act(async () => window.dispatchEvent(new Event('dg-target-refused')));
    check(button.getAttribute('aria-busy') === 'false', 'Refusal left toggle pending');
    check(container.querySelector('[role="status"]'), 'Refusal feedback missing');
    history.replaceState(null, '', original);
  });
  await run('startup-locked hosted toggle cannot emit a switch intent', async () => {
    const original = location.href;
    history.replaceState(null, '', '?host=degram&dgTarget=demo&dgGeneration=8&dgTargetLocked=1');
    await act(async () => root.render(<EnvironmentToggle key="locked" />));
    const button = container.querySelector('[role="switch"]');
    check(button.getAttribute('aria-disabled') === 'true', 'Startup override not presented');
    await act(async () => button.click());
    check(!location.hash, 'Locked toggle emitted an intent');
    history.replaceState(null, '', original);
  });
  await act(async () => root.unmount());
  if (errors.length) results.push({ name: 'Browser errors', status: 'FAIL', error: errors.join('; ') });
  const output = document.createElement('pre'); output.id = 'offline-results'; output.textContent = JSON.stringify({ results }); document.body.append(output);
})().catch(error => {
  const output = document.createElement('pre'); output.id = 'offline-results'; output.textContent = JSON.stringify({ results: [{ name: 'Harness', status: 'FAIL', error: error.message }] }); document.body.append(output);
});
