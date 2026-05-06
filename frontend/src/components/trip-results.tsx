import { Calendar, Clock, Coffee, Route } from "lucide-react";
import { Badge } from "./ui/badge";

interface TripResultsProps {
  data: {
    summary: {
      total_distance_miles: number;
      total_driving_hours: number;
      total_days: number;
      cycle_hours_remaining: number;
      num_rest_stops: number;
    };
    trip_id?: string;
    stops: {
      location: string;
      stop_type: string;
      time_label: string;
      description: string;
      duration_hours: number;
    }[];
  };
  onShowLogs: () => void;
}

export function TripResults({ data }: { data: TripResultsProps["data"] }) {
  const summary = data?.summary;
  const stops = data?.stops ?? [];

  if (!summary) {
    return (
      <div className="flex h-40 items-center justify-center text-stone-400">
        <p>Loading trip details…</p>
      </div>
    );
  }

  return (
    <div className="space-y-6 pb-20">
      <section className="space-y-3">
        <h3 className="font-medium text-sm text-stone-500 uppercase tracking-wider">
          Trip Summary
        </h3>
        <div className="grid grid-cols-2 gap-4">
          <div className="rounded-2xl bg-stone-100 p-4 dark:bg-stone-800">
            <div className="mb-2 flex items-center gap-2 text-brand-primary">
              <Route className="h-4 w-4" />
              <span className="font-bold text-[10px] uppercase tracking-wider">
                Distance
              </span>
            </div>
            <div className="flex items-baseline gap-1">
              <span className="font-bold text-2xl text-stone-900 tracking-tight dark:text-stone-100">
                {summary.total_distance_miles}
              </span>
              <span className="font-medium text-stone-400 text-xs">mi</span>
            </div>
          </div>

          <div className="rounded-2xl bg-stone-100 p-4 dark:bg-stone-800">
            <div className="mb-2 flex items-center gap-2 text-brand-primary">
              <Clock className="h-4 w-4" />
              <span className="font-bold text-[10px] uppercase tracking-wider">
                Driving
              </span>
            </div>
            <div className="flex items-baseline gap-1">
              <span className="font-bold text-2xl text-stone-900 tracking-tight dark:text-stone-100">
                {summary.total_driving_hours}
              </span>
              <span className="font-medium text-stone-400 text-xs">hrs</span>
            </div>
          </div>

          <div className="rounded-2xl bg-stone-100 p-4 dark:bg-stone-800">
            <div className="mb-2 flex items-center gap-2 text-brand-primary">
              <Calendar className="h-4 w-4" />
              <span className="font-bold text-[10px] uppercase tracking-wider">
                Duration
              </span>
            </div>
            <div className="flex items-baseline gap-1">
              <span className="font-bold text-2xl text-stone-900 tracking-tight dark:text-stone-100">
                {summary.total_days}
              </span>
              <span className="font-medium text-stone-400 text-xs">days</span>
            </div>
          </div>

          <div className="rounded-2xl bg-stone-100 p-4 dark:bg-stone-800">
            <div className="mb-2 flex items-center gap-2 text-brand-primary">
              <Clock className="h-4 w-4" />
              <span className="font-bold text-[10px] uppercase tracking-wider">
                Cycle Left
              </span>
            </div>
            <div className="flex items-baseline gap-1">
              <span className="font-bold text-2xl text-stone-900 tracking-tight dark:text-stone-100">
                {summary.cycle_hours_remaining}
              </span>
              <span className="font-medium text-stone-400 text-xs">hrs</span>
            </div>
          </div>
        </div>

        {data.trip_id && (
          <a
            className="flex w-full items-center justify-center gap-2 rounded-xl border border-stone-200 bg-white py-2.5 font-bold text-stone-600 text-xs transition-colors hover:bg-stone-50 dark:border-stone-700 dark:bg-stone-800 dark:text-stone-300 dark:hover:bg-stone-700"
            href={`${import.meta.env.VITE_API_URL || "http://localhost:8000/api"}/trip/${data.trip_id}/download-logs/`}
            rel="noopener noreferrer"
            target="_blank"
          >
            Download Log Sheets
          </a>
        )}
      </section>

      <section className="space-y-6">
        <div className="flex items-center justify-between">
          <h3 className="font-bold text-stone-400 text-xs uppercase tracking-widest">
            Journey Timeline
          </h3>
          <Badge
            className="rounded-full border-none bg-brand-primary/10 px-3 font-bold text-[10px] text-brand-primary"
            variant="outline"
          >
            {summary.num_rest_stops} Rest Stops
          </Badge>
        </div>

        <div className="relative space-y-8 pl-6 before:absolute before:top-2 before:bottom-2 before:left-[7px] before:w-0.5 before:bg-stone-200 dark:before:bg-stone-800">
          {stops.map((stop, index) => (
            <div
              className="group relative"
              // biome-ignore lint/suspicious/noArrayIndexKey: Stops don't have unique IDs from backend
              key={`${stop.location}-${stop.time_label}-${index}`}
            >
              <div className="absolute top-1 left-[-23px] h-3 w-3 rounded-full border-2 border-white bg-brand-primary shadow-sm dark:border-stone-900" />
              <div className="flex flex-col gap-1.5">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-sm text-stone-900 tracking-tight dark:text-stone-100">
                    {stop.location}
                  </span>
                  <span className="font-bold text-[10px] text-brand-primary uppercase tracking-wider">
                    {stop.time_label}
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  <Badge
                    className="rounded-lg bg-stone-100 px-2 py-0.5 font-bold text-[9px] text-stone-500 uppercase tracking-wide dark:bg-stone-800 dark:text-stone-400"
                    variant="secondary"
                  >
                    {stop.stop_type.replace("_", " ")}
                  </Badge>
                  {stop.duration_hours > 0 && (
                    <div className="flex items-center gap-1.5 rounded-lg bg-brand-primary/5 px-2 py-0.5 font-bold text-[9px] text-brand-primary uppercase">
                      <Coffee className="h-3 w-3" />
                      {stop.duration_hours}h Break
                    </div>
                  )}
                </div>

                {stop.description && (
                  <p className="mt-1 text-stone-500 text-xs leading-relaxed dark:text-stone-400">
                    {stop.description}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
