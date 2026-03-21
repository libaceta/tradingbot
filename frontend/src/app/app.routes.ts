import { Routes } from '@angular/router';

export const routes: Routes = [
  { path: '', redirectTo: '/dashboard', pathMatch: 'full' },
  {
    path: 'dashboard',
    loadComponent: () => import('./pages/dashboard/dashboard.component').then(m => m.DashboardComponent),
  },
  {
    path: 'trades',
    loadComponent: () => import('./pages/trades/trades.component').then(m => m.TradesComponent),
  },
  {
    path: 'chart',
    loadComponent: () => import('./pages/chart/chart.component').then(m => m.ChartComponent),
  },
  {
    path: 'monthly-returns',
    loadComponent: () => import('./pages/monthly-returns/monthly-returns.component').then(m => m.MonthlyReturnsComponent),
  },
  {
    path: 'backtests',
    loadComponent: () => import('./pages/backtests/backtests.component').then(m => m.BacktestsComponent),
  },
  {
    path: 'backtests/:id',
    loadComponent: () => import('./pages/backtests/backtest-detail/backtest-detail.component').then(m => m.BacktestDetailComponent),
  },
  { path: '**', redirectTo: '/dashboard' },
];
