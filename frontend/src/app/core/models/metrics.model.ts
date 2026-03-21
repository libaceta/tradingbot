export interface MetricsSummary {
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  profit_factor: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  calmar_ratio: number;
  max_drawdown: number;
  total_return: number;
  avg_r_multiple: number;
  avg_trade_duration_secs: number;
  total_fees_usdt: number;
  best_trade_pnl: number;
  worst_trade_pnl: number;
  total_pnl: number;
}

export interface ChartPoint {
  time: number;  // Unix ms
  value: number;
}

export interface MonthlyReturns {
  [yearMonth: string]: number;  // "2024-01": 3.2
}
