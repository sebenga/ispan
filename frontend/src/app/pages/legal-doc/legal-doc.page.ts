import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import {
  IonBackButton,
  IonButtons,
  IonContent,
  IonHeader,
  IonTitle,
  IonToolbar,
  IonNote,
} from '@ionic/angular/standalone';

import { LegalService } from '../../core/legal.service';

@Component({
  selector: 'app-legal-doc',
  standalone: true,
  imports: [
    CommonModule,
    IonHeader,
    IonToolbar,
    IonTitle,
    IonContent,
    IonButtons,
    IonBackButton,
    IonNote,
  ],
  template: `
    <ion-header>
      <ion-toolbar color="dark">
        <ion-buttons slot="start">
          <ion-back-button defaultHref="/legal"></ion-back-button>
        </ion-buttons>
        <ion-title>{{ title || 'Legal' }}</ion-title>
      </ion-toolbar>
    </ion-header>
    <ion-content class="ion-padding">
      <ion-note *ngIf="draft">Draft for counsel review · version {{ version }}</ion-note>
      <pre class="body">{{ body }}</pre>
    </ion-content>
  `,
  styles: [
    `
      .body {
        white-space: pre-wrap;
        font-family: inherit;
        line-height: 1.5;
        font-size: 0.95rem;
      }
    `,
  ],
})
export class LegalDocPage implements OnInit {
  title = '';
  body = '';
  version = '';
  draft = true;

  constructor(
    private readonly route: ActivatedRoute,
    private readonly legal: LegalService,
  ) {}

  ngOnInit() {
    const slug =
      (this.route.snapshot.data['slug'] as string) ||
      this.route.snapshot.paramMap.get('slug') ||
      'terms';
    this.legal.getDocument(slug).subscribe({
      next: (doc) => {
        this.title = doc.title;
        this.body = doc.body;
        this.version = doc.version;
        this.draft = doc.draft;
      },
      error: () => {
        this.title = 'Unavailable';
        this.body = 'Could not load this document. Check that the API is running.';
      },
    });
  }
}
