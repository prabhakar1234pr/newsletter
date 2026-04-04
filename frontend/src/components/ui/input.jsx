import { cn } from "@/lib/utils";

export function Input({ className, type, ...props }) {
  return (
    <input
      type={type}
      className={cn(
        "flex h-9 w-full rounded-xl border border-zinc-800 bg-zinc-900 px-3 py-2 text-sm text-white placeholder:text-zinc-600 transition-all duration-200 focus-visible:outline-none focus-visible:border-indigo-500 focus-visible:ring-2 focus-visible:ring-indigo-500/20 disabled:cursor-not-allowed disabled:opacity-50",
        className
      )}
      {...props}
    />
  );
}
