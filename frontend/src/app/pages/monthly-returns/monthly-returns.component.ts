import { Component, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';

import { MetricsService } from '../../core/services/metrics.service';

interface MonthCell {
  yearMonth: string;
  year: number;
  month: number;
  pct: number | null;
  label: string;
}

@Component({
  selector: 'app-monthly-returns',
  standalone: true,
  imports: [CommonModule, FormsModule, MatFormFieldModule, MatSelectModule],
  template: `
    <div class="page-container">
      <div class="page-header" style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">
        <h1 class="page-title">Monthly Returns</h1>
        <mat-form-field appearance="outline" style="width:120px">
          <mat-label>Year</mat-label>
          <mat-select [(ngModel)]="selectedYear" (ngModelChange)="loadData()">
            <mat-option *ngFor="let y of availableYears" [value]="y">{{ y }}</mat-option>
          </mat-select>
        </mat-form-field>
      </div>

      <!-- Summary stats -->
      <div class="return-stats card" style="margin-bottom:16px">
        <div class="ret-stat">
          <span class="ret-label">YTD Return</span>
          <span class="ret-value" [class]="ytdReturn() >= 0 ? 'profit' : 'loss'">
            {{ ytdReturn() >= 0 ? '+' : '' }}{{ ytdReturn() | number:'1.2-2' }}%
          </span>
        </div>
        <div class="ret-stat">
          <span class="ret-label">Best Month</span>
          <span class="ret-value profit">+{{ bestMonth() | number:'1.2-2' }}%</span>
        </div>
        <div class="ret-stat">
          <span class="ret-label">Worst Month</span>
          <span class="ret-value loss">{{ worstMonth() | number:'1.2-2' }}%</span>
        </div>
        <div class="ret-stat">
          <span class="ret-label">Positive Months</span>
          <span class="ret-value">{{ positiveMonths() }} / {{ totalMonths() }}</span>
        </div>
        <div class="ret-stat">
          <span class="ret-label">Avg Monthly Return</span>
          <span class="ret-value" [class]="avgMonthly() >= 0 ? 'profit' : 'loss'">
            {{ avgMonthly() >= 0 ? '+' : '' }}{{ avgMonthly() | number:'1.2-2' }}%
          </span>
        </div>
      </div>

      <!-- Heatmap -->
      <div class="card">
        <div class="card-header"><h3>Monthly Returns Heatmap</h3></div>

        <div class="heatmap">
          <!-- Month headers -->
          <div class="heatmap-row header-row">
            <div class="year-label"></div>
            <div class="month-header" *ngFor="let m of monthNames">{{ m }}</div>
          </div>

          <!-- Year rows -->
          <div class="heatmap-row" *ngFor="let year of chartYears()">
            <div class="year-label">{{ year }}</div>
            <div class="month-cell"
              *ngFor="let cell of getYearCells(year)"
              [style.background]="getCellColor(cell.pct)"
              [style.color]="getCellTextColor(cell.pct)"
              [title]="cell.yearMonth + ': ' + (cell.pct != null ? (cell.pct | number:'1.2-2') + '%' : 'N/A')"
            >
              <span *ngIf="cell.pct != null">
                {{ cell.pct >= 0 ? '+' : '' }}{{ cell.pct | number:'1.1-1' }}%
              </span>
              <span *ngIf="cell.pct == null" class="no-data">—</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Bar chart -->
      <div class="card" style="margin-top:16px">
        <div class="card-header"><h3>Monthly PnL Bar Chart</h3></div>
        <div class="bar-chart">
          <div class="bar-col" *ngFor="let cell of currentYearCells()">
            <div class="bar-wrapper">
              <div class="bar"
                [class]="(cell.pct || 0) >= 0 ? 'bar-profit' : 'bar-loss'"
                [style.height]="getBarHeight(cell.pct) + 'px'"
                [title]="cell.pct != null ? ((cell.pct >= 0 ? '+' : '') + (cell.pct | number:'1.2-2') + '%') : '—'"
              ></div>
            </div>
            <div class="bar-label">{{ getShortMonth(cell.month) }}</div>
            <div class="bar-value" [class]="(cell.pct || 0) >= 0 ? 'profit' : 'loss'" *ngIf="cell.pct != null">
              {{ cell.pct >= 0 ? '+' : '' }}{{ cell.pct | number:'1.1-1' }}%
            </div>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .return-stats {
      display: flex;
      gap: 32px;
      flex-wrap: wrap;

      .ret-stat { display: flex; flex-direction: column; gap: 4px; }
      .ret-label { font-size: 11px; color: var(--text-muted); }
      .ret-value { font-size: 18px; font-weight: 700; }
    }

    .heatmap {
      overflow-x: auto;
    }

    .heatmap-row {
      display: flex;
      gap: 4px;
      margin-bottom: 4px;
      align-items: center;
    }

    .header-row { margin-bottom: 8px; }

    .year-label {
      width: 50px;
      font-size: 12px;
      font-weight: 600;
      color: var(--text-secondary);
      flex-shrink: 0;
    }

    .month-header {
      flex: 1;
      min-width: 60px;
      text-align: center;
      font-size: 11px;
      font-weight: 600;
      color: var(--text-muted);
    }

    .month-cell {
      flex: 1;
      min-width: 60px;
      height: 44px;
      border-radius: 4px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 11px;
      font-weight: 600;
      cursor: default;
      transition: opacity 0.15s;

      &:hover { opacity: 0.8; }

      .no-data { color: var(--text-muted); }
    }

    .bar-chart {
      display: flex;
      gap: 8px;
      align-items: flex-end;
      height: 160px;
      padding: 0 8px;
    }

    .bar-col {
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: center;
      height: 100%;
    }

    .bar-wrapper {
      flex: 1;
      display: flex;
      align-items: flex-end;
      width: 100%;
    }

    .bar {
      width: 100%;
      border-radius: 3px 3px 0 0;
      min-height: 2px;
      transition: height 0.3s ease;

      &.bar-profit { background: var(--color-profit); }
      &.bar-loss { background: var(--color-loss); }
    }

    .bar-label {
      font-size: 10px;
      color: var(--text-muted);
      margin-top: 4px;
    }

    .bar-value {
      font-size: 10px;
      font-weight: 600;
      margin-top: 2px;
    }
  `],
})
export class MonthlyReturnsComponent implements OnInit {
  monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  availableYears = [2022, 2023, 2024, 2025, 2026];
  selectedYear = new Date().getFullYear();

