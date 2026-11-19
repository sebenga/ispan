import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import {
  IonBadge,
  IonButton,
  IonContent,
  IonItem,
  IonLabel,
  IonList,
} from '@ionic/angular/standalone';

import { ApiService } from '../../core/api.service';
import { AuthService } from '../../core/auth.service';
import { SoundService } from '../../core/sound.service';

@Component({
  selector: 'app-worker',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    IonContent,
    IonButton,
    IonList,
    IonItem,
    IonLabel,
    IonBadge,
  ],
  templateUrl: './worker.page.html',
  styleUrls: ['./worker.page.scss'],
})
export class WorkerPage implements OnInit {
  offers: any[] = [];
  myJobs: any[] = [];
  name = '';
  error = '';

  constructor(
    private readonly api: ApiService,
    private readonly auth: AuthService,
    private readonly router: Router,
    private readonly sound: SoundService,
  ) {}

  ngOnInit() {
    const user = this.auth.currentUser;
    if (!user) {
      void this.router.navigateByUrl('/login');
      return;
    }
    this.name = user.first_name;
    this.sound.unlock();
    this.reload();
  }

  reload() {
    this.api.myOffers().subscribe({
      next: (res) => {
        this.offers = (res.results || []).filter((o) =>
          ['notified', 'seen'].includes(o.status),
        );
      },
    });
    this.api.getJobs().subscribe((jobs) => {
      this.myJobs = jobs.filter((j) => j.worker?.id === this.auth.currentUser?.id);
    });
  }

  zar(cents: number) {
    return `R${(cents / 100).toFixed(0)}`;
  }

  tap() {
    this.sound.tap();
  }

  acceptOffer(offer: any) {
    this.error = '';
    this.sound.tap();
    this.api.acceptOffer(offer.job.id, offer.id).subscribe({
      next: (job) => {
        this.sound.success();
        void this.router.navigateByUrl(`/worker/jobs/${job.id}`);
      },
      error: (err) => {
        this.error = err?.error?.detail || 'Accept failed';
        this.reload();
      },
    });
  }

  declineOffer(offer: any) {
    this.sound.tap();
    this.api.declineOffer(offer.job.id, offer.id).subscribe({
      next: () => this.reload(),
      error: (err) => (this.error = err?.error?.detail || 'Decline failed'),
    });
  }

  logout() {
    this.sound.tap();
    this.auth.logout();
  }
}
