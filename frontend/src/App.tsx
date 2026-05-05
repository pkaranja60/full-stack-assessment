import { useState } from "react";
import { LogSheet } from "./components/log-sheet";
import { Sidebar } from "./components/sidebar";
import { TripMap } from "./components/trip-map";
import { Modal } from "./components/ui/modal";
import { useTripsList } from "./hooks/use-trips";
import type { TripData } from "./types/trip";

function App() {
  const [tripData, setTripData] = useState<TripData | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isLogsModalOpen, setIsLogsModalOpen] = useState(false);

  const { data: historyData } = useTripsList();

  const handleTripSuccess = (data: unknown) => {
    setTripData(data as TripData);
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-bg-map">
      <Sidebar
        historyData={historyData}
        isOpen={isSidebarOpen}
        onShowLogs={() => setIsLogsModalOpen(true)}
        onToggle={() => setIsSidebarOpen(!isSidebarOpen)}
        onTripSuccess={handleTripSuccess}
        setTripData={setTripData}
        tripData={tripData}
      />

      {/* Main Map View */}
      <main className="relative flex-1">
        <TripMap geometry={tripData?.route?.geometry} stops={tripData?.stops} />
      </main>

      {/* Daily Logs Modal */}
      <Modal
        isOpen={isLogsModalOpen}
        onClose={() => setIsLogsModalOpen(false)}
        title="Driver's Daily Logs"
      >
        <div className="grid grid-cols-1 gap-8 md:grid-cols-2 lg:grid-cols-3">
          {tripData?.daily_logs?.map((log) => (
            <LogSheet key={log.label} log={log} />
          ))}
        </div>
      </Modal>
    </div>
  );
}

export default App;
