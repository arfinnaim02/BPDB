import "server-only";
import type { Result } from "./types";

export function backendConfiguration(): { base: string; key: string } | null {
  const key = process.env.BACKEND_API_KEY;
  try {
    const url = new URL(process.env.BACKEND_URL || "http://127.0.0.1:8000");
    if (!key || url.username || url.password || url.search || url.hash ||
      !["http:", "https:"].includes(url.protocol)) return null;
    if (process.env.NODE_ENV === "production" && url.protocol !== "https:" &&
      !["localhost", "127.0.0.1", "[::1]"].includes(url.hostname)) return null;
    return { base: url.toString().replace(/\/$/, ""), key };
  } catch { return null; }
}

export async function backendResponse(path: string): Promise<Response | null> {
  const config = backendConfiguration();
  if (!config || !path.startsWith("/api/v1/")) return null;
  return fetch(`${config.base}${path}`, {
    headers: { "X-API-Key": config.key, Accept: "application/json" },
    cache: "no-store", redirect: "error", signal: AbortSignal.timeout(25000),
  });
}

export async function readApi<T>(path: string): Promise<Result<T>> {
  try {
    const response = await backendResponse(path);
    if (!response) return { ok: false, message: "Configure BACKEND_URL and BACKEND_API_KEY on the frontend server." };
    if (!response.ok) return { ok: false, message: response.status === 401 || response.status === 403
      ? "The API rejected the server credentials. Check BACKEND_API_KEY."
      : "The dataset service is unavailable. Check API readiness and collection logs." };
    return { ok: true, data: await response.json() as T };
  } catch {
    return { ok: false, message: "The API could not be reached in time. Check its address and availability, then retry." };
  }
}
