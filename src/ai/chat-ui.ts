// 对话界面：没有不透明的面板，回答和追问都是悬浮在桌宠旁边的气泡，背景保持透明。
// 这里只管外观和交互（布局、气泡、输入框、工具条）；请求、Markdown 渲染和设置都在 ask-ai.ts。

export interface ChatHandlers {
  submit(text: string): void;
  close(): void;
  settings(): void;
  clear(): void;
  fallback(): void;
}

export interface ChatUI {
  readonly root: HTMLElement;
  readonly input: HTMLTextAreaElement;
  isOpen(): boolean;
  open(): void;
  close(): void;
  clear(): void;
  setQuote(text: string): void;
  showEmpty(text: string | null): void;
  addUser(text: string): void;
  /** 新增一条 AI 回答，返回用来渲染内容的容器。 */
  addReply(): HTMLElement;
  endReply(body: HTMLElement): void;
  removeReply(body: HTMLElement): void;
  showTyping(on: boolean): void;
  setStatus(text: string, isError?: boolean): void;
  setMeta(text: string): void;
  setBusy(busy: boolean): void;
  showFallback(show: boolean): void;
  place(pet: DOMRect | null): void;
  scrollToEnd(): void;
}

function el<K extends keyof HTMLElementTagNameMap>(tag: K, cls = '', attrs: Record<string, string> = {}, text = ''): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  if (text) node.textContent = text;
  return node;
}

const SEND_ICON =
  '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M12 19V5M5 12l7-7 7 7" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg>';

