interface SparklineProps {
  data: number[];
  variant?: 'positive' | 'caution' | 'critical';
}

export function Sparkline({ data, variant = 'positive' }: SparklineProps) {
  if (data.length === 0) return null;

  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min;

  const points = data.map((value, index) => {
    const x = (index / (data.length - 1)) * 100;
    const y = range === 0 ? 50 : ((max - value) / range) * 100;
    return `${x},${y}`;
  }).join(' ');

  const variantColors = {
    positive: '#ffa726',
    caution: '#ffa726',
    critical: '#ef4444',
  };

  return (
    <svg width="48" height="20" className="inline-block" preserveAspectRatio="none">
      <polyline
        fill="none"
        stroke={variantColors[variant]}
        strokeWidth="1.5"
        points={points}
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}
