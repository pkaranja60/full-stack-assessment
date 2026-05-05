import { Badge } from "./ui/badge";

export interface LogSegment {
  description?: string;
  duration: number;
  end_hour: number;
  end_time: string;
  location?: string;
  miles?: number;
  start_hour: number;
  start_time: string;
  status: string;
}

interface LogSheetProps {
  log: {
    segments: LogSegment[];
    totals: Record<string, number>;
    label: string;
  };
}

export function LogSheet({ log }: LogSheetProps) {
  const { segments, totals, label } = log;

  const getStatusRow = (status: string) => {
    switch (status) {
      case "off_duty":
        return 0;
      case "sleeper_berth":
        return 1;
      case "driving":
        return 2;
      case "on_duty_not_driving":
        return 3;
      default:
        return 0;
    }
  };

  return (
    <div className="space-y-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-950">
      <div className="flex items-center justify-between border-slate-100 border-b pb-4 dark:border-slate-900">
        <h3 className="font-bold text-xl">{label}</h3>
        <div className="flex gap-4 font-mono text-[10px]">
          <div className="flex flex-col items-end">
            <span className="text-slate-400">OFF DUTY</span>
            <span className="font-bold">{totals.off_duty}h</span>
          </div>
          <div className="flex flex-col items-end">
            <span className="text-slate-400">SLEEPER</span>
            <span className="font-bold">{totals.sleeper_berth}h</span>
          </div>
          <div className="flex flex-col items-end">
            <span className="text-slate-400">DRIVING</span>
            <span className="font-bold">{totals.driving}h</span>
          </div>
          <div className="flex flex-col items-end">
            <span className="text-slate-400">ON DUTY</span>
            <span className="font-bold">{totals.on_duty_not_driving}h</span>
          </div>
        </div>
      </div>

      <div className="relative overflow-x-auto pb-4">
        <div className="min-w-[800px]">
          {/* Hour Labels */}
          <div className="mb-2 grid grid-cols-24">
            {Array.from({ length: 24 }).map((_, i) => {
              let label = i.toString();
              if (i === 0) {
                label = "MDT";
              }
              if (i === 12) {
                label = "NOON";
              }
              return (
                <div
                  className="text-center font-mono text-[9px] text-slate-400"
                  // biome-ignore lint/suspicious/noArrayIndexKey: Static grid
                  key={`hour-${i}`}
                >
                  {label}
                </div>
              );
            })}
          </div>

          {/* Grid Rows */}
          <div className="relative grid grid-rows-4 border border-slate-300 dark:border-slate-700">
            {/* Status Labels on the left */}
            <div className="absolute top-0 bottom-0 -left-20 flex w-16 flex-col justify-around pr-2 text-right font-bold text-[8px] text-slate-400">
              <span>OFF DUTY</span>
              <span>SLEEPER</span>
              <span>DRIVING</span>
              <span>ON DUTY</span>
            </div>

            {/* Grid Cells */}
            {Array.from({ length: 96 }).map((_, i) => (
              <div
                className="h-10 w-full border-slate-100 border-r border-b dark:border-slate-900"
                // biome-ignore lint/suspicious/noArrayIndexKey: Static grid
                key={`cell-${i}`}
                style={{
                  gridColumn: (i % 24) + 1,
                  gridRow: Math.floor(i / 24) + 1,
                }}
              />
            ))}

            {/* Lines */}
            <svg
              className="pointer-events-none absolute inset-0 h-full w-full"
              viewBox="0 0 24 4"
            >
              <title>ELD Status Graph</title>
              {segments.map((seg, idx) => {
                const row = getStatusRow(seg.status);
                const nextSeg = segments[idx + 1];
                const nextRow = nextSeg ? getStatusRow(nextSeg.status) : null;

                return (
                  <g key={`${seg.status}-${seg.start_hour}`}>
                    {/* Horizontal Line */}
                    <line
                      stroke="#3b82f6"
                      strokeWidth="0.08"
                      x1={seg.start_hour}
                      x2={seg.end_hour}
                      y1={row + 0.5}
                      y2={row + 0.5}
                    />
                    {/* Vertical Transition Line */}
                    {nextRow !== null && (
                      <line
                        stroke="#3b82f6"
                        strokeWidth="0.08"
                        x1={seg.end_hour}
                        x2={seg.end_hour}
                        y1={row + 0.5}
                        y2={nextRow + 0.5}
                      />
                    )}
                  </g>
                );
              })}
            </svg>
          </div>
        </div>
      </div>

      <div className="space-y-2">
        <h4 className="font-bold text-[10px] text-slate-400 uppercase">
          Daily Activity
        </h4>
        <div className="grid grid-cols-1 gap-2">
          {segments
            .filter((s) => s.status !== "off_duty" || s.duration > 0.5)
            .map((seg) => (
              <div
                className="flex items-center gap-4 rounded-md border border-slate-100 bg-slate-50 p-2 dark:border-slate-800 dark:bg-slate-900"
                key={`${seg.start_time}-${seg.status}`}
              >
                <Badge
                  className="w-20 justify-center"
                  variant={seg.status === "driving" ? "default" : "secondary"}
                >
                  {seg.status.split("_")[0]}
                </Badge>
                <span className="font-mono text-[10px] text-slate-400">
                  {seg.start_time} - {seg.end_time}
                </span>
                <span className="flex-1 font-medium text-xs">
                  {seg.description || seg.location}
                </span>
                {seg.miles !== undefined && seg.miles > 0 && (
                  <span className="font-bold text-[10px] text-brand-primary">
                    {seg.miles} mi
                  </span>
                )}
              </div>
            ))}
        </div>
      </div>
    </div>
  );
}
