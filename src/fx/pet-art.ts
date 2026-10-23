// 内置桌宠形象，全部是原创 SVG，不包含任何第三方素材。
// 动画靠 fx.css 里的类名驱动：pet-bob(整体起伏) / pet-leg-a、pet-leg-b(腿) / pet-arm(招手的手臂) /
// pet-eyes(整组眼睛，跟随鼠标) / pet-eye(单只，眨眼) / pet-zzz(睡觉) / pet-tail(猫尾巴)。
// 颜色尽量交给 CSS(fill: var(--pet-xxx))，这样同一个形象可以在不同主题里换配色。

/** 巡检小机：深灰机身、冷蓝护目镜、警示黄条纹（罗德岛主题）。 */
export const botSvg = `
<svg class="pet-svg" viewBox="0 0 96 96" width="100%" height="100%" aria-hidden="true" focusable="false">
  <defs><clipPath id="qmx-pet-band"><rect x="30" y="64" width="36" height="8" rx="3"/></clipPath></defs>
  <ellipse class="pet-shadow" cx="48" cy="90" rx="22" ry="4" fill="#000" opacity=".28"/>
  <g class="pet-bob">
    <g class="pet-leg pet-leg-a"><rect x="33" y="70" width="10" height="15" rx="4" fill="#3a414d"/><rect x="31" y="82" width="14" height="7" rx="3.5" fill="#ffd23f"/></g>
    <g class="pet-leg pet-leg-b"><rect x="53" y="70" width="10" height="15" rx="4" fill="#3a414d"/><rect x="51" y="82" width="14" height="7" rx="3.5" fill="#ffd23f"/></g>
    <rect x="22" y="50" width="8" height="18" rx="4" fill="#3a414d"/>
    <g class="pet-arm"><rect x="66" y="50" width="8" height="18" rx="4" fill="#3a414d"/></g>
    <rect x="28" y="46" width="40" height="30" rx="10" fill="#2b3038" stroke="#35b7f3" stroke-width="2"/>
    <g clip-path="url(#qmx-pet-band)">
      <rect x="30" y="64" width="36" height="8" fill="#ffd23f"/>
      <path d="M26 72l8-8h6l-8 8zM38 72l8-8h6l-8 8zM50 72l8-8h6l-8 8zM62 72l8-8h6l-8 8z" fill="#111316"/>
    </g>
    <circle class="pet-core" cx="48" cy="55" r="3.5" fill="#35b7f3"/>
    <rect x="19" y="26" width="6" height="12" rx="3" fill="#ffd23f"/>
    <rect x="71" y="26" width="6" height="12" rx="3" fill="#ffd23f"/>
    <line x1="48" y1="14" x2="48" y2="6" stroke="#aeb6c3" stroke-width="2"/>
    <circle class="pet-bulb" cx="48" cy="5" r="3.2" fill="#ffd23f"/>
    <rect x="24" y="14" width="48" height="36" rx="12" fill="#1e2228" stroke="#35b7f3" stroke-width="2"/>
    <rect x="30" y="22" width="36" height="20" rx="8" fill="#0c0e11"/>
    <g class="pet-eyes">
      <rect class="pet-eye" x="38" y="28" width="7" height="9" rx="3" fill="#5cc8f8"/>
      <rect class="pet-eye" x="51" y="28" width="7" height="9" rx="3" fill="#5cc8f8"/>
    </g>
  </g>
  <text class="pet-zzz" x="66" y="16" font-size="13" font-weight="700" fill="#ffd23f">z</text>
</svg>`;

