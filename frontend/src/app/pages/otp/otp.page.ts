import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import {
  IonBackButton,
  IonButton,
  IonButtons,
  IonContent,
  IonHeader,
  IonInput,
  IonItem,
  IonList,
  IonTitle,
  IonToolbar,
} from '@ionic/angular/standalone';

import { AuthService } from '../../core/auth.service';

@Component({
  selector: 'app-otp',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterLink,
    IonHeader,
    IonToolbar,
    IonTitle,
    IonContent,
    IonButtons,
    IonBackButton,
    IonList,
    IonItem,
    IonInput,
    IonButton,
  ],
  templateUrl: './otp.page.html',
  styleUrls: ['./otp.page.scss'],
})
export class OtpPage implements OnInit {
  emailCode = '';
  phoneCode = '';
  emailDone = false;
  phoneDone = false;
  error = '';
  loading = false;
  hint = 'Mock/DEBUG code is 123456.';

  constructor(
    private readonly auth: AuthService,
    private readonly router: Router,
  ) {}

  ngOnInit() {
    const user = this.auth.currentUser;
    if (!user) {
      void this.router.navigateByUrl('/login');
      return;
    }
    this.emailDone = !!user.email_verified;
    this.phoneDone = !!user.phone_verified;
    if (this.emailDone && this.phoneDone) {
      this.continue();
    }
  }

  verifyEmail() {
    const user = this.auth.currentUser;
    if (!user) return;
    this.loading = true;
    this.error = '';
    this.auth.verifyOtp('signup_email', user.email, this.emailCode).subscribe({
      next: () => {
        this.emailDone = true;
        this.loading = false;
        this.auth.refreshMe().subscribe({ next: () => this.maybeContinue() });
      },
      error: (err) => {
        this.loading = false;
        this.error = err?.error?.detail || 'Email code failed';
      },
    });
  }

  verifyPhone() {
    const user = this.auth.currentUser;
    if (!user) return;
    this.loading = true;
    this.error = '';
    this.auth.verifyOtp('signup_phone', user.phone, this.phoneCode).subscribe({
      next: () => {
        this.phoneDone = true;
        this.loading = false;
        this.auth.refreshMe().subscribe({ next: () => this.maybeContinue() });
      },
      error: (err) => {
        this.loading = false;
        this.error = err?.error?.detail || 'Phone code failed';
      },
    });
  }

  private maybeContinue() {
    if (this.emailDone && this.phoneDone) this.continue();
  }

  continue() {
    const user = this.auth.currentUser;
    if (!user) return;
    if (user.is_worker || user.role === 'WORKER' || user.active_profile === 'WORKER') {
      void this.router.navigateByUrl('/worker/onboarding');
    } else {
      void this.router.navigateByUrl('/customer');
    }
  }
}
