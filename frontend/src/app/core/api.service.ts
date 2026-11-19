import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable } from '@angular/core';

import { environment } from '../../environments/environment';
import { AuthService } from './auth.service';

@Injectable({ providedIn: 'root' })
export class ApiService {
  constructor(
    private readonly http: HttpClient,
    private readonly auth: AuthService,
  ) {}

  private headers(extra?: Record<string, string>) {
    const token = this.auth.accessToken;
    const base = token ? { Authorization: `Bearer ${token}` } : {};
    return new HttpHeaders({ ...base, ...extra });
  }

  getCategories() {
    return this.http.get<any[]>(`${environment.apiBaseUrl}/categories/`, {
      headers: this.headers(),
    });
  }

  getJobs(status?: string) {
    const q = status ? `?status=${status}` : '';
    return this.http.get<any[]>(`${environment.apiBaseUrl}/jobs/${q}`, {
      headers: this.headers(),
    });
  }

  getJob(id: string) {
    return this.http.get<any>(`${environment.apiBaseUrl}/jobs/${id}/`, {
      headers: this.headers(),
    });
  }

  createJob(payload: Record<string, unknown>) {
    return this.http.post<any>(`${environment.apiBaseUrl}/jobs/`, payload, {
      headers: this.headers(),
    });
  }

  cancelJob(id: string, preview = false) {
    return this.http.post<any>(
      `${environment.apiBaseUrl}/jobs/${id}/cancel/`,
      preview ? { preview: true } : {},
      { headers: this.headers() },
    );
  }

  acceptJob(id: string) {
    return this.http.post<any>(
      `${environment.apiBaseUrl}/jobs/${id}/accept/`,
      {},
      { headers: this.headers() },
    );
  }

  acceptOffer(jobId: string, offerId: string) {
    return this.http.post<any>(
      `${environment.apiBaseUrl}/jobs/${jobId}/offers/${offerId}/accept/`,
      {},
      { headers: this.headers() },
    );
  }

  declineOffer(jobId: string, offerId: string) {
    return this.http.post<any>(
      `${environment.apiBaseUrl}/jobs/${jobId}/offers/${offerId}/decline/`,
      {},
      { headers: this.headers() },
    );
  }

  myOffers() {
    return this.http.get<{ results: any[] }>(`${environment.apiBaseUrl}/jobs/offers/mine/`, {
      headers: this.headers(),
    });
  }

  tickMatch(jobId: string) {
    return this.http.post<any>(
      `${environment.apiBaseUrl}/jobs/${jobId}/match/tick/`,
      {},
      { headers: this.headers() },
    );
  }

  createQuote(jobId: string, amount_cents: number, message = '') {
    return this.http.post<any>(
      `${environment.apiBaseUrl}/jobs/${jobId}/quotes/`,
      { amount_cents, message },
      { headers: this.headers() },
    );
  }

  acceptQuote(jobId: string, quoteId: string) {
    return this.http.post<any>(
      `${environment.apiBaseUrl}/jobs/${jobId}/quotes/${quoteId}/accept/`,
      {},
      { headers: this.headers() },
    );
  }

  updateJobStatus(id: string, status: string, pin?: string) {
    return this.http.post<any>(
      `${environment.apiBaseUrl}/jobs/${id}/status/`,
      { status, pin },
      { headers: this.headers() },
    );
  }

  getWorkerProfile() {
    return this.http.get<any>(`${environment.apiBaseUrl}/auth/worker/profile/`, {
      headers: this.headers(),
    });
  }

  updateWorkerProfile(payload: Record<string, unknown>) {
    return this.http.patch<any>(`${environment.apiBaseUrl}/auth/worker/profile/`, payload, {
      headers: this.headers(),
    });
  }

  getWorkerMe() {
    return this.http.get<any>(`${environment.apiBaseUrl}/workers/me/`, {
      headers: this.headers(),
    });
  }

  patchWorkerMe(payload: Record<string, unknown>) {
    return this.http.patch<any>(`${environment.apiBaseUrl}/workers/me/`, payload, {
      headers: this.headers(),
    });
  }

  uploadWorkerDocument(form: FormData) {
    return this.http.post<any>(`${environment.apiBaseUrl}/workers/me/documents/`, form, {
      headers: this.headers(),
    });
  }

  saveBank(payload: Record<string, unknown>) {
    return this.http.put<any>(`${environment.apiBaseUrl}/workers/me/bank/`, payload, {
      headers: this.headers(),
    });
  }

  addCertificate(form: FormData) {
    return this.http.post<any>(`${environment.apiBaseUrl}/workers/me/certificates/`, form, {
      headers: this.headers(),
    });
  }

  submitVerification() {
    return this.http.post<any>(
      `${environment.apiBaseUrl}/workers/me/submit/`,
      {},
      { headers: this.headers() },
    );
  }

  adminVerificationQueue() {
    return this.http.get<{ results: any[] }>(`${environment.apiBaseUrl}/admin/verification/`, {
      headers: this.headers(),
    });
  }

  adminVerificationDecision(workerId: string, decision: 'approve' | 'reject', reason = '') {
    return this.http.post<any>(
      `${environment.apiBaseUrl}/admin/verification/${workerId}/`,
      { decision, reason },
      { headers: this.headers() },
    );
  }
}
