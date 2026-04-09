/**
 * Pure technical indicator computation functions.
 * Extracted from Technicals.tsx for reuse with Lightweight Charts.
 */

export function sma(arr: number[], window: number): (number | null)[] {
  const out: (number | null)[] = [];
  let sum = 0;
  for (let i = 0; i < arr.length; i++) {
    sum += arr[i];
    if (i >= window) sum -= arr[i - window];
    out.push(i >= window - 1 ? sum / window : null);
  }
  return out;
}

export function ema(arr: number[], period: number): (number | null)[] {
  const k = 2 / (period + 1);
  const out: (number | null)[] = [];
  let prev: number | null = null;
  for (let i = 0; i < arr.length; i++) {
    if (i < period - 1) { out.push(null); continue; }
    if (prev === null) {
      let sum = 0;
      for (let j = i - period + 1; j <= i; j++) sum += arr[j];
      prev = sum / period;
    } else {
      prev = arr[i] * k + prev * (1 - k);
    }
    out.push(prev);
  }
  return out;
}

export function hlMidpoint(high: number[], low: number[], period: number): (number | null)[] {
  const out: (number | null)[] = [];
  for (let i = 0; i < high.length; i++) {
    if (i < period - 1) { out.push(null); continue; }
    let hi = -Infinity, lo = Infinity;
    for (let j = i - period + 1; j <= i; j++) { hi = Math.max(hi, high[j]); lo = Math.min(lo, low[j]); }
    out.push((hi + lo) / 2);
  }
  return out;
}

export function addDays(dateStr: string, n: number): string {
  const d = new Date(dateStr + 'T12:00:00');
  d.setDate(d.getDate() + n);
  return d.toISOString().slice(0, 10);
}

export interface IchimokuResult {
  tenkan: (number | null)[];
  kijun: (number | null)[];
  senkouA: (number | null)[];
  senkouB: (number | null)[];
  extDates: string[];
}

export function ichimoku(
  dates: string[], high: number[], low: number[], close: number[],
  displacement = 26,
): IchimokuResult {
  const n = close.length;
  const tenkan = hlMidpoint(high, low, 9);
  const kijun = hlMidpoint(high, low, 26);
  const senkouBRaw = hlMidpoint(high, low, 52);
  const senkouA: (number | null)[] = [];
  const senkouB: (number | null)[] = [];

  for (let i = 0; i < n + displacement; i++) {
    const src = i - displacement;
    if (src < 0 || src >= n) { senkouA.push(null); senkouB.push(null); continue; }
    const t = tenkan[src], k = kijun[src];
    senkouA.push(t != null && k != null ? (t + k) / 2 : null);
    senkouB.push(senkouBRaw[src]);
  }

  const extDates = [...dates];
  if (n > 0) {
    const last = dates[n - 1];
    for (let i = 1; i <= displacement; i++) extDates.push(addDays(last, i));
  }

  return { tenkan, kijun, senkouA, senkouB, extDates };
}

export interface MacdResult {
  macdLine: (number | null)[];
  signal: (number | null)[];
  histogram: (number | null)[];
}

export function macd(close: number[], fast = 12, slow = 26, sig = 9): MacdResult {
  const emaFast = ema(close, fast);
  const emaSlow = ema(close, slow);
  const macdLine: (number | null)[] = close.map((_, i) =>
    emaFast[i] != null && emaSlow[i] != null ? emaFast[i]! - emaSlow[i]! : null
  );
  const macdValid = macdLine.filter(v => v != null) as number[];
  const sigEma = ema(macdValid, sig);
  const signal: (number | null)[] = [];
  let vi = 0;
  for (let i = 0; i < close.length; i++) {
    if (macdLine[i] != null) { signal.push(sigEma[vi++]); } else { signal.push(null); }
  }
  const histogram: (number | null)[] = macdLine.map((m, i) =>
    m != null && signal[i] != null ? m - signal[i]! : null
  );
  return { macdLine, signal, histogram };
}

export function roc(close: number[], smaPeriod = 9): (number | null)[] {
  const raw: number[] = close.map((c, i) => i === 0 ? 0 : ((c - close[i - 1]) / close[i - 1]) * 100);
  return sma(raw, smaPeriod);
}

/** Convert column-oriented API data to row-oriented LC format. */
export function toOHLC(dates: string[], open: number[], high: number[], low: number[], close: number[]) {
  return dates.map((d, i) => ({
    time: d as any, // LC Time type accepts date strings
    open: open[i],
    high: high[i],
    low: low[i],
    close: close[i],
  }));
}

export function toLineData(dates: string[], values: (number | null)[]) {
  const out: { time: any; value: number }[] = [];
  for (let i = 0; i < dates.length; i++) {
    if (values[i] != null) {
      out.push({ time: dates[i], value: values[i]! });
    }
  }
  return out;
}

export function toHistogramData(dates: string[], values: (number | null)[], posColor: string, negColor: string) {
  const out: { time: any; value: number; color: string }[] = [];
  for (let i = 0; i < dates.length; i++) {
    if (values[i] != null) {
      out.push({
        time: dates[i],
        value: values[i]!,
        color: values[i]! >= 0 ? posColor : negColor,
      });
    }
  }
  return out;
}
