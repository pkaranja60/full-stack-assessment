import { Loader2, Navigation } from "lucide-react";
import type { FormEvent } from "react";
import type { TripData } from "../types/trip";
import { useState } from "react";
import { usePlanTrip } from "../hooks/use-trips";
import { Button } from "./ui/button";
import { Input } from "./ui/input";

interface TripFormProps {
  onStart?: () => void;
  onSuccess: (data: TripData) => void;
}

export function TripForm({ onStart, onSuccess }: TripFormProps) {
  const [formData, setFormData] = useState({
    current_location: "",
    pickup_location: "",
    dropoff_location: "",
    current_cycle_used: "" as string | number,
  });

  const { mutate: planTrip, isPending, error } = usePlanTrip();

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    onStart?.();
    const submissionData = {
      ...formData,
      current_cycle_used:
        typeof formData.current_cycle_used === "string" &&
        formData.current_cycle_used === ""
          ? 0
          : Number.parseFloat(formData.current_cycle_used.toString()),
    };

    planTrip(submissionData, {
      onSuccess: (data) => {
        onSuccess(data);
      },
    });
  };

  return (
    <form className="space-y-4" onSubmit={handleSubmit}>
      <div className="space-y-3">
        <Input
          label="Current Location"
          onChange={(e) =>
            setFormData({ ...formData, current_location: e.target.value })
          }
          placeholder="Where are you now?"
          required
          value={formData.current_location}
        />
        <Input
          label="Pickup Location"
          onChange={(e) =>
            setFormData({ ...formData, pickup_location: e.target.value })
          }
          placeholder="Where is the load?"
          required
          value={formData.pickup_location}
        />
        <Input
          label="Dropoff Location"
          onChange={(e) =>
            setFormData({ ...formData, dropoff_location: e.target.value })
          }
          placeholder="Where is it going?"
          required
          value={formData.dropoff_location}
        />
        <Input
          label="Current Cycle Used (Hours)"
          max="69.9"
          min="0"
          onChange={(e) =>
            setFormData({
              ...formData,
              current_cycle_used: e.target.value,
            })
          }
          placeholder="0.0"
          step="0.1"
          type="number"
          value={formData.current_cycle_used}
        />
      </div>

      {error && (
        <div className="rounded-md border border-red-100 bg-red-50 p-3 text-red-600 text-xs">
          {error.message}
        </div>
      )}

      <Button className="w-full" disabled={isPending} type="submit">
        {isPending ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Planning Route...
          </>
        ) : (
          <>
            <Navigation className="mr-2 h-4 w-4" />
            Plan Trip
          </>
        )}
      </Button>
    </form>
  );
}
