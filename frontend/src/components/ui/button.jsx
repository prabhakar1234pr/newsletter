import { cn } from "@/lib/utils";

const BASE = "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-xl font-semibold tracking-wide transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 focus-visible:ring-offset-zinc-950 disabled:pointer-events-none disabled:opacity-40 cursor-pointer";

const VARIANTS = {
  gradient: "bg-gradient-to-r from-indigo-500 to-violet-600 text-white shadow-lg shadow-indigo-500/25 hover:shadow-indigo-500/45 hover:-translate-y-0.5 active:translate-y-0",
  glass:    "bg-white/8 backdrop-blur-sm border border-white/12 text-white hover:bg-white/14 hover:border-white/22",
  outline:  "border border-zinc-700 text-zinc-300 bg-transparent hover:bg-zinc-800 hover:border-zinc-600 hover:text-white",
  ghost:    "text-zinc-400 hover:bg-zinc-800/80 hover:text-white",
  default:  "bg-indigo-600 text-white hover:bg-indigo-500 shadow-lg shadow-indigo-500/20",
  secondary:"bg-zinc-800 text-zinc-200 hover:bg-zinc-700",
  destructive: "bg-red-600 text-white hover:bg-red-500",
  link:     "text-indigo-400 hover:text-indigo-300 underline-offset-4 hover:underline p-0 h-auto",
};

const SIZES = {
  sm:      "h-8  px-4  text-xs",
  default: "h-9  px-5  text-sm",
  lg:      "h-11 px-7  text-sm",
  xl:      "h-12 px-9  text-base",
  icon:    "h-9  w-9   text-sm",
};

export function Button({ className, variant = "default", size = "default", type = "button", ...props }) {
  return (
    <button
      type={type}
      className={cn(BASE, VARIANTS[variant] ?? VARIANTS.default, SIZES[size] ?? SIZES.default, className)}
      {...props}
    />
  );
}
