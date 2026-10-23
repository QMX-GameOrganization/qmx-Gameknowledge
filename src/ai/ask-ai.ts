// 划词问 AI：在正文里选中文字，弹出「问 AI」按钮，在侧边面板里流式显示回答。
// key 只保存在用户自己的浏览器（localStorage），请求直接从浏览器发给所选接口。
import {
  PRESETS, MAX_SELECTION, loadConfig, saveConfig, clearConfig, normalizeBaseUrl,
  chatCompletionsUrl, buildMessages, buildFallbackPrompt, parseSseChunk, describeHttpError,
} from './core.mjs';

type Msg = { role: 'system' | 'user' | 'assistant'; content: string };
type Ask = { selection: string; pageTitle: string; context: string };

let started = false;
let config = loadConfig(localStorage);
let abort: AbortController | null = null;
let current: Ask | null = null;
let history: Msg[] = [];

function el<K extends keyof HTMLElementTagNameMap>(
  tag: K, attrs: Record<string, string> = {}, text = '',
): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  if (text) node.textContent = text;
  return node;
}

// ---------- 划词按钮 ----------
const trigger = el('button', { type: 'button', class: 'qmx-ask-trigger', hidden: '' }, '问 AI');
trigger.setAttribute('aria-label', '用 AI 解释选中的文字');

function selectionInfo(): (Ask & { rect: DOMRect }) | null {
  const sel = window.getSelection();
  if (!sel || sel.isCollapsed || sel.rangeCount === 0) return null;
  const text = sel.toString().trim();
  if (!text) return null;
  const range = sel.getRangeAt(0);
  const host = range.commonAncestorContainer instanceof Element
    ? range.commonAncestorContainer
    : range.commonAncestorContainer.parentElement;
  // 只在正文里响应，避免在导航、搜索框、设置面板里弹出
  if (!host?.closest('.sl-markdown-content')) return null;
  const block = host.closest('p, li, td, blockquote, pre, h1, h2, h3, h4, h5, h6') ?? host;
  return {
    selection: text.slice(0, MAX_SELECTION * 2),
    pageTitle: document.querySelector('h1')?.textContent?.trim() ?? document.title,
    context: block.textContent ?? '',
    rect: range.getBoundingClientRect(),
  };
}

function updateTrigger() {
  const info = selectionInfo();
  if (!info) { trigger.hidden = true; return; }
  current = { selection: info.selection, pageTitle: info.pageTitle, context: info.context };
  trigger.hidden = false;
  const width = trigger.offsetWidth || 64;
  const left = Math.min(Math.max(8, info.rect.left + info.rect.width / 2 - width / 2), window.innerWidth - width - 8);
  const top = info.rect.top > 52 ? info.rect.top - 44 : info.rect.bottom + 8;
  trigger.style.left = `${left + window.scrollX}px`;
  trigger.style.top = `${top + window.scrollY}px`;
}

// ---------- 回答面板 ----------
const panel = el('aside', { class: 'qmx-ask-panel', role: 'dialog', 'aria-label': 'AI 解释', hidden: '' });
const quote = el('blockquote', { class: 'qmx-ask-quote' });
const answer = el('div', { class: 'qmx-ask-answer', 'aria-live': 'polite' });
const status = el('p', { class: 'qmx-ask-status' });
const follow = el('form', { class: 'qmx-ask-follow' });
const followInput = el('input', { type: 'text', placeholder: '继续追问…', 'aria-label': '继续追问', maxlength: '300' });
const followSend = el('button', { type: 'submit' }, '发送');
follow.append(followInput, followSend);
const bar = el('div', { class: 'qmx-ask-bar' });
const btnSettings = el('button', { type: 'button' }, '设置');
const btnFallback = el('button', { type: 'button', hidden: '' }, '复制提示词并打开 DeepSeek');
const btnClose = el('button', { type: 'button', 'aria-label': '关闭' }, '关闭');
bar.append(btnSettings, btnFallback, btnClose);
panel.append(quote, answer, status, follow, bar);

function setStatus(text: string, isError = false) {
  status.textContent = text;
  status.classList.toggle('is-error', isError);
}

function openPanel() {
  panel.hidden = false;
  trigger.hidden = true;
}

function closePanel() {
  abort?.abort();
  abort = null;
  panel.hidden = true;
  setStatus('');
}

async function send(messages: Msg[]) {
  const url = chatCompletionsUrl(config.baseUrl);
  if (!url || !config.model.trim()) {
    setStatus('还没有配置接口地址或模型名，请先点「设置」。', true);
    btnFallback.hidden = false;
    return;
  }
  abort?.abort();
  abort = new AbortController();
  const signal = abort.signal;
  const bubble = el('div', { class: 'qmx-ask-reply' });
  answer.append(bubble);
  setStatus('思考中…');
  followSend.disabled = true;
  btnFallback.hidden = true;

  try {
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    // 没填 key 就不带 Authorization，让不需要 key 的接口也能直接用
    if (config.key.trim()) headers.Authorization = `Bearer ${config.key.trim()}`;
    const res = await fetch(url, {
      method: 'POST',
      headers,
      signal,
      body: JSON.stringify({ model: config.model.trim(), messages, stream: true, temperature: 0.3 }),
    });
    if (!res.ok || !res.body) throw Object.assign(new Error('http'), { httpStatus: res.status });

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let text = '';
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const parsed = parseSseChunk(buffer);
      buffer = parsed.rest;
      if (parsed.deltas.length) {
        text += parsed.deltas.join('');
        bubble.textContent = text; // 只用 textContent，不解析 HTML，避免注入
        answer.scrollTop = answer.scrollHeight;
      }
      if (parsed.done) break;
    }
    if (!text) throw new Error('empty');
    history.push({ role: 'assistant', content: text });
    setStatus('');
  } catch (err) {
    if (signal.aborted) return;
    const code = (err as { httpStatus?: number }).httpStatus;
    bubble.remove();
    setStatus(
      code ? describeHttpError(code)
        : '无法连接到接口：可能是网络不通、浏览器跨域限制，或回答为空。可以改用下面的方式。',
      true,
    );
    btnFallback.hidden = false;
  } finally {
    if (abort?.signal === signal) followSend.disabled = false;
  }
}

