import { cva } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors",
  {
    variants: {
      variant: {
        default:   "bg-indigo-500/15 text-indigo-300 border border-indigo-500/25",
        secondary: "bg-zinc-800 text-zinc-400 border border-zinc-700",
        outline:   "border border-zinc-700 text-zinc-400",
        success:   "bg-emerald-500/15 text-emerald-400 border border-emerald-500/25",
        gradient:  "bg-gradient-to-r from-indigo-500/20 to-violet-500/20 text-indigo-300 border border-indigo-500/30",
        glow:      "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 shadow-sm shadow-emerald-500/20",
        amber:     "bg-amber-500/15 text-amber-400 border border-amber-500/25",
      },
    },
    defaultVariants: { variant: "default" },
  }
);

export function Badge({ className, variant, ...props }) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}
