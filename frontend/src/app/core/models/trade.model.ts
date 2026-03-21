export interface Trade {
  id: number;
  external_id: string;
  symbol: string;
  direction: 'LONG' | 'SHORT';
  status: 'OPEN' | 'CLOSED' | 'CANCELLED';
  entry_time: string | null;
  exit_time: string | null;
  entry_price: number | null;
  exit_price: number | null;
  quantity: number;
  notional_usdt: number | null;
  stop_loss: number | null;
  take_profit: number | null;
  gross_pnl: number | null;
  net_pnl: number | null;
  pnl_pct: number | null;
  r_multiple: number | null;
  duration_secs: number | null;
  exit_reason: string | null;
  entry_fee: number | null;
  exit_fee: number | null;
  risk_usdt: number | null;
  atr_at_entry: number | null;
  is_backtest: boolean;
  backtest_id: number | null;
  signal_id: number | null;
}

export interface PaginatedTrades {
  items: Trade[];
  total: number;
  page: number;
  pages: number;
}
