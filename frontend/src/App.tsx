import { useEffect, useState } from "react";
import { LogSheet } from "./components/log-sheet";
import { Sidebar } from "./components/sidebar";
import { TripMap } from "./components/trip-map";
import { LoadingOverlay } from "./components/ui/loading-overlay";
import { useTrip, useTripsList } from "./hooks/use-trips";
import type { TripData } from "./types/trip";

function App() {
  const [tripData, setTripData] = useState<TripData | null>(null);
  const [selectedTripId, setSelectedTripId] = useState<string | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isPlanning, setIsPlanning] = useState(false);
  const [activeView, setActiveView] = useState<"planner" | "logs">("planner");

  const { data: historyData } = useTripsList();
  const { data: tripDetails } = useTrip(selectedTripId);

  // Sync tripDetails into tripData when it arrives
  useEffect(() => {
    if (tripDetails) {
      setTripData(tripDetails as TripData);
      setIsPlanning(false);
    }
  }, [tripDetails]);

  const handleTripSuccess = (data: unknown) => {
    setIsPlanning(false);
    setSelectedTripId(null);
    setTripData(data as TripData);
    setActiveView("planner");
  };

  const handleSelectTrip = (id: string) => {
    setTripData(null);
    setSelectedTripId(id);
    setIsPlanning(true);
    setActiveView("planner");
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-bg-map">
      {isPlanning && (
        <LoadingOverlay
          message={selectedTripId ? "Fetching trip details..." : undefined}
        />
      )}

      <Sidebar
        historyData={historyData}
        isOpen={isSidebarOpen}
        onSelectTrip={handleSelectTrip}
        onShowLogs={() => setActiveView("logs")}
        onStartPlanning={() => setIsPlanning(true)}
        onToggle={() => setIsSidebarOpen(!isSidebarOpen)}
        onTripSuccess={handleTripSuccess}
        setTripData={(data) => {
          setTripData(data);
          if (data) {
            setActiveView("planner");
          } else {
            setIsPlanning(false);
            setSelectedTripId(null);
          }
        }}
        tripData={tripData}
      />

      {/* Main Content Area */}
      <main className="relative flex h-full flex-1 flex-col">
        {activeView === "planner" ? (
          <TripMap
            geometry={tripData?.route?.geometry}
            stops={tripData?.stops}
          />
        ) : (
          <div className="h-full overflow-y-auto bg-stone-50 p-8 dark:bg-stone-900">
            <div className="mx-auto max-w-5xl space-y-8">
              <header className="flex items-center justify-between">
                <div>
                  <h2 className="font-bold text-3xl text-stone-900 dark:text-stone-100">
                    Trip Log Sheets
                  </h2>
                  <p className="text-stone-500">
                    Review and verify your daily duty cycles
                  </p>
                </div>
                <div className="flex gap-4">
                  {tripData?.trip_id && (
                    <a
                      className="inline-flex items-center gap-2 rounded-full border-2 border-stone-200 bg-white px-6 py-2 font-bold text-stone-700 transition-transform hover:scale-105 dark:border-stone-800 dark:bg-stone-800 dark:text-stone-300"
                      href={`${import.meta.env.VITE_API_URL || "http://localhost:8000"}/api/trip/${tripData.trip_id}/download-logs/`}
                      rel="noopener noreferrer"
                      target="_blank"
                    >
                      Download Log Sheets
                    </a>
                  )}
                  <button
                    className="rounded-full bg-brand-primary px-6 py-2 font-bold text-white shadow-lg transition-transform hover:scale-105"
                    onClick={() => setActiveView("planner")}
                    type="button"
                  >
                    Back to Map
                  </button>
                </div>
              </header>

              {tripData?.daily_logs ? (
                <div className="grid grid-cols-1 gap-8">
                  {tripData.daily_logs.map((log) => (
                    <LogSheet
                      key={log.label}
                      log={log}
                      tripDate={tripData.created_at}
                    />
                  ))}
                </div>
              ) : (
                <div className="flex h-[400px] flex-col items-center justify-center rounded-3xl border-2 border-stone-200 border-dashed bg-white/50 text-center dark:border-stone-800 dark:bg-stone-900/50">
                  <p className="text-stone-400">
                    No trip planned yet. Please plan a trip to see your logs.
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