export function createChatUI(h: ChatHandlers): ChatUI {
  const root = el('section', 'qmx-chat', { role: 'dialog', 'aria-label': 'AI 助手', hidden: '' });
  root.dataset.side = 'right';
  root.dataset.pos = 'above';

  const scroll = el('div', 'qmx-chat__scroll', { role: 'log', 'aria-live': 'polite' });
  const log = el('div', 'qmx-chat__log');
  scroll.append(log);

  const status = el('p', 'qmx-chat__status');

  const form = el('form', 'qmx-chat__input');
  const input = el('textarea', '', { rows: '1', maxlength: '600', placeholder: '问问鲸鱼…', 'aria-label': '输入问题', enterkeyhint: 'send' });
  const send = el('button', 'qmx-chat__send', { type: 'submit', 'aria-label': '发送' });
  send.innerHTML = SEND_ICON;
  form.append(input, send);

  const tools = el('div', 'qmx-chat__tools');
  const meta = el('span', 'qmx-chat__meta');
  const btn = (label: string, fn: () => void, hidden = false) => {
    const b = el('button', '', { type: 'button' }, label);
    if (hidden) b.hidden = true;
    b.addEventListener('click', fn);
    return b;
  };
  const fallback = btn('复制提示词，去 DeepSeek 问', () => h.fallback(), true);
  tools.append(meta, fallback, btn('清空', () => h.clear()), btn('设置', () => h.settings()), btn('关闭', () => h.close()));

  root.append(scroll, status, form, tools);

  let quote: HTMLElement | null = null;
  let empty: HTMLElement | null = null;
  let typing: HTMLElement | null = null;

  const markTail = () => {
    log.querySelectorAll('.has-tail').forEach((n) => n.classList.remove('has-tail'));
    const last = log.lastElementChild;
    if (last && (last.classList.contains('qmx-msg--ai') || last.classList.contains('qmx-typing'))) last.classList.add('has-tail');
  };
  const toEnd = () => { scroll.scrollTop = scroll.scrollHeight; };

  let busy = false;
  const grow = () => { input.style.height = 'auto'; input.style.height = `${Math.min(input.scrollHeight, 112)}px`; };
  const doSubmit = () => {
    const text = input.value.trim();
    if (!text || busy) return;
    input.value = '';
    grow();
    h.submit(text);
  };
  input.addEventListener('input', grow);
  input.addEventListener('keydown', (e) => {
    // 中文输入法选字时的 Enter 不能当作发送
    if (e.key === 'Enter' && !e.shiftKey && !e.isComposing && e.keyCode !== 229) { e.preventDefault(); doSubmit(); }
  });
  form.addEventListener('submit', (e) => { e.preventDefault(); doSubmit(); });

  const dropHints = () => { empty?.remove(); empty = null; };
  const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));

  const ui: ChatUI = {
    root,
    input,
    isOpen: () => !root.hidden,
    open() { root.hidden = false; requestAnimationFrame(() => input.focus()); },
    close() { root.hidden = true; },
    clear() { log.replaceChildren(); quote = empty = typing = null; status.textContent = ''; },
    setQuote(text) {
      quote?.remove();
      quote = null;
      if (!text) return;
      quote = el('blockquote', 'qmx-chat__quote');
      quote.append(el('span', 'qmx-chat__quote-label', {}, '选中的文字'), el('span', '', {}, text.length > 140 ? `${text.slice(0, 140)}…` : text));
      log.prepend(quote);
    },
    showEmpty(text) {
      dropHints();
      if (!text) return;
      empty = el('div', 'qmx-msg qmx-msg--ai qmx-msg--hint', {}, text);
      log.append(empty);
      markTail();
    },
    addUser(text) {
      dropHints();
      log.append(el('div', 'qmx-msg qmx-msg--user', {}, text));
      markTail();
      toEnd();
    },
    addReply() {
      dropHints();
      const msg = el('div', 'qmx-msg qmx-msg--ai is-streaming');
      const body = el('div', 'qmx-msg__body');
      const copy = el('button', 'qmx-msg__copy', { type: 'button', 'aria-label': '复制这条回答' }, '复制');
      copy.addEventListener('click', async () => {
        try { await navigator.clipboard.writeText(body.innerText || body.textContent || ''); copy.textContent = '已复制'; }
        catch { copy.textContent = '复制失败'; }
        setTimeout(() => { copy.textContent = '复制'; }, 1400);
      });
      msg.append(body, copy);
      log.append(msg);
      markTail();
      toEnd();
      return body;
    },
    endReply(body) { body.closest('.qmx-msg')?.classList.remove('is-streaming'); },
    removeReply(body) { body.closest('.qmx-msg')?.remove(); markTail(); },
    showTyping(on) {
      if (!on) { typing?.remove(); typing = null; markTail(); return; }
      if (typing) return;
      dropHints();
      typing = el('div', 'qmx-typing', { 'aria-label': '鲸鱼正在思考' });
      typing.append(el('i'), el('i'), el('i'));
      log.append(typing);
      markTail();
      toEnd();
    },
    setStatus(text, isError = false) { status.textContent = text; status.classList.toggle('is-error', isError); },
    setMeta(text) { meta.textContent = text; meta.title = text; },
    setBusy(b) { busy = b; send.disabled = b; root.classList.toggle('is-busy', b); },
    showFallback(show) { fallback.hidden = !show; },
    scrollToEnd: toEnd,
    place(pet) {
      const vw = window.innerWidth;
      const vh = window.innerHeight;
      const M = 12;
      const W = Math.min(420, vw - 2 * M);
      root.style.width = `${W}px`;
      const CHROME = 118; // 输入框、状态行和工具条占的高度
      const TOP = 76; // 顶部留给站点的页头，气泡别盖住搜索框和主题选择
      let left = vw - W - 16;
      let side = 'right';
      let above = true;
      let edge = 16; // 离桌宠（或屏幕）边缘的距离
      let tail = 60;
      let room = vh * 0.6;
      if (pet) {
        const cx = pet.left + pet.width / 2;
        side = cx > vw / 2 ? 'right' : 'left';
        left = side === 'right' ? clamp(pet.right - W + 8, M, vw - W - M) : clamp(pet.left - 8, M, vw - W - M);
        tail = clamp(side === 'right' ? left + W - cx : cx - left, 28, W - 28);
        const up = pet.top - TOP;
        const down = vh - pet.bottom - M;
        above = up >= 220 || up >= down;
        edge = above ? vh - pet.top + 4 : pet.bottom + 4;
        room = (above ? up : down) - CHROME;
      } else {
        room = vh - 16 - CHROME - TOP;
      }
      root.dataset.side = side;
      root.dataset.pos = above ? 'above' : 'below';
      root.style.left = `${left}px`;
      root.style.top = above ? 'auto' : `${edge}px`;
      root.style.bottom = above ? `${edge}px` : 'auto';
      root.style.setProperty('--qmx-tail', `${tail}px`);
      scroll.style.maxHeight = `${clamp(room, 120, 560)}px`;
    },
  };
  return ui;
}
