import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useEffect, useMemo } from "react";
import {
  MapContainer,
  Marker,
  Polyline,
  Popup,
  TileLayer,
  useMap,
} from "react-leaflet";

// Function to create custom markers based on stop type
const createCustomIcon = (type: string | undefined | null) => {
  const safeType = (type || "intermediate").toLowerCase();
  let color = "#e2c41e"; // Default intermediate color
  let innerHtml = "";

  switch (safeType) {
    case "pickup":
      color = "#e2931e"; // Green for start
      innerHtml = '<div class="w-2 h-2 bg-white rounded-full"></div>';
      break;
    case "start":
      color = "#10b981"; // Green for start
      innerHtml = '<div class="w-2 h-2 bg-white rounded-full"></div>';
      break;
    case "dropoff":
      color = "#ef4444"; // Red for end
      innerHtml = '<div class="w-2 h-2 bg-white rounded-sm rotate-45"></div>';
      break;
    case "rest":
      color = "#3b82f6"; // Blue for rest
      innerHtml =
        '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M17 8h1a4 4 0 1 1 0 8h-1"></path><path d="M3 8h14v9a4 4 0 0 1-4 4H7a4 4 0 0 1-4-4Z"></path><line x1="6" x2="6" y1="2" y2="4"></line><line x1="10" x2="10" y1="2" y2="4"></line><line x1="14" x2="14" y1="2" y2="4"></line></svg>';
      break;
    case "fuel":
      color = "#8b5cf6"; // Purple for fuel/intermediate
      innerHtml =
        '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M3 14h11a2 2 0 0 0 2-2V4a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v13a3 3 0 0 0 3 3h14a2 2 0 0 0 2-2v-4a2 2 0 0 0-2-2"></path><path d="m9 2 3 3"></path><path d="m12 2-3 3"></path></svg>';
      break;
    case "break":
      color = "#f59e0b"; // Amber for 30-min breaks
      innerHtml =
        '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>';
      break;
    default:
      color = "#e2c41e"; // for any other intermediate stops
      innerHtml = '<div class="w-1.5 h-1.5 bg-white rounded-full"></div>';
      break;
  }

  return L.divIcon({
    className: "custom-marker",
    html: `
      <div class="relative flex items-center justify-center">
        <div class="w-8 h-8 rounded-full bg-white shadow-lg flex items-center justify-center p-1">
          <div class="w-full h-full rounded-full flex items-center justify-center" style="background-color: ${color}">
            ${innerHtml}
          </div>
        </div>
        <div class="absolute -bottom-1 w-2 h-2 bg-white rotate-45 shadow-lg"></div>
      </div>
    `,
    iconSize: [32, 36],
    iconAnchor: [16, 36],
    popupAnchor: [0, -36],
  });
};

interface MapProps {
  center?: [number, number];
  geometry?: { coordinates: [number, number][] };
  stops?: {
    coordinates: [number, number] | null;
    location: string;
    stop_type: string;
    time_label: string;
  }[];
}

function ChangeView({
  center,
  zoom,
}: {
  center: [number, number];
  zoom: number;
}) {
  const map = useMap();
  useEffect(() => {
    map.setView(center, zoom);
  }, [center, zoom, map]);
  return null;
}

// biome-ignore lint/suspicious/noExplicitAny: Workaround for react-leaflet v5 RC.2 type issues
const MapContainerAny = MapContainer as any;
// biome-ignore lint/suspicious/noExplicitAny: Workaround for react-leaflet v5 RC.2 type issues
const TileLayerAny = TileLayer as any;
// biome-ignore lint/suspicious/noExplicitAny: Workaround for react-leaflet v5 RC.2 type issues
const PolylineAny = Polyline as any;
// biome-ignore lint/suspicious/noExplicitAny: Workaround for react-leaflet v5 RC.2 type issues
const MarkerAny = Marker as any;
// biome-ignore lint/suspicious/noExplicitAny: Workaround for react-leaflet v5 RC.2 type issues
const PopupAny = Popup as any;

export function TripMap({
  geometry,
  stops,
  center = [39.8283, -98.5795],
}: MapProps) {
  const polyline = useMemo(
    () =>
      geometry?.coordinates?.map((coord: [number, number]) => [
        coord[1],
        coord[0],
      ]) || [],
    [geometry]
  );

  // Only render markers for stops that have valid, non-null coordinates
  const stopsWithCoords = useMemo(
    () =>
      (stops ?? []).filter(
        (s): s is typeof s & { coordinates: [number, number] } =>
          s.coordinates != null &&
          Array.isArray(s.coordinates) &&
          s.coordinates.length === 2 &&
          typeof s.coordinates[0] === "number" &&
          typeof s.coordinates[1] === "number"
      ),
    [stops]
  );

  return (
    <div className="relative h-full w-full bg-stone-100 dark:bg-stone-900">
      <MapContainerAny
        center={center}
        className="h-full w-full outline-none"
        scrollWheelZoom={true}
        zoom={4}
      >
        <TileLayerAny
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {polyline.length > 0 && (
          <PolylineAny
            opacity={0.8}
            pathOptions={{ color: "#c5a059", weight: 5 }}
            positions={polyline}
          />
        )}

        {stopsWithCoords.map((stop, index) => (
          <MarkerAny
            icon={createCustomIcon(stop.stop_type)}
            // biome-ignore lint/suspicious/noArrayIndexKey: Stops don't have a unique ID from backend
            key={`stop-${index}-${stop.location}`}
            position={[stop.coordinates[1], stop.coordinates[0]]}
          >
            <PopupAny>
              <div className="p-1 text-sm">
                <p className="font-bold text-stone-900">{stop.location}</p>
                <div className="mt-1 flex items-center gap-2">
                  <span className="rounded-full bg-stone-100 px-2 py-0.5 font-bold text-[10px] text-stone-600 uppercase">
                    {stop.stop_type.replace("_", " ")}
                  </span>
                  <span className="text-[10px] text-stone-500">
                    {stop.time_label}
                  </span>
                </div>
              </div>
            </PopupAny>
          </MarkerAny>
        ))}

        {polyline.length > 0 && (
          <ChangeView center={polyline[0] as [number, number]} zoom={6} />
        )}
      </MapContainerAny>
    </div>
  );
}
