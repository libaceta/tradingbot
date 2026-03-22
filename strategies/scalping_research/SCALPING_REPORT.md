# Scalping Strategy Research Report
*Generated: 2026-03-22 02:11 UTC*

---

## 1. Executive Summary

Backtested **10 scalping strategies** across **2 symbols** (BTCUSDT, ETHUSDT) on **2 timeframes** (5m, 15m) using **90 days** of Bybit historical data.

- Total backtests run: **80**
- Valid results: **80**
- Promising strategies (Sharpe>1.5, PF>1.3, WR>45%): **0**

### Top 3 Strategies
1. **S10_HeikinAshi** on ETHUSDT 15m | Score=2.3200, Sharpe=2.48, WR=48.2%, Return=135.8%
2. **S10_HeikinAshi** on ETHUSDT 15m | Score=1.5774, Sharpe=2.20, WR=48.2%, Return=385.2%
3. **S10_HeikinAshi** on BTCUSDT 15m | Score=0.2310, Sharpe=0.35, WR=46.6%, Return=12.0%

---

## 2. Methodology

### Data
- Exchange: Bybit (public REST API v5)
- Symbols: BTCUSDT, ETHUSDT (USDT perpetual futures)
- Timeframes: 5m, 15m
- History: 90 days
- Batch size: 200 candles with 0.25s delay

### Backtesting Assumptions
- Initial equity: $10,000 USDT
- Risk per trade: 1% and 2% of equity (tested both)
- Fee: 0.055% taker per side (0.110% round trip) - Bybit USDT perp rates
- Max 1 position at a time
- Position sizing: risk_usdt / (sl_atr_distance in price)
- No look-ahead bias: signals use shift(1)
- Entries at open of next bar after signal
- Exit: SL/TP hit via bar's high/low; open position closed at final bar's close
- Minimum 30 trades required for valid result

### Scoring
```
Score = Sharpe * (1 - max_dd/100) * profit_factor
```
Higher is better. Penalizes high drawdown.

---

## 3. Results Table (All Valid Strategies)

