'use client';

import { useMemo } from 'react';

interface VomoSparklineProps {
  values: number[];
  className?: string;
}

export default function VomoSparkline({ values, className = '' }: VomoSparklineProps) {
  const { points, zeroY } = useMemo(() => {
    const data = values.slice(-30);
    if (data.length < 2) return { points: '', zeroY: 14 };

    const width = 200;
    const height = 28;
    const min = Math.min(...data, -2);
    const max = Math.max(...data, 2);
    const range = max - min || 1;

    const pts = data.map((v, i) => {
      const x = (i / (data.length - 1)) * width;
      const y = height - ((v - min) / range) * height;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(' ');

    const zy = height - ((0 - min) / range) * height;
    return { points: pts, zeroY: zy };
  }, [values]);

  if (!points) return null;

  return (
    <svg
      viewBox="0 0 200 28"
      className={`w-full h-full ${className}`}
      preserveAspectRatio="none"
    >
      <line
        x1="0" y1={zeroY} x2="200" y2={zeroY}
        stroke="rgb(var(--border))"
        strokeWidth="0.5"
        strokeDasharray="3,3"
      />
      <polyline
        fill="none"
        stroke="rgb(var(--primary))"
        strokeWidth="1.5"
        strokeLinejoin="round"
        strokeLinecap="round"
        points={points}
      />
    </svg>
  );
}
