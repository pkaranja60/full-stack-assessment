import {
  ChevronLeft,
  ChevronRight,
  History,
  Navigation,
  Truck,
} from "lucide-react";
import { useState } from "react";
import { type LogSegment, LogSheet } from "./components/log-sheet";
import { TripForm } from "./components/trip-form";
import { TripMap } from "./components/trip-map";
import { TripResults } from "./components/trip-results";
import { Button } from "./components/ui/button";
import { Modal } from "./components/ui/modal";
import { useTripsList } from "./hooks/use-trips";

interface TripData {
  daily_logs: {
    label: string;
    segments: LogSegment[];
    totals: Record<string, number>;
  }[];
  route: { geometry: { coordinates: [number, number][] } };
  stops: {
    location: string;
    stop_type: string;
    time_label: string;
    coordinates: [number, number];
    description: string;
    duration_hours: number;
  }[];
  summary: {
    total_distance_miles: number;
    total_driving_hours: number;
    total_days: number;
    cycle_hours_remaining: number;
    num_rest_stops: number;
  };
}

function App() {
  const [tripData, setTripData] = useState<TripData | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isLogsModalOpen, setIsLogsModalOpen] = useState(false);

  const { data: historyData } = useTripsList();

  const handleTripSuccess = (data: unknown) => {
    setTripData(data as TripData);
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-slate-50 dark:bg-slate-950">
      {/* Sidebar */}
      <aside
        className={`glass-panel relative z-20 flex flex-col transition-all duration-300 ease-in-out ${
          isSidebarOpen ? "w-[400px]" : "w-0 -translate-x-full"
        }`}
      >
        <div className="flex h-full w-[400px] flex-col">
          {/* Header */}
          <header className="flex items-center justify-between border-slate-100 border-b p-6 dark:border-slate-800">
            <div className="flex items-center gap-2">
              <div className="rounded-lg bg-brand-primary p-2">
                <Truck className="h-5 w-5 text-white" />
              </div>
              <h1 className="font-bold text-xl tracking-tight">ELD Planner</h1>
            </div>
          </header>

          {/* Main Content Area */}
          <div className="custom-scrollbar flex-1 overflow-y-auto p-6">
            {tripData ? (
              <div className="space-y-4">
                <Button
                  className="mb-2 -ml-2"
                  onClick={() => setTripData(null)}
                  size="sm"
                  variant="ghost"
                >
                  <ChevronLeft className="mr-1 h-4 w-4" />
                  Back to Planner
                </Button>
                <TripResults
                  data={tripData}
                  onShowLogs={() => setIsLogsModalOpen(true)}
                />
              </div>
            ) : (
              <div className="space-y-8">
                <section>
                  <h2 className="mb-4 font-bold text-lg">Plan New Trip</h2>
                  <TripForm onSuccess={handleTripSuccess} />
                </section>

                {historyData?.trips?.length > 0 && (
                  <section className="border-slate-100 border-t pt-6 dark:border-slate-800">
                    <div className="mb-4 flex items-center gap-2 text-slate-500">
                      <History className="h-4 w-4" />
                      <h2 className="font-bold text-sm uppercase tracking-wider">
                        Recent Trips
                      </h2>
                    </div>
                    <div className="space-y-3">
                      {historyData.trips.map(
                        (trip: {
                          id: string;
                          current_location: string;
                          dropoff_location: string;
                          created_at: string;
                        }) => (
                          <button
                            className="group w-full rounded-xl border border-slate-100 bg-white p-4 text-left transition-colors hover:border-brand-primary dark:border-slate-800 dark:bg-slate-900"
                            key={trip.id}
                            // biome-ignore lint/suspicious/noExplicitAny: Trip summary from history
                            onClick={() => setTripData(trip as any)}
                            type="submit"
                          >
                            <p className="mb-1 font-bold text-brand-primary text-xs">
                              {new Date(trip.created_at).toLocaleDateString()}
                            </p>
                            <p className="truncate font-bold text-sm group-hover:text-brand-primary">
                              {trip.current_location} → {trip.dropoff_location}
                            </p>
                          </button>
                        )
                      )}
                    </div>
                  </section>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Toggle Button */}
        <button
          className={`absolute top-1/2 -right-10 z-30 -translate-y-1/2 rounded-r-xl border border-slate-200 bg-white p-2 shadow-md transition-colors hover:bg-slate-50 dark:border-slate-800 dark:bg-slate-900 ${
            !isSidebarOpen && "right-auto left-0 rounded-l-none"
          }`}
          onClick={() => setIsSidebarOpen(!isSidebarOpen)}
          type="button"
        >
          {isSidebarOpen ? (
            <ChevronLeft className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
        </button>
      </aside>

      {/* Main Map View */}
      <main className="relative flex-1">
        <TripMap geometry={tripData?.route?.geometry} stops={tripData?.stops} />

        {/* Floating Search Overlay (Mobile or collapsed view) */}
        {!isSidebarOpen && (
          <div className="slide-in-from-left absolute top-6 left-6 z-10 animate-in duration-300">
            <Button
              className="h-12 rounded-full px-6 shadow-2xl"
              onClick={() => setIsSidebarOpen(true)}
            >
              <Navigation className="mr-2 h-4 w-4" />
              Plan Trip
            </Button>
          </div>
        )}
      </main>

      {/* Logs Modal */}
      <Modal
        isOpen={isLogsModalOpen}
        onClose={() => setIsLogsModalOpen(false)}
        title="Driver's Daily Log Sheets"
      >
        <div className="space-y-10">
          {tripData?.daily_logs?.map((log) => (
            <LogSheet key={log.label} log={log} />
          ))}
        </div>
      </Modal>
    </div>
  );
}

export default App;
