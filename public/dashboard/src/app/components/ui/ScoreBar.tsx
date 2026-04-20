interface ScoreBarProps {
  score: number;
  variant?: 'positive' | 'caution' | 'critical';
}

export function ScoreBar({ score, variant = 'positive' }: ScoreBarProps) {
  const percentage = Math.round(score * 100);

  const variantClasses = {
    positive: 'bg-primary',
    caution: 'bg-primary',
    critical: 'bg-critical',
  };

  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1 bg-muted rounded-full overflow-hidden">
        <div
          className={`h-full ${variantClasses[variant]} transition-all`}
          style={{ width: `${percentage}%` }}
        />
      </div>
      <span className="text-[10px] text-muted-foreground w-8 text-right">{score.toFixed(2)}</span>
    </div>
  );
}
