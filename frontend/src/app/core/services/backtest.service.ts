import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';
import { BacktestRun, BacktestRunRequest } from '../models/backtest.model';

@Injectable({ providedIn: 'root' })
export class BacktestService {
  constructor(private api: ApiService) {}

  getBacktests(symbol?: string, engine?: string, page = 1): Observable<{items: BacktestRun[]; total: number; page: number}> {
    return this.api.get('/backtests', { symbol, engine, page, page_size: 20 });
  }

  getBacktest(id: number): Observable<BacktestRun> {
    return this.api.get<BacktestRun>(`/backtests/${id}`);
  }

  getStatus(id: number): Observable<{run_id: number; status: string; error_message: string | null}> {
    return this.api.get(`/backtests/${id}/status`);
  }

  getTrades(id: number, page = 1) {
    return this.api.get(`/backtests/${id}/trades`, { page, page_size: 50 });
  }

  getLeaderboard(symbol?: string): Observable<BacktestRun[]> {
    return this.api.get('/backtests/leaderboard', { symbol, limit: 20 });
  }

  runBacktest(req: BacktestRunRequest): Observable<{status: string; message: string}> {
    return this.api.post('/backtests/run', req);
  }
}
