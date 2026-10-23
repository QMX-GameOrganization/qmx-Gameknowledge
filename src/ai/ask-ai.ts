// 划词问 AI：在正文里选中文字，弹出「问 AI」按钮，在侧边面板里流式显示回答。
// key 只保存在用户自己的浏览器（localStorage），请求直接从浏览器发给所选接口。
import {
  PRESETS, MAX_SELECTION, loadConfig, saveConfig, clearConfig, normalizeBaseUrl, activeProfile,
  defaultProfile, modelsUrl, parseModelList, chatCompletionsUrl, buildMessages, buildFallbackPrompt, parseSseChunk, describeHttpError,
} from './core.mjs';
import { parseMarkdown } from './markdown.mjs';

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

// ---------- Markdown 渲染 ----------
// 语法树 → DOM。全程 createElement + textContent，不使用 innerHTML，模型输出里的 HTML 只会当文字显示。
/* eslint-disable @typescript-eslint/no-explicit-any */
function renderInline(nodes: any[], parent: Node) {
  for (const n of nodes) {
    switch (n.t) {
      case 'text': parent.appendChild(document.createTextNode(n.v)); break;
      case 'br': parent.appendChild(document.createElement('br')); break;
      case 'code': parent.appendChild(el('code', {}, n.v)); break;
      case 'a': {
        const a = el('a', { href: n.href, target: '_blank', rel: 'noopener noreferrer' });
        renderInline(n.c, a);
        parent.appendChild(a);
        break;
      }
      default: { // strong / em / del
        const tag = n.t === 'strong' ? 'strong' : n.t === 'del' ? 'del' : 'em';
        const node = document.createElement(tag);
        renderInline(n.c, node);
        parent.appendChild(node);
      }
    }
  }
}

function renderBlocks(blocks: any[], parent: Node) {
  for (const b of blocks) {
    switch (b.type) {
      case 'p': { const p = el('p'); renderInline(b.inline, p); parent.appendChild(p); break; }
      case 'h': { // 面板很窄，标题一律降级为 h3~h6
        const h = document.createElement(`h${Math.min(6, Math.max(3, b.level + 2))}` as 'h3');
        renderInline(b.inline, h);
        parent.appendChild(h);
        break;
      }
      case 'code': {
        const pre = el('pre');
        const code = el('code', b.lang ? { 'data-lang': b.lang } : {}, b.text);
        pre.appendChild(code);
        pre.tabIndex = 0; // 长代码需要能用键盘横向滚动
        parent.appendChild(pre);
        break;
      }
      case 'ul': case 'ol': {
        const list = el(b.type);
        if (b.type === 'ol' && b.start !== 1) list.setAttribute('start', String(b.start));
        for (const item of b.items) {
          const li = el('li');
          renderInline(item.inline, li);
          renderBlocks(item.children, li);
          list.appendChild(li);
        }
        parent.appendChild(list);
        break;
      }
      case 'quote': { const q = el('blockquote'); renderBlocks(b.blocks, q); parent.appendChild(q); break; }
      case 'hr': parent.appendChild(el('hr')); break;
      case 'table': {
        const wrap = el('div', { class: 'qmx-md-table' });
        const table = el('table');
        const thead = el('thead');
        const tr = el('tr');
        for (const cell of b.head) { const th = el('th'); renderInline(cell, th); tr.appendChild(th); }
        thead.appendChild(tr);
        const tbody = el('tbody');
        for (const row of b.rows) {
          const r = el('tr');
          for (const cell of row) { const td = el('td'); renderInline(cell, td); r.appendChild(td); }
          tbody.appendChild(r);
        }
        table.append(thead, tbody);
        wrap.appendChild(table);
        parent.appendChild(wrap);
        break;
      }
    }
  }
}

function renderMarkdown(target: HTMLElement, text: string) {
  const frag = document.createDocumentFragment();
  renderBlocks(parseMarkdown(text), frag);
  target.replaceChildren(frag);
}

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
  config = loadConfig(localStorage); // 每次发送都读最新的，多个标签页改了设置也能生效
  const profile = activeProfile(config);
  const url = chatCompletionsUrl(profile.baseUrl);
  if (!url || !profile.model.trim()) {
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
    if (profile.key.trim()) headers.Authorization = `Bearer ${profile.key.trim()}`;
    const res = await fetch(url, {
      method: 'POST',
      headers,
      signal,
      body: JSON.stringify({ model: profile.model.trim(), messages, stream: true, temperature: 0.3 }),
    });
    if (!res.ok || !res.body) throw Object.assign(new Error('http'), { httpStatus: res.status });

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let text = '';
    let raf = 0;
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const parsed = parseSseChunk(buffer);
      buffer = parsed.rest;
      if (parsed.deltas.length) {
        text += parsed.deltas.join('');
        // 流式时每帧最多重绘一次，避免长回答卡顿
        if (!raf) {
          raf = requestAnimationFrame(() => {
            raf = 0;
            renderMarkdown(bubble, text);
            answer.scrollTop = answer.scrollHeight;
          });
        }
      }
      if (parsed.done) break;
    }
    if (raf) cancelAnimationFrame(raf);
    raf = 0;
    if (!text) throw new Error('empty');
    renderMarkdown(bubble, text);
    answer.scrollTop = answer.scrollHeight;
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
const fPick = el('select', { 'aria-label': '从已获取的模型列表中选择', hidden: '' });
const bFetch = el('button', { type: 'button' }, '获取模型列表');
const modelRow = el('div', { class: 'qmx-ask-row' });
modelRow.append(fModel, bFetch);
const fKey = el('input', { type: 'password', autocomplete: 'off', spellcheck: 'false' });
const hint = el('p', { class: 'qmx-ask-hint' });
const modelMsg = el('p', { class: 'qmx-ask-hint', 'aria-live': 'polite' });
const note = el('p', { class: 'qmx-ask-hint' },
  '每个平台的地址、模型和 Key 分开保存，只存在你这台设备的浏览器里，不会上传到本站。建议使用单独创建、可随时作废的 key，并避免在公共电脑上保存。');
