import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatTableModule } from '@angular/material/table';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatSortModule } from '@angular/material/sort';

import { TradeService, TradeFilter } from '../../core/services/trade.service';
import { Trade, PaginatedTrades } from '../../core/models/trade.model';

@Component({
  selector: 'app-trades',
  standalone: true,
  imports: [
    CommonModule, FormsModule,
    MatTableModule, MatPaginatorModule, MatFormFieldModule, MatSelectModule,
    MatInputModule, MatIconModule, MatButtonModule, MatSortModule,
  ],
  template: `
    <div class="page-container">
      <h1 class="page-title">Trade History</h1>

      <!-- Filters -->
      <div class="filter-row card" style="margin-bottom:16px">
        <mat-form-field appearance="outline">
          <mat-label>Symbol</mat-label>
          <input matInput [(ngModel)]="filter.symbol" placeholder="BTCUSDT">
        </mat-form-field>

        <mat-form-field appearance="outline">
          <mat-label>Direction</mat-label>
          <mat-select [(ngModel)]="filter.direction">
            <mat-option value="">All</mat-option>
            <mat-option value="LONG">Long</mat-option>
            <mat-option value="SHORT">Short</mat-option>
          </mat-select>
        </mat-form-field>

        <mat-form-field appearance="outline">
          <mat-label>Status</mat-label>
          <mat-select [(ngModel)]="filter.status">
            <mat-option value="">All</mat-option>
            <mat-option value="CLOSED">Closed</mat-option>
            <mat-option value="OPEN">Open</mat-option>
          </mat-select>
        </mat-form-field>

        <button mat-flat-button color="primary" (click)="search()">
          <mat-icon>search</mat-icon> Search
        </button>
        <button mat-stroked-button (click)="clearFilters()">Clear</button>
      </div>

      <!-- Summary row -->
      <div class="summary-row" *ngIf="data()">
        <div class="summary-stat">
          <span>Total Trades</span>
          <strong>{{ data()!.total }}</strong>
        </div>
        <div class="summary-stat">
          <span>Total PnL</span>
          <strong [class]="totalPnl() >= 0 ? 'profit' : 'loss'">
            {{ totalPnl() >= 0 ? '+' : '' }}\${{ totalPnl() | number:'1.2-2' }}
          </strong>
        </div>
        <div class="summary-stat">
          <span>Win Rate</span>
          <strong>{{ winRate() | number:'1.1-1' }}%</strong>
        </div>
      </div>

      <!-- Table -->
      <div class="card" style="padding:0; overflow:hidden;">
        <div *ngIf="loading()" class="loading-overlay">
          <mat-icon class="spin">autorenew</mat-icon> Loading trades...
        </div>

        <table mat-table [dataSource]="trades()" *ngIf="!loading()">
          <ng-container matColumnDef="entry_time">
            <th mat-header-cell *matHeaderCellDef>Entry Time</th>
            <td mat-cell *matCellDef="let t">{{ t.entry_time | date:'MM/dd HH:mm' }}</td>
          </ng-container>

          <ng-container matColumnDef="symbol">
            <th mat-header-cell *matHeaderCellDef>Symbol</th>
            <td mat-cell *matCellDef="let t"><strong>{{ t.symbol }}</strong></td>
          </ng-container>

          <ng-container matColumnDef="direction">
            <th mat-header-cell *matHeaderCellDef>Dir</th>
            <td mat-cell *matCellDef="let t">
              <span class="badge" [class]="t.direction === 'LONG' ? 'badge-long' : 'badge-short'">
                {{ t.direction }}
              </span>
            </td>
          </ng-container>

          <ng-container matColumnDef="entry_price">
            <th mat-header-cell *matHeaderCellDef>Entry</th>
            <td mat-cell *matCellDef="let t">\${{ t.entry_price | number:'1.2-2' }}</td>
          </ng-container>

          <ng-container matColumnDef="exit_price">
            <th mat-header-cell *matHeaderCellDef>Exit</th>
            <td mat-cell *matCellDef="let t">{{ t.exit_price ? '\$' + (t.exit_price | number:'1.2-2') : '—' }}</td>
          </ng-container>

          <ng-container matColumnDef="quantity">
            <th mat-header-cell *matHeaderCellDef>Qty</th>
            <td mat-cell *matCellDef="let t">{{ t.quantity | number:'1.3-3' }}</td>
          </ng-container>

          <ng-container matColumnDef="net_pnl">
            <th mat-header-cell *matHeaderCellDef>Net PnL</th>
            <td mat-cell *matCellDef="let t" [class]="(t.net_pnl || 0) >= 0 ? 'profit' : 'loss'">
              <strong>{{ t.net_pnl != null ? ((t.net_pnl >= 0 ? '+' : '') + '\$' + (t.net_pnl | number:'1.2-2')) : '—' }}</strong>
            </td>
          </ng-container>

          <ng-container matColumnDef="pnl_pct">
            <th mat-header-cell *matHeaderCellDef>PnL%</th>
            <td mat-cell *matCellDef="let t" [class]="(t.pnl_pct || 0) >= 0 ? 'profit' : 'loss'">
              {{ t.pnl_pct != null ? ((t.pnl_pct >= 0 ? '+' : '') + (t.pnl_pct | number:'1.2-2') + '%') : '—' }}
            </td>
          </ng-container>

          <ng-container matColumnDef="r_multiple">
            <th mat-header-cell *matHeaderCellDef>R:R</th>
            <td mat-cell *matCellDef="let t" [class]="(t.r_multiple || 0) >= 0 ? 'profit' : 'loss'">
              {{ t.r_multiple != null ? (t.r_multiple | number:'1.2-2') + 'R' : '—' }}
            </td>
          </ng-container>

          <ng-container matColumnDef="duration">
            <th mat-header-cell *matHeaderCellDef>Duration</th>
            <td mat-cell *matCellDef="let t">{{ formatDuration(t.duration_secs) }}</td>
          </ng-container>

          <ng-container matColumnDef="exit_reason">
            <th mat-header-cell *matHeaderCellDef>Exit Reason</th>
            <td mat-cell *matCellDef="let t">
              <span class="exit-reason">{{ t.exit_reason || '—' }}</span>
            </td>
          </ng-container>

          <ng-container matColumnDef="status">
            <th mat-header-cell *matHeaderCellDef>Status</th>
            <td mat-cell *matCellDef="let t">
              <span class="badge" [class]="t.status === 'OPEN' ? 'badge-open' : 'badge-closed'">
                {{ t.status }}
              </span>
            </td>
          </ng-container>

          <tr mat-header-row *matHeaderRowDef="displayedCols; sticky: true"></tr>
          <tr mat-row *matRowDef="let row; columns: displayedCols;" (click)="selectTrade(row)" style="cursor:pointer"></tr>
        </table>

        <mat-paginator
          [length]="data()?.total || 0"
          [pageSize]="50"
          [pageSizeOptions]="[25, 50, 100]"
          (page)="onPage($event)"
          showFirstLastButtons>
        </mat-paginator>
      </div>

      <!-- Trade detail slide-out -->
      <div class="trade-detail-panel" *ngIf="selectedTrade()" (click)="selectedTrade.set(null)">
        <div class="trade-detail-content" (click)="$event.stopPropagation()">
          <div class="detail-header">
            <span class="badge" [class]="selectedTrade()!.direction === 'LONG' ? 'badge-long' : 'badge-short'">
              {{ selectedTrade()!.direction }}
            </span>
            <h3>{{ selectedTrade()!.symbol }}</h3>
            <button mat-icon-button (click)="selectedTrade.set(null)">
              <mat-icon>close</mat-icon>
            </button>
          </div>
          <div class="detail-grid">
            <div class="detail-item" *ngFor="let item of tradeDetailItems()">
              <span class="detail-label">{{ item.label }}</span>
              <span class="detail-value" [class]="item.class">{{ item.value }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .summary-row {
      display: flex;
      gap: 24px;
      margin-bottom: 16px;
      padding: 12px 16px;
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 8px;

      .summary-stat {
        display: flex;
        align-items: center;
        gap: 8px;
        span { font-size: 12px; color: var(--text-secondary); }
        strong { font-size: 14px; font-weight: 600; }
      }
    }

    .exit-reason {
      font-size: 11px;
      font-family: monospace;
      color: var(--text-secondary);
    }

    .spin { animation: spin 1s linear infinite; }
    @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

    .trade-detail-panel {
      position: fixed; inset: 0;
      background: rgba(0,0,0,0.6);
      z-index: 1000;
      display: flex;
      justify-content: flex-end;
    }

    .trade-detail-content {
      width: 380px;
      background: var(--bg-secondary);
      border-left: 1px solid var(--border-color);
      padding: 20px;
      overflow-y: auto;
    }

    .detail-header {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 20px;
      h3 { flex: 1; font-size: 16px; }
    }

    .detail-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }

    .detail-item {
      display: flex;
      flex-direction: column;
      gap: 3px;
      .detail-label { font-size: 11px; color: var(--text-muted); }
      .detail-value { font-size: 13px; font-weight: 500; }
    }
  `],
})
export class TradesComponent implements OnInit {
  displayedCols = ['entry_time', 'symbol', 'direction', 'entry_price', 'exit_price', 'quantity', 'net_pnl', 'pnl_pct', 'r_multiple', 'duration', 'exit_reason', 'status'];

