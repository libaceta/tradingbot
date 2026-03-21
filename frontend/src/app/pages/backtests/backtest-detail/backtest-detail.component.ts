import {
  Component, OnInit, OnDestroy, AfterViewInit,
  ElementRef, ViewChild, signal
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, ActivatedRoute } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatTableModule } from '@angular/material/table';
import { createChart, IChartApi, ISeriesApi, ColorType } from 'lightweight-charts';

import { BacktestService } from '../../../core/services/backtest.service';
import { BacktestRun } from '../../../core/models/backtest.model';
import { MetricCardComponent } from '../../../shared/components/metric-card/metric-card.component';
import { MonthlyReturnsComponent } from '../../monthly-returns/monthly-returns.component';

@Component({
  selector: 'app-backtest-detail',
  standalone: true,
  imports: [CommonModule, RouterLink, MatIconModule, MatButtonModule, MatTableModule, MetricCardComponent],
  template: `
    <div class="page-container">
      <div class="page-header" style="display:flex;align-items:center;gap:12px;margin-bottom:20px">
        <a mat-icon-button routerLink="/backtests">
          <mat-icon>arrow_back</mat-icon>
        </a>
        <h1 class="page-title" style="margin:0">
          {{ run()?.run_name || ('Backtest #' + runId) }}
        </h1>
        <span class="badge" *ngIf="run()" [ngClass]="getStatusClass(run()!.status)">{{ run()!.status }}</span>
        <span style="flex:1"></span>
        <div class="run-meta" *ngIf="run()">
          <span>{{ run()!.symbol }}</span> ·
          <span>{{ run()!.start_date }} → {{ run()!.end_date }}</span> ·
          <span>{{ run()!.engine }}</span>
        </div>
      </div>

      <div *ngIf="loading()" class="loading-overlay">Loading backtest results...</div>

      <ng-container *ngIf="run() && !loading()">
        <!-- Metrics grid -->
        <div class="metrics-grid">
          <app-metric-card label="Total Return" [value]="run()!.total_return" format="percent" [colorize]="true" />
          <app-metric-card label="Annualized Return" [value]="run()!.annualized_return" format="percent" [colorize]="true" />
          <app-metric-card label="Sharpe Ratio" [value]="run()!.sharpe_ratio" format="number" [decimals]="3" tooltip="> 1.0 is good" />
          <app-metric-card label="Sortino Ratio" [value]="run()!.sortino_ratio" format="number" [decimals]="3" tooltip="> 2.0 is good" />
          <app-metric-card label="Calmar Ratio" [value]="run()!.calmar_ratio" format="number" [decimals]="3" />
          <app-metric-card label="Max Drawdown" [value]="run()!.max_drawdown ? -run()!.max_drawdown! : null" format="percent" [colorize]="true" />
          <app-metric-card label="Win Rate" [value]="run()!.win_rate" format="number" unit="%" [decimals]="1" [colorize]="true" />
          <app-metric-card label="Profit Factor" [value]="run()!.profit_factor" format="number" [decimals]="2" [colorize]="true" />
          <app-metric-card label="Avg R Multiple" [value]="run()!.avg_r_multiple" format="number" [decimals]="2" [colorize]="true" />
          <app-metric-card label="Total Trades" [value]="run()!.total_trades" format="raw"
            [subtitle]="(run()!.winning_trades || 0) + 'W / ' + (run()!.losing_trades || 0) + 'L'" />
          <app-metric-card label="Final Equity" [value]="run()!.final_equity" format="currency" />
          <app-metric-card label="Total Fees" [value]="run()!.total_fees_usdt" format="currency" />
        </div>

        <!-- Equity curve -->
        <div class="card full-width-card" *ngIf="run()!.equity_curve?.length">
          <div class="card-header"><h3>Equity Curve</h3></div>
          <div #equityChart class="bt-chart"></div>
        </div>

        <!-- Monthly returns heatmap -->
        <div class="card full-width-card" *ngIf="run()!.monthly_returns">
          <div class="card-header"><h3>Monthly Returns</h3></div>
          <div class="monthly-heatmap">
            <div class="heatmap-row">
              <div class="year-col"></div>
              <div class="month-h" *ngFor="let m of monthNames">{{ m }}</div>
            </div>
            <div class="heatmap-row" *ngFor="let year of getYears()">
              <div class="year-col">{{ year }}</div>
              <div class="month-cell"
                *ngFor="let cell of getMonthCells(year)"
                [style.background]="getCellColor(cell.pct)"
                [title]="cell.key + ': ' + (cell.pct != null ? (cell.pct | number:'1.2-2') + '%' : 'N/A')"
              >
                <span *ngIf="cell.pct != null">{{ cell.pct >= 0 ? '+' : '' }}{{ cell.pct | number:'1.1-1' }}%</span>
                <span *ngIf="cell.pct == null" style="color:var(--text-muted)">—</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Parameters -->
        <div class="card full-width-card">
          <div class="card-header"><h3>Strategy Parameters Used</h3></div>
          <div class="params-grid">
            <div class="param-item" *ngFor="let p of paramsList()">
              <span class="param-label">{{ p.label }}</span>
              <span class="param-value">{{ p.value }}</span>
            </div>
          </div>
        </div>
      </ng-container>
    </div>
  `,
  styles: [`
    .run-meta { font-size: 13px; color: var(--text-secondary); }

    .bt-chart { height: 280px; width: 100%; }

    .monthly-heatmap { overflow-x: auto; }
    .heatmap-row { display: flex; gap: 4px; margin-bottom: 4px; align-items: center; }
    .year-col { width: 50px; font-size: 12px; font-weight: 600; color: var(--text-secondary); flex-shrink: 0; }
    .month-h { flex: 1; min-width: 55px; text-align: center; font-size: 11px; color: var(--text-muted); font-weight: 600; }
    .month-cell {
      flex: 1; min-width: 55px; height: 40px;
      border-radius: 4px; display: flex; align-items: center; justify-content: center;
      font-size: 11px; font-weight: 600;
    }

    .params-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
      gap: 8px;
    }

    .param-item {
      display: flex;
      justify-content: space-between;
      padding: 8px 12px;
      background: var(--bg-tertiary);
      border-radius: 6px;

      .param-label { font-size: 12px; color: var(--text-secondary); }
      .param-value { font-size: 12px; font-weight: 600; }
    }
  `],
})
export class BacktestDetailComponent implements OnInit, OnDestroy, AfterViewInit {
  @ViewChild('equityChart') equityChartEl?: ElementRef<HTMLDivElement>;

  monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  runId!: number;
  run = signal<BacktestRun | null>(null);
  loading = signal(true);

  private chart: IChartApi | null = null;

  constructor(
    private route: ActivatedRoute,
    private btService: BacktestService,
  ) {}

  ngOnInit(): void {
    this.runId = Number(this.route.snapshot.paramMap.get('id'));
    this.btService.getBacktest(this.runId).subscribe({
      next: (r) => { this.run.set(r); this.loading.set(false); },
      error: () => this.loading.set(false),
    });
  }

  ngAfterViewInit(): void {
    setTimeout(() => this.initChart(), 100);
  }

  ngOnDestroy(): void {
    this.chart?.remove();
  }

  private initChart(): void {
    if (!this.equityChartEl || !this.run()?.equity_curve?.length) return;

    this.chart = createChart(this.equityChartEl.nativeElement, {
      height: 280,
      layout: { background: { type: ColorType.Solid, color: '#1c2128' }, textColor: '#8b949e' },
      grid: { vertLines: { color: '#21262d' }, horzLines: { color: '#21262d' } },
      timeScale: { timeVisible: true, borderColor: '#30363d' },
      rightPriceScale: { borderColor: '#30363d' },
    });

    const series = this.chart.addAreaSeries({
      lineColor: '#58a6ff',
      topColor: 'rgba(88, 166, 255, 0.25)',
      bottomColor: 'rgba(88, 166, 255, 0)',
      lineWidth: 2,
      priceFormat: { type: 'custom', formatter: (v: number) => `$${v.toFixed(0)}` },
    });

    const data = this.run()!.equity_curve!
      .sort((a, b) => a.time - b.time)
      .map(p => ({ time: Math.floor(p.time / 1000) as any, value: p.value }));

    series.setData(data);
    this.chart.timeScale().fitContent();
  }

  getYears(): number[] {
    const mr = this.run()?.monthly_returns;
    if (!mr) return [];
    const years = [...new Set(Object.keys(mr).map(k => parseInt(k.split('-')[0])))];
    return years.sort();
  }

  getMonthCells(year: number) {
    const mr = this.run()?.monthly_returns || {};
    return Array.from({ length: 12 }, (_, i) => {
      const key = `${year}-${String(i + 1).padStart(2, '0')}`;
      return { key, pct: mr[key] ?? null };
    });
  }

  getCellColor(pct: number | null): string {
    if (pct === null) return 'var(--bg-tertiary)';
    const intensity = Math.min(Math.abs(pct) / 10, 1);
    if (pct >= 0) return `rgba(38, ${Math.round(80 + intensity * 100)}, 65, ${0.2 + intensity * 0.7})`;
    return `rgba(${Math.round(150 + intensity * 100)}, 81, 73, ${0.2 + intensity * 0.7})`;
  }

  paramsList() {
    const r = this.run();
    if (!r) return [];
    return [
      { label: 'EMA Fast', value: r.ema_fast ?? '—' },
      { label: 'EMA Slow', value: r.ema_slow ?? '—' },
      { label: 'Supertrend Period', value: r.st_period ?? '—' },
      { label: 'Supertrend Multiplier', value: r.st_multiplier ?? '—' },
      { label: 'RSI Period', value: r.rsi_period ?? '—' },
      { label: 'RSI Overbought', value: r.rsi_ob ?? '—' },
      { label: 'RSI Oversold', value: r.rsi_os ?? '—' },
      { label: 'Initial Capital', value: `$${r.initial_capital}` },
    ];
  }

  getStatusClass(status: string): string {
    return { done: 'badge-long', running: 'badge-open', pending: 'badge-closed', failed: 'badge-short' }[status] || 'badge-closed';
  }
}
