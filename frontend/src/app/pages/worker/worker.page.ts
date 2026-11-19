import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import {
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
  selector: 'app-worker',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    IonHeader,
    IonToolbar,
    IonTitle,
    IonContent,
    IonButtons,
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
  openJobs: any[] = [];
  myJobs: any[] = [];
  name = '';

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
    this.name = user.first_name;
    this.reload();
  }

  reload() {
    this.api.getJobs().subscribe((jobs) => {
      this.openJobs = jobs.filter((j) => j.status === 'OPEN' && !j.worker);
      this.myJobs = jobs.filter((j) => j.worker?.id === this.auth.currentUser?.id);
    });
  }

  zar(cents: number) {
    return `R${(cents / 100).toFixed(0)}`;
  }

  accept(id: string) {
    this.api.acceptJob(id).subscribe(() => {
      void this.router.navigateByUrl(`/worker/jobs/${id}`);
    });
  }

  logout() {
    this.auth.logout();
  }
}
