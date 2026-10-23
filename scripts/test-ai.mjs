// 划词问 AI 的纯逻辑测试。用法：node scripts/test-ai.mjs
import assert from "node:assert/strict";
import {
  CONFIG_KEY, PRESETS, defaultConfig, defaultProfile, activeProfile, modelsUrl, parseModelList, normalizeBaseUrl, chatCompletionsUrl, loadConfig, saveConfig,
  clearConfig, clip, buildMessages, buildFallbackPrompt, parseSseChunk, describeHttpError,
} from "../src/ai/core.mjs";
import { parseInline, parseMarkdown, safeUrl } from "../src/ai/markdown.mjs";

let passed = 0;
const test = (name, fn) => { fn(); passed++; console.log("✓", name); };
const memory = () => {
  const map = new Map();
  return { getItem: (k) => map.get(k) ?? null, setItem: (k, v) => map.set(k, v), removeItem: (k) => map.delete(k) };
};

test("Base URL 去掉末尾斜杠，拒绝非 http(s)", () => {
  assert.equal(normalizeBaseUrl(" https://api.deepseek.com/ "), "https://api.deepseek.com");
  assert.equal(normalizeBaseUrl("javascript:alert(1)"), "");
  assert.equal(normalizeBaseUrl(""), "");
  assert.equal(chatCompletionsUrl("https://opencode.ai/inference/openai/v1/"), "https://opencode.ai/inference/openai/v1/chat/completions");
  assert.equal(chatCompletionsUrl("ftp://x"), "");
});

test("配置：默认值、保存读取、清除、损坏数据回退", () => {
  const s = memory();
  assert.deepEqual(loadConfig(s), defaultConfig());
  const cfg = defaultConfig();
  cfg.active = "deepseek";
  cfg.profiles.deepseek = { baseUrl: "https://api.deepseek.com", model: "deepseek-chat", key: "sk-test", models: ["deepseek-chat"] };
  assert.ok(saveConfig(s, cfg));
  assert.deepEqual(loadConfig(s), cfg);
  clearConfig(s);
  assert.deepEqual(loadConfig(s), defaultConfig());
  s.setItem(CONFIG_KEY, "{坏的json");
  assert.deepEqual(loadConfig(s), defaultConfig());
  s.setItem(CONFIG_KEY, "null");
  assert.deepEqual(loadConfig(s), defaultConfig());
  s.setItem(CONFIG_KEY, JSON.stringify({ active: "不存在", profiles: { deepseek: { baseUrl: 1, model: null, key: 5, models: "x" } } }));
  const fixed = loadConfig(s);
  assert.equal(fixed.active, "opencode");
  assert.deepEqual(fixed.profiles.deepseek, defaultProfile("deepseek"));
});

test("各平台的 Key 分开存储，互不影响", () => {
  const s = memory();
  const cfg = defaultConfig();
  cfg.profiles.deepseek.key = "sk-deepseek";
  cfg.profiles.siliconflow.key = "sk-silicon";
  cfg.active = "siliconflow";
  saveConfig(s, cfg);
  const back = loadConfig(s);
  assert.equal(back.profiles.deepseek.key, "sk-deepseek");
  assert.equal(back.profiles.siliconflow.key, "sk-silicon");
  assert.equal(back.profiles.opencode.key, "");
  assert.equal(activeProfile(back).key, "sk-silicon");
});

test("旧版单份配置自动迁移到对应平台", () => {
  const s = memory();
  s.setItem(CONFIG_KEY, JSON.stringify({ preset: "deepseek", baseUrl: "https://api.deepseek.com", model: "deepseek-chat", key: "sk-old" }));
  const cfg = loadConfig(s);
  assert.equal(cfg.active, "deepseek");
  assert.equal(cfg.profiles.deepseek.key, "sk-old");
  assert.equal(cfg.profiles.opencode.key, "");
  s.setItem(CONFIG_KEY, JSON.stringify({ preset: "未知", baseUrl: "https://x.com/v1", model: "m", key: "k" }));
  assert.equal(loadConfig(s).active, "custom");
});

