import { Calendar, Clock, Coffee, Navigation, Route } from "lucide-react";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
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
        <div className="grid grid-cols-2 gap-3">
          <Card className="border-none bg-stone-100/50 dark:bg-stone-900/50">
            <CardContent className="flex flex-col items-center p-4 text-center">
              <Route className="mb-1 h-5 w-5 text-brand-primary" />
              <span className="font-bold text-stone-900 text-xl dark:text-stone-100">
                {summary.total_distance_miles}
              </span>
              <span className="text-[10px] text-stone-500">MILES</span>
            </CardContent>
          </Card>
          <Card className="border-none bg-stone-100/50 dark:bg-stone-900/50">
            <CardContent className="flex flex-col items-center p-4 text-center">
              <Clock className="mb-1 h-5 w-5 text-brand-primary" />
              <span className="font-bold text-stone-900 text-xl dark:text-stone-100">
                {summary.total_driving_hours}
              </span>
              <span className="text-[10px] text-stone-500">DRIVING HRS</span>
            </CardContent>
          </Card>
          <Card className="border-none bg-stone-100/50 dark:bg-stone-900/50">
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
              className="relative"
              key={`${stop.location}-${stop.time_label}`}
            >
              <div className="absolute top-1 -left-[18px] h-2 w-2 rounded-full border-2 border-white bg-brand-primary dark:border-stone-900" />
              <div className="flex flex-col gap-1">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-sm text-stone-900 dark:text-stone-100">
                    {stop.location}
                  </span>
                  <Badge
                    className="bg-stone-100 text-[10px] text-stone-600 dark:bg-stone-800 dark:text-stone-400"
                    variant="secondary"
                  >
                    {stop.stop_type.replace("_", " ")}
                  </Badge>
                </div>
                <div className="flex items-center gap-3 text-[10px] text-stone-500">
                  <span className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {stop.time_label}
                  </span>
                  {stop.duration_hours > 0 && (
                    <span className="flex items-center gap-1">
                      <Coffee className="h-3 w-3" />
                      {stop.duration_hours}h rest
                    </span>
                  )}
                </div>
                {stop.description && (
                  <p className="mt-1 text-stone-600 text-xs dark:text-stone-400">
                    {stop.description}
                  </p>
                )}
              </div>
            </div>
          ))}
        </div>
      </section>

      <div className="fixed right-6 bottom-6 left-[424px] flex justify-center lg:left-[424px]">
        <Button
          className="h-12 rounded-full px-8 shadow-2xl transition-transform hover:scale-105"
          onClick={onShowLogs}
          size="lg"
        >
          <Navigation className="mr-2 h-5 w-5" />
          View Daily Log Sheets
        </Button>
      </div>
    </div>
  );
}
