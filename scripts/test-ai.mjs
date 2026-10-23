// 划词问 AI 的纯逻辑测试。用法：node scripts/test-ai.mjs
import assert from "node:assert/strict";
import {
  CONFIG_KEY, DEFAULT_CONFIG, PRESETS, normalizeBaseUrl, chatCompletionsUrl, loadConfig, saveConfig,
  clearConfig, clip, buildMessages, buildFallbackPrompt, parseSseChunk, describeHttpError,
} from "../src/ai/core.mjs";

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
  assert.deepEqual(loadConfig(s), DEFAULT_CONFIG);
  const cfg = { preset: "deepseek", baseUrl: "https://api.deepseek.com", model: "deepseek-chat", key: "sk-test" };
  assert.ok(saveConfig(s, cfg));
  assert.deepEqual(loadConfig(s), cfg);
  clearConfig(s);
  assert.deepEqual(loadConfig(s), DEFAULT_CONFIG);
  s.setItem(CONFIG_KEY, "{坏的json");
  assert.deepEqual(loadConfig(s), DEFAULT_CONFIG);
  s.setItem(CONFIG_KEY, JSON.stringify({ preset: "不存在", baseUrl: 1, model: null, key: 5 }));
  const fixed = loadConfig(s);
  assert.equal(fixed.preset, "custom");
  assert.equal(fixed.key, "");
});

test("存储不可用时 saveConfig 返回 false 而不是抛错", () => {
  const broken = { setItem() { throw new Error("denied"); } };
  assert.equal(saveConfig(broken, DEFAULT_CONFIG), false);
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

console.log(`\n${passed} 项通过`);