test("模型列表地址与解析：OpenAI 格式、Ollama 格式、字符串数组、去重排序", () => {
  assert.equal(modelsUrl("https://api.deepseek.com/"), "https://api.deepseek.com/models");
  assert.equal(modelsUrl("ftp://x"), "");
  assert.deepEqual(parseModelList({ data: [{ id: "b" }, { id: "a" }, { id: "a" }, { object: "x" }] }), ["a", "b"]);
  assert.deepEqual(parseModelList({ models: [{ name: "llama3" }, { name: "qwen" }] }), ["llama3", "qwen"]);
  assert.deepEqual(parseModelList(["z", " y ", ""]), ["y", "z"]);
  assert.deepEqual(parseModelList({ error: "nope" }), []);
  assert.deepEqual(parseModelList(null), []);
  assert.equal(parseModelList({ data: Array.from({ length: 800 }, (_, i) => ({ id: `m${i}` })) }).length, 500);
});

test("存储不可用时 saveConfig 返回 false 而不是抛错", () => {
  const broken = { setItem() { throw new Error("denied"); } };
  assert.equal(saveConfig(broken, defaultConfig()), false);
});

test("预设都有 label，且除自定义外有可用的 Base URL", () => {
  for (const [id, p] of Object.entries(PRESETS)) {
    assert.ok(p.label);
    if (id !== "custom") assert.ok(normalizeBaseUrl(p.baseUrl), id);
  }
});

test("clip 压平空白并截断", () => {
  assert.equal(clip("a \n\n  b", 10), "a b");
  assert.equal(clip("x".repeat(20), 5), "xxxxx…");
});

test("buildMessages 带上标题、段落和选中文字，并拼接追问历史", () => {
  const m = buildMessages({ selection: "NativeArray", pageTitle: "NativeContainer", context: "NativeArray 是…", history: [{ role: "assistant", content: "它是…" }, { role: "user", content: "为什么？" }] });
  assert.equal(m[0].role, "system");
  assert.match(m[1].content, /文章标题：NativeContainer/);
  assert.match(m[1].content, /选中的文字：NativeArray/);
  assert.equal(m.length, 4);
  assert.equal(m[3].content, "为什么？");
});

test("buildMessages 会截断超长选区", () => {
  const m = buildMessages({ selection: "字".repeat(5000) });
  assert.ok(m[1].content.length < 700);
});

test("回退提示词包含系统说明和选中文字", () => {
  const p = buildFallbackPrompt({ selection: "SIMD", pageTitle: "Burst" });
  assert.match(p, /游戏开发知识库/);
  assert.match(p, /SIMD/);
});

test("SSE 解析：完整行、半截行、[DONE]、坏 JSON", () => {
  const chunk1 = 'data: {"choices":[{"delta":{"content":"你"}}]}\n\ndata: {"choices":[{"delta":{"content":"好';
  const a = parseSseChunk(chunk1);
  assert.deepEqual(a.deltas, ["你"]);
  assert.equal(a.done, false);
  const b = parseSseChunk(a.rest + '"}}]}\n\ndata: 不是json\n\n: 心跳\n\ndata: [DONE]\n');
  assert.deepEqual(b.deltas, ["好"]);
  assert.equal(b.done, true);
});

test("SSE 解析：忽略没有 content 的 delta（如 role 或空串）", () => {
  const r = parseSseChunk('data: {"choices":[{"delta":{"role":"assistant"}}]}\ndata: {"choices":[{"delta":{"content":""}}]}\n');
  assert.deepEqual(r.deltas, []);
});

test("HTTP 错误提示", () => {
  assert.match(describeHttpError(401), /Key/);
  assert.match(describeHttpError(404), /模型名/);
  assert.match(describeHttpError(429), /额度/);
  assert.match(describeHttpError(503), /暂时不可用/);
  assert.match(describeHttpError(418), /418/);
});

// ---------- Markdown ----------
const flat = (nodes) => nodes.map((n) => (n.t === "text" || n.t === "code" ? n.v : n.t === "br" ? "\n" : flat(n.c))).join("");

