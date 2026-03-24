export function fmtNum(v: number | null | undefined, decimals = 2): string {
  if (v == null || !isFinite(v)) return '\u2014';
  return v.toLocaleString('en-US', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

export function generateExpressionLabel(expr: string): string {
  const seriesMatch = expr.match(/Series\(["']([^"']+)["']\)/);
  if (seriesMatch) {
    let label = seriesMatch[1];
    const transforms: string[] = [];
    const rollingMatch = expr.match(/\.rolling\((\d+)\)\.(\w+)\(\)/);
    if (rollingMatch) transforms.push(`rolling ${rollingMatch[1]} ${rollingMatch[2]}`);
    const pctMatch = expr.match(/\.pct_change\((\d+)?\)/);
    if (pctMatch) transforms.push(`pct_change${pctMatch[1] ? ` ${pctMatch[1]}` : ''}`);
    const resampleMatch = expr.match(/\.resample\(["'](\w+)["']\)\.(\w+)\(\)/);
    if (resampleMatch) transforms.push(`${resampleMatch[2]} ${resampleMatch[1]}`);
    const wrapperMatch = expr.match(/^(\w+)\(Series/);
    if (wrapperMatch && wrapperMatch[1] !== 'Series') transforms.unshift(wrapperMatch[1]);
    if (transforms.length > 0) label += ` (${transforms.join(', ')})`;
    return label.length > 40 ? label.slice(0, 37) + '...' : label;
  }
  return expr.length > 40 ? expr.slice(0, 37) + '...' : expr;
}
