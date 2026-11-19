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

  private headers() {
    const token = this.auth.accessToken;
    return token
      ? new HttpHeaders({ Authorization: `Bearer ${token}` })
      : new HttpHeaders();
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

  acceptJob(id: string) {
    return this.http.post<any>(
      `${environment.apiBaseUrl}/jobs/${id}/accept/`,
      {},
      { headers: this.headers() },
    );
  }

  updateJobStatus(id: string, status: string) {
    return this.http.post<any>(
      `${environment.apiBaseUrl}/jobs/${id}/status/`,
      { status },
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
}