const actions = el('div', { class: 'qmx-ask-bar' });
const bSave = el('button', { type: 'submit', value: 'save' }, '保存');
const bReset = el('button', { type: 'button' }, '重置此平台');
const bClear = el('button', { type: 'button' }, '清除全部');
const bCancel = el('button', { type: 'submit', value: 'cancel', formnovalidate: '' }, '取消');
actions.append(bSave, bReset, bClear, bCancel);
const modelField = el('label');
modelField.append(el('span', {}, '模型名（可手动填写，或先获取列表再选择）'), modelRow, fPick);
form.append(field('平台', fPreset), field('接口地址 (Base URL)', fBase), modelField, modelMsg,
  field('API Key', fKey), hint, note, actions);
dialog.append(form);

// 对话框里编辑的是草稿，点「保存」才写入 localStorage；每个平台一份，互不覆盖。
let draft = loadConfig(localStorage);
let shown = draft.active; // 表单当前显示的平台

function readForm() { // 把表单内容写回草稿里当前显示的平台
  const p = draft.profiles[shown];
  p.baseUrl = fBase.value.trim();
  p.model = fModel.value.trim();
  p.key = fKey.value.trim();
}

function refreshPresetLabels() {
  for (const opt of Array.from(fPreset.options)) {
    const has = draft.profiles[opt.value]?.key;
    opt.textContent = PRESETS[opt.value as keyof typeof PRESETS].label + (has ? '（已填 Key）' : '');
  }
}

function fillModels(list: string[], selected: string) {
  fPick.replaceChildren(el('option', { value: '' }, `从 ${list.length} 个模型中选择…`),
    ...list.map((id) => el('option', { value: id }, id)));
  fPick.value = list.includes(selected) ? selected : '';
  fPick.hidden = list.length === 0;
}

function showProfile(id: string) {
  shown = id;
  draft.active = id;
  const p = draft.profiles[id];
  fPreset.value = id;
  fBase.value = p.baseUrl;
  fModel.value = p.model;
  fKey.value = p.key;
  fillModels(p.models, p.model);
  hint.textContent = PRESETS[id as keyof typeof PRESETS].keyHint;
  modelMsg.textContent = '';
  modelMsg.classList.remove('is-error');
  refreshPresetLabels();
}

function modelNote(text: string, isError = false) {
  modelMsg.textContent = text;
  modelMsg.classList.toggle('is-error', isError);
}

fPreset.addEventListener('change', () => { readForm(); showProfile(fPreset.value); });
fKey.addEventListener('input', () => { readForm(); refreshPresetLabels(); });
fPick.addEventListener('change', () => { if (fPick.value) fModel.value = fPick.value; });

bFetch.addEventListener('click', async () => {
  const id = shown; // 获取期间用户可能切换平台，结果只写回发起请求的那个平台
  const url = modelsUrl(fBase.value);
  if (!url) { modelNote('接口地址不合法，需要以 http:// 或 https:// 开头。', true); return; }
  bFetch.disabled = true;
  modelNote('获取中…');
  try {
    const headers: Record<string, string> = {};
    if (fKey.value.trim()) headers.Authorization = `Bearer ${fKey.value.trim()}`;
    const res = await fetch(url, { headers, signal: AbortSignal.timeout(15000) });
    if (!res.ok) throw Object.assign(new Error('http'), { httpStatus: res.status });
    const list = parseModelList(await res.json());
    if (!list.length) throw new Error('empty');
    draft.profiles[id].models = list;
    if (shown === id) {
      fillModels(list, fModel.value.trim());
      modelNote(`获取到 ${list.length} 个模型，从下拉框选择即可。`);
    }
  } catch (err) {
    if (shown !== id) return;
    const code = (err as { httpStatus?: number }).httpStatus;
    modelNote(code ? describeHttpError(code)
      : '没能获取到模型列表：可能是网络不通、浏览器跨域限制，或该平台不提供列表。可以直接手动填写模型名。', true);
  } finally {
    bFetch.disabled = false;
  }
});

bReset.addEventListener('click', () => {
  draft.profiles[shown] = defaultProfile(shown);
  showProfile(shown);
});

bClear.addEventListener('click', () => {
  clearConfig(localStorage);
  draft = loadConfig(localStorage); // 存储已清空，得到全部默认值
  config = loadConfig(localStorage);
  showProfile(draft.active);
  modelNote('已清除所有平台保存的设置。');
});

dialog.addEventListener('close', () => {
  if (dialog.returnValue !== 'save') return;
  readForm();
  config = draft;
  if (!saveConfig(localStorage, config)) setStatus('浏览器不允许保存设置，本次刷新后会丢失。', true);
  else if (!normalizeBaseUrl(activeProfile(config).baseUrl)) setStatus('接口地址不合法，需要以 http:// 或 https:// 开头。', true);
});

function openSettings() {
  draft = loadConfig(localStorage);
  showProfile(draft.active);
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