function ask(target: Ask) {
  current = target;
  history = [];
  answer.replaceChildren();
  quote.textContent = target.selection.length > 120 ? `${target.selection.slice(0, 120)}…` : target.selection;
  openPanel();
  void send(buildMessages(target));
}

// ---------- 设置对话框 ----------
const dialog = el('dialog', { class: 'qmx-ask-settings', 'aria-labelledby': 'qmx-ask-settings-title' });
const form = el('form', { method: 'dialog' });
form.append(el('h2', { id: 'qmx-ask-settings-title' }, 'AI 设置'));

function field(label: string, input: HTMLElement): HTMLLabelElement {
  const wrap = el('label');
  wrap.append(el('span', {}, label), input);
  return wrap;
}

const fPreset = el('select');
for (const [id, p] of Object.entries(PRESETS)) fPreset.append(el('option', { value: id }, p.label));
const fBase = el('input', { type: 'url', placeholder: 'https://…/v1', autocomplete: 'off', spellcheck: 'false' });
const fModel = el('input', { type: 'text', autocomplete: 'off', spellcheck: 'false' });
const fKey = el('input', { type: 'password', autocomplete: 'off', spellcheck: 'false' });
const hint = el('p', { class: 'qmx-ask-hint' });
const note = el('p', { class: 'qmx-ask-hint' },
  'Key 只保存在你这台设备的浏览器里，不会上传到本站。建议使用单独创建、可随时作废的 key，并避免在公共电脑上保存。');
const actions = el('div', { class: 'qmx-ask-bar' });
const bSave = el('button', { type: 'submit', value: 'save' }, '保存');
const bClear = el('button', { type: 'button' }, '清除已保存的设置');
const bCancel = el('button', { type: 'submit', value: 'cancel', formnovalidate: '' }, '取消');
actions.append(bSave, bClear, bCancel);
form.append(field('服务', fPreset), field('接口地址 (Base URL)', fBase), field('模型名', fModel),
  field('API Key', fKey), hint, note, actions);
dialog.append(form);

function fillForm() {
  fPreset.value = config.preset;
  fBase.value = config.baseUrl;
  fModel.value = config.model;
  fKey.value = config.key;
  hint.textContent = PRESETS[config.preset as keyof typeof PRESETS]?.keyHint ?? '';
}

fPreset.addEventListener('change', () => {
  const p = PRESETS[fPreset.value as keyof typeof PRESETS];
  if (fPreset.value !== 'custom') { fBase.value = p.baseUrl; fModel.value = p.model; }
  hint.textContent = p.keyHint;
});

bClear.addEventListener('click', () => {
  clearConfig(localStorage);
  config = loadConfig(localStorage);
  fillForm();
});

dialog.addEventListener('close', () => {
  if (dialog.returnValue !== 'save') return;
  const baseUrl = normalizeBaseUrl(fBase.value);
  config = { preset: fPreset.value, baseUrl, model: fModel.value.trim(), key: fKey.value.trim() };
  if (!saveConfig(localStorage, config)) setStatus('浏览器不允许保存设置，本次刷新后会丢失。', true);
  else if (!baseUrl) setStatus('接口地址不合法，需要以 http:// 或 https:// 开头。', true);
});

function openSettings() {
  config = loadConfig(localStorage);
  fillForm();
  dialog.returnValue = '';
  dialog.showModal();
}

// ---------- 事件与初始化 ----------
trigger.addEventListener('mousedown', (e) => e.preventDefault()); // 点按钮不要清掉选区
trigger.addEventListener('click', () => { if (current) ask(current); });
btnClose.addEventListener('click', closePanel);
btnSettings.addEventListener('click', openSettings);
btnFallback.addEventListener('click', async () => {
  if (!current) return;
  try {
    await navigator.clipboard.writeText(buildFallbackPrompt(current));
    setStatus('提示词已复制，在新打开的页面里粘贴即可。');
  } catch {
    setStatus('无法自动复制，请手动选中上面的文字后到 DeepSeek 提问。', true);
  }
  window.open('https://chat.deepseek.com/', '_blank', 'noopener,noreferrer');
});
follow.addEventListener('submit', (e) => {
  e.preventDefault();
  const q = followInput.value.trim();
  if (!q || !current || followSend.disabled) return;
  followInput.value = '';
  history.push({ role: 'user', content: q });
  answer.append(el('div', { class: 'qmx-ask-user' }, q));
  void send(buildMessages({ ...current, history }));
});

export function initAskAi() {
  if (started) return;
  started = true;
  document.body.append(trigger, panel, dialog);
  document.querySelectorAll('[data-qmx-ai-settings]').forEach((b) => b.addEventListener('click', openSettings));
  const refresh = () => requestAnimationFrame(updateTrigger);
  document.addEventListener('mouseup', refresh);
  document.addEventListener('keyup', (e) => { if (e.key.startsWith('Arrow') || e.key === 'Shift') refresh(); });
  document.addEventListener('touchend', () => setTimeout(updateTrigger, 250));
  document.addEventListener('selectionchange', () => { if (!window.getSelection()?.toString().trim()) trigger.hidden = true; });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && !panel.hidden && !dialog.open) closePanel(); });
}
