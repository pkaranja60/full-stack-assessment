import { Calendar, Clock, Coffee, Fuel, MapPin, Route } from "lucide-react";
import { Badge } from "./ui/badge";
import { Card, CardContent } from "./ui/card";

interface TripResultsProps {
  data: {
    summary: {
      total_distance_miles: number;
      total_driving_hours: number;
      total_days: number;
      cycle_hours_remaining: number;
      num_rest_stops: number;
    };
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

export function TripResults({ data, onShowLogs }: TripResultsProps) {
  const { summary, stops } = data;

  return (
    <div className="space-y-6 pb-20">
      <section className="space-y-3">
        <h3 className="font-medium text-slate-500 text-sm uppercase tracking-wider">
          Trip Summary
        </h3>
        <div className="grid grid-cols-2 gap-3">
          <Card className="border-none bg-slate-50 dark:bg-slate-900">
            <CardContent className="flex flex-col items-center p-4 text-center">
              <Route className="mb-1 h-5 w-5 text-brand-primary" />
              <span className="font-bold text-xl">
                {summary.total_distance_miles}
              </span>
              <span className="text-[10px] text-slate-500">MILES</span>
            </CardContent>
          </Card>
          <Card className="border-none bg-slate-50 dark:bg-slate-900">
            <CardContent className="flex flex-col items-center p-4 text-center">
              <Clock className="mb-1 h-5 w-5 text-brand-primary" />
              <span className="font-bold text-xl">
                {summary.total_driving_hours}
              </span>
              <span className="text-[10px] text-slate-500">DRIVING HRS</span>
            </CardContent>
          </Card>
          <Card className="border-none bg-slate-50 dark:bg-slate-900">
            <CardContent className="flex flex-col items-center p-4 text-center">
              <Calendar className="mb-1 h-5 w-5 text-brand-primary" />
              <span className="font-bold text-xl">{summary.total_days}</span>
              <span className="text-[10px] text-slate-500">TOTAL DAYS</span>
            </CardContent>
          </Card>
          <Card className="border-none bg-slate-50 dark:bg-slate-900">
            <CardContent className="flex flex-col items-center p-4 text-center">
              <Clock className="mb-1 h-5 w-5 text-brand-primary" />
              <span className="font-bold text-xl">
                {summary.cycle_hours_remaining}
              </span>
              <span className="text-[10px] text-slate-500">
                REMAINING CYCLE
              </span>
            </CardContent>
          </Card>
        </div>
      </section>

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="font-medium text-slate-500 text-sm uppercase tracking-wider">
            Route & Stops
          </h3>
          <Badge variant="outline">{summary.num_rest_stops} Rest Stops</Badge>
        </div>
        <div className="relative space-y-0 before:absolute before:top-2 before:bottom-2 before:left-[17px] before:w-0.5 before:bg-slate-200 dark:before:bg-slate-800">
          {stops.map((stop) => (
            <div
              className="group relative py-3 pl-10"
              key={`${stop.location}-${stop.time_label}`}
            >
              <div className="absolute top-1/2 left-0 z-10 flex h-9 w-9 -translate-y-1/2 items-center justify-center rounded-full border-2 border-slate-200 bg-white transition-colors group-hover:border-brand-primary dark:border-slate-800 dark:bg-slate-950">
                {stop.stop_type === "fuel" && (
                  <Fuel className="h-4 w-4 text-amber-500" />
                )}
                {stop.stop_type === "rest" && (
                  <Coffee className="h-4 w-4 text-emerald-500" />
                )}
                {stop.stop_type !== "fuel" && stop.stop_type !== "rest" && (
                  <MapPin className="h-4 w-4 text-brand-primary" />
                )}
              </div>
              <div className="space-y-1">
                <div className="flex items-center justify-between">
                  <h4 className="font-bold text-sm">{stop.location}</h4>
                  <span className="font-mono text-[10px] text-slate-400">
                    {stop.time_label.split(",")[1]}
                  </span>
                </div>
                <p className="text-slate-500 text-xs">{stop.description}</p>
                <div className="flex gap-2">
                  <Badge className="text-[9px] uppercase" variant="secondary">
                    {stop.stop_type.replace("_", " ")}
                  </Badge>
                  {stop.duration_hours > 0 && (
                    <span className="text-[10px] text-slate-400 italic">
                      {stop.duration_hours}h duration
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      <div className="fixed right-[calc(100vw-var(--sidebar-width)+24px)] bottom-6 left-6 z-20">
        <button
          className="flex w-full items-center justify-center gap-2 rounded-full bg-slate-900 py-4 font-bold text-white tracking-tight shadow-xl transition-all hover:scale-[1.02] active:scale-[0.98] dark:bg-slate-50 dark:text-slate-900"
          onClick={onShowLogs}
          type="button"
        >
          <Calendar className="h-5 w-5" />
          VIEW DAILY LOG SHEETS
        </button>
      </div>
    </div>
  );
}
