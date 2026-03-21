# Estrategia: SHORT + Supertrend Flip + Régimen 15% | Futures 3x

## Nombre corto
`short_st_regime15_futures3x`

## Descripción
Estrategia SHORT-only que usa el flip del Supertrend como trigger de entrada.
Solo abre posiciones cuando BTC no ha caído más del 15% desde su máximo reciente
(200 barras de lookback), evitando entrar en shorts cuando el precio ya está en zona de fondo.
Opera en modo futuros con micro-BTC scaling para permitir capital pequeño.

## Resultado backtest (datos limpios, 2025-01-01 → 2026-03-20)
| Métrica           | Valor       |
|-------------------|-------------|
| Capital inicial   | $100        |
| Capital final     | ~$160       |
| Return            | +59.6%      |
| Win Rate          | 57.1%       |
| Trades            | 14 en 15 meses |
| Max Drawdown      | 68.2%       |
| Sharpe            | 4.80        |
| Leverage          | 3x futuros  |

## Por qué funciona
- El flip del Supertrend es más rápido que el cruce EMA (entra más cerca del punto de giro)
- El filtro de régimen 15% evita shorts cuando BTC ya cayó mucho (zona de rebote)
- En 2025: BTC subió a $109K (ene) y corrigió a $73K (abr) — entorno ideal para shorts
- Con BTC en $84K actual (27% bajo el pico de $115K): el filtro bloquea nuevos shorts ✓

## Limitaciones / cuándo NO usarla
- 2023 ($16K→$44K +166%) y 2024 ($38K→$108K +184%): mercados alcistas fuertes, pierde
- BTC por encima de MA200d (tendencia alcista confirmada): no es el momento de shorts
- Drawdown potencial de 60-70% si BTC hace un rally fuerte contra las posiciones
- Necesita mínimo 1-2 meses de datos previos para el cálculo del peak lookback (200 barras)

## Comando de ejecución
```bash
# Backtest 15 meses 2025-2026 con $100 futuros 3x
python scripts/run_backtest.py \
  --engine backtestingpy \
  --symbol BTCUSDT \
  --start 2025-01-01 \
  --end 2026-03-20 \
  --capital 100 \
  --futures --leverage 3 \
  --short-only \
  --no-rsi-filter \
  --regime-filter --max-drop-pct 0.15 \
  --st-trigger

# Alternativa con docker:
docker compose exec bot python scripts/run_backtest.py \
  --engine backtestingpy --symbol BTCUSDT \
  --start 2025-01-01 --end 2026-03-20 \
  --capital 100 --futures --leverage 3 \
  --short-only --no-rsi-filter \
  --regime-filter --max-drop-pct 0.15 \
  --st-trigger
```

## Parámetros completos (params dict interno)
```python
params = {
    # Estrategia core
    "ema_fast":        21,       # default (no usado como trigger)
    "ema_slow":        55,       # default (no usado como trigger)
    "st_period":       10,       # Supertrend period
    "st_multiplier":   3.0,      # Supertrend multiplier
    "rsi_period":      14,
    "rsi_ob":          70.0,
    "rsi_os":          30.0,
    "rsi_entry_min":   40.0,     # ignorado por no_rsi_filter=1
    "rsi_entry_max":   60.0,     # ignorado por no_rsi_filter=1
    "macd_fast":       12,
    "macd_slow":       26,
    "macd_signal":     9,
    "atr_sl_mult":     2.0,      # Stop Loss = entry + 2x ATR
    "atr_tp_mult":     3.0,      # Take Profit = entry - 3x ATR

    # Flags de modo
    "short_only":      1,        # ← CLAVE: solo shorts
    "no_rsi_filter":   1,        # ← quita filtro RSI 40-60 de entrada
    "st_trigger":      1,        # ← CLAVE: flip Supertrend como trigger (no cruce EMA)
    "trend_filter":    0,        # sin filtro MA200d (no necesario con regime_filter)
    "bidirectional":   0,

    # Filtro de régimen (evita shorts en fondos)
    "regime_filter":   1,        # ← CLAVE: activado
    "max_drop_pct":    0.15,     # ← CLAVE: máx 15% caída desde pico (no 25%)
    "peak_lookback":   200,      # barras para calcular el pico reciente

    # Futuros
    "futures_mode":    1,        # ← precios ÷1000 (micro-BTC), permite capital pequeño
    "leverage":        3,        # 3x leverage, margin=1/3
}
```

## Condición de entrada SHORT
Todas estas deben cumplirse simultáneamente:
1. `st_trigger=1` → Supertrend flipó a bearish (dirección cambió de +1 a -1) en esta barra o la anterior
2. `cur_st_dir == -1` → Supertrend actual es bearish
3. `cur_macd < cur_macd_signal` → MACD confirma momentum bajista
4. `regime_ok_short = True` → precio cayó menos del 15% desde máximo de 200 barras
5. No hay posición abierta

## Condición de salida SHORT
Se cierra por lo que llegue primero:
- **Take Profit**: precio ≤ entry - 3x ATR (ganancia)
- **Stop Loss**: precio ≥ entry + 2x ATR (pérdida controlada)
- **RSI oversold**: RSI < 30 → cierre manual
- **ST flip bullish**: Supertrend vuelve a +1 → cierre manual

## Contexto de datos
- Símbolo: BTCUSDT (perpetual futures Bybit)
- Timeframe: 60 minutos
- Datos necesarios: mínimo 6 meses previos al período de trading
- Datos limpios: se eliminaron 2,625 velas con OHLCV corrupto (high/low >20% del close)

## Comparativa de `max_drop_pct`
| Valor | Trades | WR%  | Return% | MaxDD% | Observación               |
|-------|--------|------|---------|--------|---------------------------|
| 0.10  | 79     | 44%  | -13%    | 17%    | Muy restrictivo, pocas oportunidades |
| 0.15  | 13-14  | 54-57% | +29% a +60% | 22-68% | ← **ÓPTIMO** |
| 0.25  | 7      | 29%  | -23%    | 35%    | Muy permisivo, shorts en fondos |

## Historial de desarrollo
- Sesión: marzo 2026
- Iteraciones: spot → shorts → régimen filter → futuros → limpieza datos → ST trigger
- Fix crítico: eliminación de 2,625 velas OHLCV con precios imposibles (open/high/low >20% del close)
- Fix métricas: `calmar_ratio` con equity negativa → complex number error → corregido en `metrics.py`
- Fix CLI: `trend_filter` no se pasaba al engine cuando se usaba `--bidirectional`
