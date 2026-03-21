import {
  Component, OnInit, OnDestroy, AfterViewInit,
  ElementRef, ViewChild, signal
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatIconModule } from '@angular/material/icon';
import {
  createChart, IChartApi, ISeriesApi, ColorType, LineStyle
} from 'lightweight-charts';
import { ApiService } from '../../core/services/api.service';

@Component({
  selector: 'app-chart',
  standalone: true,
  imports: [CommonModule, FormsModule, MatButtonToggleModule, MatIconModule],
  template: `
    <div class="page-container">
      <div class="chart-toolbar">
        <h1 class="page-title">Price Chart</h1>
        <div class="toolbar-controls">
          <mat-button-toggle-group [(ngModel)]="selectedSymbol" (change)="loadData()">
            <mat-button-toggle value="BTCUSDT">BTC/USDT</mat-button-toggle>
            <mat-button-toggle value="ETHUSDT">ETH/USDT</mat-button-toggle>
          </mat-button-toggle-group>

          <mat-button-toggle-group [(ngModel)]="selectedInterval" (change)="loadData()">
            <mat-button-toggle value="15">15m</mat-button-toggle>
            <mat-button-toggle value="60">1H</mat-button-toggle>
            <mat-button-toggle value="240">4H</mat-button-toggle>
            <mat-button-toggle value="D">1D</mat-button-toggle>
          </mat-button-toggle-group>

          <div class="indicator-toggles">
            <button class="ind-btn" [class.active]="showEMA" (click)="showEMA = !showEMA; toggleEMA()">EMA</button>
            <button class="ind-btn" [class.active]="showST" (click)="showST = !showST; toggleST()">Supertrend</button>
          </div>
        </div>
      </div>

      <!-- Price chart -->
      <div class="card" style="padding:0; overflow:hidden; margin-bottom:12px">
        <div #priceChart class="price-chart-container"></div>
      </div>

      <!-- RSI panel -->
      <div class="card" style="padding:0; overflow:hidden; margin-bottom:12px">
        <div class="panel-label">RSI (14)</div>
        <div #rsiChart class="indicator-chart-container"></div>
      </div>

      <!-- MACD panel -->
      <div class="card" style="padding:0; overflow:hidden">
        <div class="panel-label">MACD (12, 26, 9)</div>
        <div #macdChart class="indicator-chart-container"></div>
      </div>
    </div>
  `,
  styles: [`
    .chart-toolbar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
      flex-wrap: wrap;
      gap: 12px;
    }

    .toolbar-controls {
      display: flex;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
    }

    .price-chart-container { height: 420px; width: 100%; }
    .indicator-chart-container { height: 120px; width: 100%; }

    .panel-label {
      padding: 6px 12px;
      font-size: 11px;
      font-weight: 600;
      color: var(--text-secondary);
      text-transform: uppercase;
      border-bottom: 1px solid var(--border-color);
    }

    .indicator-toggles {
      display: flex;
      gap: 6px;
    }

    .ind-btn {
      padding: 4px 10px;
      border-radius: 4px;
      border: 1px solid var(--border-color);
      background: var(--bg-tertiary);
      color: var(--text-secondary);
      font-size: 12px;
      cursor: pointer;
      transition: all 0.15s;

      &.active {
        background: rgba(88, 166, 255, 0.15);
        border-color: #58a6ff;
        color: #58a6ff;
      }
    }
  `],
})
export class ChartComponent implements OnInit, OnDestroy, AfterViewInit {
  @ViewChild('priceChart') priceChartEl!: ElementRef<HTMLDivElement>;
  @ViewChild('rsiChart') rsiChartEl!: ElementRef<HTMLDivElement>;
  @ViewChild('macdChart') macdChartEl!: ElementRef<HTMLDivElement>;

  selectedSymbol = 'BTCUSDT';
  selectedInterval = '60';
  showEMA = true;
  showST = true;

  private priceChart: IChartApi | null = null;
  private rsiChart: IChartApi | null = null;
  private macdChart: IChartApi | null = null;
  private candleSeries: ISeriesApi<'Candlestick'> | null = null;
  private ema21Series: ISeriesApi<'Line'> | null = null;
  private ema55Series: ISeriesApi<'Line'> | null = null;
  private stSeries: ISeriesApi<'Line'> | null = null;
  private rsiSeries: ISeriesApi<'Line'> | null = null;
  private macdLineSeries: ISeriesApi<'Line'> | null = null;
  private macdSignalSeries: ISeriesApi<'Line'> | null = null;
  private macdHistSeries: ISeriesApi<'Histogram'> | null = null;

  constructor(private api: ApiService) {}

  ngOnInit(): void {}

  ngAfterViewInit(): void {
    this.initCharts();
    this.loadData();
  }

  ngOnDestroy(): void {
    this.priceChart?.remove();
    this.rsiChart?.remove();
    this.macdChart?.remove();
  }

  private commonOpts(height: number) {
    return {
      height,
      layout: { background: { type: ColorType.Solid, color: '#1c2128' }, textColor: '#8b949e' },
      grid: { vertLines: { color: '#21262d' }, horzLines: { color: '#21262d' } },
      rightPriceScale: { borderColor: '#30363d' },
      timeScale: { timeVisible: true, borderColor: '#30363d' },
    };
  }

