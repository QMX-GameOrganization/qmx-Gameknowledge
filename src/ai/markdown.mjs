// 轻量 Markdown 解析：只产出语法树，不生成 HTML。
// 渲染端用 createElement/textContent 构建 DOM，所以模型输出里的任何 HTML 都只会当文字显示。
// 支持：标题、段落、围栏代码块、行内代码、粗体、斜体、删除线、链接、有序/无序列表（可嵌套）、
// 引用、分隔线、表格。流式输出时未闭合的标记会按原样显示，闭合后自动变成格式。

const ITEM = /^(\s*)([-*+]|\d{1,9}[.)])\s+(.*)$/;
const FENCE = /^\s*(```+|~~~+)\s*([\w+#.-]*)/;
const HEADING = /^(#{1,6})\s+(.*?)\s*#*\s*$/;
const HR = /^\s{0,3}([-*_])(?:\s*\1){2,}\s*$/;
const TABLE_SEP = /^\s*\|?\s*:?-{2,}:?\s*(?:\|\s*:?-{2,}:?\s*)*\|?\s*$/;

const indentOf = (line) => line.match(/^\s*/)[0].replace(/\t/g, '    ').length;
const isBlank = (line) => !line.trim();

/** 只放行 http(s) 链接，挡掉 javascript: 等协议。 */
export function safeUrl(href) {
  try {
    const url = new URL(String(href).trim());
    return url.protocol === 'http:' || url.protocol === 'https:' ? url.href : '';
  } catch {
    return '';
  }
}

const isWordChar = (ch) => !!ch && /[\p{L}\p{N}]/u.test(ch);

/** 行内解析，返回节点数组：{t:'text'|'code'|'strong'|'em'|'del'|'a'|'br'}。 */
export function parseInline(src) {
  const out = [];
  let buf = '';
  const flush = () => { if (buf) { out.push({ t: 'text', v: buf }); buf = ''; } };
  let i = 0;
  while (i < src.length) {
    const ch = src[i];

    if (ch === '\\' && i + 1 < src.length && /[\\`*_{}[\]()#+\-.!~|>]/.test(src[i + 1])) {
      buf += src[i + 1];
      i += 2;
      continue;
    }

    if (ch === '`') {
      const end = src.indexOf('`', i + 1);
      if (end > i + 1) { flush(); out.push({ t: 'code', v: src.slice(i + 1, end) }); i = end + 1; continue; }
    }

    const two = src.slice(i, i + 2);
    if ((two === '**' || two === '__' || two === '~~') && src[i + 2] && !/\s/.test(src[i + 2])) {
      // 下划线只在词边界生效，避免 snake_case 被吃掉
      const okStart = two !== '__' || !isWordChar(src[i - 1]);
      const end = okStart ? src.indexOf(two, i + 2) : -1;
      if (end > i + 2 && !/\s/.test(src[end - 1])) {
        flush();
        out.push({ t: two === '~~' ? 'del' : 'strong', c: parseInline(src.slice(i + 2, end)) });
        i = end + 2;
        continue;
      }
    }

    if ((ch === '*' || ch === '_') && src[i + 1] && !/\s/.test(src[i + 1]) && src[i + 1] !== ch) {
      const okStart = ch === '*' || !isWordChar(src[i - 1]);
      let end = -1;
      if (okStart) {
        for (let j = i + 1; j < src.length; j++) {
          if (src[j] === '\\') { j++; continue; }
          if (src[j] === ch && !/\s/.test(src[j - 1]) && src[j + 1] !== ch && (ch === '*' || !isWordChar(src[j + 1]))) {
            end = j;
            break;
          }
        }
      }
      if (end > i + 1) {
        flush();
        out.push({ t: 'em', c: parseInline(src.slice(i + 1, end)) });
        i = end + 1;
        continue;
      }
    }

    if (ch === '[') {
      const mid = src.indexOf('](', i + 1);
      if (mid > i) {
        const close = src.indexOf(')', mid + 2);
        if (close > mid) {
          const href = safeUrl(src.slice(mid + 2, close).split(/\s+/)[0]);
          if (href) {
            flush();
            out.push({ t: 'a', href, c: parseInline(src.slice(i + 1, mid)) });
            i = close + 1;
            continue;
          }
        }
      }
    }

    buf += ch;
    i++;
  }
  flush();
  return out;
}

