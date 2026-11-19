import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Router } from '@angular/router';
import { BehaviorSubject, tap } from 'rxjs';

import { environment } from '../../environments/environment';

export interface AuthUser {
  id: string;
  email: string;
  phone: string;
  role: 'CUSTOMER' | 'WORKER' | 'ADMIN';
  first_name: string;
  last_name: string;
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
    return this.http.post<AuthUser>(`${environment.apiBaseUrl}/auth/register/`, payload).pipe(
      tap(() => {
        /* register then login */
      }),
    );
  }

  login(email: string, password: string) {
    return this.http
      .post<{ access: string; refresh: string; user: AuthUser }>(
        `${environment.apiBaseUrl}/auth/login/`,
        { email, password },
      )
      .pipe(
        tap((res) => {
          localStorage.setItem('ispan_access', res.access);
          localStorage.setItem('ispan_refresh', res.refresh);
          localStorage.setItem('ispan_user', JSON.stringify(res.user));
          this.user$.next(res.user);
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
