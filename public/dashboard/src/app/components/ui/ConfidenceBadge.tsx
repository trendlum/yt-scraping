interface ConfidenceBadgeProps {
  confidence: 'high' | 'medium' | 'low';
}

export function ConfidenceBadge({ confidence }: ConfidenceBadgeProps) {
  const variantClasses = {
    high: 'bg-positive/10 text-positive border-positive/20',
    medium: 'bg-primary/10 text-primary border-primary/20',
    low: 'bg-critical/10 text-critical border-critical/20',
  };

  return (
    <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] uppercase tracking-wide border ${variantClasses[confidence]}`}>
      {confidence}
    </span>
  );
}
