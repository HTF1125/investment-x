import { describe, it, expect } from 'vitest'
import { applyChartTheme, PlotlyFigure } from '../chartTheme'

// ── Helpers ──

function makeFigure(overrides: Partial<PlotlyFigure> = {}): PlotlyFigure {
  return {
    data: [
      {
        type: 'scatter',
        x: ['2024-01-01', '2024-02-01', '2024-03-01'],
        y: [100, 110, 105],
        name: 'Test Series',
      },
    ],
    layout: {
      title: { text: 'Test Chart' },
      xaxis: { type: 'date' },
      yaxis: {},
    },
    ...overrides,
  }
}

// ── Tests ──

describe('applyChartTheme', () => {
  describe('null / undefined handling', () => {
    it('returns null when given null', () => {
      expect(applyChartTheme(null, 'dark')).toBeNull()
    })

    it('returns undefined when given undefined', () => {
      expect(applyChartTheme(undefined, 'dark')).toBeUndefined()
    })
  })

  describe('structuredClone immutability', () => {
    it('does not mutate the original figure', () => {
      const original = makeFigure()
      const originalJson = JSON.stringify(original)

      applyChartTheme(original, 'dark')

      expect(JSON.stringify(original)).toBe(originalJson)
    })

    it('returns a new object reference', () => {
      const original = makeFigure()
      const result = applyChartTheme(original, 'dark')

      expect(result).not.toBe(original)
    })
  })

  describe('dark theme', () => {
    it('applies dark background colors', () => {
      const result = applyChartTheme(makeFigure(), 'dark')!

      expect(result.layout.paper_bgcolor).toBe('rgb(15,15,18)')
      expect(result.layout.plot_bgcolor).toBe('rgb(15,15,18)')
    })

    it('applies dark text colors', () => {
      const result = applyChartTheme(makeFigure(), 'dark')!

      expect(result.layout.font.color).toBe('rgb(226,232,240)')
    })

    it('applies dark hover label styling', () => {
      const result = applyChartTheme(makeFigure(), 'dark')!

      expect(result.layout.hoverlabel.bgcolor).toBe('rgba(9,9,11,0.96)')
    })
  })

  describe('light theme', () => {
    it('applies light background colors', () => {
      const result = applyChartTheme(makeFigure(), 'light')!

      expect(result.layout.paper_bgcolor).toBe('rgb(255,255,255)')
      expect(result.layout.plot_bgcolor).toBe('rgb(255,255,255)')
    })

    it('applies light text colors', () => {
      const result = applyChartTheme(makeFigure(), 'light')!

      expect(result.layout.font.color).toBe('rgb(9,9,11)')
    })

    it('applies light hover label styling', () => {
      const result = applyChartTheme(makeFigure(), 'light')!

      expect(result.layout.hoverlabel.bgcolor).toBe('rgba(255,255,255,0.98)')
    })
  })

  describe('transparent background option', () => {
    it('sets transparent backgrounds when transparentBackground is true', () => {
      const result = applyChartTheme(makeFigure(), 'dark', {
        transparentBackground: true,
      })!

      expect(result.layout.paper_bgcolor).toBe('rgba(0,0,0,0)')
      expect(result.layout.plot_bgcolor).toBe('rgba(0,0,0,0)')
    })

    it('uses theme backgrounds when transparentBackground is false', () => {
      const result = applyChartTheme(makeFigure(), 'dark', {
        transparentBackground: false,
      })!

      expect(result.layout.paper_bgcolor).toBe('rgb(15,15,18)')
    })
  })

  describe('layout properties', () => {
    it('sets autosize to true and clears width/height', () => {
      const fig = makeFigure()
      fig.layout.width = 800
      fig.layout.height = 600
      const result = applyChartTheme(fig, 'dark')!

      expect(result.layout.autosize).toBe(true)
      expect(result.layout.width).toBeUndefined()
      expect(result.layout.height).toBeUndefined()
    })

    it('sets hovermode to "x unified" for timeseries charts', () => {
      const result = applyChartTheme(makeFigure(), 'dark')!

      expect(result.layout.hovermode).toBe('x unified')
    })

    it('sets dragmode to pan', () => {
      const result = applyChartTheme(makeFigure(), 'dark')!

      expect(result.layout.dragmode).toBe('pan')
    })

    it('applies the colorway palette', () => {
      const result = applyChartTheme(makeFigure(), 'dark')!

      expect(result.layout.colorway).toBeInstanceOf(Array)
      expect(result.layout.colorway.length).toBeGreaterThan(0)
      expect(result.layout.colorway[0]).toBe('#00D2FF')
    })

    it('applies compact margins', () => {
      const result = applyChartTheme(makeFigure(), 'dark')!

      expect(result.layout.margin).toEqual({ t: 30, l: 0, r: 0, b: 0 })
    })
  })

  describe('axis styling', () => {
    it('applies date tick format to date x-axes', () => {
      const result = applyChartTheme(makeFigure(), 'dark')!

      expect(result.layout.xaxis.tickformat).toBe('%Y-%m-%d')
    })

    it('hides rangeslider on x-axes', () => {
      const result = applyChartTheme(makeFigure(), 'dark')!

      expect(result.layout.xaxis.rangeslider).toEqual({ visible: false })
    })

    it('enables spikes on axes', () => {
      const result = applyChartTheme(makeFigure(), 'dark')!

      expect(result.layout.xaxis.showspikes).toBe(true)
      expect(result.layout.yaxis.showspikes).toBe(true)
    })

    it('styles axis tick fonts with theme colors', () => {
      const result = applyChartTheme(makeFigure(), 'dark')!

      expect(result.layout.yaxis.tickfont.color).toBe('rgba(161,161,170,0.9)')
    })
  })

  describe('legend behavior', () => {
    it('hides legend when there is only one trace', () => {
      const fig = makeFigure()
      fig.data = [{ type: 'scatter', y: [1, 2, 3], name: 'Only' }]
      const result = applyChartTheme(fig, 'dark')!

      expect(result.layout.showlegend).toBe(false)
    })

    it('does not force-show legend when there are multiple differently-named traces', () => {
      const fig = makeFigure()
      fig.data = [
        { type: 'scatter', y: [1, 2], name: 'A' },
        { type: 'scatter', y: [3, 4], name: 'B' },
        { type: 'scatter', y: [5, 6], name: 'C' },
      ]
      const result = applyChartTheme(fig, 'dark')!

      // showlegend should be undefined (let Plotly decide) for 3+ unique names
      expect(result.layout.showlegend).toBeUndefined()
    })

    it('shows legend for pie charts regardless of trace count', () => {
      const fig: PlotlyFigure = {
        data: [{ type: 'pie', values: [30, 70], labels: ['A', 'B'] }],
        layout: {},
      }
      const result = applyChartTheme(fig, 'dark')!

      expect(result.layout.showlegend).toBe(true)
    })

    it('hides legend when data is empty', () => {
      const fig: PlotlyFigure = { data: [], layout: {} }
      const result = applyChartTheme(fig, 'dark')!

      expect(result.layout.showlegend).toBe(false)
    })
  })

  describe('annotations', () => {
    it('re-colors annotations with theme text color', () => {
      const fig = makeFigure()
      fig.layout.annotations = [
        { text: 'Note', x: 0.5, y: 0.5, font: { size: 14 } },
      ]
      const result = applyChartTheme(fig, 'light')!

      expect(result.layout.annotations[0].font.color).toBe('rgb(9,9,11)')
    })
  })

  describe('shapes', () => {
    it('re-colors year_boundary shapes with theme grid color', () => {
      const fig = makeFigure()
      fig.layout.shapes = [
        { name: 'year_boundary', line: { color: 'red', width: 1 } },
        { name: 'other', line: { color: 'blue', width: 1 } },
      ]
      const result = applyChartTheme(fig, 'dark')!

      // year_boundary should be re-colored
      expect(result.layout.shapes[0].line.color).toBe('rgba(39,39,42,0.8)')
      // other shape should keep its color
      expect(result.layout.shapes[1].line.color).toBe('blue')
    })
  })

  describe('scatter layout detection', () => {
    it('sets hovermode to "closest" for numeric x-axis charts', () => {
      const fig: PlotlyFigure = {
        data: [{ type: 'scatter', x: [1, 2, 3], y: [4, 5, 6] }],
        layout: { xaxis: { type: 'linear' } },
      }
      const result = applyChartTheme(fig, 'dark')!

      expect(result.layout.hovermode).toBe('closest')
    })
  })

  describe('empty / missing layout', () => {
    it('handles a figure with no layout', () => {
      const fig: PlotlyFigure = { data: [{ y: [1, 2, 3] }] }
      const result = applyChartTheme(fig, 'dark')!

      expect(result.layout).toBeDefined()
      expect(result.layout.paper_bgcolor).toBe('rgb(15,15,18)')
    })
  })
})
