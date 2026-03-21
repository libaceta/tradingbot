import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MatTableModule } from '@angular/material/table';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatExpansionModule } from '@angular/material/expansion';

import { BacktestService } from '../../core/services/backtest.service';
import { BacktestRun, BacktestRunRequest } from '../../core/models/backtest.model';

@Component({
  selector: 'app-backtests',
  standalone: true,
  imports: [
    CommonModule, FormsModule, RouterLink,
    MatTableModule, MatButtonModule, MatFormFieldModule, MatInputModule,
    MatSelectModule, MatIconModule, MatProgressSpinnerModule, MatExpansionModule,
  ],
  template: `
    <div class="page-container">
      <h1 class="page-title">Backtests</h1>

      <!-- Run form -->
      <mat-expansion-panel class="card" style="margin-bottom:16px">
        <mat-expansion-panel-header>
          <mat-panel-title><mat-icon>science</mat-icon>&nbsp; Run New Backtest</mat-panel-title>
        </mat-expansion-panel-header>

        <div class="run-form">
          <mat-form-field appearance="outline">
            <mat-label>Engine</mat-label>
            <mat-select [(ngModel)]="newRun.engine">
              <mat-option value="backtestingpy">Backtesting.py (Detailed)</mat-option>
              <mat-option value="vectorbt">VectorBT (Optimization)</mat-option>
            </mat-select>
          </mat-form-field>

          <mat-form-field appearance="outline">
            <mat-label>Symbol</mat-label>
            <input matInput [(ngModel)]="newRun.symbol">
          </mat-form-field>

          <mat-form-field appearance="outline">
            <mat-label>Interval</mat-label>
            <mat-select [(ngModel)]="newRun.interval">
              <mat-option value="15">15m</mat-option>
              <mat-option value="60">1H</mat-option>
              <mat-option value="240">4H</mat-option>
              <mat-option value="D">1D</mat-option>
            </mat-select>
          </mat-form-field>

          <mat-form-field appearance="outline">
            <mat-label>Start Date</mat-label>
            <input matInput [(ngModel)]="newRun.start_date" placeholder="2022-01-01">
          </mat-form-field>

          <mat-form-field appearance="outline">
            <mat-label>End Date</mat-label>
            <input matInput [(ngModel)]="newRun.end_date" placeholder="2024-12-31">
          </mat-form-field>

          <mat-form-field appearance="outline">
            <mat-label>Initial Capital ($)</mat-label>
            <input matInput type="number" [(ngModel)]="newRun.initial_capital">
          </mat-form-field>

          <mat-form-field appearance="outline">
            <mat-label>Run Name (optional)</mat-label>
            <input matInput [(ngModel)]="newRun.run_name">
          </mat-form-field>

          <button mat-flat-button color="primary" (click)="submitRun()" [disabled]="submitting()">
            <mat-icon>play_arrow</mat-icon>
            {{ submitting() ? 'Starting...' : 'Run Backtest' }}
          </button>

          <div class="run-message" *ngIf="runMessage()" [class.success]="!runError()">
            {{ runMessage() }}
          </div>
        </div>
      </mat-expansion-panel>

      <!-- Leaderboard -->
      <div class="card" style="margin-bottom:16px">
        <div class="card-header"><h3>Top Configurations (by Sharpe Ratio)</h3></div>
        <table mat-table [dataSource]="leaderboard()">
          <ng-container matColumnDef="rank">
            <th mat-header-cell *matHeaderCellDef>#</th>
            <td mat-cell *matCellDef="let r; let i = index">{{ i + 1 }}</td>
          </ng-container>
          <ng-container matColumnDef="symbol"><th mat-header-cell *matHeaderCellDef>Symbol</th><td mat-cell *matCellDef="let r">{{ r.symbol }}</td></ng-container>
          <ng-container matColumnDef="ema"><th mat-header-cell *matHeaderCellDef>EMA</th><td mat-cell *matCellDef="let r">{{ r.ema_fast }}/{{ r.ema_slow }}</td></ng-container>
          <ng-container matColumnDef="st_mult"><th mat-header-cell *matHeaderCellDef>ST Mult</th><td mat-cell *matCellDef="let r">{{ r.st_multiplier }}</td></ng-container>
          <ng-container matColumnDef="sharpe"><th mat-header-cell *matHeaderCellDef>Sharpe</th><td mat-cell *matCellDef="let r" class="profit">{{ r.sharpe_ratio | number:'1.3-3' }}</td></ng-container>
          <ng-container matColumnDef="return"><th mat-header-cell *matHeaderCellDef>Return%</th><td mat-cell *matCellDef="let r" [class]="(r.total_return || 0) >= 0 ? 'profit' : 'loss'">{{ r.total_return | number:'1.2-2' }}%</td></ng-container>
          <ng-container matColumnDef="max_dd"><th mat-header-cell *matHeaderCellDef>Max DD%</th><td mat-cell *matCellDef="let r" class="loss">{{ r.max_drawdown | number:'1.2-2' }}%</td></ng-container>
          <ng-container matColumnDef="win_rate"><th mat-header-cell *matHeaderCellDef>Win Rate</th><td mat-cell *matCellDef="let r">{{ r.win_rate | number:'1.1-1' }}%</td></ng-container>
          <ng-container matColumnDef="trades"><th mat-header-cell *matHeaderCellDef>Trades</th><td mat-cell *matCellDef="let r">{{ r.total_trades }}</td></ng-container>
          <ng-container matColumnDef="actions">
            <th mat-header-cell *matHeaderCellDef></th>
            <td mat-cell *matCellDef="let r">
              <a mat-icon-button [routerLink]="['/backtests', r.id]" title="View Details">
                <mat-icon>open_in_new</mat-icon>
              </a>
            </td>
          </ng-container>
          <tr mat-header-row *matHeaderRowDef="leaderCols"></tr>
          <tr mat-row *matRowDef="let row; columns: leaderCols;"></tr>
        </table>
      </div>

      <!-- All runs -->
      <div class="card">
        <div class="card-header"><h3>All Backtest Runs</h3></div>
        <table mat-table [dataSource]="runs()">
          <ng-container matColumnDef="id"><th mat-header-cell *matHeaderCellDef>ID</th><td mat-cell *matCellDef="let r">{{ r.id }}</td></ng-container>
          <ng-container matColumnDef="name"><th mat-header-cell *matHeaderCellDef>Name</th><td mat-cell *matCellDef="let r" style="max-width:200px;overflow:hidden;text-overflow:ellipsis">{{ r.run_name || '—' }}</td></ng-container>
          <ng-container matColumnDef="engine"><th mat-header-cell *matHeaderCellDef>Engine</th><td mat-cell *matCellDef="let r"><span class="badge badge-open">{{ r.engine }}</span></td></ng-container>
          <ng-container matColumnDef="symbol"><th mat-header-cell *matHeaderCellDef>Symbol</th><td mat-cell *matCellDef="let r">{{ r.symbol }}</td></ng-container>
          <ng-container matColumnDef="period"><th mat-header-cell *matHeaderCellDef>Period</th><td mat-cell *matCellDef="let r">{{ r.start_date }} → {{ r.end_date }}</td></ng-container>
          <ng-container matColumnDef="status">
            <th mat-header-cell *matHeaderCellDef>Status</th>
            <td mat-cell *matCellDef="let r">
              <div class="status-cell">
                <mat-progress-spinner *ngIf="r.status === 'running'" diameter="14" mode="indeterminate"></mat-progress-spinner>
                <span class="badge" [ngClass]="getStatusClass(r.status)">{{ r.status }}</span>
              </div>
            </td>
          </ng-container>
          <ng-container matColumnDef="sharpe"><th mat-header-cell *matHeaderCellDef>Sharpe</th><td mat-cell *matCellDef="let r">{{ r.sharpe_ratio != null ? (r.sharpe_ratio | number:'1.3-3') : '—' }}</td></ng-container>
          <ng-container matColumnDef="return"><th mat-header-cell *matHeaderCellDef>Return%</th><td mat-cell *matCellDef="let r" [class]="(r.total_return || 0) >= 0 ? 'profit' : 'loss'">{{ r.total_return != null ? ((r.total_return | number:'1.2-2') + '%') : '—' }}</td></ng-container>
          <ng-container matColumnDef="created_at"><th mat-header-cell *matHeaderCellDef>Created</th><td mat-cell *matCellDef="let r">{{ r.created_at | date:'MM/dd HH:mm' }}</td></ng-container>
          <ng-container matColumnDef="actions">
            <th mat-header-cell *matHeaderCellDef></th>
            <td mat-cell *matCellDef="let r">
              <a mat-icon-button [routerLink]="['/backtests', r.id]" title="View Details">
                <mat-icon>open_in_new</mat-icon>
              </a>
            </td>
          </ng-container>
          <tr mat-header-row *matHeaderRowDef="runCols"></tr>
          <tr mat-row *matRowDef="let row; columns: runCols;"></tr>
        </table>
      </div>
    </div>
  `,
  styles: [`
    .run-form {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      align-items: flex-start;
      padding: 8px 0;

      mat-form-field { min-width: 160px; }
    }

    .run-message {
      padding: 8px 12px;
      border-radius: 4px;
      font-size: 13px;
      background: rgba(88, 166, 255, 0.1);
      color: var(--color-neutral);
      border: 1px solid rgba(88, 166, 255, 0.3);

      &.success { color: var(--color-profit); background: rgba(38, 166, 65, 0.1); border-color: rgba(38, 166, 65, 0.3); }
    }

    .status-cell {
      display: flex;
      align-items: center;
      gap: 6px;
    }
  `],
})
export class BacktestsComponent implements OnInit {
  leaderCols = ['rank', 'symbol', 'ema', 'st_mult', 'sharpe', 'return', 'max_dd', 'win_rate', 'trades', 'actions'];
  runCols = ['id', 'name', 'engine', 'symbol', 'period', 'status', 'sharpe', 'return', 'created_at', 'actions'];