  data = signal<PaginatedTrades | null>(null);
  loading = signal(false);
  selectedTrade = signal<Trade | null>(null);
  currentPage = 1;

  filter: TradeFilter = { status: '', page_size: 50 };

  constructor(private tradeService: TradeService) {}

  ngOnInit(): void {
    this.search();
  }

  search(): void {
    this.loading.set(true);
    this.currentPage = 1;
    this.tradeService.getTrades({ ...this.filter, page: 1 }).subscribe({
      next: (d) => { this.data.set(d); this.loading.set(false); },
      error: () => this.loading.set(false),
    });
  }

  clearFilters(): void {
    this.filter = { status: '', page_size: 50 };
    this.search();
  }

  onPage(event: PageEvent): void {
    this.currentPage = event.pageIndex + 1;
    this.loading.set(true);
    this.tradeService.getTrades({ ...this.filter, page: this.currentPage, page_size: event.pageSize }).subscribe({
      next: (d) => { this.data.set(d); this.loading.set(false); },
      error: () => this.loading.set(false),
    });
  }

  selectTrade(t: Trade): void {
    this.selectedTrade.set(t);
  }

  trades() {
    return this.data()?.items ?? [];
  }

  totalPnl(): number {
    return this.trades().reduce((sum, t) => sum + (t.net_pnl || 0), 0);
  }

