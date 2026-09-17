import { cn } from "../../lib/utils";

export function Card({ className, ...props }) {
  return <div className={cn("glass-panel rounded-panel", className)} {...props} />;
}

export function CardHeader({ className, ...props }) {
  return <div className={cn("border-b border-border px-5 py-4", className)} {...props} />;
}

export function CardTitle({ className, ...props }) {
  return <h2 className={cn("text-base font-semibold text-foreground", className)} {...props} />;
}

export function CardContent({ className, ...props }) {
  return <div className={cn("px-5 py-5", className)} {...props} />;
}
