import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import {
  IonBadge,
  IonButton,
  IonCheckbox,
  IonContent,
  IonIcon,
  IonItem,
  IonList,
} from '@ionic/angular/standalone';
import { addIcons } from 'ionicons';
import { volumeHighOutline, volumeMuteOutline } from 'ionicons/icons';

import { environment } from '../../../environments/environment';
import { LegalService } from '../../core/legal.service';
import { SoundService } from '../../core/sound.service';

addIcons({ volumeHighOutline, volumeMuteOutline });

@Component({
  selector: 'app-legal-gate',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterLink,
    IonContent,
    IonList,
    IonItem,
    IonCheckbox,
    IonButton,
    IonIcon,
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
    readonly sound: SoundService,
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

  onScroll(_ev: CustomEvent) {
    this.scrolled = true;
  }

  toggleSound(ev: Event) {
    ev.stopPropagation();
    this.sound.toggleMute();
    if (!this.sound.muted) this.sound.tap();
  }

  scrollToConsent() {
    this.sound.unlock();
    this.sound.softWhoosh();
    document.getElementById('consent')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    this.scrolled = true;
  }

  markRead(_doc: string) {
    this.scrolled = true;
    this.sound.tap();
  }

  onCheck() {
    this.sound.tap();
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
        this.sound.success();
        void this.router.navigateByUrl('/login');
      },
      error: (err) => {
        if (err?.status === 0 || err?.status >= 500) {
          this.legal.rememberLocal(this.version, flags);
          this.loading = false;
          this.sound.success();
          void this.router.navigateByUrl('/login');
          return;
        }
        this.loading = false;
        this.error = err?.error?.detail || 'Could not save consent.';
      },
    });
  }
}
