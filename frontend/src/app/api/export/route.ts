import { isAuthenticated } from "../../../lib/auth";
import { backendResponse } from "../../../lib/backend";
import { filters } from "../../../lib/filters";
export const dynamic = "force-dynamic";
export async function GET(request: Request): Promise<Response> {
  if (!await isAuthenticated()) return Response.json({ error: "Sign in required" }, { status: 401 });
  const url = new URL(request.url);
  const f = filters({ start_date: url.searchParams.get("start_date") ?? undefined, end_date: url.searchParams.get("end_date") ?? undefined });
  if (f.error) return Response.json({ error: f.error }, { status: 422 });
  const layout = url.searchParams.get("layout") === "evidence" ? "evidence" : "daily";
  const q = new URLSearchParams({ layout });
  if (f.start) q.set("start_date", f.start);
  if (f.end) q.set("end_date", f.end);
  try {
    const upstream = await backendResponse(`/api/v1/dataset/export.csv?${q}`);
    if (!upstream?.ok) return Response.json({ error: upstream?.status === 422
      ? "This export is too large. Narrow the date range or use the export CLI."
      : "Export unavailable. Check the API connection and server credentials." }, { status: upstream?.status === 422 ? 422 : 503 });
    const headers = new Headers({ "Content-Type": "text/csv; charset=utf-8", "Content-Disposition": `attachment; filename="${layout === "daily" ? "bpdb-master-daily.csv" : "bpdb-source-evidence.csv"}"`, "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff" });
    for (const name of ["X-Dataset-SHA256", "X-Exported-At", "X-Canonical-Dates", "X-Measurement-Rows"]) {
      const value = upstream.headers.get(name);
      if (value) headers.set(name, value);
    }
    return new Response(upstream.body, { headers });
  } catch { return Response.json({ error: "Export timed out or the service could not be reached. Try a smaller date range." }, { status: 503 }); }
}

