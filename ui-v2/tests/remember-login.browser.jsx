import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import LandingLayer from '../src/landing/LandingLayer.jsx';
import { setLang } from '../src/i18n/index.js';

window.IS_REACT_ACT_ENVIRONMENT = true;
const results = [], calls = [], errors = [];
window.addEventListener('error', e => errors.push(e.message));
window.addEventListener('unhandledrejection', e => errors.push(String(e.reason)));
let accepted = false;
window.fetch = async (url, init) => {
  calls.push({ url, body: init.body ? JSON.parse(init.body) : null });
  if (url.endsWith('/auth/options')) return Response.json({ selfRegistration: true });
  if (url.endsWith('/auth/login')) return Response.json({ username: 'synthetic' });
  if (url.endsWith('/auth/me')) return Response.json({ username: 'synthetic', memberships: [] });
  throw new Error(`Unexpected request: ${url}`);
};
const check = (ok, why) => { if (!ok) throw new Error(why); };
const container = document.createElement('div'); document.body.append(container);
const root = createRoot(container);
const render = () => root.render(<LandingLayer active={false} user={null} onFly={() => {}} onUser={() => { accepted = true; }} />);
const click = async element => { check(element, 'Control missing'); await act(async () => element.click()); };
const input = async (element, value) => act(async () => {
  element.focus();
  Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(element, value);
  element.dispatchEvent(new Event('input', { bubbles: true }));
  element.dispatchEvent(new Event('change', { bubbles: true }));
});
const button = text => [...container.querySelectorAll('button')].find(e => e.textContent === text);
async function run(id, fn) { try { await fn(); results.push({ id, status: 'PASS' }); } catch (e) { results.push({ id, status: 'FAIL', error: e.message }); } }
(async () => {
  for (const host of [false, true]) {
    history.replaceState(null, '', location.pathname + (host ? '?host=degram' : ''));
    for (const remembered of [false, true]) {
      await run(`${host ? 'DeGram' : 'WebUI'} remembered=${remembered}`, async () => {
        accepted = false;
        await act(async () => { setLang('en'); render(); });
        await click(button('Log in'));
        const checkbox = container.querySelector('input[type=checkbox]');
        check(checkbox && !checkbox.checked, 'Default is not unchecked');
        check(checkbox.labels[0].textContent.includes('Remember me'), 'Accessible label missing');
        check(document.getElementById(checkbox.getAttribute('aria-describedby')).textContent.includes('30 days'), 'Hint missing');
        await act(async () => setLang('ru'));
        check(checkbox.labels[0].textContent.includes('Запомнить меня'), 'Russian label missing');
        await act(async () => setLang('en'));
        if (remembered) await click(checkbox);
        check(checkbox.checked === remembered, 'Checkbox did not toggle');
        await input(container.querySelector('input[autocomplete=username]'), 'synthetic');
        await input(container.querySelector('input[type=password]'), 'synthetic-password-only');
        await click([...container.querySelectorAll('#dgl-hero-form-card button')].find(e => e.textContent === 'Log in'));
        for (let i = 0; i < 20 && !accepted; i++) await act(async () => { await new Promise(r => setTimeout(r, 0)); });
        check(accepted, `Login did not establish identity: ${container.querySelector('#dgl-hero-form-card')?.textContent}; calls=${JSON.stringify(calls.map(c => c.url))}`);
        const login = calls.filter(c => c.url.endsWith('/auth/login')).at(-1);
        check(login.body.rememberMe === remembered, 'Opt-in lost in request');
        check(!Object.values(localStorage).some(v => String(v).includes('synthetic-password-only')), 'Password leaked to storage');
      });
    }
    await run(`${host ? 'DeGram' : 'WebUI'} option only belongs to login`, async () => {
      await click(button('Log in'));
      await click([...container.querySelectorAll('.dgl-auth-switch')].find(e => e.textContent.includes('Accept invite')));
      check(!container.querySelector('input[type=checkbox]'), 'Remember option leaked into invite');
      await click([...container.querySelectorAll('.dgl-auth-switch')].find(e => e.textContent.includes('Register')));
      check(!container.querySelector('input[type=checkbox]'), 'Remember option leaked into register');
      await click(container.querySelector('.dgl-auth-cancel'));
    });
  }
  await act(async () => root.unmount());
  check(!errors.length, errors.join(', '));
  const output = document.createElement('pre'); output.id = 'offline-results';
  output.textContent = JSON.stringify({ results, errors }); document.body.append(output);
})().catch(e => { document.body.textContent = `HARNESS_ERROR: ${e.stack}`; });
