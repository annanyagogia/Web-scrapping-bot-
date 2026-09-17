import { cn } from "../../lib/utils";

export function Badge({ className, tone = "default", ...props }) {
  const tones = {
    default: "border-sky-400/25 bg-sky-400/10 text-sky-200",
    success: "border-emerald-400/25 bg-emerald-400/10 text-emerald-200",
    warning: "border-amber-400/25 bg-amber-400/10 text-amber-200",
    danger: "border-rose-400/25 bg-rose-400/10 text-rose-200",
    muted: "border-slate-500/25 bg-slate-500/10 text-slate-300"
  };

  return (
    <span
      className={cn(
        "inline-flex min-h-6 items-center rounded-full border px-2.5 text-xs font-medium",
        tones[tone],
        className
      )}
      {...props}
    />
  );
}
