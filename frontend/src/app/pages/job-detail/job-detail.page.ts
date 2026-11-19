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
  IonSelect,
  IonSelectOption,
  IonTitle,
  IonToolbar,
} from '@ionic/angular/standalone';
import { Subscription } from 'rxjs';

import { ApiService } from '../../core/api.service';
import { AuthService } from '../../core/auth.service';
import { RealtimeService } from '../../core/realtime.service';

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
    IonSelect,
    IonSelectOption,
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
  chat: any[] = [];
  chatBody = '';
  location: any = null;
  navigation: { google_maps?: string | null; waze?: string | null } | null = null;
  etaMinutes: number | null = null;
  sosMessage = '';
  testCard: 'succeed' | 'fail' | 'insufficient_funds' | 'webhook_delay' = 'succeed';
  payMessage = '';
  private tickTimer: ReturnType<typeof setInterval> | null = null;
  private pingTimer: ReturnType<typeof setInterval> | null = null;
  private rtSub: Subscription | null = null;

  constructor(
    private readonly route: ActivatedRoute,
    private readonly api: ApiService,
    private readonly auth: AuthService,
    private readonly realtime: RealtimeService,
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
    if (this.pingTimer) clearInterval(this.pingTimer);
    this.rtSub?.unsubscribe();
  }

  reload(id?: string) {
    const jobId = id || this.job?.id;
    if (!jobId) return;
    this.api.getJob(jobId).subscribe({
      next: (job) => {
        this.job = job;
        this.location = job.location;
        this.navigation = job.navigation;
        this.quoteAmount = Math.round((job.budget_cents || 0) / 100);
        this.maybeStartTick();
        this.setupRealtime(jobId);
        this.loadChat(jobId);
        this.maybeStartWorkerPings();
      },
      error: () => void this.router.navigateByUrl('/'),
    });
  }

  private setupRealtime(jobId: string) {
    this.rtSub?.unsubscribe();
    this.realtime.joinJob(jobId);
    this.rtSub = this.realtime.watch().subscribe(({ event, payload }) => {
      if (payload?.job_id && payload.job_id !== jobId) return;
      if (event === 'job:location') {
        this.location = payload;
        this.etaMinutes = payload.eta_minutes ?? this.etaMinutes;
      }
      if (event === 'job:eta') {
        this.etaMinutes = payload.eta_minutes;
      }
      if (event === 'job:chat') {
        this.chat = [...this.chat, payload];
      }
      if (event === 'job:status' || event === 'job:accepted') {
        this.reload(jobId);
      }
      if (event === 'sos:alert') {
        this.sosMessage = payload.disclaimer || 'SOS alert sent.';
      }
    });
  }

  private loadChat(jobId: string) {
    this.api.getChat(jobId).subscribe({
      next: (res) => (this.chat = res.results || []),
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

  private maybeStartWorkerPings() {
    if (this.pingTimer) clearInterval(this.pingTimer);
    if (!this.isWorker || !this.job) return;
    if (!['EN_ROUTE', 'ARRIVED', 'IN_PROGRESS'].includes(this.job.status)) return;
    // Simulated travel toward job coords for demo (device GPS can replace this).
    let t = 0;
    this.pingTimer = setInterval(() => {
      t += 1;
      const baseLat = this.job.lat ?? -33.9249;
      const baseLng = this.job.lng ?? 18.4241;
      const lat = baseLat + 0.008 - t * 0.0008;
      const lng = baseLng - 0.004 + t * 0.0004;
      this.api.postLocation(this.job.id, lat, lng, 15).subscribe({
        next: (payload) => {
          this.location = payload;
          this.etaMinutes = payload.eta_minutes;
        },
        error: () => {
          /* status may have left allowed set */
        },
      });
    }, 4000);
  }

  zar(cents: number | null | undefined) {
    if (cents == null) return '—';
    return `R${(cents / 100).toFixed(0)}`;
  }

  setStatus(status: string) {
    this.error = '';
    this.api.updateJobStatus(this.job.id, status).subscribe({
      next: (job) => {
        this.job = job;
        this.maybeStartWorkerPings();
      },
      error: (err) => (this.error = err?.error?.detail || 'Update failed'),
    });
  }

  accept() {
    this.api.acceptJob(this.job.id).subscribe({
      next: (job) => (this.job = job),
      error: (err) => (this.error = err?.error?.detail || 'Accept failed'),
    });
  }

  sendChat() {
    const body = this.chatBody.trim();
    if (!body) return;
    this.api.postChat(this.job.id, body).subscribe({
      next: (msg) => {
        this.chat = [...this.chat, msg];
        this.chatBody = '';
      },
      error: (err) => (this.error = err?.error?.detail || 'Chat failed'),
    });
  }

  openNav(kind: 'google_maps' | 'waze') {
    const url = this.navigation?.[kind];
    if (url) window.open(url, '_blank');
  }

  payEscrow() {
    this.payMessage = '';
    this.error = '';
    this.api.payEscrow(this.job.id, this.testCard).subscribe({
      next: (res) => {
        this.payMessage = `Payment ${res.payment.status}`;
        this.reload();
      },
      error: (err) => (this.error = err?.error?.detail || 'Payment failed'),
    });
  }

  triggerSos() {
    this.api
      .triggerSos(this.job.id, {
        lat: this.location?.lat ?? this.job.lat,
        lng: this.location?.lng ?? this.job.lng,
        note: 'SOS from app',
      })
      .subscribe({
        next: (res) => (this.sosMessage = res.disclaimer),
        error: (err) => (this.error = err?.error?.detail || 'SOS failed'),
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

  showLiveTrack(): boolean {
    return !!this.job && ['EN_ROUTE', 'ARRIVED', 'IN_PROGRESS'].includes(this.job.status);
  }
}