/** 方块史莱姆：果冻质感的绿色方块，里面悬浮着一小块金矿（方块世界主题）。 */
export const slimeSvg = `
<svg class="pet-svg" viewBox="0 0 96 96" width="100%" height="100%" aria-hidden="true" focusable="false">
  <defs>
    <linearGradient id="qmx-slime-body" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#8fd14f"/><stop offset="1" stop-color="#5fa02e"/>
    </linearGradient>
  </defs>
  <ellipse class="pet-shadow" cx="48" cy="90" rx="26" ry="4" fill="#000" opacity=".3"/>
  <g class="pet-bob pet-body">
    <rect x="16" y="32" width="64" height="54" rx="15" fill="url(#qmx-slime-body)" stroke="#3f7a1f" stroke-width="2.5"/>
    <rect x="22" y="38" width="22" height="8" rx="4" fill="#fff" opacity=".35"/>
    <g fill="#3f7a1f" opacity=".28"><rect x="26" y="66" width="7" height="7"/><rect x="62" y="72" width="7" height="7"/><rect x="58" y="44" width="5" height="5"/></g>
    <rect class="pet-core" x="40" y="58" width="15" height="15" rx="3" fill="#e8b339" stroke="#a97c10" stroke-width="1.5" transform="rotate(10 47 65)"/>
    <g class="pet-eyes">
      <rect class="pet-eye" x="30" y="46" width="9" height="13" rx="3.5" fill="#1b2a12"/>
      <rect class="pet-eye" x="57" y="46" width="9" height="13" rx="3.5" fill="#1b2a12"/>
    </g>
    <path d="M43 63q5 4.5 10 0" fill="none" stroke="#1b2a12" stroke-width="2.4" stroke-linecap="round"/>
  </g>
  <text class="pet-zzz" x="68" y="26" font-size="13" font-weight="700" fill="#e8b339">z</text>
</svg>`;

/** 小猫：配色通过 --pet-fur / --pet-shade / --pet-inner / --pet-accent 由主题决定（摩卡、拿铁）。 */
export const catSvg = `
<svg class="pet-svg" viewBox="0 0 96 96" width="100%" height="100%" aria-hidden="true" focusable="false">
  <ellipse class="pet-shadow" cx="48" cy="90" rx="24" ry="4" fill="#000" opacity=".25"/>
  <g class="pet-bob">
    <path class="pet-tail cat-stroke" d="M68 72C86 72 88 50 76 44" fill="none" stroke-width="7" stroke-linecap="round"/>
    <g class="pet-leg pet-leg-a"><rect class="cat-fur" x="33" y="74" width="10" height="13" rx="5"/><ellipse class="cat-shade" cx="38" cy="86" rx="6.5" ry="3.2"/></g>
    <g class="pet-leg pet-leg-b"><rect class="cat-fur" x="53" y="74" width="10" height="13" rx="5"/><ellipse class="cat-shade" cx="58" cy="86" rx="6.5" ry="3.2"/></g>
    <ellipse class="cat-fur" cx="48" cy="64" rx="22" ry="16"/>
    <ellipse class="cat-shade" cx="48" cy="69" rx="12" ry="9" opacity=".55"/>
    <g class="pet-arm"><ellipse class="cat-fur" cx="68" cy="62" rx="5" ry="9"/></g>
    <path class="cat-accent" d="M31 52Q48 59 65 52L65 58Q48 65 31 58Z"/>
    <path class="cat-fur" d="M27 25L29 7L43 18Z"/><path class="cat-fur" d="M69 25L67 7L53 18Z"/>
    <path class="cat-inner" d="M31 20L32 12L38 17Z"/><path class="cat-inner" d="M65 20L64 12L58 17Z"/>
    <ellipse class="cat-fur" cx="48" cy="36" rx="25" ry="20"/>
    <circle class="cat-inner" cx="33" cy="42" r="4" opacity=".55"/><circle class="cat-inner" cx="63" cy="42" r="4" opacity=".55"/>
    <g class="pet-eyes">
      <ellipse class="pet-eye" cx="39" cy="35" rx="3.2" ry="4.6" fill="#24242f"/>
      <ellipse class="pet-eye" cx="57" cy="35" rx="3.2" ry="4.6" fill="#24242f"/>
    </g>
    <path class="cat-inner" d="M46 42h4l-2 3z"/>
    <path d="M48 45q-3 4-6 2M48 45q3 4 6 2" fill="none" stroke="#24242f" stroke-width="1.5" stroke-linecap="round"/>
    <g stroke="#24242f" stroke-width="1" opacity=".45" stroke-linecap="round"><path d="M28 41l-8-2M28 44l-8 1M68 41l8-2M68 44l8 1"/></g>
  </g>
  <text class="pet-zzz" x="68" y="14" font-size="13" font-weight="700" style="fill:var(--pet-accent)">z</text>
</svg>`;
