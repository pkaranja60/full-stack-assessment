import type { LogSegment } from "../components/log-sheet";

export interface TripData {
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