| Rank | Strategy | Symbol | TF | Risk | Trades | WR% | Return% | MaxDD% | Sharpe | Sortino | PF | Calmar | Score |
|------|----------|--------|----|------|--------|-----|---------|--------|--------|---------|-----|--------|-------|
| 1 | S10_HeikinAshi | ETHUSDT | 15m | 1% | 771 | 48.2 | 135.8 | 22.5 | 2.48 | 10.08 | 1.207 | 6.04 | 2.3200 |
| 2 | S10_HeikinAshi | ETHUSDT | 15m | 2% | 771 | 48.2 | 385.2 | 40.7 | 2.20 | 4.83 | 1.207 | 9.47 | 1.5774 |
| 3 | S10_HeikinAshi | BTCUSDT | 15m | 1% | 776 | 46.6 | 12.0 | 35.6 | 0.35 | 2.02 | 1.026 | 0.34 | 0.2310 |
| 4 | S10_HeikinAshi | BTCUSDT | 15m | 2% | 776 | 46.6 | 9.5 | 60.3 | 0.15 | 0.55 | 1.012 | 0.16 | 0.0619 |
| 5 | S2_RSI2_MeanRev | BTCUSDT | 5m | 2% | 1199 | 37.1 | -100.0 | 100.0 | -6.30 | -5.37 | 0.176 | -1.00 | -0.0000 |
| 6 | S10_HeikinAshi | BTCUSDT | 5m | 2% | 2632 | 46.6 | -100.0 | 100.0 | -4.37 | -3.96 | 0.511 | -1.00 | -0.0000 |
| 7 | S2_RSI2_MeanRev | ETHUSDT | 5m | 2% | 1191 | 41.0 | -100.0 | 100.0 | -6.13 | -5.34 | 0.285 | -1.00 | -0.0000 |
| 8 | S7_Keltner | BTCUSDT | 5m | 2% | 825 | 38.4 | -100.0 | 100.0 | -6.51 | -5.62 | 0.200 | -1.00 | -0.0001 |
| 9 | S4_BB_RSI | BTCUSDT | 5m | 2% | 991 | 41.6 | -100.0 | 100.0 | -5.20 | -4.84 | 0.402 | -1.00 | -0.0002 |
| 10 | S2_RSI2_MeanRev | BTCUSDT | 5m | 1% | 1199 | 37.1 | -100.0 | 100.0 | -9.29 | -8.00 | 0.156 | -1.00 | -0.0003 |
| 11 | S3_Supertrend | BTCUSDT | 5m | 2% | 413 | 31.7 | -99.9 | 99.9 | -5.07 | -4.62 | 0.203 | -1.00 | -0.0007 |
| 12 | S6_StochRSI_EMA | BTCUSDT | 5m | 2% | 637 | 35.8 | -99.9 | 99.9 | -5.70 | -5.54 | 0.325 | -1.00 | -0.0015 |
| 13 | S5_MACD_EMA | BTCUSDT | 5m | 2% | 649 | 36.5 | -99.8 | 99.8 | -4.49 | -4.60 | 0.440 | -1.00 | -0.0038 |
| 14 | S10_HeikinAshi | BTCUSDT | 5m | 1% | 2632 | 46.6 | -99.9 | 99.9 | -6.49 | -5.91 | 0.477 | -1.00 | -0.0041 |
| 15 | S8_VWAP_Bounce | BTCUSDT | 5m | 2% | 637 | 39.9 | -99.8 | 99.8 | -4.84 | -4.61 | 0.389 | -1.00 | -0.0043 |
| 16 | S2_RSI2_MeanRev | ETHUSDT | 5m | 1% | 1191 | 41.0 | -99.7 | 99.7 | -9.05 | -8.30 | 0.299 | -1.00 | -0.0079 |
| 17 | S4_BB_RSI | ETHUSDT | 5m | 2% | 992 | 46.0 | -99.6 | 99.6 | -3.94 | -4.12 | 0.612 | -1.00 | -0.0091 |
| 18 | S3_Supertrend | ETHUSDT | 5m | 2% | 373 | 31.6 | -99.4 | 99.4 | -5.34 | -5.45 | 0.313 | -1.00 | -0.0104 |
| 19 | S7_Keltner | ETHUSDT | 5m | 2% | 740 | 43.0 | -99.2 | 99.2 | -4.77 | -4.86 | 0.494 | -1.00 | -0.0181 |
| 20 | S9_EMA_Ribbon | BTCUSDT | 5m | 2% | 924 | 43.3 | -99.2 | 99.3 | -4.58 | -4.79 | 0.552 | -1.00 | -0.0183 |
| 21 | S7_Keltner | BTCUSDT | 5m | 1% | 825 | 38.4 | -99.1 | 99.1 | -9.18 | -8.39 | 0.228 | -1.00 | -0.0192 |
| 22 | S6_StochRSI_EMA | ETHUSDT | 5m | 2% | 612 | 36.9 | -99.1 | 99.2 | -5.29 | -5.82 | 0.455 | -1.00 | -0.0201 |
| 23 | S8_VWAP_Bounce | ETHUSDT | 5m | 2% | 674 | 40.1 | -98.8 | 99.0 | -4.42 | -4.76 | 0.529 | -1.00 | -0.0241 |
| 24 | S10_HeikinAshi | ETHUSDT | 5m | 2% | 2453 | 48.1 | -97.7 | 98.8 | -2.82 | -2.95 | 0.782 | -0.99 | -0.0270 |
| 25 | S4_BB_RSI | BTCUSDT | 5m | 1% | 991 | 41.6 | -98.8 | 98.9 | -7.75 | -7.79 | 0.385 | -1.00 | -0.0339 |
| 26 | S9_EMA_Ribbon | ETHUSDT | 5m | 2% | 943 | 41.5 | -98.2 | 98.5 | -4.11 | -4.91 | 0.650 | -1.00 | -0.0415 |
| 27 | S3_Supertrend | BTCUSDT | 5m | 1% | 413 | 31.7 | -97.2 | 97.3 | -7.59 | -7.42 | 0.216 | -1.00 | -0.0448 |
| 28 | S5_MACD_EMA | ETHUSDT | 5m | 2% | 641 | 37.8 | -97.5 | 97.8 | -3.77 | -4.42 | 0.582 | -1.00 | -0.0474 |
| 29 | S1_EMA_Cross | ETHUSDT | 5m | 2% | 438 | 35.8 | -97.6 | 97.6 | -5.35 | -6.04 | 0.426 | -1.00 | -0.0538 |
| 30 | S1_EMA_Cross | BTCUSDT | 5m | 2% | 429 | 41.3 | -96.8 | 97.0 | -4.57 | -4.86 | 0.465 | -1.00 | -0.0633 |
| 31 | S6_StochRSI_EMA | BTCUSDT | 5m | 1% | 637 | 35.8 | -96.9 | 97.0 | -8.08 | -8.82 | 0.347 | -1.00 | -0.0854 |
| 32 | S2_RSI2_MeanRev | BTCUSDT | 15m | 2% | 369 | 41.5 | -93.8 | 94.4 | -5.75 | -6.79 | 0.422 | -0.99 | -0.1358 |
| 33 | S5_MACD_EMA | BTCUSDT | 5m | 1% | 649 | 36.5 | -94.9 | 95.3 | -6.52 | -7.67 | 0.456 | -1.00 | -0.1408 |
| 34 | S8_VWAP_Bounce | BTCUSDT | 5m | 1% | 637 | 39.9 | -94.6 | 94.9 | -7.10 | -7.76 | 0.407 | -1.00 | -0.1478 |
| 35 | S3_Supertrend | ETHUSDT | 5m | 1% | 373 | 31.6 | -91.6 | 91.7 | -7.27 | -8.87 | 0.345 | -1.00 | -0.2075 |
| 36 | S4_BB_RSI | ETHUSDT | 5m | 1% | 992 | 46.0 | -93.3 | 93.4 | -5.67 | -7.26 | 0.602 | -1.00 | -0.2255 |
| 37 | S2_RSI2_MeanRev | ETHUSDT | 15m | 2% | 375 | 42.7 | -87.0 | 87.9 | -4.00 | -7.12 | 0.623 | -0.99 | -0.3023 |
| 38 | S7_Keltner | ETHUSDT | 5m | 1% | 740 | 43.0 | -90.3 | 90.7 | -6.67 | -8.58 | 0.515 | -0.99 | -0.3187 |
| 39 | S9_EMA_Ribbon | BTCUSDT | 5m | 1% | 924 | 43.3 | -90.2 | 90.9 | -5.97 | -8.13 | 0.598 | -0.99 | -0.3259 |
| 40 | S6_StochRSI_EMA | ETHUSDT | 5m | 1% | 612 | 36.9 | -90.0 | 90.3 | -6.71 | -9.87 | 0.505 | -1.00 | -0.3277 |
| 41 | S10_HeikinAshi | ETHUSDT | 5m | 1% | 2453 | 48.1 | -81.0 | 87.9 | -3.28 | -5.07 | 0.850 | -0.92 | -0.3386 |
| 42 | S8_VWAP_Bounce | ETHUSDT | 5m | 1% | 674 | 40.1 | -88.5 | 89.2 | -5.84 | -8.25 | 0.563 | -0.99 | -0.3555 |
| 43 | S4_BB_RSI | ETHUSDT | 15m | 2% | 332 | 43.1 | -76.1 | 79.9 | -2.68 | -5.50 | 0.711 | -0.95 | -0.3830 |
| 44 | S9_EMA_Ribbon | ETHUSDT | 5m | 1% | 943 | 41.5 | -85.7 | 86.6 | -4.93 | -8.89 | 0.690 | -0.99 | -0.4566 |
| 45 | S4_BB_RSI | BTCUSDT | 15m | 2% | 338 | 46.5 | -73.6 | 76.1 | -2.74 | -5.69 | 0.706 | -0.97 | -0.4636 |
| 46 | S8_VWAP_Bounce | ETHUSDT | 15m | 2% | 285 | 41.4 | -37.7 | 50.0 | -1.08 | -6.03 | 0.878 | -0.75 | -0.4732 |
| 47 | S5_MACD_EMA | ETHUSDT | 5m | 1% | 641 | 37.8 | -82.9 | 84.2 | -4.82 | -7.79 | 0.628 | -0.98 | -0.4789 |
| 48 | S6_StochRSI_EMA | BTCUSDT | 15m | 2% | 220 | 35.9 | -75.8 | 78.9 | -4.40 | -8.45 | 0.516 | -0.96 | -0.4802 |
| 49 | S5_MACD_EMA | BTCUSDT | 15m | 2% | 205 | 35.1 | -65.4 | 74.4 | -2.98 | -6.84 | 0.632 | -0.88 | -0.4815 |
| 50 | S6_StochRSI_EMA | ETHUSDT | 15m | 2% | 221 | 32.1 | -77.9 | 78.6 | -4.57 | -9.72 | 0.508 | -0.99 | -0.4978 |
| 51 | S1_EMA_Cross | ETHUSDT | 5m | 1% | 438 | 35.8 | -83.8 | 84.0 | -6.52 | -10.44 | 0.479 | -1.00 | -0.5002 |
| 52 | S3_Supertrend | ETHUSDT | 15m | 2% | 125 | 26.4 | -71.9 | 73.0 | -4.33 | -10.02 | 0.432 | -0.98 | -0.5044 |
| 53 | S5_MACD_EMA | ETHUSDT | 15m | 2% | 208 | 35.6 | -45.4 | 52.7 | -1.31 | -6.61 | 0.827 | -0.86 | -0.5133 |
| 54 | S1_EMA_Cross | BTCUSDT | 5m | 1% | 429 | 41.3 | -81.2 | 82.0 | -5.72 | -7.94 | 0.499 | -0.99 | -0.5141 |
| 55 | S3_Supertrend | BTCUSDT | 15m | 2% | 140 | 35.0 | -66.1 | 71.0 | -3.26 | -6.84 | 0.544 | -0.93 | -0.5145 |
| 56 | S8_VWAP_Bounce | BTCUSDT | 15m | 2% | 293 | 40.3 | -66.0 | 67.2 | -2.50 | -6.92 | 0.734 | -0.98 | -0.6022 |
| 57 | S9_EMA_Ribbon | BTCUSDT | 15m | 2% | 302 | 43.0 | -50.9 | 55.7 | -1.68 | -6.00 | 0.818 | -0.91 | -0.6089 |
| 58 | S8_VWAP_Bounce | ETHUSDT | 15m | 1% | 285 | 41.4 | -19.1 | 27.8 | -0.97 | -9.36 | 0.891 | -0.69 | -0.6208 |
| 59 | S1_EMA_Cross | BTCUSDT | 15m | 2% | 164 | 41.5 | -40.8 | 53.1 | -1.77 | -6.09 | 0.752 | -0.77 | -0.6247 |
| 60 | S7_Keltner | BTCUSDT | 15m | 2% | 233 | 42.1 | -69.6 | 69.9 | -3.40 | -8.79 | 0.626 | -1.00 | -0.6409 |
| 61 | S1_EMA_Cross | ETHUSDT | 15m | 2% | 151 | 34.4 | -56.3 | 61.2 | -2.55 | -10.04 | 0.652 | -0.92 | -0.6451 |
| 62 | S9_EMA_Ribbon | ETHUSDT | 15m | 2% | 307 | 41.4 | -46.2 | 46.8 | -1.45 | -11.25 | 0.846 | -0.99 | -0.6512 |
| 63 | S2_RSI2_MeanRev | BTCUSDT | 15m | 1% | 369 | 41.5 | -74.4 | 75.8 | -6.59 | -11.76 | 0.460 | -0.98 | -0.7348 |
| 64 | S5_MACD_EMA | ETHUSDT | 15m | 1% | 208 | 35.6 | -24.5 | 30.0 | -1.30 | -9.81 | 0.831 | -0.82 | -0.7557 |
| 65 | S7_Keltner | ETHUSDT | 15m | 2% | 207 | 43.0 | -51.1 | 52.1 | -2.44 | -9.51 | 0.708 | -0.98 | -0.8259 |
| 66 | S1_EMA_Cross | BTCUSDT | 15m | 1% | 164 | 41.5 | -21.9 | 31.0 | -1.57 | -7.73 | 0.780 | -0.71 | -0.8442 |
| 67 | S9_EMA_Ribbon | ETHUSDT | 15m | 1% | 307 | 41.4 | -24.9 | 25.4 | -1.33 | -15.97 | 0.858 | -0.98 | -0.8531 |
| 68 | S9_EMA_Ribbon | BTCUSDT | 15m | 1% | 302 | 43.0 | -28.3 | 32.6 | -1.57 | -8.67 | 0.833 | -0.87 | -0.8803 |
| 69 | S5_MACD_EMA | BTCUSDT | 15m | 1% | 205 | 35.1 | -39.9 | 48.5 | -2.76 | -10.44 | 0.671 | -0.82 | -0.9532 |
| 70 | S2_RSI2_MeanRev | ETHUSDT | 15m | 1% | 375 | 42.7 | -63.0 | 64.3 | -4.34 | -13.11 | 0.628 | -0.98 | -0.9719 |
| 71 | S4_BB_RSI | ETHUSDT | 15m | 1% | 332 | 43.1 | -50.0 | 54.3 | -3.04 | -10.05 | 0.701 | -0.92 | -0.9753 |
| 72 | S3_Supertrend | BTCUSDT | 15m | 1% | 140 | 35.0 | -40.8 | 45.3 | -3.18 | -9.97 | 0.574 | -0.90 | -0.9969 |
| 73 | S3_Supertrend | ETHUSDT | 15m | 1% | 125 | 26.4 | -46.3 | 47.5 | -4.30 | -16.43 | 0.458 | -0.97 | -1.0348 |
| 74 | S4_BB_RSI | BTCUSDT | 15m | 1% | 338 | 46.5 | -47.4 | 50.0 | -2.92 | -9.86 | 0.710 | -0.95 | -1.0373 |
| 75 | S1_EMA_Cross | ETHUSDT | 15m | 1% | 151 | 34.4 | -33.0 | 37.0 | -2.53 | -16.75 | 0.660 | -0.89 | -1.0527 |
| 76 | S8_VWAP_Bounce | BTCUSDT | 15m | 1% | 293 | 40.3 | -40.2 | 41.3 | -2.38 | -11.27 | 0.754 | -0.97 | -1.0536 |
| 77 | S6_StochRSI_EMA | BTCUSDT | 15m | 1% | 220 | 35.9 | -49.9 | 53.2 | -4.09 | -13.61 | 0.569 | -0.94 | -1.0884 |
| 78 | S6_StochRSI_EMA | ETHUSDT | 15m | 1% | 221 | 32.1 | -52.1 | 52.9 | -4.32 | -16.84 | 0.553 | -0.99 | -1.1268 |
| 79 | S7_Keltner | ETHUSDT | 15m | 1% | 207 | 43.0 | -29.1 | 29.9 | -2.20 | -13.56 | 0.736 | -0.97 | -1.1336 |
| 80 | S7_Keltner | BTCUSDT | 15m | 1% | 233 | 42.1 | -43.9 | 44.2 | -3.29 | -12.90 | 0.644 | -0.99 | -1.1852 |

