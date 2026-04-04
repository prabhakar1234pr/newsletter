import { cn } from "@/lib/utils";

const ANIMATIONS = {
  "nudge-right":    "group-hover:translate-x-1 transition-transform duration-200",
  "nudge-diagonal": "group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform duration-200",
  "nudge-down":     "group-hover:translate-y-1 transition-transform duration-200",
  "rotate-90":      "group-hover:rotate-90 transition-transform duration-200",
  "sparkle":        "animate-sparkle",
  "float":          "animate-float",
  "spin-slow":      "group-hover:rotate-180 transition-transform duration-500",
};

export function AnimatedIcon({ icon: Icon, animation, className, ...props }) {
  return (
    <span className={cn("inline-flex", ANIMATIONS[animation] || "", className)}>
      <Icon {...props} />
    </span>
  );
}
