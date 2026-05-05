import type { ButtonHTMLAttributes, Ref } from "react";
import { cn } from "../../lib/utils";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  ref?: Ref<HTMLButtonElement>;
  size?: "sm" | "md" | "lg";
  variant?: "primary" | "secondary" | "outline" | "ghost" | "danger";
}

const Button = ({
  className,
  variant = "primary",
  size = "md",
  ref,
  ...props
}: ButtonProps) => {
  const variants = {
    primary: "bg-brand-primary text-white hover:bg-brand-primary/90 shadow-sm",
    secondary:
      "bg-brand-secondary text-white hover:bg-brand-secondary/90 shadow-sm",
    outline:
      "border border-slate-200 bg-transparent hover:bg-slate-100 dark:border-slate-800 dark:hover:bg-slate-800",
    ghost: "hover:bg-slate-100 dark:hover:bg-slate-800",
    danger: "bg-red-600 text-white hover:bg-red-700 shadow-sm",
  };

  const sizes = {
    sm: "h-8 px-3 text-xs",
    md: "h-10 px-4 py-2",
    lg: "h-12 px-8 text-lg",
  };

  return (
    <button
      className={cn(
        "inline-flex items-center justify-center rounded-md font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-primary disabled:pointer-events-none disabled:opacity-50",
        variants[variant],
        sizes[size],
        className
      )}
      ref={ref}
      {...props}
    />
  );
};
Button.displayName = "Button";

export { Button };
