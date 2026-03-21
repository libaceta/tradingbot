import { Injectable, signal } from '@angular/core';
import { ApiService } from './api.service';
import { BotStatus } from '../models/status.model';

@Injectable({ providedIn: 'root' })
export class StatusService {
  status = signal<BotStatus | null>(null);
  private _interval: ReturnType<typeof setInterval> | null = null;

  constructor(private api: ApiService) {}

  startPolling(intervalMs = 10000): void {
    this.refresh();
    this._interval = setInterval(() => this.refresh(), intervalMs);
  }

  private refresh(): void {
    this.api.get<BotStatus>('/status').subscribe({
      next: (s) => this.status.set(s),
      error: () => {},
    });
  }

  pause() {
    return this.api.post('/status/pause', {});
  }

  resume() {
    return this.api.post('/status/resume', {});
  }
}
