import type { HTMLAttributes } from "react";
import { cn } from "../../lib/utils";

export interface BadgeProps extends HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "secondary" | "outline" | "success" | "warning";
}

function Badge({ className, variant = "default", ...props }: BadgeProps) {
  const variants = {
    default: "bg-slate-900 text-slate-50 dark:bg-slate-50 dark:text-slate-900",
    secondary:
      "bg-slate-100 text-slate-900 dark:bg-slate-800 dark:text-slate-50",
    outline:
      "text-slate-950 border border-slate-200 dark:text-slate-50 dark:border-slate-800",
    success:
      "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400",
    warning:
      "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
  };

  return (
    <div
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 font-semibold text-xs transition-colors focus:outline-none focus:ring-2 focus:ring-slate-950 focus:ring-offset-2 dark:focus:ring-slate-300",
        variants[variant],
        className
      )}
      {...props}
    />
  );
}

export { Badge };