---

## 4. Top 3 Strategies - Detailed Analysis

### #1: S10_HeikinAshi

- **Symbol**: ETHUSDT
- **Timeframe**: 15m
- **Risk per trade**: 1%
- **Total trades**: 771
- **Win rate**: 48.2%
- **Total return**: 135.8%
- **Max drawdown**: 22.5%
- **Sharpe ratio**: 2.479
- **Sortino ratio**: 10.077
- **Profit factor**: 1.207
- **Calmar ratio**: 6.042
- **Avg trade PnL**: $17.61
- **Composite score**: 2.3200

### #2: S10_HeikinAshi

- **Symbol**: ETHUSDT
- **Timeframe**: 15m
- **Risk per trade**: 2%
- **Total trades**: 771
- **Win rate**: 48.2%
- **Total return**: 385.2%
- **Max drawdown**: 40.7%
- **Sharpe ratio**: 2.203
- **Sortino ratio**: 4.834
- **Profit factor**: 1.207
- **Calmar ratio**: 9.472
- **Avg trade PnL**: $49.97
- **Composite score**: 1.5774

### #3: S10_HeikinAshi

- **Symbol**: BTCUSDT
- **Timeframe**: 15m
- **Risk per trade**: 1%
- **Total trades**: 776
- **Win rate**: 46.6%
- **Total return**: 12.0%
- **Max drawdown**: 35.6%
- **Sharpe ratio**: 0.350
- **Sortino ratio**: 2.018
- **Profit factor**: 1.026
- **Calmar ratio**: 0.337
- **Avg trade PnL**: $1.55
- **Composite score**: 0.2310

