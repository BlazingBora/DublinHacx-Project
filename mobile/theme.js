export const colors = {
  bg: "#0f1115",
  surface: "#1a1d24",
  border: "#2a2e37",
  text: "#e8e9ed",
  muted: "#9aa0ab",
  accent: "#4ade80",
  danger: "#ef4444",
  urgent: "#f87171",
  soon: "#facc15",
  stale: "#fb923c",
  freeze: "#60a5fa",
};

export function urgencyColor(urgency) {
  switch (urgency) {
    case "danger":
      return colors.danger;
    case "stale":
      return colors.stale;
    case "urgent":
      return colors.urgent;
    case "soon":
      return colors.soon;
    case "fresh":
      return colors.accent;
    default:
      return colors.muted;
  }
}

export function severityColor(severity) {
  switch (severity) {
    case "high":
      return colors.danger;
    case "medium":
      return colors.soon;
    case "low":
      return colors.accent;
    default:
      return colors.soon;
  }
}
