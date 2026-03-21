import {
  Component, OnInit, OnDestroy, AfterViewInit,
  ElementRef, ViewChild, ChangeDetectionStrategy, signal, computed
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatTableModule } from '@angular/material/table';
import { Subscription } from 'rxjs';
import { createChart, IChartApi, ISeriesApi, ColorType, LineStyle } from 'lightweight-charts';

import { MetricCardComponent } from '../../shared/components/metric-card/metric-card.component';
import { MetricsService } from '../../core/services/metrics.service';
import { MetricsSummary, ChartPoint } from '../../core/models/metrics.model';
import { Portfolio, BotStatus } from '../../core/models/status.model';
import { StatusService } from '../../core/services/status.service';
import { WebsocketService } from '../../core/services/websocket.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, MatIconModule, MatButtonModule, MatTableModule, MetricCardComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="page-container">
      <div class="page-header">
        <h1 class="page-title">Dashboard</h1>
        <div class="header-actions">
          <span class="last-update">Updated {{ lastUpdate() }}</span>
          <button mat-stroked-button (click)="refresh()" class="refresh-btn">
            <mat-icon>refresh</mat-icon> Refresh
          </button>
        </div>
      </div>

      <!-- Metrics row -->
      <div class="metrics-grid">
        <app-metric-card label="Sharpe Ratio" [value]="metrics()?.sharpe_ratio ?? null"
          format="number" [decimals]="3" tooltip="Risk-adjusted return (target > 1.0)" />
        <app-metric-card label="Sortino Ratio" [value]="metrics()?.sortino_ratio ?? null"
          format="number" [decimals]="3" tooltip="Downside-only risk ratio (target > 2.0)" />
        <app-metric-card label="Calmar Ratio" [value]="metrics()?.calmar_ratio ?? null"
          format="number" [decimals]="3" tooltip="Return / Max Drawdown" />
        <app-metric-card label="Win Rate" [value]="metrics()?.win_rate ?? null"
          format="number" unit="%" [decimals]="1" tooltip="% of winning trades" [colorize]="true" />
        <app-metric-card label="Max Drawdown" [value]="metrics()?.max_drawdown ? -(metrics()!.max_drawdown) : null"
          format="percent" [decimals]="2" tooltip="Largest peak-to-trough decline" [colorize]="true" />
        <app-metric-card label="Profit Factor" [value]="metrics()?.profit_factor ?? null"
          format="number" [decimals]="2" tooltip="Gross profit / Gross loss (target > 1.5)" [colorize]="true" />
        <app-metric-card label="Avg R:R" [value]="metrics()?.avg_r_multiple ?? null"
          format="number" [decimals]="2" tooltip="Average reward-to-risk multiple" [colorize]="true" />
        <app-metric-card label="Total Return" [value]="metrics()?.total_return ?? null"
          format="percent" [decimals]="2" [colorize]="true" />
        <app-metric-card label="Total PnL" [value]="metrics()?.total_pnl ?? null"
          format="currency" [colorize]="true" />
        <app-metric-card label="Total Trades" [value]="metrics()?.total_trades ?? null"
          format="raw" [subtitle]="tradesSubtitle()" />
        <app-metric-card label="Total Fees" [value]="metrics()?.total_fees_usdt ?? null"
          format="currency" />
        <app-metric-card label="Avg Duration" [value]="metrics()?.avg_trade_duration_secs ?? null"
          format="duration" />
      </div>

      <!-- Charts row -->
      <div class="charts-grid">
        <!-- Equity Curve -->
        <div class="card">
          <div class="card-header"><h3>Equity Curve</h3></div>
          <div #equityChart class="chart-container"></div>
        </div>

        <!-- Live Positions -->
        <div class="card">
          <div class="card-header">
            <h3>Live Positions</h3>
            <span class="badge" [class]="'badge-' + (botStatus()?.mode || 'unknown')">
              {{ botStatus()?.mode || 'unknown' }}
            </span>
          </div>
          <div *ngIf="!positions()?.length" class="empty-state">
            <mat-icon>inbox</mat-icon>
            <span>No open positions</span>
          </div>
          <table mat-table [dataSource]="positions() || []" *ngIf="positions()?.length" class="positions-table">
            <ng-container matColumnDef="symbol">
              <th mat-header-cell *matHeaderCellDef>Symbol</th>
              <td mat-cell *matCellDef="let p">{{ p.symbol }}</td>
            </ng-container>
            <ng-container matColumnDef="side">
              <th mat-header-cell *matHeaderCellDef>Side</th>
              <td mat-cell *matCellDef="let p">
                <span class="badge" [class]="p.side === 'Buy' ? 'badge-long' : 'badge-short'">
                  {{ p.side === 'Buy' ? 'LONG' : 'SHORT' }}
                </span>
              </td>
            </ng-container>
            <ng-container matColumnDef="size">
              <th mat-header-cell *matHeaderCellDef>Size</th>
              <td mat-cell *matCellDef="let p">{{ p.size }}</td>
            </ng-container>
            <ng-container matColumnDef="avg_price">
              <th mat-header-cell *matHeaderCellDef>Avg Price</th>
              <td mat-cell *matCellDef="let p">\${{ p.avg_price | number:'1.2-2' }}</td>
            </ng-container>
            <ng-container matColumnDef="unrealized_pnl">
              <th mat-header-cell *matHeaderCellDef>PnL</th>
              <td mat-cell *matCellDef="let p" [class]="p.unrealized_pnl >= 0 ? 'profit' : 'loss'">
                {{ p.unrealized_pnl >= 0 ? '+' : '' }}\${{ p.unrealized_pnl | number:'1.2-2' }}
              </td>
            </ng-container>
            <tr mat-header-row *matHeaderRowDef="positionCols"></tr>
            <tr mat-row *matRowDef="let row; columns: positionCols;"></tr>
          </table>

          <!-- Portfolio stats -->
          <div class="portfolio-stats" *ngIf="portfolio()">
            <div class="stat">
              <span class="stat-label">Equity</span>
              <span class="stat-value">\${{ portfolio()!.equity_usdt | number:'1.2-2' }}</span>
            </div>
            <div class="stat">
              <span class="stat-label">Available</span>
              <span class="stat-value">\${{ portfolio()!.available_usdt | number:'1.2-2' }}</span>
            </div>
            <div class="stat">
              <span class="stat-label">Drawdown</span>
              <span class="stat-value loss">{{ portfolio()!.drawdown_pct | number:'1.2-2' }}%</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Drawdown chart -->
      <div class="card full-width-card">
        <div class="card-header"><h3>Drawdown</h3></div>
        <div #drawdownChart class="chart-container chart-small"></div>
      </div>
    </div>
  `,
  styles: [`
    .page-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 20px;
    }

    .header-actions {
      display: flex;
      align-items: center;
      gap: 12px;

      .last-update { font-size: 12px; color: var(--text-muted); }
      .refresh-btn { color: var(--text-secondary); border-color: var(--border-color); }
    }

    .chart-container {
      height: 280px;
      width: 100%;
    }

    .chart-small { height: 140px; }

    .empty-state {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      padding: 32px;
      color: var(--text-muted);
      font-size: 13px;

      mat-icon { font-size: 20px; }
    }

    .positions-table {
      width: 100%;
      background: transparent;
    }

    .portfolio-stats {
      display: flex;
      justify-content: space-around;
      padding: 12px 0 4px;
      border-top: 1px solid var(--border-color);
      margin-top: 8px;

      .stat {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 2px;

        .stat-label { font-size: 11px; color: var(--text-muted); }
        .stat-value { font-size: 14px; font-weight: 600; }
      }
    }
  `],
})
export class DashboardComponent implements OnInit, OnDestroy, AfterViewInit {
  @ViewChild('equityChart', { static: false }) equityChartEl!: ElementRef<HTMLDivElement>;
  @ViewChild('drawdownChart', { static: false }) drawdownChartEl!: ElementRef<HTMLDivElement>;

  metrics = signal<MetricsSummary | null>(null);
  portfolio = signal<Portfolio | null>(null);
  lastUpdate = signal<string>('—');
  positionCols = ['symbol', 'side', 'size', 'avg_price', 'unrealized_pnl'];

  positions = computed(() => this.statusService.status()?.open_positions ?? []);
  botStatus = computed(() => this.statusService.status());

  tradesSubtitle = computed(() => {
    const m = this.metrics();
    if (!m) return '';
    return `${m.winning_trades}W / ${m.losing_trades}L`;
  });

  private equityChart: IChartApi | null = null;
  private drawdownChart: IChartApi | null = null;
  private equitySeries: ISeriesApi<'Area'> | null = null;
  private drawdownSeries: ISeriesApi<'Histogram'> | null = null;
  private wsSub: Subscription | null = null;

  constructor(
    private metricsService: MetricsService,
    private statusService: StatusService,
    private wsService: WebsocketService,
  ) {}

  ngOnInit(): void {
    this.refresh();
    this.subscribeWs();
  }

  ngAfterViewInit(): void {
    this.initCharts();
    this.loadChartData();
  }

  ngOnDestroy(): void {
    this.wsSub?.unsubscribe();
    this.equityChart?.remove();
    this.drawdownChart?.remove();
  }

  refresh(): void {
    this.metricsService.getSummary().subscribe(m => this.metrics.set(m));
    this.metricsService.getPortfolio().subscribe(p => this.portfolio.set(p));
    this.lastUpdate.set(new Date().toLocaleTimeString());
    this.loadChartData();
  }

  private initCharts(): void {
    const commonOpts = {
      layout: { background: { type: ColorType.Solid, color: '#1c2128' }, textColor: '#8b949e' },
      grid: { vertLines: { color: '#21262d' }, horzLines: { color: '#21262d' } },
      timeScale: { timeVisible: true, borderColor: '#30363d' },
      rightPriceScale: { borderColor: '#30363d' },
      crosshair: { mode: 1 },
    };

    this.equityChart = createChart(this.equityChartEl.nativeElement, {
      ...commonOpts,
      height: 280,
    });
    this.equitySeries = this.equityChart.addAreaSeries({
      lineColor: '#58a6ff',
      topColor: 'rgba(88, 166, 255, 0.25)',
      bottomColor: 'rgba(88, 166, 255, 0)',
      lineWidth: 2,
      priceFormat: { type: 'custom', formatter: (v: number) => `$${v.toFixed(0)}` },
    });

    this.drawdownChart = createChart(this.drawdownChartEl.nativeElement, {
      ...commonOpts,
      height: 140,
    });
    this.drawdownSeries = this.drawdownChart.addHistogramSeries({
      color: '#f85149',
      priceFormat: { type: 'custom', formatter: (v: number) => `${v.toFixed(2)}%` },
    });
  }

  private loadChartData(): void {
    this.metricsService.getEquityCurve().subscribe(data => {
      if (this.equitySeries && data.length) {
        const sorted = [...data].sort((a, b) => a.time - b.time);
        this.equitySeries.setData(
          sorted.map(p => ({ time: Math.floor(p.time / 1000) as any, value: p.value }))
        );
        this.equityChart?.timeScale().fitContent();
      }
    });

    this.metricsService.getDrawdown().subscribe(data => {
      if (this.drawdownSeries && data.length) {
        const sorted = [...data].sort((a, b) => a.time - b.time);
        this.drawdownSeries.setData(
          sorted.map(p => ({ time: Math.floor(p.time / 1000) as any, value: p.value, color: '#f85149' }))
        );
        this.drawdownChart?.timeScale().fitContent();
      }
    });
  }

  private subscribeWs(): void {
    this.wsSub = this.wsService.connect().subscribe(event => {
      if (event.type === 'portfolio') {
        this.metricsService.getPortfolio().subscribe(p => this.portfolio.set(p));
        this.loadChartData();
      }
      if (event.type === 'trade_close') {
        this.refresh();
      }
    });
  }
}
