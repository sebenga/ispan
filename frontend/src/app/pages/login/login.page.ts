import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import {
  IonBadge,
  IonButton,
  IonContent,
  IonInput,
  IonItem,
  IonList,
} from '@ionic/angular/standalone';

import { environment } from '../../../environments/environment';
import { AuthService } from '../../core/auth.service';
import { SoundService } from '../../core/sound.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterLink,
    IonContent,
    IonList,
    IonItem,
    IonInput,
    IonButton,
    IonBadge,
  ],
  templateUrl: './login.page.html',
  styleUrls: ['./login.page.scss'],
})
export class LoginPage {
  email = '';
  password = '';
  error = '';
  loading = false;
  paymentTestMode = environment.paymentTestMode;

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
    const email = this.email.trim();
    const password = this.password;
    if (!email || !password) {
      this.error = 'Enter email and password.';
      return;
    }
    this.loading = true;
    this.error = '';
    this.sound.tap();
    this.auth.login(email, password).subscribe({
      next: (res) => {
        this.loading = false;
        this.sound.success();
        const u = res.user;
        if (u.is_support || u.role === 'ADMIN') {
          void this.router.navigateByUrl('/admin/verification');
        } else if (u.is_worker || u.role === 'WORKER' || u.active_profile === 'WORKER') {
          void this.router.navigateByUrl('/worker');
        } else {
          void this.router.navigateByUrl('/customer');
        }
      },
      error: (err) => {
        this.loading = false;
        const detail = err?.error?.detail;
        this.error =
          typeof detail === 'string'
            ? detail
            : err?.status === 0
              ? 'Cannot reach the API (is it running on port 8001?)'
              : 'No active account found with the given credentials';
      },
    });
  }
}
