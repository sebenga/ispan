import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import {
  IonButton,
  IonContent,
  IonInput,
  IonItem,
  IonList,
  IonSelect,
  IonSelectOption,
} from '@ionic/angular/standalone';

import { environment } from '../../../environments/environment';
import { AuthService } from '../../core/auth.service';
import { SoundService } from '../../core/sound.service';

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterLink,
    IonContent,
    IonList,
    IonItem,
    IonInput,
    IonSelect,
    IonSelectOption,
    IonButton,
  ],
  templateUrl: './register.page.html',
  styleUrls: ['./register.page.scss'],
})
export class RegisterPage {
  first_name = '';
  last_name = '';
  email = '';
  phone = '';
  password = '';
  role: 'CUSTOMER' | 'WORKER' = 'CUSTOMER';
  error = '';
  loading = false;

  constructor(
    private readonly auth: AuthService,
    private readonly router: Router,
    private readonly sound: SoundService,
  ) {}

  unlockAudio() {
    this.sound.unlock();
  }

  tap() {
    this.sound.tap();
  }

  submit() {
    this.error = '';
    this.sound.tap();
    const first_name = this.first_name.trim();
    const last_name = this.last_name.trim();
    const email = this.email.trim().toLowerCase();
    const phone = this.normalizePhone(this.phone);
    const password = this.password;

    if (!first_name || !last_name || !email || !phone || !password) {
      this.error = 'Please fill in all fields.';
      return;
    }
    if (password.length < 8) {
      this.error = 'Password must be at least 8 characters.';
      return;
    }
    if (!email.includes('@')) {
      this.error = 'Enter a valid email address.';
      return;
    }

    this.loading = true;
    this.auth
      .register({
        first_name,
        last_name,
        email,
        phone,
        password,
        role: this.role,
        consent_version: environment.legalVersion,
        consent_flags: {
          age_18: true,
          terms: true,
          privacy: true,
        },
      })
      .subscribe({
        next: () => {
          this.loading = false;
          this.sound.success();
          void this.router.navigateByUrl('/otp');
        },
        error: (err) => {
          this.loading = false;
          this.error = this.formatApiError(err);
        },
      });
  }

  private normalizePhone(raw: string): string {
    const trimmed = raw.trim().replace(/[\s-]/g, '');
    if (!trimmed) return '';
    if (trimmed.startsWith('+')) return trimmed;
    if (trimmed.startsWith('0') && trimmed.length >= 10) {
      return `+27${trimmed.slice(1)}`;
    }
    if (trimmed.startsWith('27') && trimmed.length >= 11) {
      return `+${trimmed}`;
    }
    return trimmed;
  }

  private formatApiError(err: { status?: number; error?: unknown }): string {
    if (err?.status === 0) {
      return 'Cannot reach the API. Is the backend running on port 8001?';
    }
    const body = err?.error;
    if (!body || typeof body !== 'object') {
      return 'Registration failed. Please try again.';
    }
    const record = body as Record<string, unknown>;
    if (typeof record['detail'] === 'string') return record['detail'];

    const parts: string[] = [];
    for (const [key, value] of Object.entries(record)) {
      const label = key.replace(/_/g, ' ');
      if (Array.isArray(value) && value.length) {
        parts.push(`${label}: ${String(value[0])}`);
      } else if (typeof value === 'string') {
        parts.push(`${label}: ${value}`);
      }
    }
    return parts.join(' · ') || 'Registration failed. Please try again.';
  }
}
