import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiService } from './api.service';
import { PaginatedTrades } from '../models/trade.model';

export interface TradeFilter {
  symbol?: string;
  status?: string;
  direction?: string;
  date_from?: string;
  date_to?: string;
  is_backtest?: boolean;
  backtest_id?: number;
  page?: number;
  page_size?: number;
}

@Injectable({ providedIn: 'root' })
export class TradeService {
  constructor(private api: ApiService) {}

  getTrades(filter: TradeFilter = {}): Observable<PaginatedTrades> {
    return this.api.get<PaginatedTrades>('/trades', {
      ...filter,
      page: filter.page ?? 1,
      page_size: filter.page_size ?? 50,
    } as Record<string, string | number | boolean | null | undefined>);
  }
}
