import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
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
  IonTitle,
  IonToolbar,
} from '@ionic/angular/standalone';

import { ApiService } from '../../core/api.service';
import { AuthService } from '../../core/auth.service';

@Component({
  selector: 'app-job-detail',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    IonHeader,
    IonToolbar,
    IonTitle,
    IonContent,
    IonButtons,
    IonBackButton,
    IonBadge,
    IonList,
    IonItem,
    IonLabel,
    IonButton,
    IonInput,
  ],
  templateUrl: './job-detail.page.html',
  styleUrls: ['./job-detail.page.scss'],
})
export class JobDetailPage implements OnInit, OnDestroy {
  job: any = null;
  role: string | null = null;
  isWorker = false;
  isCustomer = false;
  error = '';
  pins: { start_pin?: string; finish_pin?: string } | null = null;
  quoteAmount = 0;
  quoteMessage = '';
  cancelPreview: any = null;
  private tickTimer: ReturnType<typeof setInterval> | null = null;

  constructor(
    private readonly route: ActivatedRoute,
    private readonly api: ApiService,
    private readonly auth: AuthService,
    private readonly router: Router,
  ) {}

  ngOnInit() {
    const user = this.auth.currentUser;
    this.role = user?.role ?? null;
    this.isWorker = !!(user?.is_worker || user?.role === 'WORKER' || user?.active_profile === 'WORKER');
    this.isCustomer = !!(user?.is_customer || user?.role === 'CUSTOMER');
    const id = this.route.snapshot.paramMap.get('id');
    if (!id) return;
    const stored = localStorage.getItem(`ispan_pins_${id}`);
    if (stored) {
      try {
        this.pins = JSON.parse(stored);
      } catch {
        this.pins = null;
      }
    }
    this.reload(id);
  }

  ngOnDestroy() {
    if (this.tickTimer) clearInterval(this.tickTimer);
  }

  reload(id?: string) {
    const jobId = id || this.job?.id;
    if (!jobId) return;
    this.api.getJob(jobId).subscribe({
      next: (job) => {
        this.job = job;
        this.quoteAmount = Math.round((job.budget_cents || 0) / 100);
        this.maybeStartTick();
      },
      error: () => void this.router.navigateByUrl('/'),
    });
  }

  private maybeStartTick() {
    if (this.tickTimer) clearInterval(this.tickTimer);
    if (
      this.isCustomer &&
      this.job &&
      (this.job.status === 'REQUESTED' || this.job.status === 'OFFERED') &&
      this.job.mode === 'instant'
    ) {
      this.tickTimer = setInterval(() => {
        this.api.tickMatch(this.job.id).subscribe({
          next: (res) => (this.job = res.job),
        });
      }, 5000);
    }
  }

  zar(cents: number | null | undefined) {
    if (cents == null) return '—';
    return `R${(cents / 100).toFixed(0)}`;
  }

  setStatus(status: string) {
    this.error = '';
    this.api.updateJobStatus(this.job.id, status).subscribe({
      next: (job) => (this.job = job),
      error: (err) => (this.error = err?.error?.detail || 'Update failed'),
    });
  }

  accept() {
    this.api.acceptJob(this.job.id).subscribe({
      next: (job) => (this.job = job),
      error: (err) => (this.error = err?.error?.detail || 'Accept failed'),
    });
  }

  submitQuote() {
    this.api
      .createQuote(this.job.id, Math.round(this.quoteAmount * 100), this.quoteMessage)
      .subscribe({
        next: () => this.reload(),
        error: (err) => (this.error = err?.error?.detail || 'Quote failed'),
      });
  }

  acceptQuote(qid: string) {
    this.api.acceptQuote(this.job.id, qid).subscribe({
      next: (job) => (this.job = job),
      error: (err) => (this.error = err?.error?.detail || 'Could not accept quote'),
    });
  }

  previewCancel() {
    this.api.cancelJob(this.job.id, true).subscribe({
      next: (snap) => (this.cancelPreview = snap),
      error: (err) => (this.error = err?.error?.detail || 'Preview failed'),
    });
  }

  confirmCancel() {
    this.api.cancelJob(this.job.id).subscribe({
      next: (job) => {
        this.job = job;
        this.cancelPreview = null;
      },
      error: (err) => (this.error = err?.error?.detail || 'Cancel failed'),
    });
  }

  workerActions(): { label: string; status: string }[] {
    const map: Record<string, { label: string; status: string }[]> = {
      ACCEPTED: [{ label: 'Mark en route', status: 'EN_ROUTE' }],
      EN_ROUTE: [{ label: 'Mark arrived', status: 'ARRIVED' }],
      ARRIVED: [{ label: 'Start job (needs customer PIN)', status: 'IN_PROGRESS' }],
      IN_PROGRESS: [{ label: 'Complete (needs finish PIN)', status: 'COMPLETED' }],
    };
    return map[this.job?.status] || [];
  }

  looking(): boolean {
    return (
      this.isCustomer &&
      this.job &&
      (this.job.status === 'REQUESTED' || this.job.status === 'OFFERED') &&
      this.job.mode === 'instant'
    );
  }
}
