// 划词问 AI：在正文里选中文字，弹出「问 AI」按钮，在侧边面板里流式显示回答。
// key 只保存在用户自己的浏览器（store），请求直接从浏览器发给所选接口。
import {
  PRESETS, MAX_SELECTION, loadConfig, saveConfig, clearConfig, normalizeBaseUrl, activeProfile,
  defaultProfile, modelsUrl, parseModelList, chatCompletionsUrl, buildMessages, buildFallbackPrompt, parseSseChunk, describeHttpError,
  balanceUrl, parseBalance, formatBalance,
} from './core.mjs';
import { parseMarkdown } from './markdown.mjs';
import {
  initPet, loadPack, importSheet, resetSheet, setBase, react, activity, setChatOpen, petRect, isPetEnabled, setPetEnabled,
} from './companion';
import { createChatUI } from './chat-ui';

type Msg = { role: 'system' | 'user' | 'assistant'; content: string };
type Ask = { selection: string; pageTitle: string; context: string };

// 浏览器屏蔽站点数据（或在沙箱 iframe 里）时，读取 localStorage 本身就会抛 SecurityError。
// 此时退回内存存储：本次页面内可用，刷新后丢失，但助手其余功能照常工作。
function pickStorage(): Pick<Storage, 'getItem' | 'setItem' | 'removeItem'> {
  try {
    const s = window.localStorage;
    s.getItem('qmx-ai-probe');
    return s;
  } catch {
    const mem = new Map<string, string>();
    return {
      getItem: (k) => mem.get(k) ?? null,
      setItem: (k, v) => { mem.set(k, String(v)); },
      removeItem: (k) => { mem.delete(k); },
    };
  }
}
const store = pickStorage();

let started = false;
let config = loadConfig(store);
let abort: AbortController | null = null;
let current: Ask | null = null; // 面板正在进行的对话（selection 为空表示直接提问）
let pending: Ask | null = null; // 当前划选、尚未提问的文字
let history: Msg[] = [];
let siteBase = '/';

function el<K extends keyof HTMLElementTagNameMap>(
  tag: K, attrs: Record<string, string> = {}, text = '',
): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  if (text) node.textContent = text;
  return node;
}

// ---------- 划词按钮 ----------
const trigger = el('button', { type: 'button', class: 'qmx-ask-trigger', hidden: '' });
// 鲸鱼头像只在有图集时显示（样式里按 data-qmx-whale 控制）
trigger.append(el('span', { class: 'qmx-ask-trigger__icon', 'aria-hidden': 'true' }), el('span', {}, '问 AI'));
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
  pending = { selection: info.selection, pageTitle: info.pageTitle, context: info.context };
  trigger.hidden = false;
  const width = trigger.offsetWidth || 64;
  const left = Math.min(Math.max(8, info.rect.left + info.rect.width / 2 - width / 2), window.innerWidth - width - 8);
  const top = info.rect.top > 52 ? info.rect.top - 44 : info.rect.bottom + 8;
  trigger.style.left = `${left + window.scrollX}px`;
  trigger.style.top = `${top + window.scrollY}px`;
}

// ---------- 对话界面：透明背景，回答是桌宠旁边的气泡 ----------
const ui = createChatUI({
  submit: (text) => submitQuestion(text),
  close: () => closePanel(),
  settings: () => openSettings(),
  clear: () => clearChat(),
  fallback: () => { void copyFallback(); },
});

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

const setStatus = (text: string, isError = false) => ui.setStatus(text, isError);

// 工具条左侧的小字：当前平台、模型，以及 DeepSeek 官方平台的余额
let balanceText = '';
let balanceAt = 0;
let balanceFor = '';

function updateHead() {
  const label = PRESETS[config.active as keyof typeof PRESETS]?.label.replace(/（.*?）/, '') ?? '';
  const model = activeProfile(config).model.trim() || '未选择模型';
  ui.setMeta(`${label} · ${model}${balanceText ? ` · 余额 ${balanceText}` : ''}`);
}

async function fetchBalance(baseUrl: string, key: string): Promise<string> {
  const url = balanceUrl(baseUrl);
  if (!url || !key.trim()) return '';
  const res = await fetch(url, { headers: { Authorization: `Bearer ${key.trim()}` }, signal: AbortSignal.timeout(10000) });
  if (!res.ok) throw Object.assign(new Error('http'), { httpStatus: res.status });
  return formatBalance(parseBalance(await res.json()));
}