  leaderboard = signal<BacktestRun[]>([]);
  runs = signal<BacktestRun[]>([]);
  submitting = signal(false);
  runMessage = signal('');
  runError = signal(false);

  newRun: BacktestRunRequest & { run_name?: string } = {
    engine: 'backtestingpy',
    symbol: 'BTCUSDT',
    interval: '60',
    start_date: '2022-01-01',
    end_date: '2024-12-31',
    initial_capital: 10000,
    params: {},
    run_name: '',
  };

  constructor(private btService: BacktestService) {}

  ngOnInit(): void {
    this.loadAll();
  }

  loadAll(): void {
    this.btService.getLeaderboard().subscribe(d => this.leaderboard.set(d));
    this.btService.getBacktests().subscribe(d => this.runs.set(d.items));
  }

  submitRun(): void {
    this.submitting.set(true);
    this.runMessage.set('');
    this.btService.runBacktest(this.newRun).subscribe({
      next: (r) => {
        this.runMessage.set(r.message);
        this.runError.set(false);
        this.submitting.set(false);
        setTimeout(() => this.loadAll(), 2000);
      },
      error: (e) => {
        this.runMessage.set('Error: ' + e.message);
        this.runError.set(true);
        this.submitting.set(false);
      },
    });
  }

  getStatusClass(status: string): string {
    const map: Record<string, string> = {
      done: 'badge-long',
      running: 'badge-open',
      pending: 'badge-closed',
      failed: 'badge-short',
    };
    return map[status] || 'badge-closed';
  }
}