  winRate(): number {
    const t = this.trades();
    if (!t.length) return 0;
    return t.filter(x => (x.net_pnl || 0) > 0).length / t.length * 100;
  }

  formatDuration(secs: number | null): string {
    if (!secs) return '—';
    if (secs < 3600) return `${Math.round(secs / 60)}m`;
    if (secs < 86400) return `${(secs / 3600).toFixed(1)}h`;
    return `${(secs / 86400).toFixed(1)}d`;
  }

  tradeDetailItems() {
    const t = this.selectedTrade();
    if (!t) return [];
    return [
      { label: 'Entry Time', value: t.entry_time ? new Date(t.entry_time).toLocaleString() : '—', class: '' },
      { label: 'Exit Time', value: t.exit_time ? new Date(t.exit_time).toLocaleString() : '—', class: '' },
      { label: 'Entry Price', value: t.entry_price ? `$${t.entry_price.toFixed(2)}` : '—', class: '' },
      { label: 'Exit Price', value: t.exit_price ? `$${t.exit_price.toFixed(2)}` : '—', class: '' },
      { label: 'Quantity', value: t.quantity ? t.quantity.toFixed(4) : '—', class: '' },
      { label: 'Notional', value: t.notional_usdt ? `$${t.notional_usdt.toFixed(2)}` : '—', class: '' },
      { label: 'Stop Loss', value: t.stop_loss ? `$${t.stop_loss.toFixed(2)}` : '—', class: '' },
      { label: 'Take Profit', value: t.take_profit ? `$${t.take_profit.toFixed(2)}` : '—', class: '' },
      { label: 'Gross PnL', value: t.gross_pnl != null ? `$${t.gross_pnl.toFixed(2)}` : '—', class: (t.gross_pnl || 0) >= 0 ? 'profit' : 'loss' },
      { label: 'Net PnL', value: t.net_pnl != null ? `$${t.net_pnl.toFixed(2)}` : '—', class: (t.net_pnl || 0) >= 0 ? 'profit' : 'loss' },
      { label: 'PnL %', value: t.pnl_pct != null ? `${t.pnl_pct.toFixed(3)}%` : '—', class: (t.pnl_pct || 0) >= 0 ? 'profit' : 'loss' },
      { label: 'R Multiple', value: t.r_multiple != null ? `${t.r_multiple.toFixed(2)}R` : '—', class: (t.r_multiple || 0) >= 0 ? 'profit' : 'loss' },
      { label: 'ATR at Entry', value: t.atr_at_entry ? `$${t.atr_at_entry.toFixed(2)}` : '—', class: '' },
      { label: 'Risk (USDT)', value: t.risk_usdt ? `$${t.risk_usdt.toFixed(2)}` : '—', class: '' },
      { label: 'Entry Fee', value: t.entry_fee ? `$${t.entry_fee.toFixed(4)}` : '—', class: '' },
      { label: 'Exit Reason', value: t.exit_reason || '—', class: '' },
    ];
  }
}
