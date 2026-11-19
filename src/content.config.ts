import { defineCollection, z } from "astro:content";
import { docsLoader } from "@astrojs/starlight/loaders";
import { docsSchema } from "@astrojs/starlight/schema";

export const collections = {
  docs: defineCollection({
    loader: docsLoader(),
    schema: docsSchema({
      extend: z.object({
        // 页面层使用这些字段生成封面、专题入口和精选内容。
        // 旧文章可以省略，展示层会回退到目录名称和默认视觉。
        cover: z.string().optional(),
        coverAlt: z.string().optional(),
        series: z.string().optional(),
        featured: z.boolean().default(false),
      }),
    }),
  }),
};
