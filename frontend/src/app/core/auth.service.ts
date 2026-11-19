import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Router } from '@angular/router';
import { BehaviorSubject, tap } from 'rxjs';

import { environment } from '../../environments/environment';

export interface AuthUser {
  id: string;
  email: string;
  phone: string;
  role: string;
  is_customer?: boolean;
  is_worker?: boolean;
  is_support?: boolean;
  active_profile?: string;
  first_name: string;
  last_name: string;
  email_verified?: boolean;
  phone_verified?: boolean;
}

interface AuthResponse {
  access: string;
  refresh: string;
  user: AuthUser;
  otp?: { hint?: string };
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly user$ = new BehaviorSubject<AuthUser | null>(this.readUser());

  constructor(
    private readonly http: HttpClient,
    private readonly router: Router,
  ) {}

  get currentUser(): AuthUser | null {
    return this.user$.value;
  }

  watch() {
    return this.user$.asObservable();
  }

  get accessToken(): string | null {
    return localStorage.getItem('ispan_access');
  }

  register(payload: Record<string, unknown>) {
    return this.http
      .post<AuthResponse>(`${environment.apiBaseUrl}/auth/register/`, payload)
      .pipe(tap((res) => this.persist(res)));
  }

  login(email: string, password: string) {
    return this.http
      .post<AuthResponse>(`${environment.apiBaseUrl}/auth/login/`, {
        email: email.trim().toLowerCase(),
        password,
      })
      .pipe(tap((res) => this.persist(res)));
  }

  verifyOtp(purpose: string, destination: string, code: string) {
    return this.http.post<{ email_verified?: boolean; phone_verified?: boolean }>(
      `${environment.apiBaseUrl}/auth/otp/verify/`,
      { purpose, destination, code },
      { headers: this.authHeaders() },
    );
  }

  refreshMe() {
    return this.http
      .get<AuthUser>(`${environment.apiBaseUrl}/auth/me/`, { headers: this.authHeaders() })
      .pipe(
        tap((user) => {
          localStorage.setItem('ispan_user', JSON.stringify(user));
          this.user$.next(user);
        }),
      );
  }

  logout() {
    localStorage.removeItem('ispan_access');
    localStorage.removeItem('ispan_refresh');
    localStorage.removeItem('ispan_user');
    this.user$.next(null);
    void this.router.navigateByUrl('/login');
  }

  private persist(res: AuthResponse) {
    localStorage.setItem('ispan_access', res.access);
    localStorage.setItem('ispan_refresh', res.refresh);
    localStorage.setItem('ispan_user', JSON.stringify(res.user));
    this.user$.next(res.user);
  }

  private authHeaders(): HttpHeaders {
    const token = this.accessToken;
    return token
      ? new HttpHeaders({ Authorization: `Bearer ${token}` })
      : new HttpHeaders();
  }

  private readUser(): AuthUser | null {
    const raw = localStorage.getItem('ispan_user');
    if (!raw) return null;
    try {
      return JSON.parse(raw) as AuthUser;
    } catch {
      return null;
    }
  }
}
