import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import {
  IonButton,
  IonButtons,
  IonContent,
  IonHeader,
  IonItem,
  IonLabel,
  IonList,
  IonTextarea,
  IonTitle,
  IonToolbar,
} from '@ionic/angular/standalone';

import { ApiService } from '../../core/api.service';
import { AuthService } from '../../core/auth.service';

@Component({
  selector: 'app-admin-verification',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    IonHeader,
    IonToolbar,
    IonTitle,
    IonContent,
    IonButtons,
    IonButton,
    IonList,
    IonItem,
    IonLabel,
    IonTextarea,
  ],
  templateUrl: './admin-verification.page.html',
  styleUrls: ['./admin-verification.page.scss'],
})
export class AdminVerificationPage implements OnInit {
  rows: any[] = [];
  reasons: Record<string, string> = {};
  error = '';
  loading = false;

  constructor(
    private readonly api: ApiService,
    private readonly auth: AuthService,
    private readonly router: Router,
  ) {}

  ngOnInit() {
    const user = this.auth.currentUser;
    if (!user) {
      void this.router.navigateByUrl('/login');
      return;
    }
    this.reload();
  }

  reload() {
    this.loading = true;
    this.api.adminVerificationQueue().subscribe({
      next: (res) => {
        this.rows = res.results || [];
        this.loading = false;
      },
      error: (err) => {
        this.loading = false;
        this.error = err?.error?.detail || 'Staff access required.';
      },
    });
  }

  approve(id: string) {
    this.api.adminVerificationDecision(id, 'approve').subscribe({
      next: () => this.reload(),
      error: (err) => (this.error = err?.error?.detail || 'Approve failed'),
    });
  }

  reject(id: string) {
    const reason = (this.reasons[id] || '').trim();
    if (!reason) {
      this.error = 'Rejection reason is required.';
      return;
    }
    this.api.adminVerificationDecision(id, 'reject', reason).subscribe({
      next: () => this.reload(),
      error: (err) => (this.error = err?.error?.detail || 'Reject failed'),
    });
  }

  logout() {
    this.auth.logout();
  }
}
