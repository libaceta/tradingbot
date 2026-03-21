import { Component, computed } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatListModule } from '@angular/material/list';
import { CommonModule, UpperCasePipe } from '@angular/common';
import { StatusService } from './core/services/status.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    RouterOutlet, RouterLink, RouterLinkActive,
    MatIconModule, MatToolbarModule, MatSidenavModule, MatListModule,
    CommonModule, UpperCasePipe,
  ],
  template: `
    <div class="app-layout">
      <!-- Sidebar -->
      <nav class="sidebar">
        <div class="sidebar-brand">
          <mat-icon class="brand-icon">trending_up</mat-icon>
          <span class="brand-name">TradingBot</span>
        </div>

        <div class="bot-status" [class]="'state-' + botState()"
             [title]="status()?.is_halted ? ('Halted: ' + status()?.halt_reason) : ''">
          <span class="status-dot"></span>
          <div class="status-info">
            <span class="status-state">{{ botState() === 'on' ? 'ON' : botState() === 'off' ? 'OFF' : botState() === 'halted' ? 'HALTED' : 'connecting...' }}</span>
            <span class="status-mode" *ngIf="status()">{{ status()?.mode | uppercase }}</span>
          </div>
        </div>

        <ul class="nav-list">
          <li *ngFor="let item of navItems">
            <a [routerLink]="item.path" routerLinkActive="active" class="nav-item">
              <mat-icon>{{ item.icon }}</mat-icon>
              <span>{{ item.label }}</span>
            </a>
          </li>
        </ul>

        <div class="sidebar-footer">
          <div class="equity-info">
            <span class="equity-label">Balance</span>
            <span class="equity-value">{{ status() ? '$' + (status()!.equity_usdt | number:'1.2-2') : '—' }}</span>
          </div>
        </div>
      </nav>

      <!-- Main content -->
      <main class="main-content">
        <router-outlet />
      </main>
    </div>
  `,
  styles: [`
    .app-layout {
      display: flex;
      height: 100vh;
      overflow: hidden;
    }

    .sidebar {
      width: var(--sidebar-width);
      background: var(--bg-secondary);
      border-right: 1px solid var(--border-color);
      display: flex;
      flex-direction: column;
      flex-shrink: 0;
    }

    .sidebar-brand {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 20px 16px 16px;
      border-bottom: 1px solid var(--border-color);

      .brand-icon { color: #58a6ff; font-size: 22px; }
      .brand-name { font-size: 16px; font-weight: 700; color: var(--text-primary); }
    }

    .bot-status {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 10px 16px;
      cursor: default;

      .status-dot {
        width: 10px; height: 10px;
        border-radius: 50%;
        flex-shrink: 0;
      }

      .status-info {
        display: flex;
        flex-direction: column;
        gap: 1px;
      }

      .status-state {
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 0.8px;
      }

      .status-mode {
        font-size: 10px;
        font-weight: 400;
        color: var(--text-muted);
        letter-spacing: 0.4px;
      }

      &.state-on {
        .status-dot { background: var(--color-profit); animation: pulse 2s infinite; }
        .status-state { color: var(--color-profit); }
      }

      &.state-off {
        .status-dot { background: var(--color-loss); }
        .status-state { color: var(--color-loss); }
      }

      &.state-halted {
        .status-dot { background: #d29922; }
        .status-state { color: #d29922; }
      }

      &.state-connecting {
        .status-dot { background: var(--text-muted); animation: pulse 2s infinite; }
        .status-state { color: var(--text-muted); }
      }
    }

    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.4; }
    }

    .nav-list {
      list-style: none;
      padding: 8px 0;
      flex: 1;
    }

    .nav-item {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 10px 16px;
      color: var(--text-secondary);
      text-decoration: none;
      font-size: 13px;
      font-weight: 500;
      border-radius: 0;
      transition: all 0.15s ease;
      border-left: 3px solid transparent;

      mat-icon { font-size: 18px; width: 18px; height: 18px; }

      &:hover {
        background: var(--bg-tertiary);
        color: var(--text-primary);
      }

      &.active {
        background: rgba(88, 166, 255, 0.08);
        color: #58a6ff;
        border-left-color: #58a6ff;
      }
    }

    .sidebar-footer {
      padding: 12px 16px;
      border-top: 1px solid var(--border-color);
    }

    .equity-info {
      display: flex;
      justify-content: space-between;
      align-items: center;

      .equity-label { font-size: 11px; color: var(--text-muted); }
      .equity-value { font-size: 14px; font-weight: 600; color: var(--text-primary); }
    }

    .main-content {
      flex: 1;
      overflow-y: auto;
      background: var(--bg-primary);
    }
  `],
})
export class AppComponent {
  navItems = [
    { path: '/dashboard', icon: 'dashboard', label: 'Dashboard' },
    { path: '/trades', icon: 'swap_horiz', label: 'Trades' },
    { path: '/chart', icon: 'candlestick_chart', label: 'Chart' },
    { path: '/monthly-returns', icon: 'grid_on', label: 'Monthly Returns' },
    { path: '/backtests', icon: 'science', label: 'Backtests' },
  ];

  status = this.statusService.status;

  botState = computed(() => {
    const s = this.statusService.status();
    if (!s) return 'connecting';
    if (s.is_halted) return 'halted';
    if (s.bot_running) return 'on';
    return 'off';
  });

  constructor(private statusService: StatusService) {
    this.statusService.startPolling();
  }
}
