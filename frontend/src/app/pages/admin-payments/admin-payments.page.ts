import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import {
  IonButton,
  IonButtons,
  IonContent,
  IonHeader,
  IonItem,
  IonLabel,
  IonList,
  IonTitle,
  IonToolbar,
} from '@ionic/angular/standalone';

import { ApiService } from '../../core/api.service';
import { AuthService } from '../../core/auth.service';

@Component({
  selector: 'app-admin-payments',
  standalone: true,
  imports: [
    CommonModule,
    IonHeader,
    IonToolbar,
    IonTitle,
    IonContent,
    IonButtons,
    IonButton,
    IonList,
    IonItem,
    IonLabel,
  ],
  templateUrl: './admin-payments.page.html',
  styleUrls: ['./admin-payments.page.scss'],
})
export class AdminPaymentsPage implements OnInit {
  data: any = null;
  error = '';
  message = '';

  constructor(
    private readonly api: ApiService,
    private readonly auth: AuthService,
    private readonly router: Router,
  ) {}

  ngOnInit() {
    if (!this.auth.currentUser) {
      void this.router.navigateByUrl('/login');
      return;
    }
    this.reload();
  }

  reload() {
    this.api.adminMockPayments().subscribe({
      next: (d) => (this.data = d),
      error: (err) => (this.error = err?.error?.detail || 'Staff only'),
    });
  }

  fireWebhook(paymentId: string) {
    this.api
      .adminMockAction({ action: 'fire_webhook', payment_id: paymentId, status: 'success' })
      .subscribe({
        next: (r) => {
          this.message = JSON.stringify(r);
          this.reload();
        },
        error: (err) => (this.error = err?.error?.detail || 'Webhook failed'),
      });
  }

  autoRelease() {
    this.api.adminMockAction({ action: 'auto_release' }).subscribe({
      next: (r) => {
        this.message = `Released ${r.released}`;
        this.reload();
      },
    });
  }
}
