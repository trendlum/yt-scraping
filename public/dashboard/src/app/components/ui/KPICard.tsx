import { DeltaPill } from './DeltaPill';

interface KPICardProps {
  label: string;
  value: number;
  delta?: number;
}

export function KPICard({ label, value, delta }: KPICardProps) {
  return (
    <div className="bg-card border border-border rounded-lg p-3">
      <div className="text-[10px] text-muted-foreground mb-2 uppercase tracking-wide">{label}</div>
      <div className="flex items-baseline gap-2">
        <div className="text-xl font-medium text-foreground">{value}</div>
        {delta !== undefined && <DeltaPill value={delta} />}
      </div>
    </div>
  );
}
