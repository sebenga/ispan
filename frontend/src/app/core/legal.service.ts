import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';

import { environment } from '../../environments/environment';

const STORAGE_KEY = 'ispan_legal_consent';

@Injectable({ providedIn: 'root' })
export class LegalService {
  constructor(private readonly http: HttpClient) {}

  hasAccepted(version: string): boolean {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return false;
      const parsed = JSON.parse(raw) as { version?: string };
      return parsed.version === version;
    } catch {
      return false;
    }
  }

  rememberLocal(version: string, flags: Record<string, boolean>) {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ version, flags, accepted_at: new Date().toISOString() }),
    );
  }

  private get legalBase() {
    return environment.legalApiBaseUrl || environment.apiBaseUrl.replace(/\/v1\/?$/, '');
  }

  getVersion() {
    return this.http.get<{
      version: string;
      documents: string[];
      required_flags: string[];
    }>(`${this.legalBase}/legal/version/`);
  }

  getDocument(slug: string) {
    return this.http.get<{ title: string; body: string; version: string; draft: boolean }>(
      `${this.legalBase}/legal/documents/${slug}/`,
    );
  }

  submitConsent(version: string, flags: Record<string, boolean>) {
    let anon_id = localStorage.getItem('ispan_anon_id');
    if (!anon_id) {
      anon_id = crypto.randomUUID();
      localStorage.setItem('ispan_anon_id', anon_id);
    }
    return this.http.post(`${this.legalBase}/legal/consent/`, {
      version,
      flags,
      anon_id,
    });
  }
}
