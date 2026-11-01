export const count = (value: number | null | undefined) => value == null ? "—" : value.toLocaleString("en-GB");
export function calendar(value: string | null): string {
  if (!value) return "No date yet";
  const parsed = new Date(`${value}T00:00:00Z`);
  return Number.isNaN(parsed.getTime()) ? "Unknown date" : parsed.toLocaleDateString("en-GB", {
    day: "numeric", month: "short", year: "numeric", timeZone: "UTC",
  });
}
export function timestamp(value: string | null): string {
  if (!value) return "Not recorded";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? "Unknown time" : parsed.toLocaleString("en-GB", {
    timeZone: "Asia/Dhaka", day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit",
  });
}
export function duration(start: string, finish: string | null): string {
  if (!finish) return "In progress";
  const seconds = Math.max(0, Math.round((Date.parse(finish) - Date.parse(start)) / 1000));
  if (!Number.isFinite(seconds)) return "Unknown";
  return seconds < 60 ? `${seconds}s` : `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
}
export function safeSourceUrl(value: string): string | undefined {
  try { const u = new URL(value); return ["https:", "http:"].includes(u.protocol) && !u.username && !u.password ? u.href : undefined; }
  catch { return undefined; }
}
export const metricLabel = (key: string) => key.replaceAll("_", " ").replace(/^./, c => c.toUpperCase());
