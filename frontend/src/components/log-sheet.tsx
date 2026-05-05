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
    <div className="space-y-6 rounded-xl border border-stone-200 bg-white p-6 shadow-sm dark:border-stone-800 dark:bg-stone-900/50">
      <div className="flex items-center justify-between border-stone-200 border-b pb-4 dark:border-stone-800">
        <div>
          <p className="font-bold text-stone-400 text-xs uppercase tracking-widest">
            Daily Log Sheet
          </p>
          <h3 className="font-bold text-stone-900 text-xl dark:text-stone-100">
            {label}
          </h3>
        </div>
        <div className="flex gap-4 font-mono text-[10px]">
          <div className="flex flex-col items-end">
            <span className="text-stone-400">OFF DUTY</span>
            <span className="font-bold text-stone-700 dark:text-stone-300">
              {totals.off_duty}h
            </span>
          </div>
          <div className="flex flex-col items-end">
            <span className="text-stone-400">SLEEPER</span>
            <span className="font-bold text-stone-700 dark:text-stone-300">
              {totals.sleeper_berth}h
            </span>
          </div>
          <div className="flex flex-col items-end">
            <span className="text-stone-400">DRIVING</span>
            <span className="font-bold text-brand-primary">
              {totals.driving}h
            </span>
          </div>
          <div className="flex flex-col items-end">
            <span className="text-stone-400">ON DUTY</span>
            <span className="font-bold text-stone-700 dark:text-stone-300">
              {totals.on_duty_not_driving}h
            </span>
          </div>
        </div>
      </div>

      <div className="custom-scrollbar relative overflow-x-auto pb-4">
        <div className="min-w-[700px]">
          {/* Hour Labels */}
          <div className="mb-2 grid grid-cols-24">
            {Array.from({ length: 24 }).map((_, i) => (
              <div
                className="text-center font-mono text-[9px] text-stone-400"
                // biome-ignore lint/suspicious/noArrayIndexKey: Static 24h grid
                key={`hour-${i}`}
              >
                {(() => {
                  if (i === 0) {
                    return "MDT";
                  }
                  if (i === 12) {
                    return "NOON";
                  }
                  return i;
                })()}
              </div>
            ))}
          </div>

          {/* Grid Rows */}
          <div className="relative grid grid-rows-4 border border-stone-300 dark:border-stone-700">
            {/* Status Labels on the left */}
            <div className="absolute top-0 bottom-0 -left-16 flex w-14 flex-col justify-around pr-2 text-right font-bold text-[8px] text-stone-400">
              <span>OFF</span>
              <span>SLEEP</span>
              <span>DRIVE</span>
              <span>DUTY</span>
            </div>

            {/* Grid Cells */}
            {Array.from({ length: 96 }).map((_, i) => (
              <div
                className="h-8 w-full border-stone-100 border-r border-b dark:border-stone-800"
                // biome-ignore lint/suspicious/noArrayIndexKey: Static 96-cell grid
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
                      stroke={seg.status === "driving" ? "#c5a059" : "#78716c"}
                      strokeWidth="0.1"
                      x1={seg.start_hour}
                      x2={seg.end_hour}
                      y1={row + 0.5}
                      y2={row + 0.5}
                    />
                    {/* Vertical Transition Line */}
                    {nextRow !== null && (
                      <line
                        stroke="#78716c"
                        strokeWidth="0.05"
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
        <h4 className="font-bold text-[10px] text-stone-400 uppercase tracking-widest">
          Daily Log Detail
        </h4>
        <div className="grid grid-cols-1 gap-1.5">
          {segments
            .filter((s) => s.status !== "off_duty" || s.duration > 0.5)
            .map((seg) => (
              <div
                className="flex items-center gap-4 rounded-lg border border-stone-100 bg-stone-50/50 p-2.5 transition-colors hover:bg-stone-100 dark:border-stone-800 dark:bg-stone-900/30 dark:hover:bg-stone-900/50"
                key={`${seg.start_time}-${seg.status}`}
              >
                <div
                  className={`h-2 w-2 rounded-full ${
                    seg.status === "driving"
                      ? "bg-brand-primary"
                      : "bg-stone-300 dark:bg-stone-700"
                  }`}
                />
                <span className="w-24 font-mono text-[10px] text-stone-400">
                  {seg.start_time} - {seg.end_time}
                </span>
                <span className="flex-1 font-medium text-stone-700 text-xs dark:text-stone-300">
                  {seg.description || seg.location}
                </span>
                {seg.miles !== undefined && seg.miles > 0 && (
                  <span className="font-bold text-[10px] text-brand-primary">
                    {seg.miles} MI
                  </span>
                )}
              </div>
            ))}
        </div>
      </div>
    </div>
  );
}
