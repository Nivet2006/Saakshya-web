// Off-main-thread AudioWorkletProcessor for Sakshya ASHA Voice Field Register.
// Performs DC-offset / 85 Hz 1st-order high-pass filtering, linear resampling to
// 16,000 Hz mono, exact 512-sample (32 ms) Int16 PCM framing, and per-frame RMS /
// clipping diagnostics without blocking the React main thread.

class SakshyaCaptureProcessor extends AudioWorkletProcessor {
  constructor(options) {
    super();
    const opts = (options && options.processorOptions) || {};
    this.targetSampleRate = opts.targetSampleRate || 16000;
    this.frameSamples = opts.frameSamples || 512;
    this.inputRate = sampleRate || 48000;

    // 1st-order 85 Hz high-pass filter to attenuate fan/AC/wind/traffic rumble
    const rc = 1.0 / (2.0 * Math.PI * 85.0);
    const dt = 1.0 / this.inputRate;
    this.hpAlpha = rc / (rc + dt);
    this.hpPrevX = 0.0;
    this.hpPrevY = 0.0;

    this.pending = [];
    this.active = true;

    this.port.onmessage = (ev) => {
      if (ev && ev.data && ev.data.type === 'set_active') {
        this.active = Boolean(ev.data.active);
        if (!this.active) {
          this.pending = [];
        }
      }
    };
  }

  process(inputs) {
    if (!this.active) return true;
    const input = inputs[0];
    if (!input || input.length === 0 || !input[0]) return true;

    const ch0 = input[0];
    const ch1 = input.length > 1 ? input[1] : null;
    const len = ch0.length;
    if (len === 0) return true;

    // Downmix to mono + apply 85 Hz high-pass + count clipping
    const filtered = new Float32Array(len);
    let clipped = 0;
    let peak = 0;
    let sumSq = 0;
    let px = this.hpPrevX;
    let py = this.hpPrevY;
    const a = this.hpAlpha;

    for (let i = 0; i < len; i++) {
      const raw = ch1 ? 0.5 * (ch0[i] + ch1[i]) : ch0[i];
      const absRaw = raw < 0 ? -raw : raw;
      if (absRaw >= 0.995) clipped += 1;
      if (absRaw > peak) peak = absRaw;

      const y = a * (py + raw - px);
      px = raw;
      py = y;
      filtered[i] = y;
      sumSq += y * y;
    }
    this.hpPrevX = px;
    this.hpPrevY = py;

    // Resample to 16,000 Hz
    if (this.inputRate === this.targetSampleRate) {
      for (let i = 0; i < len; i++) {
        const clamped = Math.max(-1, Math.min(1, filtered[i]));
        this.pending.push(clamped < 0 ? Math.round(clamped * 0x8000) : Math.round(clamped * 0x7fff));
      }
    } else {
      const ratio = this.inputRate / this.targetSampleRate;
      const outLen = Math.floor(len / ratio);
      for (let i = 0; i < outLen; i++) {
        const srcIdx = i * ratio;
        const low = Math.floor(srcIdx);
        const high = Math.min(low + 1, len - 1);
        const frac = srcIdx - low;
        const val = filtered[low] * (1 - frac) + filtered[high] * frac;
        const clamped = Math.max(-1, Math.min(1, val));
        this.pending.push(clamped < 0 ? Math.round(clamped * 0x8000) : Math.round(clamped * 0x7fff));
      }
    }

    const rms = Math.sqrt(sumSq / len);

    while (this.pending.length >= this.frameSamples) {
      const frame = new Int16Array(this.pending.splice(0, this.frameSamples));
      this.port.postMessage(
        {
          type: 'pcm_frame',
          buffer: frame.buffer,
          rms,
          peak,
          clipped,
          inputRate: this.inputRate,
        },
        [frame.buffer]
      );
      clipped = 0;
    }

    return true;
  }
}

registerProcessor('sakshya-capture-processor', SakshyaCaptureProcessor);

