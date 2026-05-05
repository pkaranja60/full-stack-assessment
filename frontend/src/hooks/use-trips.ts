import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type TripPlanRequest } from "../services/api";

export function usePlanTrip() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: TripPlanRequest) => api.planTrip(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["trips"] });
    },
  });
}

export function useTrip(id: string | null) {
  return useQuery({
    queryKey: ["trip", id],
    queryFn: () => (id ? api.getTrip(id) : Promise.reject("No ID provided")),
    enabled: !!id,
  });
}

export function useTripsList() {
  return useQuery({
    queryKey: ["trips"],
    queryFn: () => api.listTrips(),
  });
}
