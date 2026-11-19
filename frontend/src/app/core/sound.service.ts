import { Injectable } from '@angular/core';

/**
 * Soft UI tones via Web Audio API (no asset files).
 * Browsers require a user gesture before audio can play.
 */
@Injectable({ providedIn: 'root' })
export class SoundService {
  private ctx: AudioContext | null = null;
  private unlocked = false;
  muted = localStorage.getItem('ispan_sound_muted') === '1';

  toggleMute() {
    this.muted = !this.muted;
    localStorage.setItem('ispan_sound_muted', this.muted ? '1' : '0');
    if (!this.muted) this.unlock();
  }

  unlock() {
    if (this.unlocked) return;
    const Ctx = window.AudioContext || (window as any).webkitAudioContext;
    if (!Ctx) return;
    this.ctx = new Ctx();
    void this.ctx.resume();
    this.unlocked = true;
  }

  tap() {
    this.play([{ f: 520, t: 0, d: 0.06, g: 0.04 }, { f: 780, t: 0.05, d: 0.08, g: 0.03 }]);
  }

  success() {
    this.play([
      { f: 440, t: 0, d: 0.1, g: 0.05 },
      { f: 554, t: 0.09, d: 0.12, g: 0.045 },
      { f: 659, t: 0.18, d: 0.18, g: 0.04 },
    ]);
  }

  softWhoosh() {
    this.play([{ f: 180, t: 0, d: 0.22, g: 0.03, type: 'triangle' }]);
  }

  private play(
    notes: { f: number; t: number; d: number; g: number; type?: OscillatorType }[],
  ) {
    if (this.muted) return;
    this.unlock();
    const ctx = this.ctx;
    if (!ctx) return;
    const now = ctx.currentTime;
    for (const n of notes) {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = n.type || 'sine';
      osc.frequency.setValueAtTime(n.f, now + n.t);
      gain.gain.setValueAtTime(0.0001, now + n.t);
      gain.gain.exponentialRampToValueAtTime(n.g, now + n.t + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + n.t + n.d);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(now + n.t);
      osc.stop(now + n.t + n.d + 0.02);
    }
  }
}
