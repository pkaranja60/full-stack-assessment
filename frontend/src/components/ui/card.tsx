import type { HTMLAttributes, Ref } from "react";
import { cn } from "../../lib/utils";

const Card = ({
  className,
  ref,
  ...props
}: HTMLAttributes<HTMLDivElement> & { ref?: Ref<HTMLDivElement> }) => (
  <div
    className={cn(
      "rounded-lg border border-slate-200 bg-white text-slate-950 shadow-sm dark:border-slate-800 dark:bg-slate-950 dark:text-slate-50",
      className
    )}
    ref={ref}
    {...props}
  />
);
Card.displayName = "Card";

const CardHeader = ({
  className,
  ref,
  ...props
}: HTMLAttributes<HTMLDivElement> & { ref?: Ref<HTMLDivElement> }) => (
  <div
    className={cn("flex flex-col space-y-1.5 p-6", className)}
    ref={ref}
    {...props}
  />
);
CardHeader.displayName = "CardHeader";

const CardTitle = ({
  className,
  ref,
  ...props
}: HTMLAttributes<HTMLHeadingElement> & { ref?: Ref<HTMLHeadingElement> }) => (
  <h3
    className={cn(
      "font-semibold text-2xl leading-none tracking-tight",
      className
    )}
    ref={ref}
    {...props}
  />
);
CardTitle.displayName = "CardTitle";

const CardContent = ({
  className,
  ref,
  ...props
}: HTMLAttributes<HTMLDivElement> & { ref?: Ref<HTMLDivElement> }) => (
  <div className={cn("p-6 pt-0", className)} ref={ref} {...props} />
);
CardContent.displayName = "CardContent";

export { Card, CardContent, CardHeader, CardTitle };
