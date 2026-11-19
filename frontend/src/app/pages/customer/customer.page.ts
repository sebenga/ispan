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
  selector: 'app-customer',
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
  templateUrl: './customer.page.html',
  styleUrls: ['./customer.page.scss'],
})
export class CustomerPage implements OnInit {
  jobs: any[] = [];
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
    this.api.getJobs().subscribe((jobs) => (this.jobs = jobs));
  }

  zar(cents: number) {
    return `R${(cents / 100).toFixed(0)}`;
  }

  logout() {
    this.auth.logout();
  }
}
