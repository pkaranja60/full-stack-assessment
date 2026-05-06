import { ChevronLeft, History, Navigation, Truck } from "lucide-react";
import type { TripData } from "../types/trip";
import { TripForm } from "./trip-form";
import { TripResults } from "./trip-results";
import { Button } from "./ui/button";

interface SidebarProps {
  // biome-ignore lint/suspicious/noExplicitAny: History data from API
  historyData: any;
  isOpen: boolean;
  onSelectTrip: (id: string) => void;
  onShowLogs: () => void;
  onStartPlanning: () => void;
  onToggle: () => void;
  onTripSuccess: (data: TripData) => void;
  setTripData: (data: TripData | null) => void;
  tripData: TripData | null;
}

export function Sidebar({
  historyData,
  isOpen,
  onSelectTrip,
  onShowLogs,
  onStartPlanning,
  onToggle,
  onTripSuccess,
  setTripData,
  tripData,
}: SidebarProps) {
  return (
    <aside
      className={`glass-panel absolute sm:relative z-40 flex h-full flex-col overflow-hidden transition-all duration-300 ease-in-out ${
        isOpen ? "w-full sm:w-[400px]" : "w-0 -translate-x-full"
      }`}
    >
      <div className="flex h-full w-full flex-col sm:w-[400px]">
        {/* Header */}
        <header className="flex shrink-0 items-center justify-between border-stone-200 border-b p-6 dark:border-stone-800">
          <div className="flex items-center gap-2">
            <div className="rounded-lg bg-brand-primary p-2 shadow-inner">
              <Truck className="h-5 w-5 text-white" />
            </div>
            <h1 className="font-bold text-brand-primary text-xl tracking-tight">
              ELD Planner
            </h1>
          </div>
          {/* Mobile Close Button */}
          <button
            className="rounded-full p-2 hover:bg-stone-100 sm:hidden dark:hover:bg-stone-800"
            onClick={onToggle}
            type="button"
          >
            <ChevronLeft className="h-5 w-5" />
          </button>
        </header>

        {/* Main Content Area */}
        <div className="custom-scrollbar min-h-0 flex-1 overflow-y-auto p-6">
          {tripData ? (
            <div className="space-y-6">
              <button
                className="group flex items-center font-bold text-brand-primary text-xs uppercase tracking-widest transition-colors hover:text-brand-primary/80"
                onClick={() => setTripData(null)}
                type="button"
              >
                <ChevronLeft className="mr-1 h-4 w-4 transition-transform group-hover:-translate-x-1" />
                Back to Planner
              </button>
              <TripResults data={tripData} />
            </div>
          ) : (
            <div className="space-y-8">
              <section>
                <h2 className="mb-4 font-bold text-brand-primary text-xl tracking-tight">
                  Plan New Trip
                </h2>
                <TripForm onStart={onStartPlanning} onSuccess={onTripSuccess} />
              </section>

              {historyData?.trips?.length > 0 && (
                <section className="border-stone-200 border-t pt-8 dark:border-stone-800">
                  <div className="mb-6 flex items-center gap-2 text-stone-400">
                    <History className="h-4 w-4" />
                    <h2 className="font-bold text-xs uppercase tracking-widest">
                      Recent Trips
                    </h2>
                  </div>
                  {/* Scrollable Trips List */}
                  <div className="custom-scrollbar max-h-[400px] space-y-3 overflow-y-auto pr-2">
                    {historyData.trips.map(
                      (trip: {
                        id: string;
                        current_location: string;
                        dropoff_location: string;
                        created_at: string;
                      }) => (
                        <button
                          className="group w-full rounded-2xl border border-stone-200 bg-white/50 p-4 text-left transition-all hover:border-brand-primary hover:bg-white hover:shadow-lg dark:border-stone-800 dark:bg-stone-900/50"
                          key={trip.id}
                          onClick={() => onSelectTrip(trip.id)}
                          type="button"
                        >
                          <p className="mb-1 font-bold text-[10px] text-stone-400 uppercase tracking-wider transition-colors group-hover:text-brand-primary">
                            {new Date(trip.created_at).toLocaleDateString()}
                          </p>
                          <p className="truncate font-bold text-sm text-stone-700 group-hover:text-brand-primary dark:text-stone-300">
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

        {tripData && (
          <footer className="shrink-0 border-stone-200 border-t p-6 dark:border-stone-800">
            <div className="space-y-3">
              <Button
                className="h-14 w-full rounded-2xl bg-brand-primary font-bold text-lg text-white shadow-brand-primary/20 shadow-xl transition-all hover:scale-[1.02] hover:bg-brand-primary/90"
                onClick={onShowLogs}
                size="lg"
              >
                <Navigation className="mr-3 h-5 w-5" />
                View Daily Log Sheets
              </Button>
            </div>
          </footer>
        )}
      </div>

      {/* Toggle Button (Desktop only) */}
      <button
        className={`absolute top-1/2 -right-10 z-50 hidden -translate-y-1/2 items-center justify-center rounded-r-xl border border-stone-200 bg-bg-sidebar p-2 shadow-md transition-all hover:bg-stone-100 sm:flex dark:border-stone-800 dark:bg-stone-900 ${
          isOpen ? "" : "right-auto left-0 rounded-l-none"
        }`}
        onClick={onToggle}
        type="button"
      >
        <ChevronLeft
          className={`h-4 w-4 transition-transform duration-300 ${
            isOpen ? "" : "rotate-180"
          }`}
        />
      </button>
    </aside>

  );
}
