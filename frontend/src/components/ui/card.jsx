import { cn } from "@/lib/utils";

export function Card({ className, ...props }) {
  return (
    <div
      className={cn(
        "rounded-2xl bg-zinc-900 border border-zinc-800",
        className
      )}
      {...props}
    />
  );
}

export function CardHeader({ className, ...props }) {
  return <div className={cn("p-6 pb-0", className)} {...props} />;
}

export function CardTitle({ className, ...props }) {
  return (
    <h3 className={cn("text-xl font-bold text-white font-heading", className)} {...props} />
  );
}

export function CardDescription({ className, ...props }) {
  return (
    <p className={cn("text-sm text-zinc-400 mt-1", className)} {...props} />
  );
}

export function CardContent({ className, ...props }) {
  return <div className={cn("p-6", className)} {...props} />;
}

export function CardFooter({ className, ...props }) {
  return (
    <div className={cn("flex items-center p-6 pt-0", className)} {...props} />
  );
}

export function GlassCard({ className, ...props }) {
  return (
    <div
      className={cn(
        "rounded-2xl bg-white/5 backdrop-blur-sm border border-white/10 transition-all duration-300 hover:border-indigo-500/40 hover:-translate-y-0.5",
        className
      )}
      {...props}
    />
  );
}
