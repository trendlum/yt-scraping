interface StatusChipProps {
  status: string;
  variant?: 'positive' | 'caution' | 'critical' | 'neutral';
}

export function StatusChip({ status, variant = 'neutral' }: StatusChipProps) {
  const variantClasses = {
    positive: 'bg-positive/10 text-positive border-positive/20',
    caution: 'bg-primary/10 text-primary border-primary/20',
    critical: 'bg-critical/10 text-critical border-critical/20',
    neutral: 'bg-muted text-muted-foreground border-border',
  };

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded border text-[10px] ${variantClasses[variant]}`}>
      {status.replace(/_/g, ' ')}
    </span>
  );
}