  returnsData = signal<{[key: string]: number}>({});

  ytdReturn = computed(() => {
    const d = this.returnsData();
    return Object.values(d).reduce((s, v) => s + v, 0);
  });
  bestMonth = computed(() => Math.max(0, ...Object.values(this.returnsData())));
  worstMonth = computed(() => Math.min(0, ...Object.values(this.returnsData())));
  positiveMonths = computed(() => Object.values(this.returnsData()).filter(v => v > 0).length);
  totalMonths = computed(() => Object.keys(this.returnsData()).length);
  avgMonthly = computed(() => {
    const vals = Object.values(this.returnsData());
    return vals.length ? vals.reduce((s, v) => s + v, 0) / vals.length : 0;
  });

  chartYears = computed(() => {
    const keys = Object.keys(this.returnsData());
    const years = [...new Set(keys.map(k => parseInt(k.split('-')[0])))];
    return years.sort();
  });

  currentYearCells = computed(() => this.getYearCells(this.selectedYear));

  constructor(private metricsService: MetricsService) {}

  ngOnInit(): void {
    this.loadData();
  }

  loadData(): void {
    this.metricsService.getMonthlyReturns(this.selectedYear).subscribe(d => {
      this.returnsData.set(d);
    });
  }

  getYearCells(year: number): MonthCell[] {
    return Array.from({ length: 12 }, (_, i) => {
      const month = i + 1;
      const yearMonth = `${year}-${String(month).padStart(2, '0')}`;
      const pct = this.returnsData()[yearMonth] ?? null;
      return { yearMonth, year, month, pct, label: this.monthNames[i] };
    });
  }

  getCellColor(pct: number | null): string {
    if (pct === null) return 'var(--bg-tertiary)';
    if (pct === 0) return 'var(--bg-tertiary)';
    const intensity = Math.min(Math.abs(pct) / 10, 1);
    if (pct > 0) {
      const g = Math.round(80 + intensity * 100);
      return `rgba(38, ${g}, 65, ${0.2 + intensity * 0.7})`;
    } else {
      const r = Math.round(150 + intensity * 100);
      return `rgba(${r}, 81, 73, ${0.2 + intensity * 0.7})`;
    }
  }

  getCellTextColor(pct: number | null): string {
    if (pct === null) return 'var(--text-muted)';
    const intensity = Math.min(Math.abs(pct || 0) / 10, 1);
    return intensity > 0.5 ? '#fff' : 'var(--text-primary)';
  }

  getBarHeight(pct: number | null): number {
    if (pct === null) return 0;
    const maxPct = Math.max(...this.currentYearCells().map(c => Math.abs(c.pct || 0)), 1);
    return Math.max(4, Math.abs(pct) / maxPct * 100);
  }

  getShortMonth(month: number): string {
    return this.monthNames[month - 1];
  }
}
