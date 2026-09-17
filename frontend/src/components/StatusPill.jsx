import { Badge } from "./ui/badge";

export function StatusPill({ status }) {
  const normalized = String(status || "idle").toLowerCase();
  const tone =
    normalized === "success"
      ? "success"
      : normalized === "failed" || normalized === "error"
        ? "danger"
        : normalized === "running" || normalized === "empty"
          ? "warning"
          : "muted";

  return <Badge tone={tone}>{status || "idle"}</Badge>;
}
