import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import {
  IonBackButton,
  IonButton,
  IonButtons,
  IonCheckbox,
  IonContent,
  IonHeader,
  IonInput,
  IonItem,
  IonList,
  IonSelect,
  IonSelectOption,
  IonTextarea,
  IonTitle,
  IonToolbar,
} from '@ionic/angular/standalone';

import { ApiService } from '../../core/api.service';

@Component({
  selector: 'app-post-job',
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
    IonList,
    IonItem,
    IonInput,
    IonTextarea,
    IonSelect,
    IonSelectOption,
    IonButton,
    IonCheckbox,
  ],
  templateUrl: './post-job.page.html',
  styleUrls: ['./post-job.page.scss'],
})
export class PostJobPage implements OnInit {
  categories: any[] = [];
  flatCategories: any[] = [];
  category_id = '';
  title = '';
  description = '';
  address_line = '';
  suburb = '';
  payment_method: 'ESCROW' | 'CASH' = 'ESCROW';
  budget_rand = 350;
  mode: 'instant' | 'scheduled' = 'instant';
  scheduled_at = '';
  women_preferred = false;
  accept_cancellation_policy = false;
  policyText = '';
  error = '';
  loading = false;

  constructor(
    private readonly api: ApiService,
    private readonly router: Router,
  ) {}

  ngOnInit() {
    this.api.getCategories().subscribe((cats) => {
      this.categories = cats;
      this.flatCategories = [];
      for (const c of cats) {
        this.flatCategories.push(c);
        for (const child of c.children || []) {
          this.flatCategories.push({
            ...child,
            name: `${c.name} · ${child.name}`,
          });
        }
      }
      if (this.flatCategories[0]) {
        this.category_id = this.flatCategories[0].id;
        this.onCategoryChange();
      }
    });
  }

  onCategoryChange() {
    const cat = this.flatCategories.find((c) => c.id === this.category_id);
    if (!cat) return;
    this.budget_rand = Math.round(cat.suggested_min_cents / 100);
    const pct = (cat.cancel_fee_bps || 5000) / 100;
    const hours = (cat.cancel_window_minutes || 120) / 60;
    this.policyText =
      `Free cancellation until ${hours} hours before the scheduled start ` +
      `(or before a worker accepts an instant job). After that, a late fee of ${pct}% ` +
      `of the agreed amount applies. Workers set their own rates — the budget band is a suggestion.`;
  }

  submit() {
    if (!this.accept_cancellation_policy) {
      this.error = 'Please acknowledge the cancellation policy.';
      return;
    }
    this.loading = true;
    this.error = '';
    const payload: Record<string, unknown> = {
      category_id: this.category_id,
      title: this.title,
      description: this.description,
      payment_method: this.payment_method,
      budget_cents: Math.round(this.budget_rand * 100),
      mode: this.mode,
      is_immediate: this.mode === 'instant',
      address_line: this.address_line,
      suburb: this.suburb,
      city: 'Cape Town',
      lat: -33.9249,
      lng: 18.4241,
      women_preferred: this.women_preferred,
      accept_cancellation_policy: true,
    };
    if (this.mode === 'scheduled' && this.scheduled_at) {
      payload['scheduled_at'] = new Date(this.scheduled_at).toISOString();
    }
    this.api.createJob(payload).subscribe({
      next: (job) => {
        this.loading = false;
        if (job.pins?.start_pin) {
          localStorage.setItem(
            `ispan_pins_${job.id}`,
            JSON.stringify(job.pins),
          );
        }
        void this.router.navigateByUrl(`/customer/jobs/${job.id}`);
      },
      error: (err) => {
        this.loading = false;
        this.error =
          err?.error?.accept_cancellation_policy?.[0] ||
          err?.error?.detail ||
          'Could not create job';
      },
    });
  }
}
