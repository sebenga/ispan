import { Injectable, OnDestroy } from '@angular/core';
import { io, Socket } from 'socket.io-client';
import { Observable, Subject } from 'rxjs';

import { environment } from '../../environments/environment';
import { AuthService } from './auth.service';

@Injectable({ providedIn: 'root' })
export class RealtimeService implements OnDestroy {
  private socket: Socket | null = null;
  private readonly events$ = new Subject<{ event: string; payload: any }>();

  constructor(private readonly auth: AuthService) {}

  connect(): Socket | null {
    const token = this.auth.accessToken;
    if (!token) return null;
    if (this.socket?.connected) return this.socket;

    this.socket?.disconnect();
    this.socket = io(environment.realtimeUrl, {
      auth: { token },
      transports: ['websocket', 'polling'],
      autoConnect: true,
    });

    const forward = (event: string) => {
      this.socket?.on(event, (payload) => this.events$.next({ event, payload }));
    };
    [
      'job:location',
      'job:eta',
      'job:chat',
      'job:status',
      'job:accepted',
      'sos:alert',
      'offer:new',
    ].forEach(forward);

    return this.socket;
  }

  disconnect() {
    this.socket?.disconnect();
    this.socket = null;
  }

  watch(): Observable<{ event: string; payload: any }> {
    return this.events$.asObservable();
  }

  joinJob(jobId: string) {
    const socket = this.connect();
    socket?.emit('subscribe', [`job:${jobId}`, `user:${this.auth.currentUser?.id}`]);
  }

  sendLocation(jobId: string, lat: number, lng: number, accuracy_m?: number) {
    this.connect()?.emit('job:location', { job_id: jobId, lat, lng, accuracy_m });
  }

  sendChat(jobId: string, body: string) {
    this.connect()?.emit('job:chat', { job_id: jobId, body });
  }

  triggerSos(jobId: string, lat?: number, lng?: number, note?: string) {
    this.connect()?.emit('sos:trigger', { job_id: jobId, lat, lng, note });
  }

  ngOnDestroy() {
    this.disconnect();
  }
}