---

## 5. Parameter Sensitivity (Top Promising Strategies)

*No parameter variations ran (no strategies met the promising threshold).*

---

## 6. Implementation Recommendations

### Priority Implementation Order

1. **S10_HeikinAshi** — Integrate into FastAPI bot using existing indicator library.
2. **S10_HeikinAshi** — Integrate into FastAPI bot using existing indicator library.
3. **S10_HeikinAshi** — Integrate into FastAPI bot using existing indicator library.

### Bot Integration Notes

- The existing FastAPI bot already has: EMA, RSI, ATR, Supertrend, MACD indicators
- New indicators needed: StochRSI, VWAP (daily-reset), Heikin Ashi, Keltner Channel
- Use Bybit linear perpetuals (same exchange already configured)
- Position sizing formula: `qty = (equity * risk_pct) / (sl_atr_mult * atr_value)`
- Always use taker orders for entries to ensure fills (market orders)
- Consider maker orders (limit) for exits to reduce fees
- Implement per-symbol trade cooldown (at least 1 candle) to avoid over-trading
- Paper-trade on Bybit testnet for at least 2 weeks before live

### Timeframe Recommendation

- **15m** generally shows better risk-adjusted returns than 5m due to lower noise
- **5m** has more trades but higher fee drag
- Consider running 15m as primary with 5m as confirmation

---

## 7. Risk Warnings

1. **Past performance does not guarantee future results.** Crypto markets are highly dynamic.
2. **Fee drag is significant for scalping.** At 0.11% round-trip, strategies with low R:R ratios are disadvantaged.
3. **Slippage not modeled.** Real execution may be worse, especially on 5m with small ATR.
4. **Funding rates not included.** Bybit perpetuals have 8-hourly funding; hold times crossing funding windows incur costs.
5. **Overfitting risk.** More trades = more statistical confidence. Prefer strategies with >100 trades.
6. **Regime dependency.** Trend-following strategies fail in ranging markets and vice versa.
7. **Never risk more than 1% per trade on live capital** until a strategy has proven itself in paper trading.
8. **Always maintain stop-losses.** Do not override automated exits.

---
*Generated by backtest_scalping.py — Bybit USDT Perp data*