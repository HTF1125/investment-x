/**
 * Lightweight Charts theme configuration.
 * Maps Investment-X design tokens to LC chart options.
 */
import { ColorType, CrosshairMode, type DeepPartial, type ChartOptions } from 'lightweight-charts';

const MONO = '"Space Mono", "SF Mono", "Fira Code", monospace';

export interface TechnicalsColors {
  ema21: string;
  ema55: string;
  tenkan: string;
  kijun: string;
  cloudFill: string;
  cloudLine: string;
  macdLine: string;
  macdSignal: string;
  macdHistPos: string;
  macdHistNeg: string;
  rocPos: string;
  rocNeg: string;
  candleUp: string;
  candleDown: string;
  text: string;
  textDim: string;
  grid: string;
  divider: string;
  crosshair: string;
  tooltipBg: string;
  tooltipBorder: string;
}

const DARK: TechnicalsColors = {
  ema21: 'rgba(200,200,210,0.6)',
  ema55: 'rgba(220,75,75,0.6)',
  tenkan: 'rgba(80,170,200,0.4)',
  kijun: 'rgba(160,110,60,0.45)',
  cloudFill: 'rgba(80,180,200,0.06)',
  cloudLine: 'rgba(80,180,200,0.15)',
  macdLine: 'rgba(0,180,150,0.8)',
  macdSignal: 'rgba(220,100,50,0.6)',
  macdHistPos: 'rgba(0,180,150,0.5)',
  macdHistNeg: 'rgba(0,180,150,0.25)',
  rocPos: 'rgba(0,180,150,0.45)',
  rocNeg: 'rgba(220,80,80,0.45)',
  candleUp: '#4ade80',
  candleDown: '#f87171',
  text: 'rgba(200,200,210,0.55)',
  textDim: 'rgba(200,200,210,0.3)',
  grid: 'rgba(255,255,255,0.03)',
  divider: 'rgba(255,255,255,0.06)',
  crosshair: 'rgba(200,200,210,0.25)',
  tooltipBg: 'rgba(12,14,22,0.95)',
  tooltipBorder: 'rgba(255,255,255,0.08)',
};

const LIGHT: TechnicalsColors = {
  ema21: 'rgba(30,30,40,0.5)',
  ema55: 'rgba(200,50,50,0.6)',
  tenkan: 'rgba(40,130,170,0.4)',
  kijun: 'rgba(140,85,35,0.45)',
  cloudFill: 'rgba(60,150,180,0.07)',
  cloudLine: 'rgba(60,150,180,0.15)',
  macdLine: 'rgba(0,150,130,0.8)',
  macdSignal: 'rgba(200,80,40,0.6)',
  macdHistPos: 'rgba(0,160,130,0.5)',
  macdHistNeg: 'rgba(0,160,130,0.25)',
  rocPos: 'rgba(0,160,130,0.45)',
  rocNeg: 'rgba(200,60,60,0.45)',
  candleUp: '#16a34a',
  candleDown: '#dc2626',
  text: 'rgba(40,40,45,0.55)',
  textDim: 'rgba(40,40,45,0.3)',
  grid: 'rgba(0,0,0,0.03)',
  divider: 'rgba(0,0,0,0.06)',
  crosshair: 'rgba(40,40,45,0.25)',
  tooltipBg: 'rgba(255,254,251,0.95)',
  tooltipBorder: 'rgba(0,0,0,0.08)',
};

export function getColors(theme: 'light' | 'dark'): TechnicalsColors {
  return theme === 'dark' ? DARK : LIGHT;
}

export function getChartOptions(theme: 'light' | 'dark'): DeepPartial<ChartOptions> {
  const c = getColors(theme);
  return {
    layout: {
      background: { type: ColorType.Solid, color: 'transparent' },
      textColor: c.text,
      fontFamily: MONO,
      fontSize: 11,
    },
    grid: {
      vertLines: { color: c.grid },
      horzLines: { color: c.grid },
    },
    crosshair: {
      mode: CrosshairMode.Normal,
      vertLine: { color: c.crosshair, width: 1, style: 3, labelBackgroundColor: c.tooltipBg },
      horzLine: { color: c.crosshair, width: 1, style: 3, labelBackgroundColor: c.tooltipBg },
    },
    rightPriceScale: {
      borderVisible: false,
      scaleMargins: { top: 0.05, bottom: 0.05 },
    },
    timeScale: {
      borderVisible: false,
      timeVisible: false,
      rightOffset: 5,
    },
    handleScale: { axisPressedMouseMove: { time: true, price: true } },
    handleScroll: { vertTouchDrag: false },
  };
}

/** Chart options for sub-panes (MACD, ROC) — no time labels, smaller margins */
export function getSubPaneOptions(theme: 'light' | 'dark'): DeepPartial<ChartOptions> {
  const base = getChartOptions(theme);
  return {
    ...base,
    timeScale: {
      ...base.timeScale,
      visible: false, // Hide time axis on sub-panes
    },
    rightPriceScale: {
      ...base.rightPriceScale,
      scaleMargins: { top: 0.1, bottom: 0.1 },
    },
  };
}
