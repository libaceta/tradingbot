export interface BotStatus {
  bot_running: boolean;
  mode: 'testnet' | 'live' | 'paused';
  uptime_secs: number;
  open_positions: Position[];
  equity_usdt: number;
  is_halted: boolean;
  halt_reason: string;
}

export interface Position {
  symbol: string;
  side: string;
  size: number;
  avg_price: number;
  unrealized_pnl: number;
}

export interface Portfolio {
  equity_usdt: number;
  available_usdt: number;
  unrealized_pnl: number;
  open_positions: number;
  drawdown_pct: number;
  peak_equity: number;
  snapshot_time: string;
}
