import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
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

@Component({
  selector: 'app-job-detail',
  standalone: true,
  imports: [
    CommonModule,
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
  ],
  templateUrl: './job-detail.page.html',
  styleUrls: ['./job-detail.page.scss'],
})
export class JobDetailPage implements OnInit {
  job: any = null;
  role: string | null = null;
  error = '';

  constructor(
    private readonly route: ActivatedRoute,
    private readonly api: ApiService,
    private readonly auth: AuthService,
    private readonly router: Router,
  ) {}

  ngOnInit() {
    this.role = this.auth.currentUser?.role ?? null;
    const id = this.route.snapshot.paramMap.get('id');
    if (!id) return;
    this.api.getJob(id).subscribe({
      next: (job) => (this.job = job),
      error: () => void this.router.navigateByUrl('/'),
    });
  }

  zar(cents: number) {
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

  workerActions(): { label: string; status: string }[] {
    const map: Record<string, { label: string; status: string }[]> = {
      ACCEPTED: [{ label: 'Mark en route', status: 'EN_ROUTE' }],
      EN_ROUTE: [{ label: 'Start job', status: 'IN_PROGRESS' }],
      IN_PROGRESS: [{ label: 'Request confirmation', status: 'AWAITING_CONFIRMATION' }],
    };
    return map[this.job?.status] || [];
  }
}