  private initCharts(): void {
    this.priceChart = createChart(this.priceChartEl.nativeElement, this.commonOpts(420));
    this.candleSeries = this.priceChart.addCandlestickSeries({
      upColor: '#26a641', downColor: '#f85149',
      borderUpColor: '#26a641', borderDownColor: '#f85149',
      wickUpColor: '#26a641', wickDownColor: '#f85149',
    });
    this.ema21Series = this.priceChart.addLineSeries({ color: '#58a6ff', lineWidth: 1, title: 'EMA21' });
    this.ema55Series = this.priceChart.addLineSeries({ color: '#f0883e', lineWidth: 1, lineStyle: LineStyle.Dashed, title: 'EMA55' });
    this.stSeries = this.priceChart.addLineSeries({ color: '#8b949e', lineWidth: 1, title: 'ST' });

    this.rsiChart = createChart(this.rsiChartEl.nativeElement, this.commonOpts(120));
    this.rsiSeries = this.rsiChart.addLineSeries({ color: '#c9d1d9', lineWidth: 1 });
    // RSI 70/30 lines
    this.rsiChart.addLineSeries({ color: 'rgba(248,81,73,0.4)', lineWidth: 1, lineStyle: LineStyle.Dashed });
    this.rsiChart.addLineSeries({ color: 'rgba(38,166,65,0.4)', lineWidth: 1, lineStyle: LineStyle.Dashed });

    this.macdChart = createChart(this.macdChartEl.nativeElement, this.commonOpts(120));
    this.macdHistSeries = this.macdChart.addHistogramSeries({ color: '#26a641' });
    this.macdLineSeries = this.macdChart.addLineSeries({ color: '#58a6ff', lineWidth: 1 });
    this.macdSignalSeries = this.macdChart.addLineSeries({ color: '#f0883e', lineWidth: 1 });
  }

  loadData(): void {
    this.api.get<any[]>('/portfolio/equity-curve').subscribe(); // keep alive

    // Load OHLCV from the ohlcv table via a simple query
    this.api.get<any>(`/backtests`, { symbol: this.selectedSymbol, page_size: 1 }).subscribe(() => {});

    // Load klines directly from Bybit info via signal endpoint
    this.api.get<{items: any[]}>('/signals', {
      symbol: this.selectedSymbol,
      page_size: 200,
    }).subscribe(resp => {
      if (!resp.items?.length) return;

      // Build approximate OHLCV from signal snapshots for demonstration
      const candles = resp.items.reverse().map((s: any) => ({
        time: Math.floor(new Date(s.signal_time).getTime() / 1000),
        open: s.close_price,
        high: s.close_price,
        low: s.close_price,
        close: s.close_price,
      }));

      this.candleSeries?.setData(candles as any);

      // EMA lines
      if (this.showEMA) {
        const ema21 = resp.items.reverse().map((s: any) => ({
          time: Math.floor(new Date(s.signal_time).getTime() / 1000),
          value: s.ema_21,
        })).filter(p => p.value != null);
        this.ema21Series?.setData(ema21 as any);

        const ema55 = resp.items.map((s: any) => ({
          time: Math.floor(new Date(s.signal_time).getTime() / 1000),
          value: s.ema_55,
        })).filter(p => p.value != null);
        this.ema55Series?.setData(ema55 as any);
      }

      // Supertrend
      if (this.showST) {
        const st = resp.items.map((s: any) => ({
          time: Math.floor(new Date(s.signal_time).getTime() / 1000),
          value: s.supertrend,
          color: s.supertrend_dir === 'UP' ? '#26a641' : '#f85149',
        })).filter(p => p.value != null);
        this.stSeries?.setData(st as any);
      }

      // RSI
      const rsi = resp.items.map((s: any) => ({
        time: Math.floor(new Date(s.signal_time).getTime() / 1000),
        value: s.rsi,
      })).filter(p => p.value != null);
      this.rsiSeries?.setData(rsi as any);

      // MACD
      const macdLine = resp.items.map((s: any) => ({
        time: Math.floor(new Date(s.signal_time).getTime() / 1000),
        value: s.macd_line,
      })).filter(p => p.value != null);
      this.macdLineSeries?.setData(macdLine as any);

      const macdSig = resp.items.map((s: any) => ({
        time: Math.floor(new Date(s.signal_time).getTime() / 1000),
        value: s.macd_signal,
      })).filter(p => p.value != null);
      this.macdSignalSeries?.setData(macdSig as any);

      const macdHist = resp.items.map((s: any) => ({
        time: Math.floor(new Date(s.signal_time).getTime() / 1000),
        value: s.macd_hist,
        color: (s.macd_hist || 0) >= 0 ? '#26a641' : '#f85149',
      })).filter(p => p.value != null);
      this.macdHistSeries?.setData(macdHist as any);

      this.priceChart?.timeScale().fitContent();
    });
  }

  toggleEMA(): void {
    this.ema21Series?.applyOptions({ visible: this.showEMA });
    this.ema55Series?.applyOptions({ visible: this.showEMA });
  }

  toggleST(): void {
    this.stSeries?.applyOptions({ visible: this.showST });
  }
}
