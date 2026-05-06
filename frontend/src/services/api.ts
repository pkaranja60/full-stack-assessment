const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";

export interface TripPlanRequest {
  current_cycle_used: number;
  current_location: string;
  dropoff_location: string;
  pickup_location: string;
}

export const api = {
  async planTrip(data: TripPlanRequest) {
    const response = await fetch(`${API_BASE_URL}/trip/plan/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || "Failed to plan trip");
    }
    return response.json();
  },

  async getTrip(id: string) {
    const response = await fetch(`${API_BASE_URL}/trip/${id}/`);
    if (!response.ok) {
      throw new Error("Failed to fetch trip");
    }
    return response.json();
  },

  async listTrips() {
    const response = await fetch(`${API_BASE_URL}/trips/`);
    if (!response.ok) {
      throw new Error("Failed to fetch trips");
    }
    return response.json();
  },
};
