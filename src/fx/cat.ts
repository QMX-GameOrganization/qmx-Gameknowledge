// 猫咪桌宠：摩卡（夜晚）和拿铁（午后）共用同一个原创形象，配色由 fx.css 里的 --pet-* 变量决定。

import { createPetFx } from './pet-fx';
import { catSvg } from './pet-art';

const common = {
  kind: 'cat',
  svg: catSvg,
  walkSpeed: 38,
  wakeLine: '喵?我才没睡着。',
  endLine: '读到最后啦,喵。',
  onPoke: (audio: import('./audio').AudioManager) => audio.mew(),
  onLand: (audio: import('./audio').AudioManager) => audio.thud(),
  onBoot: () => {},
};

/** 摩卡：深色主题，夜里的猫，声音低一点。 */
export const mochaCat = createPetFx('mocha', {
  ...common,
  lines: [
    '喵~今晚读到哪里了?',
    '夜深了,再读一篇就睡吧。',
    '我帮你盯着,有 bug 就叫我。',
    '你的屏幕暖烘烘的,适合打盹。',
    '摸摸我,今天的代码就不报错。',
    '喵?这段代码看起来很可疑。',
    '小声点,我在假装睡觉。',
    '拖我飞起来试试,我会四脚落地。',
  ],
  greeting: '喵,晚上好。',
  onPoke: (audio) => audio.mew(true),
});

/** 拿铁：浅色主题，午后的猫。 */
export const latteCat = createPetFx('latte', {
  ...common,
  lines: [
    '喵~下午好,今天读点什么?',
    '来杯拿铁,再读下去吧。',
    '阳光刚刚好,适合看文档。',
    '我帮你盯着,有 bug 就叫我。',
    '摸摸我,今天的代码就不报错。',
    '喵?这段代码看起来很可疑。',
    '读累了就伸个懒腰吧。',
    '拖我飞起来试试,我会四脚落地。',
  ],
  greeting: '喵~下午好。',
});
