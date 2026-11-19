import type { CollectionEntry } from "astro:content";

export type KnowledgeDoc = CollectionEntry<"docs">;

/**
 * 判断文章是否属于公开内容区域。首页、专题页和文章抽屉共用这条边界。
 */
export function isPublicDoc(doc: KnowledgeDoc) {
  return /^(knowledge|projects|guide)\//.test(doc.id);
}

/**
 * 从目录结构回退生成专题名称，保证旧文章没有 series 字段时仍然可以归类。
 */
export function getDocSeries(doc: KnowledgeDoc) {
  if (doc.data.series) return doc.data.series;
  const parts = doc.id.split("/");
  return parts[0] === "knowledge" ? parts[1] ?? "知识库" : parts[0] ?? "知识库";
}

/**
 * 把内容条目转换成页面层需要的稳定链接，统一处理站点 base 路径。
 */
/**
 * 返回文章所属的一级专题键，用于专题页和首页入口之间的稳定关联。
 */
export function getDocCollectionKey(doc: KnowledgeDoc) {
  const parts = doc.id.split("/");
  return parts[0] === "knowledge" ? parts[1] ?? "knowledge" : parts[0] ?? "knowledge";
}

export function getDocHref(doc: KnowledgeDoc, base: string) {
  return base + "/" + doc.id + "/";
}

/**
 * 文章没有真实图片封面时仍返回一个稳定的视觉类别，让卡片和文章页保持有封面区域。
 */
export function getDocVisualKey(doc: KnowledgeDoc) {
  const series = getDocSeries(doc).toLowerCase();
  if (series.includes("unity") || series.includes("ecs")) return "unity";
  if (series.includes("c#") || series.includes("csharp") || series.includes("面向对象")) return "language";
  if (series.includes("unreal") || series.includes("ue")) return "unreal";
  if (series.includes("minecraft") || series.includes("源码")) return "source";
  if (series.includes("项目") || doc.id.startsWith("projects/")) return "project";
  return "reference";
}

export function getDocDate(doc: KnowledgeDoc) {
  return doc.data.date instanceof Date ? doc.data.date : undefined;
}
