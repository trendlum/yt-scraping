interface DeltaPillProps {
  value: number;
}

export function DeltaPill({ value }: DeltaPillProps) {
  const isPositive = value > 0;
  const isNeutral = value === 0;

  if (isNeutral) {
    return (
      <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] text-muted-foreground">
        0
      </span>
    );
  }

  return (
    <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] ${isPositive ? 'bg-positive/10 text-positive' : 'bg-critical/10 text-critical'}`}>
      {isPositive ? '+' : ''}{value}
    </span>
  );
}
