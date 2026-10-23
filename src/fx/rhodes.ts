// 罗德岛：页面底部的桌宠「巡检小机」。行为与交互见 pet-fx.ts，形象见 pet-art.ts。
// 界面细节(警示条纹、标题标记等)在 fx.css 里。

import { createPetFx } from './pet-fx';
import { botSvg } from './pet-art';

export default createPetFx('rhodes', {
  kind: 'bot',
  svg: botSvg,
  lines: [
    '博士,今天也在整理知识库吗?',
    '我是巡检小机,负责看守这个页面。',
    '代码块读完了吗?别忘了动手试一试。',
    '文档改完,记得写更新说明。',
    '拖拽我可以换个位置,别扔太高。',
    '右上角可以切换主题,换换心情。',
    '检测到一篇长文,建议分段阅读。',
    '休息一下吧,眼睛也需要待机。',
    '需要的资料都在左边的目录里。',
    '一切正常,继续工作吧。',
  ],
  greeting: '博士,欢迎来到罗德岛知识库。',
  wakeLine: '……啊,我没睡着。',
  endLine: '读到底了,辛苦啦。',
  onPoke: (audio) => audio.terminalBeep(),
  onLand: (audio) => audio.thud(),
  onBoot: (audio) => audio.boot(),
});
