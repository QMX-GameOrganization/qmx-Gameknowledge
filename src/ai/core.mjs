// 划词问 AI 的纯逻辑部分：预设、配置读写、提示词、流式响应解析。
// 不碰 DOM，可以直接用 node scripts/test-ai.mjs 测试。

export const CONFIG_KEY = 'qmx-ai-config';
export const MAX_SELECTION = 500;
export const MAX_CONTEXT = 400;

// 预设只是帮用户少填几项。Base URL 和模型名都可以在设置里改。
// 注意：这些地址与模型名来自各平台文档，未逐家验证过浏览器直连（CORS）是否放行。
// opencode 的免费模型是限时活动，随时可能下架，所以不要在别处写死。
export const PRESETS = {
  opencode: {
    label: 'OpenCode 免费模型（限时）',
    baseUrl: 'https://opencode.ai/inference/openai/v1',
    model: 'deepseek-v4.1-flash-free',
    keyHint: '是否需要 key 取决于 OpenCode，留空会先尝试不带 key 调用',
  },
  deepseek: {
    label: 'DeepSeek 官方',
    baseUrl: 'https://api.deepseek.com',
    model: 'deepseek-chat',
    keyHint: '在 platform.deepseek.com 创建，按量付费',
  },
  siliconflow: {
    label: '硅基流动',
    baseUrl: 'https://api.siliconflow.cn/v1',
    model: 'deepseek-ai/DeepSeek-V3',
    keyHint: '在 siliconflow.cn 创建',
  },
  ollama: {
    label: '本地 Ollama',
    baseUrl: 'http://localhost:11434/v1',
    model: '',
    keyHint: '本地不需要 key；需设置 OLLAMA_ORIGINS 允许本站跨域',
  },
  custom: {
    label: '自定义（OpenAI 兼容）',
    baseUrl: '',
    model: '',
    keyHint: '',
  },
};

export const DEFAULT_CONFIG = Object.freeze({
  preset: 'opencode',
  baseUrl: PRESETS.opencode.baseUrl,
  model: PRESETS.opencode.model,
  key: '',
});

/** 去掉末尾斜杠，只接受 http(s)。不合法返回空串。 */
export function normalizeBaseUrl(value) {
  const text = String(value ?? '').trim().replace(/\/+$/, '');
  if (!/^https?:\/\/[^\s]+$/i.test(text)) return '';
  return text;
}

export function chatCompletionsUrl(baseUrl) {
  const base = normalizeBaseUrl(baseUrl);
  return base ? `${base}/chat/completions` : '';
}

/** 从 storage 读取配置；损坏或缺字段时回退默认值。 */
export function loadConfig(storage) {
  try {
    const raw = storage.getItem(CONFIG_KEY);
    if (!raw) return { ...DEFAULT_CONFIG };
    const data = JSON.parse(raw);
    const preset = Object.hasOwn(PRESETS, data.preset) ? data.preset : 'custom';
    return {
      preset,
      baseUrl: typeof data.baseUrl === 'string' ? data.baseUrl : DEFAULT_CONFIG.baseUrl,
      model: typeof data.model === 'string' ? data.model : DEFAULT_CONFIG.model,
      key: typeof data.key === 'string' ? data.key : '',
    };
  } catch {
    return { ...DEFAULT_CONFIG };
  }
}

export function saveConfig(storage, config) {
  try {
    storage.setItem(CONFIG_KEY, JSON.stringify(config));
    return true;
  } catch {
    return false;
  }
}

export function clearConfig(storage) {
  try { storage.removeItem(CONFIG_KEY); } catch { /* 隐私模式下可能不可用 */ }
}

/** 把选中文字压成单行并截断，避免把整页发出去。 */
export function clip(text, max) {
  const flat = String(text ?? '').replace(/\s+/g, ' ').trim();
  return flat.length > max ? `${flat.slice(0, max)}…` : flat;
}

const SYSTEM_PROMPT =
  '你是游戏开发知识库的阅读助手。用户在文章里选中了一段文字，请用简体中文解释它的含义、' +
  '在上下文中的作用，必要时给一个简短例子。回答要准确、简洁；不确定时直接说明，不要编造。';

/**
 * 拼出发给模型的 messages。
 * history 是之后的追问记录（{role, content}[]），首轮传空数组。
 */
export function buildMessages({ selection, pageTitle = '', context = '', history = [] }) {
  const sel = clip(selection, MAX_SELECTION);
  const ctx = clip(context, MAX_CONTEXT);
  const lines = [];
  if (pageTitle) lines.push(`文章标题：${clip(pageTitle, 120)}`);
  if (ctx) lines.push(`所在段落：${ctx}`);
  lines.push(`选中的文字：${sel}`);
  lines.push('请解释这段文字。');
  return [
    { role: 'system', content: SYSTEM_PROMPT },
    { role: 'user', content: lines.join('\n') },
    ...history,
  ];
}

/** 失败时给用户复制到网页版 DeepSeek 的提示词。 */
export function buildFallbackPrompt({ selection, pageTitle = '', context = '' }) {
  const [, user] = buildMessages({ selection, pageTitle, context });
  return `${SYSTEM_PROMPT}\n\n${user.content}`;
}

/**
 * 增量解析 OpenAI 风格的 SSE 流。
 * 传入累积缓冲区，返回新增的文本片段、剩余未成行的缓冲区，以及是否收到 [DONE]。
 */
export function parseSseChunk(buffer) {
  const deltas = [];
  let done = false;
  const lines = buffer.split(/\r?\n/);
  const rest = lines.pop() ?? '';
  for (const line of lines) {
    if (!line.startsWith('data:')) continue;
    const payload = line.slice(5).trim();
    if (!payload) continue;
    if (payload === '[DONE]') { done = true; continue; }
    try {
      const json = JSON.parse(payload);
      const text = json?.choices?.[0]?.delta?.content;
      if (typeof text === 'string' && text) deltas.push(text);
    } catch {
      // 半截 JSON 或心跳注释，忽略即可
    }
  }
  return { deltas, rest, done };
}

/** 把 HTTP 状态码翻成用户能看懂的提示。 */
export function describeHttpError(status) {
  if (status === 401 || status === 403) return '鉴权失败：请在设置里填写有效的 API Key。';
  if (status === 404) return '接口地址或模型名不对，请检查设置。';
  if (status === 429) return '请求太频繁或额度用完了，请稍后再试。';
  if (status >= 500) return '服务暂时不可用，请稍后再试。';
  return `请求失败（HTTP ${status}）。`;
}