test("Markdown 行内：粗体、斜体、行内代码、删除线、链接", () => {
  const n = parseInline("a **粗** 和 *斜* 和 `x*y` 和 ~~删~~ 和 [站点](https://example.com/a)");
  assert.deepEqual(n.map((x) => x.t), ["text", "strong", "text", "em", "text", "code", "text", "del", "text", "a"]);
  assert.equal(n.find((x) => x.t === "code").v, "x*y");
  assert.equal(n.find((x) => x.t === "a").href, "https://example.com/a");
});

test("Markdown 行内：snake_case、乘号、未闭合标记保持原样", () => {
  assert.deepEqual(parseInline("my_var_name").map((x) => x.t), ["text"]);
  // 带空格的乘号不是强调；不带空格的 2*3*4 按 CommonMark 会把 3 变成斜体，这里保持一致
  assert.deepEqual(parseInline("2 * 3 * 4").map((x) => x.t), ["text"]);
  assert.deepEqual(parseInline("2*3*4").map((x) => x.t), ["text", "em", "text"]);
  assert.deepEqual(parseInline("**还没写完").map((x) => x.t), ["text"]);
  assert.equal(flat(parseInline("\\*不是斜体\\*")), "*不是斜体*");
});

test("链接只允许 http(s)，javascript: 变成普通文字", () => {
  assert.equal(safeUrl("javascript:alert(1)"), "");
  assert.equal(safeUrl("data:text/html,x"), "");
  assert.ok(safeUrl("http://a.com"));
  const n = parseInline("[点我](javascript:alert(1))");
  assert.ok(n.every((x) => x.t === "text"));
});

test("HTML 标签不会被当作标记，只是文字", () => {
  const b = parseMarkdown("<img src=x onerror=alert(1)>\n\n<script>alert(1)</script>");
  assert.ok(b.every((x) => x.type === "p" && x.inline.every((i) => i.t === "text" || i.t === "br")));
});

test("Markdown 块：标题、段落换行、分隔线", () => {
  const b = parseMarkdown("## 标题\n第一行\n第二行\n\n---\n\n### 小节");
  assert.deepEqual(b.map((x) => x.type), ["h", "p", "hr", "h"]);
  assert.equal(b[0].level, 2);
  assert.ok(b[1].inline.some((x) => x.t === "br"));
});

test("Markdown 块：围栏代码块保留内容，流式未闭合时也能显示", () => {
  const b = parseMarkdown("看这个：\n```csharp\nvar a = 1;\n  var b = *2*;\n```\n结束");
  assert.deepEqual(b.map((x) => x.type), ["p", "code", "p"]);
  assert.equal(b[1].lang, "csharp");
  assert.equal(b[1].text, "var a = 1;\n  var b = *2*;");
  const open = parseMarkdown("```js\nconst x = 1;");
  assert.equal(open[0].type, "code");
  assert.equal(open[0].text, "const x = 1;");
});

test("Markdown 块：有序/无序列表、嵌套、起始序号", () => {
  const b = parseMarkdown("1. 一\n2. 二\n   - 子项 A\n   - 子项 B\n3. 三\n\n- 甲\n- 乙");
  assert.deepEqual(b.map((x) => x.type), ["ol", "ul"]);
  assert.equal(b[0].items.length, 3);
  assert.equal(b[0].items[1].children[0].type, "ul");
  assert.equal(b[0].items[1].children[0].items.length, 2);
  assert.equal(parseMarkdown("3. 从三开始\n4. 四")[0].start, 3);
});

test("Markdown 块：引用和表格", () => {
  const q = parseMarkdown("> 引用 **重点**\n> 第二行");
  assert.equal(q[0].type, "quote");
  assert.equal(q[0].blocks[0].type, "p");
  const t = parseMarkdown("| 名称 | 说明 |\n| --- | --- |\n| Job | 任务 |\n| Burst | 编译器 |");
  assert.equal(t[0].type, "table");
  assert.equal(t[0].head.length, 2);
  assert.equal(t[0].rows.length, 2);
  assert.equal(flat(t[0].rows[1][0]), "Burst");
});

test("Markdown：空输入与超长输入不会崩", () => {
  assert.deepEqual(parseMarkdown(""), []);
  assert.deepEqual(parseMarkdown(null), []);
  assert.ok(parseMarkdown("*".repeat(5000) + "\n" + "[".repeat(3000)).length > 0);
});

console.log(`\n${passed} 项通过`);
