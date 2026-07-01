/**
 * SeatProgress component for displaying tenant usage
 */

import { formatValues } from '../utils';

interface SeatProgressProps {
  label: string;
  used: number;
  limit: number;
  t: (key: string, options?: any) => string;
}

export function SeatProgress({ label, used, limit, t }: SeatProgressProps) {
  const displayLimit = limit > 0 ? limit : '∞';
  const percentage = limit > 0 ? Math.min(100, Math.round((used / limit) * 100)) : used > 0 ? 100 : 0;
  const warn = limit > 0 && used / limit >= 0.9;
  return (
    <div className="rounded border border-slate-100 bg-white p-3 text-sm">
      <div className="flex items-center justify-between text-xs uppercase text-slate-400">
        <span>{label}</span>
        <span className="text-slate-500">
          {limit > 0
            ? t('app.platform.tenants.usage.limit', formatValues({ used, limit }))
            : t('app.platform.tenants.usage.unlimited', formatValues({ used }))}
        </span>
      </div>
      <div className="mt-2 h-2 rounded-full bg-slate-100">
        <div
          className={['h-2 rounded-full', warn ? 'bg-amber-500' : 'bg-brand-500'].join(' ')}
          style={{ width: `${percentage}%` }}
        />
      </div>
      <div className="mt-2 text-sm font-semibold text-slate-900">
        {used}
        <span className="ml-1 text-slate-500">/ {displayLimit}</span>
      </div>
    </div>
  );
}

