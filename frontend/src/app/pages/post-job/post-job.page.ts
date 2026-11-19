import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import {
  IonBackButton,
  IonButton,
  IonButtons,
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
  ],
  templateUrl: './post-job.page.html',
  styleUrls: ['./post-job.page.scss'],
})
export class PostJobPage implements OnInit {
  categories: any[] = [];
  category_id = '';
  title = '';
  description = '';
  address_line = '';
  suburb = '';
  payment_method: 'ESCROW' | 'CASH' = 'ESCROW';
  budget_rand = 350;
  error = '';
  loading = false;

  constructor(
    private readonly api: ApiService,
    private readonly router: Router,
  ) {}

  ngOnInit() {
    this.api.getCategories().subscribe((cats) => {
      this.categories = cats;
      if (cats[0]) {
        this.category_id = cats[0].id;
        this.budget_rand = Math.round(cats[0].suggested_min_cents / 100);
      }
    });
  }

  onCategoryChange() {
    const cat = this.categories.find((c) => c.id === this.category_id);
    if (cat) this.budget_rand = Math.round(cat.suggested_min_cents / 100);
  }

  submit() {
    this.loading = true;
    this.error = '';
    this.api
      .createJob({
        category_id: this.category_id,
        title: this.title,
        description: this.description,
        payment_method: this.payment_method,
        budget_cents: Math.round(this.budget_rand * 100),
        is_immediate: true,
        address_line: this.address_line,
        suburb: this.suburb,
        city: 'Cape Town',
      })
      .subscribe({
        next: (job) => {
          this.loading = false;
          void this.router.navigateByUrl(`/customer/jobs/${job.id}`);
        },
        error: (err) => {
          this.loading = false;
          this.error = err?.error?.detail || 'Could not create job';
        },
      });
  }
}
