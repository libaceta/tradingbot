import { Injectable } from '@angular/core';
import { Observable, Subject, timer } from 'rxjs';
import { webSocket, WebSocketSubject } from 'rxjs/webSocket';
import { retryWhen, delayWhen } from 'rxjs/operators';
import { environment } from '../../../environments/environment';

export interface WsEvent {
  type: 'tick' | 'signal' | 'trade_open' | 'trade_close' | 'portfolio' | 'heartbeat';
  data: Record<string, unknown>;
}

@Injectable({ providedIn: 'root' })
export class WebsocketService {
  private ws$: WebSocketSubject<WsEvent> | null = null;
  private messages$ = new Subject<WsEvent>();

  connect(): Observable<WsEvent> {
    if (!this.ws$ || this.ws$.closed) {
      this.ws$ = webSocket<WsEvent>({
        url: environment.wsUrl,
        openObserver: { next: () => console.log('[WS] Connected') },
        closeObserver: { next: () => console.log('[WS] Disconnected') },
      });

      this.ws$.pipe(
        retryWhen(errors => errors.pipe(delayWhen(() => timer(3000))))
      ).subscribe({
        next: (msg) => this.messages$.next(msg),
        error: (err) => console.error('[WS] Error', err),
      });
    }
    return this.messages$.asObservable();
  }

  disconnect(): void {
    this.ws$?.complete();
    this.ws$ = null;
  }
}
