import type { InputHTMLAttributes, Ref } from "react";
import { cn } from "../../lib/utils";

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  error?: string;
  label?: string;
  ref?: Ref<HTMLInputElement>;
}

const Input = ({
  className,
  type,
  label,
  error,
  id,
  ref,
  ...props
}: InputProps) => {
  const inputId = id || label?.toLowerCase().replace(/\s+/g, "-");
  return (
    <div className="w-full space-y-1.5">
      {label && (
        <label
          className="font-medium text-sm text-stone-700 leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 dark:text-stone-300"
          htmlFor={inputId}
        >
          {label}
        </label>
      )}
      <input
        className={cn(
          "flex h-10 w-full rounded-md border border-stone-200 bg-white/50 px-3 py-2 text-sm ring-offset-white file:border-0 file:bg-transparent file:font-medium file:text-sm placeholder:text-stone-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-primary focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 dark:border-stone-800 dark:bg-stone-900/50 dark:ring-offset-stone-950 dark:placeholder:text-stone-500",
          error && "border-red-500 focus-visible:ring-red-500",
          className
        )}
        id={inputId}
        ref={ref}
        type={type}
        {...props}
      />
      {error && <p className="text-red-500 text-xs">{error}</p>}
    </div>
  );
};
Input.displayName = "Input";

export { Input };
