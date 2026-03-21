export interface BacktestRun {
  id: number;
  run_name: string | null;
  engine: string;
  symbol: string;
  interval: string;
  start_date: string;
  end_date: string;
  initial_capital: number;
  status: 'pending' | 'running' | 'done' | 'failed';
  created_at: string;
  completed_at: string | null;
  // Parameters
  ema_fast: number | null;
  ema_slow: number | null;
  st_period: number | null;
  st_multiplier: number | null;
  rsi_period: number | null;
  rsi_ob: number | null;
  rsi_os: number | null;
  // Metrics
  total_trades: number | null;
  winning_trades: number | null;
  losing_trades: number | null;
  win_rate: number | null;
  total_return: number | null;
  annualized_return: number | null;
  max_drawdown: number | null;
  sharpe_ratio: number | null;
  sortino_ratio: number | null;
  calmar_ratio: number | null;
  profit_factor: number | null;
  avg_r_multiple: number | null;
  final_equity: number | null;
  total_fees_usdt: number | null;
  // JSONB curves (only in detail view)
  equity_curve?: Array<{time: number; value: number}>;
  monthly_returns?: {[key: string]: number};
}

export interface BacktestRunRequest {
  engine: string;
  symbol: string;
  interval: string;
  start_date: string;
  end_date: string;
  initial_capital: number;
  params: Record<string, unknown>;
  param_ranges?: Record<string, number[]> | null;
  run_name?: string;
}
