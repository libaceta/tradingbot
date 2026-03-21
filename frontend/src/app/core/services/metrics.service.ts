import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';
import { MetricsSummary, ChartPoint, MonthlyReturns } from '../models/metrics.model';
import { Portfolio } from '../models/status.model';

@Injectable({ providedIn: 'root' })
export class MetricsService {
  constructor(private api: ApiService) {}

  getSummary(): Observable<MetricsSummary> {
    return this.api.get<MetricsSummary>('/metrics/summary');
  }

  getEquityCurve(): Observable<ChartPoint[]> {
    return this.api.get<ChartPoint[]>('/portfolio/equity-curve');
  }

  getDrawdown(): Observable<ChartPoint[]> {
    return this.api.get<ChartPoint[]>('/portfolio/drawdown');
  }

  getPortfolio(): Observable<Portfolio> {
    return this.api.get<Portfolio>('/portfolio/current');
  }

  getMonthlyReturns(year?: number): Observable<MonthlyReturns> {
    return this.api.get<MonthlyReturns>('/portfolio/monthly-returns', year ? { year } : {});
  }

  getByMonth(): Observable<Array<{year_month: string; pnl: number; trade_count: number; win_rate: number}>> {
    return this.api.get('/metrics/by-month');
  }
}
