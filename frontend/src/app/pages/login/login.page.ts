import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import {
  IonButton,
  IonContent,
  IonHeader,
  IonIcon,
  IonInput,
  IonItem,
  IonList,
  IonTitle,
  IonToolbar,
  IonBadge,
} from '@ionic/angular/standalone';

import { environment } from '../../../environments/environment';
import { AuthService } from '../../core/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterLink,
    IonHeader,
    IonToolbar,
    IonTitle,
    IonContent,
    IonList,
    IonItem,
    IonInput,
    IonButton,
    IonIcon,
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
  ) {}

  submit() {
    this.loading = true;
    this.error = '';
    this.auth.login(this.email, this.password).subscribe({
      next: (res) => {
        this.loading = false;
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
        this.error = err?.error?.detail || 'Login failed';
      },
    });
  }
}
