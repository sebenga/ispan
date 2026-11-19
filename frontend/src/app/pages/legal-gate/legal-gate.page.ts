import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import {
  IonButton,
  IonCheckbox,
  IonContent,
  IonHeader,
  IonIcon,
  IonItem,
  IonLabel,
  IonList,
  IonTitle,
  IonToolbar,
  IonNote,
  IonBadge,
} from '@ionic/angular/standalone';

import { environment } from '../../../environments/environment';
import { LegalService } from '../../core/legal.service';

@Component({
  selector: 'app-legal-gate',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterLink,
    IonHeader,
    IonToolbar,
    IonTitle,
    IonContent,
    IonList,
    IonItem,
    IonLabel,
    IonCheckbox,
    IonButton,
    IonIcon,
    IonNote,
    IonBadge,
  ],
  templateUrl: './legal-gate.page.html',
  styleUrls: ['./legal-gate.page.scss'],
})
export class LegalGatePage implements OnInit {
  version = environment.legalVersion;
  age18 = false;
  terms = false;
  privacy = false;
  scrolled = false;
  error = '';
  loading = false;
  paymentTestMode = environment.paymentTestMode;

  constructor(
    private readonly legal: LegalService,
    private readonly router: Router,
  ) {}

  ngOnInit() {
    if (this.legal.hasAccepted(this.version)) {
      void this.router.navigateByUrl('/login');
      return;
    }
    this.legal.getVersion().subscribe({
      next: (v) => (this.version = v.version),
      error: () => {
        /* offline: still allow local version */
      },
    });
  }

  onScroll(ev: CustomEvent) {
    const el = ev.detail?.scrollTop != null ? ev.target : null;
    // Mark acknowledgement once the user has scrolled the notice area.
    this.scrolled = true;
  }

  get canAccept(): boolean {
    return this.age18 && this.terms && this.privacy && this.scrolled;
  }

  accept() {
    if (!this.age18) {
      this.error = 'You must be 18 or over to use iSpan.';
      return;
    }
    if (!this.canAccept) {
      this.error = 'Please read the notices and tick all boxes.';
      return;
    }
    this.loading = true;
    this.error = '';
    const flags = { age_18: this.age18, terms: this.terms, privacy: this.privacy };
    this.legal.submitConsent(this.version, flags).subscribe({
      next: () => {
        this.legal.rememberLocal(this.version, flags);
        this.loading = false;
        void this.router.navigateByUrl('/login');
      },
      error: (err) => {
        // Persist locally even if API is briefly unavailable, so the gate is not stuck.
        if (err?.status === 0 || err?.status >= 500) {
          this.legal.rememberLocal(this.version, flags);
          this.loading = false;
          void this.router.navigateByUrl('/login');
          return;
        }
        this.loading = false;
        this.error = err?.error?.detail || 'Could not save consent.';
      },
    });
  }
}
