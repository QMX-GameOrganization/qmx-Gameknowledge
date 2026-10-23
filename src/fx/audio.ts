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
    } else {
      this.stopLoops(); // 关掉正在播放的环境音(比如雨声)
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

  // ───── 噪声与循环音 ─────

  private noiseBuffer: AudioBuffer | null = null;
  private loops = new Map<string, () => void>();

  private getNoise(): AudioBuffer | null {
    const ctx = this.ctx;
    if (!ctx) return null;
    if (!this.noiseBuffer) {
      const length = ctx.sampleRate * 2;
      const buf = ctx.createBuffer(1, length, ctx.sampleRate);
      const data = buf.getChannelData(0);
      for (let i = 0; i < length; i++) data[i] = Math.random() * 2 - 1;
      this.noiseBuffer = buf;
    }
    return this.noiseBuffer;
  }

  /** 一小段滤波后的噪声：碎裂声、纸张沙沙声。 */
  private noise(opts: { dur: number; filter: BiquadFilterType; freq: number; gain: number; q?: number; delay?: number }) {
    const ctx = this.ctx;
    const buf = this.getNoise();
    if (!ctx || !buf || !this.master) return;
    const t0 = ctx.currentTime + (opts.delay ?? 0);
    const src = ctx.createBufferSource();
    src.buffer = buf;
    const filter = ctx.createBiquadFilter();
    filter.type = opts.filter;
    filter.frequency.value = opts.freq;
    filter.Q.value = opts.q ?? 0.7;
    const amp = ctx.createGain();
    amp.gain.setValueAtTime(0.0001, t0);
    amp.gain.exponentialRampToValueAtTime(opts.gain, t0 + 0.01);
    amp.gain.exponentialRampToValueAtTime(0.0001, t0 + opts.dur);
    src.connect(filter).connect(amp).connect(this.master);
    src.start(t0, Math.random());
    src.stop(t0 + opts.dur + 0.05);
  }

  /** 环境雨声：淡入淡出的循环噪声。on=false 时淡出并停止。 */
  rain(on: boolean) {
    const key = 'rain';
    if (!on) {
      this.loops.get(key)?.();
      this.loops.delete(key);
      return;
    }
    if (this.loops.has(key) || !this.enabled || !this.ctx || this.ctx.state !== 'running' || !this.master) return;
    const ctx = this.ctx;
    const buf = this.getNoise();
    if (!buf) return;
    const src = ctx.createBufferSource();
    src.buffer = buf;
    src.loop = true;
    const filter = ctx.createBiquadFilter();
    filter.type = 'bandpass';
    filter.frequency.value = 1500;
    filter.Q.value = 0.5;
    const amp = ctx.createGain();
    amp.gain.setValueAtTime(0.0001, ctx.currentTime);
    amp.gain.exponentialRampToValueAtTime(0.02, ctx.currentTime + 1.5);
    src.connect(filter).connect(amp).connect(this.master);
    src.start();
    this.loops.set(key, () => {
      const now = ctx.currentTime;
      amp.gain.cancelScheduledValues(now);
      amp.gain.setValueAtTime(Math.max(amp.gain.value, 0.0001), now);
      amp.gain.exponentialRampToValueAtTime(0.0001, now + 1.2);
      src.stop(now + 1.3);
    });
  }

  /** 切换主题或关闭特效时调用：停掉所有循环音。 */
  stopLoops() {
    this.loops.forEach((stop) => stop());
    this.loops.clear();
  }

  // ───── 春樱 / 夏日 ─────

  /** 日式五声音阶(平调子)的筝拨弦。 */
  pluck() {
    if (!this.allowed('pluck', 140)) return;
    const scale = [587.33, 659.25, 698.46, 880.0, 932.33, 1174.66];
    const f = scale[Math.floor(Math.random() * scale.length)];
    this.tone({ freq: f, dur: 0.9, type: 'triangle', gain: 0.05 });
    this.tone({ freq: f * 2, dur: 0.45, gain: 0.012 });
  }

  /** 水滴。 */
  plink() {
    if (!this.allowed('plink', 90)) return;
    this.tone({ freq: 1100, slideTo: 420, dur: 0.13, gain: 0.04 });
  }

  // ───── 像素终端 ─────

  /** 8 位风格：click 是上行三连音，key 是极短的按键声。 */
  retro(kind: 'click' | 'key') {
    if (kind === 'key') {
      if (!this.allowed('retro-key', 40)) return;
      this.tone({ freq: 760 + Math.random() * 240, dur: 0.03, type: 'square', gain: 0.012 });
      return;
    }
    if (!this.allowed('retro-click', 120)) return;
    [523.25, 659.25, 783.99].forEach((freq, i) => this.tone({ freq, dur: 0.06, type: 'square', gain: 0.022, delay: i * 0.05 }));
  }

  // ───── 初音 ─────

  private melodyIndex = 0;
  /** 按固定旋律逐个弹出音符，连续点击就是一小段曲调。 */
  melody() {
    if (!this.allowed('melody', 90)) return;
    const tune = [659.25, 783.99, 880.0, 783.99, 987.77, 880.0, 783.99, 659.25, 587.33, 659.25, 783.99, 1046.5];
    const f = tune[this.melodyIndex++ % tune.length];
    this.tone({ freq: f, dur: 0.45, type: 'triangle', gain: 0.045 });
    this.tone({ freq: f * 2, dur: 0.3, gain: 0.012, delay: 0.005 });
  }

  // ───── 方块世界 ─────

  /** 方块破碎。 */
  crack() {
    if (!this.allowed('crack', 80)) return;
    this.noise({ dur: 0.14, filter: 'lowpass', freq: 900, gain: 0.09 });
    this.tone({ freq: 120, slideTo: 55, dur: 0.12, gain: 0.05 });
  }

  /** 史莱姆弹跳。 */
  boing() {
    if (!this.allowed('boing', 150)) return;
    this.tone({ freq: 180, slideTo: 440, dur: 0.1, gain: 0.05 });
    this.tone({ freq: 440, slideTo: 200, dur: 0.12, gain: 0.04, delay: 0.09 });
  }

  // ───── 赛博霓虹 ─────

  /** 激光「咻」。 */
  zap() {
    if (!this.allowed('zap', 100)) return;
    this.tone({ freq: 1400, slideTo: 180, dur: 0.14, type: 'sawtooth', gain: 0.018 });
  }

  // ───── Nord ─────

  /** 冰晶一样的清脆长音。 */
  icy() {
    if (!this.allowed('icy', 200)) return;
    this.tone({ freq: 1318.5, dur: 1.1, gain: 0.03 });
    this.tone({ freq: 1975.5, dur: 0.8, gain: 0.014, delay: 0.02 });
  }

  // ───── 猫 ─────

  /** 喵。low 为低沉版本(夜晚的摩卡猫)。 */
  mew(low = false) {
    if (!this.allowed('mew', 300)) return;
    const k = low ? 0.82 : 1;
    this.tone({ freq: 700 * k, slideTo: 960 * k, dur: 0.16, gain: 0.035 });
    this.tone({ freq: 960 * k, slideTo: 600 * k, dur: 0.24, gain: 0.03, delay: 0.15 });
  }

  // ───── GitHub / 护眼纸张 ─────

  /** 提交成功的轻点两下。 */
  commit() {
    if (!this.allowed('commit', 60)) return;
    this.tone({ freq: 1000, dur: 0.04, type: 'square', gain: 0.012 });
    this.tone({ freq: 1500, dur: 0.05, type: 'square', gain: 0.012, delay: 0.04 });
  }

  /** 翻纸的沙沙声。 */
  paper() {
    if (!this.allowed('paper', 150)) return;
    this.noise({ dur: 0.14, filter: 'highpass', freq: 3000, gain: 0.025 });
  }

  /** 读完一页的清亮铃声。 */
  bell() {
    if (!this.allowed('bell', 3000)) return;
    this.tone({ freq: 880, dur: 1.2, gain: 0.03 });
    this.tone({ freq: 1760, dur: 0.8, gain: 0.012, delay: 0.01 });
  }
}
