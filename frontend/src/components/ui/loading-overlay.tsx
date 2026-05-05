import { Loader2 } from "lucide-react";

export function LoadingOverlay({
  message = "Calculating optimal route...",
}: {
  message?: string;
}) {
  return (
    <div className="fade-in absolute inset-0 z-100 flex animate-in flex-col items-center justify-center bg-bg-map/80 backdrop-blur-sm transition-all duration-500">
      <div className="flex flex-col items-center gap-4 rounded-3xl border border-stone-200 bg-white/50 p-12 shadow-2xl dark:border-stone-800 dark:bg-stone-900/50">
        <div className="relative flex h-16 w-16 items-center justify-center">
          <Loader2 className="h-12 w-12 animate-spin text-brand-primary" />
          <div className="absolute inset-0 animate-ping rounded-full bg-brand-primary/20" />
        </div>
        <p className="animate-pulse font-bold text-lg text-stone-700 dark:text-stone-300">
          {message}
        </p>
      </div>
    </div>
  );
}
