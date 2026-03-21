import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';

@Component({
  selector: 'app-metric-card',
  standalone: true,
  imports: [CommonModule, MatIconModule, MatTooltipModule],
  template: `
    <div class="metric-card" [class.positive]="isPositive()" [class.negative]="isNegative()">
      <div class="metric-label">
        {{ label }}
        <mat-icon *ngIf="tooltip" [matTooltip]="tooltip" class="help-icon">info_outline</mat-icon>
      </div>
      <div class="metric-value">
        <span class="value-text">{{ formattedValue }}</span>
        <span *ngIf="unit" class="value-unit">{{ unit }}</span>
      </div>
      <div *ngIf="subtitle" class="metric-subtitle">{{ subtitle }}</div>
    </div>
  `,
  styles: [`
    .metric-card {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 8px;
      padding: 14px 16px;
      transition: border-color 0.15s;

      &:hover { border-color: var(--text-muted); }
      &.positive { border-top: 2px solid var(--color-profit); }
      &.negative { border-top: 2px solid var(--color-loss); }
    }

    .metric-label {
      display: flex;
      align-items: center;
      gap: 4px;
      font-size: 11px;
      font-weight: 600;
      color: var(--text-secondary);
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-bottom: 8px;

      .help-icon {
        font-size: 13px;
        width: 13px;
        height: 13px;
        color: var(--text-muted);
        cursor: help;
      }
    }

    .metric-value {
      display: flex;
      align-items: baseline;
      gap: 4px;

      .value-text {
        font-size: 22px;
        font-weight: 700;
        color: var(--text-primary);
        line-height: 1;
      }

      .value-unit {
        font-size: 12px;
        color: var(--text-secondary);
      }
    }

    .metric-subtitle {
      font-size: 11px;
      color: var(--text-muted);
      margin-top: 4px;
    }
  `],
})
export class MetricCardComponent {
  @Input() label = '';
  @Input() value: number | string | null = null;
  @Input() unit = '';
  @Input() format: 'number' | 'percent' | 'currency' | 'duration' | 'raw' = 'number';
  @Input() decimals = 2;
  @Input() tooltip = '';
  @Input() subtitle = '';
  @Input() colorize = false;  // apply green/red based on sign

  get formattedValue(): string {
    if (this.value === null || this.value === undefined) return '—';
    if (typeof this.value === 'string') return this.value;

    const n = this.value as number;
    switch (this.format) {
      case 'percent': return `${n >= 0 ? '+' : ''}${n.toFixed(this.decimals)}%`;
      case 'currency': return `$${Math.abs(n).toLocaleString('en', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
      case 'duration': return this.formatDuration(n);
      case 'number': return n.toFixed(this.decimals);
      default: return String(n);
    }
  }

  isPositive(): boolean {
    return this.colorize && typeof this.value === 'number' && this.value > 0;
  }

  isNegative(): boolean {
    return this.colorize && typeof this.value === 'number' && this.value < 0;
  }

  private formatDuration(secs: number): string {
    if (secs < 3600) return `${Math.round(secs / 60)}m`;
    if (secs < 86400) return `${(secs / 3600).toFixed(1)}h`;
    return `${(secs / 86400).toFixed(1)}d`;
  }
}
