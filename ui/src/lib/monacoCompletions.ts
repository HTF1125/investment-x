/**
 * Monaco IntelliSense completions for the Investment-X chart DSL.
 * Provides autocomplete for Series(), transforms, Plotly, pandas, and quant functions.
 */
import type { Monaco } from '@monaco-editor/react';

const IX_COMPLETIONS = [
  // Data fetching
  { label: 'Series', kind: 'Function', insertText: 'Series("${1:CODE}")', detail: '(code, freq?, ccy?) → pd.Series', documentation: 'Fetch a timeseries by code. E.g. Series("SPX_INDEX:PX_LAST")' },
  { label: 'MultiSeries', kind: 'Function', insertText: 'MultiSeries(${1:name}=Series("${2:CODE}"))', detail: '(**series) → pd.DataFrame', documentation: 'Combine multiple Series into a DataFrame with named columns.' },
  // Transforms
  { label: 'Rebase', kind: 'Function', insertText: 'Rebase(${1:series})', detail: '(series) → pd.Series', documentation: 'Rebase series to start at 100.' },
  { label: 'Resample', kind: 'Function', insertText: 'Resample(${1:series}, freq="${2:ME}")', detail: '(series, freq="ME") → pd.Series', documentation: 'Resample to target frequency (ME, QE, YE, W, D).' },
  { label: 'PctChange', kind: 'Function', insertText: 'PctChange(${1:series}, periods=${2:1})', detail: '(series, periods=1) → pd.Series', documentation: 'Percentage change over N periods.' },
  { label: 'Diff', kind: 'Function', insertText: 'Diff(${1:series}, periods=${2:1})', detail: '(series, periods=1) → pd.Series', documentation: 'Difference over N periods.' },
  { label: 'MovingAverage', kind: 'Function', insertText: 'MovingAverage(${1:series}, window=${2:3})', detail: '(series, window=3) → pd.Series', documentation: 'Rolling mean over window.' },
  { label: 'StandardScalar', kind: 'Function', insertText: 'StandardScalar(${1:series}, window=${2:20})', detail: '(series, window=20) → pd.Series', documentation: 'Z-score normalization using rolling mean/std.' },
  { label: 'Offset', kind: 'Function', insertText: 'Offset(${1:series}, months=${2:0}, days=${3:0})', detail: '(series, months=0, days=0, start?) → pd.Series', documentation: 'Shift series index by months/days.' },
  { label: 'MonthEndOffset', kind: 'Function', insertText: 'MonthEndOffset(${1:series}, months=${2:3})', detail: '(series, months=3) → pd.Series', documentation: 'Offset and align to month end.' },
  { label: 'Clip', kind: 'Function', insertText: 'Clip(${1:series}, lower=${2:None}, upper=${3:None})', detail: '(series, lower?, upper?) → pd.Series', documentation: 'Clip values to bounds.' },
  { label: 'Ffill', kind: 'Function', insertText: 'Ffill(${1:series})', detail: '(series) → pd.Series', documentation: 'Forward fill missing values.' },
  // Quant
  { label: 'Correlation', kind: 'Function', insertText: 'Correlation("${1:CODE1}", "${2:CODE2}", window=${3:120})', detail: '(*codes, window?, method?) → pd.DataFrame', documentation: 'Correlation matrix from series codes.' },
  { label: 'RollingCorrelation', kind: 'Function', insertText: 'RollingCorrelation("${1:CODE1}", "${2:CODE2}", window=${3:60})', detail: '(code1, code2, window=60) → pd.Series', documentation: 'Rolling correlation between two series.' },
  { label: 'Regression', kind: 'Function', insertText: 'Regression("${1:Y_CODE}", "${2:X_CODE}")', detail: '(y_code, *x_codes) → dict', documentation: 'Multi-factor regression (prices → returns).' },
  { label: 'RollingBeta', kind: 'Function', insertText: 'RollingBeta("${1:Y_CODE}", "${2:X_CODE}", window=${3:60})', detail: '(y_code, x_code, window=60) → pd.Series', documentation: 'Rolling beta between two series.' },
  { label: 'PCA', kind: 'Function', insertText: 'PCA("${1:CODE1}", "${2:CODE2}", n_components=${3:3})', detail: '(*codes, n_components=3) → dict', documentation: 'PCA decomposition from series codes.' },
  { label: 'VaR', kind: 'Function', insertText: 'VaR("${1:CODE}", confidence=${2:0.95})', detail: '(code, confidence=0.95, window?, method?) → dict', documentation: 'Value-at-Risk. method: "historical" or "parametric".' },
  { label: 'ExpectedShortfall', kind: 'Function', insertText: 'ExpectedShortfall("${1:CODE}", confidence=${2:0.95})', detail: '(code, confidence=0.95, window?) → dict', documentation: 'Expected Shortfall (CVaR) for a series.' },
  // Plotly helpers
  { label: 'apply_theme', kind: 'Function', insertText: 'apply_theme(${1:fig})', detail: '(fig, mode?) → fig', documentation: 'Apply the Investment-X chart theme.' },
  { label: 'make_subplots', kind: 'Function', insertText: 'make_subplots(rows=${1:2}, cols=${2:1}, shared_xaxes=${3:True})', detail: '(rows, cols, ...) → go.Figure', documentation: 'Create a Plotly figure with subplots.' },
  { label: 'df_plot', kind: 'Function', insertText: 'df_plot(${1:df}, x="${2:col}", y="${3:col}", kind="${4:line}")', detail: '(df, x?, y?, kind?, title?) → go.Figure', documentation: 'Quick plot helper for DataFrames.' },
  // Plotly graph objects
  { label: 'go.Figure', kind: 'Constructor', insertText: 'go.Figure()', detail: '() → Figure', documentation: 'Create a new Plotly figure.' },
  { label: 'go.Scatter', kind: 'Constructor', insertText: 'go.Scatter(x=${1:x}, y=${2:y}, name="${3:name}", mode="${4:lines}")', detail: '(x, y, name, mode, ...) → Scatter trace', documentation: 'Scatter/line trace.' },
  { label: 'go.Bar', kind: 'Constructor', insertText: 'go.Bar(x=${1:x}, y=${2:y}, name="${3:name}")', detail: '(x, y, name, ...) → Bar trace', documentation: 'Bar chart trace.' },
  { label: 'go.Heatmap', kind: 'Constructor', insertText: 'go.Heatmap(z=${1:z}, x=${2:x}, y=${3:y})', detail: '(z, x, y, ...) → Heatmap trace', documentation: 'Heatmap trace.' },
  { label: 'go.Candlestick', kind: 'Constructor', insertText: 'go.Candlestick(x=${1:dates}, open=${2:o}, high=${3:h}, low=${4:l}, close=${5:c})', detail: '(x, open, high, low, close) → Candlestick', documentation: 'OHLC candlestick trace.' },
  // Plotly express
  { label: 'px.line', kind: 'Function', insertText: 'px.line(${1:df}, x="${2:col}", y="${3:col}", title="${4:title}")', detail: '(df, x, y, ...) → go.Figure', documentation: 'Plotly Express line chart.' },
  { label: 'px.bar', kind: 'Function', insertText: 'px.bar(${1:df}, x="${2:col}", y="${3:col}", title="${4:title}")', detail: '(df, x, y, ...) → go.Figure', documentation: 'Plotly Express bar chart.' },
  { label: 'px.scatter', kind: 'Function', insertText: 'px.scatter(${1:df}, x="${2:col}", y="${3:col}", title="${4:title}")', detail: '(df, x, y, ...) → go.Figure', documentation: 'Plotly Express scatter chart.' },
  { label: 'px.area', kind: 'Function', insertText: 'px.area(${1:df}, x="${2:col}", y="${3:col}", title="${4:title}")', detail: '(df, x, y, ...) → go.Figure', documentation: 'Plotly Express area chart.' },
  { label: 'px.histogram', kind: 'Function', insertText: 'px.histogram(${1:df}, x="${2:col}", title="${3:title}")', detail: '(df, x, ...) → go.Figure', documentation: 'Plotly Express histogram.' },
  // Figure methods
  { label: 'fig.add_trace', kind: 'Method', insertText: 'fig.add_trace(${1:trace})', detail: '(trace, row?, col?) → fig', documentation: 'Add a trace to the figure.' },
  { label: 'fig.update_layout', kind: 'Method', insertText: 'fig.update_layout(${1:})', detail: '(**kwargs) → fig', documentation: 'Update layout properties (title, axes, etc.).' },
  { label: 'fig.update_xaxes', kind: 'Method', insertText: 'fig.update_xaxes(${1:})', detail: '(**kwargs) → fig', documentation: 'Update x-axis properties.' },
  { label: 'fig.update_yaxes', kind: 'Method', insertText: 'fig.update_yaxes(${1:})', detail: '(**kwargs) → fig', documentation: 'Update y-axis properties.' },
  { label: 'fig.add_hline', kind: 'Method', insertText: 'fig.add_hline(y=${1:0}, line_dash="${2:dash}", line_color="${3:gray}")', detail: '(y, line_dash?, ...) → fig', documentation: 'Add a horizontal line.' },
  { label: 'fig.add_vline', kind: 'Method', insertText: 'fig.add_vline(x="${1:2020-01-01}", line_dash="${2:dash}")', detail: '(x, ...) → fig', documentation: 'Add a vertical line.' },
  { label: 'fig.add_vrect', kind: 'Method', insertText: 'fig.add_vrect(x0="${1:start}", x1="${2:end}", fillcolor="${3:gray}", opacity=${4:0.2}, line_width=${5:0})', detail: '(x0, x1, ...) → fig', documentation: 'Add a vertical rectangle (shaded region).' },
  { label: 'fig.add_annotation', kind: 'Method', insertText: 'fig.add_annotation(x=${1:x}, y=${2:y}, text="${3:text}", showarrow=${4:False})', detail: '(x, y, text, ...) → fig', documentation: 'Add a text annotation.' },
  // Common pandas
  { label: '.loc', kind: 'Property', insertText: '.loc["${1:2020}":]', detail: 'Label-based indexing', documentation: 'Slice by label. E.g. .loc["2020":] for data from 2020.' },
  { label: '.iloc', kind: 'Property', insertText: '.iloc[${1:-252}:]', detail: 'Position-based indexing', documentation: 'Slice by position. E.g. .iloc[-252:] for last 252 rows.' },
  { label: '.dropna', kind: 'Method', insertText: '.dropna()', detail: '() → Series/DataFrame', documentation: 'Drop rows with missing values.' },
  { label: '.fillna', kind: 'Method', insertText: '.fillna(${1:0})', detail: '(value) → Series/DataFrame', documentation: 'Fill missing values.' },
  { label: '.rolling', kind: 'Method', insertText: '.rolling(${1:20}).mean()', detail: '(window) → Rolling', documentation: 'Rolling window operations.' },
  { label: '.resample', kind: 'Method', insertText: '.resample("${1:ME}").last()', detail: '(freq) → Resampler', documentation: 'Resample time series data.' },
  { label: '.pct_change', kind: 'Method', insertText: '.pct_change(${1:1})', detail: '(periods=1) → Series', documentation: 'Percentage change.' },
  { label: 'pd.DataFrame', kind: 'Constructor', insertText: 'pd.DataFrame(${1:data})', detail: '(data, columns?, index?) → DataFrame', documentation: 'Create a DataFrame.' },
  { label: 'np.array', kind: 'Function', insertText: 'np.array(${1:data})', detail: '(data) → ndarray', documentation: 'Create a numpy array.' },
];