async function refreshBalance() {
  const p = activeProfile(config);
  const id = `${p.baseUrl}|${p.key}`;
  if (id === balanceFor && balanceText && Date.now() - balanceAt < 300_000) return;
  balanceText = '';
  balanceFor = id;
  updateHead();
  try {
    balanceText = await fetchBalance(p.baseUrl, p.key);
    balanceAt = Date.now();
  } catch { /* 余额只是锦上添花，拿不到就不显示 */ }
  updateHead();
}

/** 对话气泡跟着桌宠走：放在它上面（空间不够就放下面），尾巴指向它。 */
const placePanel = () => ui.place(petRect());

function openPanel() {
  config = loadConfig(store);
  updateHead();
  void refreshBalance();
  setChatOpen(true); // 先让桌宠露面，才能量出它的位置
  placePanel();
  ui.open();
  trigger.hidden = true;
}

function closePanel() {
  abort?.abort();
  abort = null;
  ui.close();
  ui.setStatus('');
  ui.showTyping(false);
  ui.setBusy(false);
  setChatOpen(false);
  setBase('idle');
}

/** 清空对话：回到只有一句提示的空白状态，桌宠回到待机。 */
function clearChat() {
  abort?.abort();
  abort = null;
  history = [];
  current = current && { ...current, selection: '' };
  ui.clear();
  ui.showTyping(false);
  ui.setBusy(false);
  ui.showEmpty('对话已清空。想问点什么？直接输入，或者先在文章里划词。');
  setBase('idle');
}

async function send(messages: { role: string; content: string }[]) {
  config = loadConfig(store); // 每次发送都读最新的，多个标签页改了设置也能生效
  const profile = activeProfile(config);
  const url = chatCompletionsUrl(profile.baseUrl);
  if (!url || !profile.model.trim()) {
    setStatus('还没有配置接口地址或模型名，请先点「设置」。', true);
    ui.showFallback(true);
    return;
  }
  abort?.abort();
  abort = new AbortController();
  const signal = abort.signal;
  let bubble: HTMLElement | null = null; // 第一个字到了才创建回答气泡，在那之前显示「思考中」的小点点
  ui.showTyping(true);
  ui.setStatus('');
  ui.setBusy(true);
  ui.showFallback(false);
  setBase('thinking');

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
        if (!text) { ui.showTyping(false); bubble = ui.addReply(); setBase('talking'); }
        text += parsed.deltas.join('');
        // 流式时每帧最多重绘一次，避免长回答卡顿
        if (!raf) {
          raf = requestAnimationFrame(() => {
            raf = 0;
            if (bubble) { renderMarkdown(bubble, text); ui.scrollToEnd(); }
          });
        }
      }
      if (parsed.done) break;
    }
    if (raf) cancelAnimationFrame(raf);
    raf = 0;
    if (!text || !bubble) throw new Error('empty');
    renderMarkdown(bubble, text);
    ui.endReply(bubble);
    ui.scrollToEnd();
    history.push({ role: 'assistant', content: text });
    setStatus('');
    setBase('idle');
    react('happy');
  } catch (err) {
    if (signal.aborted) return;
    const code = (err as { httpStatus?: number }).httpStatus;
    ui.showTyping(false);
    if (bubble) ui.removeReply(bubble);
    setBase('idle');
    react('sad');
    setStatus(
      code ? describeHttpError(code)
        : '无法连接到接口：可能是网络不通、浏览器跨域限制，或回答为空。可以改用下面的方式。',
      true,
    );
    ui.showFallback(true);
  } finally {
    if (abort?.signal === signal) ui.setBusy(false);
  }
}

function ask(target: Ask) {
  current = target;
  history = [];
  ui.clear();
  ui.setQuote(target.selection);
  openPanel();
  void send(buildMessages(target));
}

/** 点桌宠：不带选中文字，直接提问。已经在直接提问时保留之前的对话。 */
function openFree() {
  if (ui.isOpen()) { ui.input.focus(); return; }
  if (!current || current.selection) {
    current = { selection: '', pageTitle: document.querySelector('h1')?.textContent?.trim() ?? document.title, context: '' };
    history = [];
    ui.clear();
    ui.showEmpty('想问点什么？直接输入，或者先在文章里划词。');
  }
  setStatus('');
  openPanel();
}

