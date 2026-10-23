// 音效管理：全部用 Web Audio 实时合成，不需要音频文件。
//
// 浏览器规定页面必须在用户操作之后才能出声，所以：
//   - 默认关闭，用户点「音效」按钮才开启（点击本身就是授权操作）；
//   - 上次选择了开启时，会在页面第一次点击 / 按键后恢复。
// 所有声音音量都很低，并且有最小间隔，避免连续触发时吵人。

const KEY = 'qmx-sound';

type ToneOptions = {
  freq: number;
  dur?: number;
  type?: OscillatorType;
  gain?: number;
  delay?: number;
  slideTo?: number;
};

// 五声音阶(C 大调五声)，随机挑音不会不和谐。
const PENTATONIC = [523.25, 587.33, 659.25, 783.99, 880.0, 1046.5];

export class AudioManager {
  enabled = false;
  private ctx: AudioContext | null = null;
  private master: GainNode | null = null;
  private last = new Map<string, number>();

  constructor() {
    try {
      this.enabled = localStorage.getItem(KEY) === '1';
    } catch {
      this.enabled = false;
    }
    // 上次开启过：等用户在页面上做出第一次操作后再解锁音频。
    const unlock = () => {
      if (this.enabled) void this.resume();
    };
    window.addEventListener('pointerdown', unlock, { once: true, capture: true });
    window.addEventListener('keydown', unlock, { once: true, capture: true });
  }

  async setEnabled(value: boolean) {
    this.enabled = value;
    try {
      localStorage.setItem(KEY, value ? '1' : '0');
    } catch {
      /* 隐私模式下写不进去也没关系 */
    }
    if (value) {
      await this.resume();
      this.blip(); // 给用户一个「已开启」的反馈
    }
  }

  private async resume() {
    if (!this.ctx) {
      const Ctor = window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
      if (!Ctor) return;
      this.ctx = new Ctor();
      this.master = this.ctx.createGain();
      this.master.gain.value = 0.6;
      this.master.connect(this.ctx.destination);
    }
    if (this.ctx.state === 'suspended') await this.ctx.resume().catch(() => {});
  }

  /** 同一类声音在 minGap 毫秒内只响一次。 */
  private allowed(key: string, minGap: number) {
    if (!this.enabled || !this.ctx || this.ctx.state !== 'running' || document.hidden) return false;
    const now = performance.now();
    if (now - (this.last.get(key) ?? -Infinity) < minGap) return false;
    this.last.set(key, now);
    return true;
  }

  private tone({ freq, dur = 0.2, type = 'sine', gain = 0.06, delay = 0, slideTo }: ToneOptions) {
    const ctx = this.ctx;
    if (!ctx || !this.master) return;
    const t0 = ctx.currentTime + delay;
    const osc = ctx.createOscillator();
    const amp = ctx.createGain();
    osc.type = type;
    osc.frequency.setValueAtTime(freq, t0);
    if (slideTo) osc.frequency.exponentialRampToValueAtTime(slideTo, t0 + dur);
    // 快起慢落的包络，避免「啪」的爆音
    amp.gain.setValueAtTime(0.0001, t0);
    amp.gain.exponentialRampToValueAtTime(gain, t0 + 0.012);
    amp.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
    osc.connect(amp).connect(this.master);
    osc.start(t0);
    osc.stop(t0 + dur + 0.05);
  }

  /** 开启音效时的确认声。 */
  blip() {
    if (!this.allowed('blip', 100)) return;
    this.tone({ freq: 660, dur: 0.09, gain: 0.05 });
    this.tone({ freq: 990, dur: 0.14, gain: 0.05, delay: 0.08 });
  }

  // ───── 星夜 ─────

  /** 清脆的星光声：点击或扫过一群星星。 */
  chime(soft = false) {
    if (!this.allowed(soft ? 'chime-soft' : 'chime', soft ? 260 : 120)) return;
    const f = PENTATONIC[Math.floor(Math.random() * PENTATONIC.length)];
    const g = soft ? 0.022 : 0.05;
    this.tone({ freq: f, dur: soft ? 0.35 : 0.7, gain: g });
    this.tone({ freq: f * 2, dur: soft ? 0.25 : 0.45, gain: g * 0.35, delay: 0.01 });
  }

  /** 流星划过。 */
  whoosh() {
    if (!this.allowed('whoosh', 3000)) return;
    this.tone({ freq: 1500, slideTo: 320, dur: 0.7, gain: 0.025, type: 'triangle' });
  }

  // ───── 罗德岛 ─────

  /** 终端式双音提示：点击桌宠。 */
  terminalBeep() {
    if (!this.allowed('beep', 120)) return;
    this.tone({ freq: 660, dur: 0.06, type: 'square', gain: 0.025 });
    this.tone({ freq: 880, dur: 0.08, type: 'square', gain: 0.025, delay: 0.07 });
  }

  /** 切入主题时的启动音。 */
  boot() {
    if (!this.allowed('boot', 1500)) return;
    [440, 660, 880].forEach((freq, i) => this.tone({ freq, dur: 0.07, type: 'square', gain: 0.02, delay: i * 0.07 }));
  }

  /** 桌宠落地。 */
  thud() {
    if (!this.allowed('thud', 200)) return;
    this.tone({ freq: 150, slideTo: 60, dur: 0.14, gain: 0.07 });
  }

  /** 打字机一样的单字提示音(气泡出字时用，很轻)。 */
  tick() {
    if (!this.allowed('tick', 45)) return;
    this.tone({ freq: 1200 + Math.random() * 200, dur: 0.025, type: 'square', gain: 0.008 });
  }
}