/** 段落内的换行保留为 <br>，模型常用单个换行分行。 */
function inlineWithBreaks(lines) {
  const nodes = [];
  lines.forEach((line, idx) => {
    if (idx) nodes.push({ t: 'br' });
    nodes.push(...parseInline(line.trim()));
  });
  return nodes;
}

function splitRow(line) {
  let text = line.trim();
  if (text.startsWith('|')) text = text.slice(1);
  if (text.endsWith('|') && !text.endsWith('\\|')) text = text.slice(0, -1);
  return text.split(/(?<!\\)\|/).map((cell) => cell.trim().replace(/\\\|/g, '|'));
}

const startsBlock = (line, next) =>
  FENCE.test(line) || HEADING.test(line) || HR.test(line) || ITEM.test(line) || /^\s*>/.test(line) ||
  (line.includes('|') && next !== undefined && TABLE_SEP.test(next));

function parseList(lines, start) {
  const first = lines[start].match(ITEM);
  const base = indentOf(lines[start]);
  const ordered = /\d/.test(first[2]);
  const list = { type: ordered ? 'ol' : 'ul', start: ordered ? parseInt(first[2], 10) : 1, items: [] };
  let i = start;
  while (i < lines.length) {
    const m = lines[i].match(ITEM);
    if (!m || indentOf(lines[i]) !== base || /\d/.test(m[2]) !== ordered) break;
    const sub = [];
    i++;
    while (i < lines.length) {
      if (isBlank(lines[i])) {
        let k = i;
        while (k < lines.length && isBlank(lines[k])) k++;
        if (k < lines.length && indentOf(lines[k]) > base) { sub.push(...lines.slice(i, k)); i = k; continue; }
        i = k;
        break;
      }
      if (indentOf(lines[i]) > base) { sub.push(lines[i]); i++; continue; }
      break;
    }
    const strip = sub.filter((l) => !isBlank(l)).reduce((min, l) => Math.min(min, indentOf(l)), Infinity);
    const body = sub.map((l) => (isBlank(l) ? '' : l.replace(/\t/g, '    ').slice(Number.isFinite(strip) ? strip : 0)));
    list.items.push({ inline: parseInline(m[3].trim()), children: parseBlocks(body) });
  }
  return { list, next: i };
}

export function parseBlocks(lines) {
  const blocks = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (isBlank(line)) { i++; continue; }

    const fence = line.match(FENCE);
    if (fence) {
      const mark = fence[1][0].repeat(fence[1].length);
      const body = [];
      i++;
      while (i < lines.length && !lines[i].trim().startsWith(mark)) body.push(lines[i++]);
      i++; // 跳过结束围栏；流式输出时可能还没到，此时代码块先显示已收到的部分
      const pad = indentOf(line);
      blocks.push({ type: 'code', lang: fence[2], text: body.map((l) => l.slice(Math.min(pad, indentOf(l)))).join('\n') });
      continue;
    }

    const heading = line.match(HEADING);
    if (heading) { blocks.push({ type: 'h', level: heading[1].length, inline: parseInline(heading[2]) }); i++; continue; }

    if (HR.test(line)) { blocks.push({ type: 'hr' }); i++; continue; }

    if (/^\s*>/.test(line)) {
      const inner = [];
      while (i < lines.length && /^\s*>/.test(lines[i])) inner.push(lines[i++].replace(/^\s*>\s?/, ''));
      blocks.push({ type: 'quote', blocks: parseBlocks(inner) });
      continue;
    }

    if (line.includes('|') && i + 1 < lines.length && TABLE_SEP.test(lines[i + 1])) {
      const head = splitRow(line).map(parseInline);
      const rows = [];
      i += 2;
      while (i < lines.length && !isBlank(lines[i]) && lines[i].includes('|')) rows.push(splitRow(lines[i++]).map(parseInline));
      blocks.push({ type: 'table', head, rows });
      continue;
    }

    if (ITEM.test(line)) {
      const { list, next } = parseList(lines, i);
      blocks.push(list);
      i = next;
      continue;
    }

    const para = [line];
    i++;
    while (i < lines.length && !isBlank(lines[i]) && !startsBlock(lines[i], lines[i + 1])) para.push(lines[i++]);
    blocks.push({ type: 'p', inline: inlineWithBreaks(para) });
  }
  return blocks;
}

export function parseMarkdown(text) {
  return parseBlocks(String(text ?? '').replace(/\r\n?/g, '\n').split('\n'));
}