/** 输入框里提交了一个问题（追问或直接提问）。 */
function submitQuestion(q: string) {
  if (!current) return;
  history.push({ role: 'user', content: q });
  ui.addUser(q);
  activity();
  void send(buildMessages({ ...current, history }));
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
// 鲸鱼形象：这几项立即生效，不走「保存」
const petSection = el('fieldset', { class: 'qmx-ask-pet-set' });
const petToggle = el('input', { type: 'checkbox' });
const petToggleLabel = el('label', { class: 'qmx-ask-check' });
petToggleLabel.append(petToggle, el('span', {}, '在页面右下角常驻鲸鱼助手（点击提问，可拖动）'));
const petFile = el('input', { type: 'file', accept: 'image/webp,image/png', hidden: '' });
const bImport = el('button', { type: 'button' }, '导入形象图集');
const bPetReset = el('button', { type: 'button' }, '恢复默认形象');
const petRow = el('div', { class: 'qmx-ask-bar qmx-ask-bar--start' });
petRow.append(bImport, bPetReset, petFile);
const petMsg = el('p', { class: 'qmx-ask-hint', 'aria-live': 'polite' });
petSection.append(el('legend', {}, '鲸鱼形象'), petToggleLabel, petRow,
  el('p', { class: 'qmx-ask-hint' }, '图集为 8 列 × 11 行（单格 192×208）的 webp 或 png，导入后只保存在这台设备的浏览器里。'), petMsg);

petToggle.addEventListener('change', () => setPetEnabled(petToggle.checked));
bImport.addEventListener('click', () => petFile.click());
petFile.addEventListener('change', async () => {
  const file = petFile.files?.[0];
  petFile.value = '';
  if (!file) return;
  petMsg.textContent = await importSheet(file);
});
bPetReset.addEventListener('click', async () => {
  await resetSheet(siteBase);
  petMsg.textContent = '已恢复默认形象。';
});

form.append(field('平台', fPreset), field('接口地址 (Base URL)', fBase), modelField, modelMsg,
  field('API Key', fKey), hint, note, actions, petSection);
dialog.append(form);

// 对话框里编辑的是草稿，点「保存」才写入 store；每个平台一份，互不覆盖。
let draft = loadConfig(store);
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
  clearConfig(store);
  draft = loadConfig(store); // 存储已清空，得到全部默认值
  config = loadConfig(store);
  showProfile(draft.active);
  modelNote('已清除所有平台保存的设置。');
});

dialog.addEventListener('close', () => {
  if (dialog.returnValue !== 'save') return;
  readForm();
  config = draft;
  updateHead();
  void refreshBalance();
  if (!saveConfig(store, config)) setStatus('浏览器不允许保存设置，本次刷新后会丢失。', true);
  else if (!normalizeBaseUrl(activeProfile(config).baseUrl)) setStatus('接口地址不合法，需要以 http:// 或 https:// 开头。', true);
});

function openSettings() {
  petToggle.checked = isPetEnabled();
  petMsg.textContent = '';
  draft = loadConfig(store);
  showProfile(draft.active);
  dialog.returnValue = '';
  dialog.showModal();
}

// ---------- 事件与初始化 ----------
trigger.addEventListener('mousedown', (e) => e.preventDefault()); // 点按钮不要清掉选区
trigger.addEventListener('click', () => { if (pending) { activity(); ask(pending); } });

/** 请求失败时的退路：把提示词复制到剪贴板，去网页版 DeepSeek 粘贴。 */
async function copyFallback() {
  if (!current) return;
  try {
    await navigator.clipboard.writeText(buildFallbackPrompt({ ...current, history }));
    setStatus('提示词已复制，在新打开的页面里粘贴即可。');
  } catch {
    setStatus('无法自动复制，请手动选中文字后到 DeepSeek 提问。', true);
  }
  window.open('https://chat.deepseek.com/', '_blank', 'noopener,noreferrer');
}

export function initAskAi(base = '/') {
  if (started) return;
  started = true;
  siteBase = base;
  document.body.append(trigger, ui.root, dialog);
  void loadPack(base);
  initPet({ onOpen: openFree, isOpen: () => ui.isOpen() });
  // 桌宠被拖动或窗口变化时，气泡跟着走
  const follow = () => { if (ui.isOpen()) placePanel(); };
  window.addEventListener('qmx-pet-move', follow);
  window.addEventListener('resize', follow);
  document.querySelectorAll('[data-qmx-ai-settings]').forEach((b) => b.addEventListener('click', openSettings));
  const refresh = () => requestAnimationFrame(updateTrigger);
  document.addEventListener('mouseup', refresh);
  document.addEventListener('keyup', (e) => { if (e.key.startsWith('Arrow') || e.key === 'Shift') refresh(); });
  document.addEventListener('touchend', () => setTimeout(updateTrigger, 250));
  document.addEventListener('selectionchange', () => { if (!window.getSelection()?.toString().trim()) trigger.hidden = true; });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && ui.isOpen() && !dialog.open) closePanel(); });
}
