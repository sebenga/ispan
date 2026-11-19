import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import {
  IonBackButton,
  IonBadge,
  IonButton,
  IonButtons,
  IonContent,
  IonHeader,
  IonInput,
  IonItem,
  IonLabel,
  IonList,
  IonSelect,
  IonSelectOption,
  IonTextarea,
  IonTitle,
  IonToolbar,
} from '@ionic/angular/standalone';

import { ApiService } from '../../core/api.service';
import { AuthService } from '../../core/auth.service';

@Component({
  selector: 'app-worker-onboarding',
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
    IonButton,
    IonList,
    IonItem,
    IonInput,
    IonTextarea,
    IonSelect,
    IonSelectOption,
    IonLabel,
    IonBadge,
  ],
  templateUrl: './worker-onboarding.page.html',
  styleUrls: ['./worker-onboarding.page.scss'],
})
export class WorkerOnboardingPage implements OnInit {
  me: any = null;
  bio = '';
  idNumber = '';
  docType: 'sa_id' | 'passport' = 'sa_id';
  idFile: File | null = null;
  holderName = '';
  bankName = '';
  accountNumber = '';
  branchCode = '';
  error = '';
  message = '';
  loading = false;

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
    this.api.getWorkerMe().subscribe({
      next: (data) => {
        this.me = data;
        this.bio = data.bio || '';
        if (data.bank_account) {
          this.holderName = data.bank_account.holder_name || '';
          this.bankName = data.bank_account.bank_name || '';
          this.branchCode = data.bank_account.branch_code || '';
        }
      },
      error: () => {
        this.error = 'Could not load worker profile.';
      },
    });
  }

  onFile(ev: Event) {
    const input = ev.target as HTMLInputElement;
    this.idFile = input.files?.[0] || null;
  }

  saveBio() {
    this.api.patchWorkerMe({ bio: this.bio }).subscribe({
      next: (data) => {
        this.me = data;
        this.message = 'Profile saved.';
      },
      error: (err) => (this.error = err?.error?.detail || 'Save failed'),
    });
  }

  uploadId() {
    if (!this.idFile) {
      this.error = 'Choose an ID or passport file first.';
      return;
    }
    this.loading = true;
    this.error = '';
    const form = new FormData();
    form.append('doc_type', this.docType);
    form.append('file', this.idFile);
    if (this.idNumber) form.append('id_number', this.idNumber);
    this.api.uploadWorkerDocument(form).subscribe({
      next: () => {
        this.loading = false;
        this.message = 'Document uploaded (encrypted at rest).';
        this.reload();
      },
      error: (err) => {
        this.loading = false;
        this.error = err?.error?.detail || 'Upload failed';
      },
    });
  }

  saveBank() {
    this.loading = true;
    this.error = '';
    this.api
      .saveBank({
        holder_name: this.holderName,
        bank_name: this.bankName,
        account_number: this.accountNumber,
        branch_code: this.branchCode,
      })
      .subscribe({
        next: () => {
          this.loading = false;
          this.message = 'Bank details saved.';
          this.accountNumber = '';
          this.reload();
        },
        error: (err) => {
          this.loading = false;
          this.error = err?.error?.detail || 'Bank save failed';
        },
      });
  }

  submit() {
    this.loading = true;
    this.error = '';
    this.api.submitVerification().subscribe({
      next: (data) => {
        this.loading = false;
        this.me = { ...this.me, ...data };
        this.message = 'Submitted for verification. You cannot receive payouts until approved.';
      },
      error: (err) => {
        this.loading = false;
        this.error = err?.error?.detail || 'Submit failed';
      },
    });
  }
}
