import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
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
  IonSelect,
  IonSelectOption,
  IonTitle,
  IonToolbar,
} from '@ionic/angular/standalone';

import { AuthService } from '../../core/auth.service';

@Component({
  selector: 'app-register',
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
  ) {}

  submit() {
    this.loading = true;
    this.error = '';
    this.auth
      .register({
        first_name: this.first_name,
        last_name: this.last_name,
        email: this.email,
        phone: this.phone,
        password: this.password,
        role: this.role,
      })
      .subscribe({
        next: () => {
          this.auth.login(this.email, this.password).subscribe({
            next: (res) => {
              this.loading = false;
              void this.router.navigateByUrl(
                res.user.role === 'WORKER' ? '/worker' : '/customer',
              );
            },
            error: () => {
              this.loading = false;
              void this.router.navigateByUrl('/login');
            },
          });
        },
        error: (err) => {
          this.loading = false;
          this.error = err?.error?.detail || 'Registration failed';
        },
      });
  }
}