let _registered = false;

/**
 * Register Investment-X Python completions with Monaco.
 * Safe to call multiple times — only registers once.
 */
export function registerIxCompletions(monaco: Monaco): void {
  if (_registered) return;
  _registered = true;

  monaco.languages.registerCompletionItemProvider('python', {
    triggerCharacters: ['.', '(', '"', "'"],
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    provideCompletionItems(model: any, position: any) {
      const word = model.getWordUntilPosition(position);
      const lineContent = model.getLineContent(position.lineNumber);
      const textBefore = lineContent.substring(0, position.column - 1);
      const range = {
        startLineNumber: position.lineNumber,
        endLineNumber: position.lineNumber,
        startColumn: word.startColumn,
        endColumn: word.endColumn,
      };

      const suggestions = IX_COMPLETIONS
        .filter((c) => {
          if (c.label.includes('.')) {
            const prefix = c.label.split('.')[0] + '.';
            return textBefore.endsWith(prefix) || textBefore.endsWith(prefix.slice(0, -1));
          }
          return true;
        })
        .map((c) => {
          const kindMap: Record<string, number> = {
            Function: monaco.languages.CompletionItemKind.Function,
            Method: monaco.languages.CompletionItemKind.Method,
            Constructor: monaco.languages.CompletionItemKind.Constructor,
            Property: monaco.languages.CompletionItemKind.Property,
          };
          return {
            label: c.label,
            kind: kindMap[c.kind] ?? monaco.languages.CompletionItemKind.Function,
            insertText: c.insertText,
            insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
            detail: c.detail,
            documentation: c.documentation,
            range,
          };
        });

      return { suggestions };
    },
  });
}
