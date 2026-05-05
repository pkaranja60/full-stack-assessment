import L from "leaflet";
import {
  MapContainer,
  Marker,
  Polyline,
  Popup,
  TileLayer,
  useMap,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";
import markerIcon from "leaflet/dist/images/marker-icon.png";

// Fix for default marker icons in React
import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";
import { useEffect } from "react";

(
  L.Icon.Default.prototype as L.IconOptions & { _getIconUrl?: string }
)._getIconUrl = undefined;
L.Icon.Default.mergeOptions({
  iconUrl: markerIcon,
  iconRetinaUrl: markerIcon2x,
  shadowUrl: markerShadow,
});

interface MapProps {
  center?: [number, number];
  geometry?: { coordinates: [number, number][] };
  stops?: {
    coordinates: [number, number];
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

export function TripMap({
  geometry,
  stops,
  center = [39.8283, -98.5795],
}: MapProps) {
  const polyline =
    geometry?.coordinates?.map((coord: [number, number]) => [
      coord[1],
      coord[0],
    ]) || [];

  return (
    <div className="relative h-full w-full">
      <MapContainerAny
        center={center}
        className="h-full w-full"
        scrollWheelZoom={true}
        zoom={4}
      >
        <TileLayerAny
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {polyline.length > 0 && (
          <PolylineAny
            opacity={0.7}
            pathOptions={{ color: "#3b82f6", weight: 4 }}
            positions={polyline}
          />
        )}

        {stops?.map((stop) => (
          <Marker
            key={`${stop.location}-${stop.stop_type}`}
            position={[stop.coordinates[1], stop.coordinates[0]]}
          >
            <Popup>
              <div className="text-sm">
                <p className="font-bold">{stop.location}</p>
                <p className="text-slate-500 capitalize">
                  {stop.stop_type.replace("_", " ")}
                </p>
                <p className="text-xs">{stop.time_label}</p>
              </div>
            </Popup>
          </Marker>
        ))}

        {polyline.length > 0 && (
          <ChangeView center={polyline[0] as [number, number]} zoom={6} />
        )}
      </MapContainerAny>
    </div>
  );
}
