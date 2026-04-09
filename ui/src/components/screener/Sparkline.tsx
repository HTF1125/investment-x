'use client';

interface Props {
  data: number[];  // 0-1 normalized
  width?: number;
  height?: number;
  positive?: boolean;
}

export default function Sparkline({ data, width = 80, height = 24, positive = true }: Props) {
  if (!data || data.length < 2) return <div style={{ width, height }} />;

  const points = data
    .map((v, i) => `${(i / (data.length - 1)) * width},${(1 - v) * height}`)
    .join(' ');

  return (
    <svg width={width} height={height} className="shrink-0" viewBox={`0 0 ${width} ${height}`}>
      <polyline
        points={points}
        fill="none"
        strokeWidth={1.2}
        strokeLinejoin="round"
        strokeLinecap="round"
        className={positive ? 'stroke-success/70' : 'stroke-destructive/70'}
      />
    </svg>
  );
}
