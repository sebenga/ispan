import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import {
  IonBackButton,
  IonBadge,
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
import { environment } from '../../../environments/environment';

@Component({
  selector: 'app-wallet',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    IonHeader,
    IonToolbar,
    IonTitle,
    IonContent,
    IonButtons,
    IonBackButton,
    IonButton,
    IonBadge,
    IonList,
    IonItem,
    IonLabel,
  ],
  templateUrl: './wallet.page.html',
  styleUrls: ['./wallet.page.scss'],
})
export class WalletPage implements OnInit {
  wallet: any = null;
  ledger: any[] = [];
  error = '';
  message = '';
  testMode = environment.paymentTestMode;

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
    this.api.getWallet().subscribe({
      next: (w) => (this.wallet = w),
      error: (err) => (this.error = err?.error?.detail || 'Could not load wallet'),
    });
    this.api.getWalletLedger().subscribe({
      next: (res) => (this.ledger = res.results || []),
    });
  }

  zar(cents: number) {
    return `R${(cents / 100).toFixed(2)}`;
  }

  payout() {
    this.error = '';
    this.message = '';
    this.api.requestPayout().subscribe({
      next: (p) => {
        this.message = `Payout ${this.zar(p.amount_cents)} · ${p.status}`;
        this.reload();
      },
      error: (err) => (this.error = err?.error?.detail || 'Payout failed'),
    });
  }
}
